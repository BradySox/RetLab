import html
import logging
from typing import Callable, Dict, TypeVar

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QCloseEvent, QIcon
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from game.debriefing import Debriefing
from game.retlab.cruise_raids import debrief_expenditures
from game.retlab.flight_grades import FlightCard, Grade
from game.theater import Player
from qt_ui.theme import RETRIBUTION_DARK
from qt_ui.windows.GameUpdateSignal import GameUpdateSignal

T = TypeVar("T")

#: Rows a lost-units list shows before it scrolls.
LOSS_ROWS_BEFORE_SCROLL = 10
#: Rows a lost-units list keeps when the window is squeezed onto a small screen.
LOSS_ROWS_MINIMUM = 3
#: The report cards column, in logical pixels. Its height follows the left column.
CARDS_WIDTH = 500
CARDS_HEIGHT = 420


class ContentSizedScrollArea(QScrollArea):
    """A scroll area that asks for its content's size, up to a cap.

    A plain QScrollArea reports a small fixed hint and shrinks to two rows before
    anything else in a layout gives way, and without setWidgetResizable its
    content keeps its own narrow width inside an empty frame.
    """

    def __init__(self, content: QWidget, max_height: int, width: int = 0) -> None:
        super().__init__()
        self.max_height = max_height
        self.fixed_width = width
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setWidget(content)

    def sizeHint(self) -> QSize:
        content = self.widget().sizeHint()
        bar = self.verticalScrollBar().sizeHint().width()
        return QSize(
            self.fixed_width or content.width() + bar,
            min(content.height(), self.max_height),
        )


class LossGrid(QGridLayout):
    def __init__(self, debriefing: Debriefing, player: Player) -> None:
        super().__init__()
        self.rows = 0
        self.setContentsMargins(4, 2, 4, 2)
        self.setHorizontalSpacing(12)
        self.setVerticalSpacing(2)
        self.setColumnStretch(0, 1)

        self.add_loss_rows(
            debriefing.aircraft_losses_by_type(player), lambda u: u.display_name
        )
        self.add_loss_rows(
            debriefing.front_line_losses_by_type(player), lambda u: str(u)
        )
        self.add_loss_rows(
            debriefing.motorpool_losses_by_type(player),
            lambda u: f"{u} from motorpool",
        )
        self.add_loss_rows(
            debriefing.convoy_losses_by_type(player), lambda u: f"{u} from convoy"
        )
        self.add_loss_rows(
            debriefing.cargo_ship_losses_by_type(player),
            lambda u: f"{u} from cargo ship",
        )
        self.add_loss_rows(
            debriefing.airlift_losses_by_type(player), lambda u: f"{u} from airlift"
        )
        self.add_loss_rows(debriefing.ground_object_losses_by_type(player), lambda u: u)
        self.add_loss_rows(debriefing.scenery_losses_by_type(player), lambda u: u)

        # TODO: Display dead ground object units and runways.

        if not self.rows:
            self.addWidget(QLabel("None"), 0, 0)
            self.rows = 1
        # Keeps a short list at the top of a box taller than it needs.
        self.setRowStretch(self.rows, 1)

    def add_loss_rows(self, losses: Dict[T, int], make_name: Callable[[T], str]):
        for unit_type, count in losses.items():
            try:
                name = make_name(unit_type)
            except AttributeError:
                logging.exception(f"Could not make unit name for {unit_type}")
                name = unit_type.id
            self.addWidget(QLabel(name), self.rows, 0)
            self.addWidget(
                QLabel(str(count)), self.rows, 1, Qt.AlignmentFlag.AlignRight
            )
            self.rows += 1


class ScrollingCasualtyReportContainer(QGroupBox):
    def __init__(self, debriefing: Debriefing, player: Player) -> None:
        country = (
            debriefing.player_country if player.is_blue else debriefing.enemy_country
        )
        super().__init__(f"{country}'s lost units:")
        grid = LossGrid(debriefing, player)
        scroll_content = QWidget()
        scroll_content.setLayout(grid)
        full_height = scroll_content.sizeHint().height()
        row_height = full_height / grid.rows
        self.scroll_area = ContentSizedScrollArea(
            scroll_content,
            max_height=min(full_height, round(row_height * LOSS_ROWS_BEFORE_SCROLL)),
        )
        self.scroll_area.setMinimumHeight(
            min(full_height, round(row_height * LOSS_ROWS_MINIMUM))
        )
        layout = QVBoxLayout()
        layout.addWidget(self.scroll_area)
        self.setLayout(layout)


class MissionImpactGrid(QGridLayout):
    def __init__(self, debriefing: Debriefing) -> None:
        super().__init__()
        for row, (label, value) in enumerate(self._rows_for(debriefing)):
            self.addWidget(QLabel(f"<b>{label}</b>"), row, 0)
            self.addWidget(QLabel(value), row, 1)

    @staticmethod
    def _rows_for(debriefing: Debriefing) -> list[tuple[str, str]]:
        blue_losses = debriefing.loss_counts(Player.BLUE)
        red_losses = debriefing.loss_counts(Player.RED)
        captured = [
            capture.control_point.name
            for capture in debriefing.base_captures
            if capture.captured_by_player.is_blue
        ]
        lost = [
            capture.control_point.name
            for capture in debriefing.base_captures
            if capture.captured_by_player.is_red
        ]
        runways = [airfield.name for airfield in debriefing.damaged_runways]

        rows = [
            (
                "Mission status",
                (
                    "Mission ended normally"
                    if debriefing.state_data.mission_ended
                    else "Mission ended early or state data was incomplete"
                ),
            ),
            (
                "Bases captured",
                ", ".join(captured) if captured else "None",
            ),
            (
                "Bases lost",
                ", ".join(lost) if lost else "None",
            ),
            (
                "Runways damaged",
                ", ".join(runways) if runways else "None",
            ),
            (
                f"{debriefing.player_country} losses",
                f"{blue_losses.aircraft} aircraft, {blue_losses.front_line} front-line "
                f"units, {blue_losses.ground_objects} site units, {blue_losses.bases_lost} bases",
            ),
            (
                f"{debriefing.enemy_country} losses",
                f"{red_losses.aircraft} aircraft, {red_losses.front_line} front-line "
                f"units, {red_losses.ground_objects} site units, {red_losses.bases_lost} bases",
            ),
        ]
        return rows


class MissionImpactContainer(QGroupBox):
    def __init__(self, debriefing: Debriefing) -> None:
        super().__init__("Mission Impact")
        layout = QVBoxLayout()
        layout.addLayout(MissionImpactGrid(debriefing))
        self.setLayout(layout)


class RescueReport(QGroupBox):
    """Lists the downed pilots CSAR recovered this mission, per coalition.

    Rescues are the counterpart to the casualty report: an airframe is still lost,
    but the pilot comes back, so they are reported separately rather than folded
    into the loss grid.
    """

    def __init__(self, debriefing: Debriefing) -> None:
        super().__init__("Pilots recovered by CSAR:")
        layout = QGridLayout()
        self.setLayout(layout)

        any_rescues = False
        for player in (Player.BLUE, Player.RED):
            rescued = debriefing.rescued_pilots_for(player)
            if not rescued:
                continue
            any_rescues = True
            country = (
                debriefing.player_country
                if player.is_blue
                else debriefing.enemy_country
            )
            layout.addWidget(QLabel(f"<b>{country}</b>"), layout.rowCount(), 0)
            for pilot in rescued:
                row = layout.rowCount()
                layout.addWidget(QLabel(pilot.name), row, 0)
                layout.addWidget(QLabel(f"{pilot.squadron} ({pilot.aircraft})"), row, 1)

        if not any_rescues:
            layout.addWidget(QLabel("No pilots were recovered."), 0, 0)


class FlightReportCard(QWidget):
    """One flight: the job and its grade, who flew it, then the findings."""

    GRADE_COLORS = {
        Grade.ABOVE_AVERAGE: RETRIBUTION_DARK.success,
        Grade.AVERAGE: RETRIBUTION_DARK.text_dim,
        Grade.BELOW_AVERAGE: RETRIBUTION_DARK.warning,
        Grade.UNSAT: RETRIBUTION_DARK.danger,
    }

    def __init__(self, card: FlightCard) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        headline = QLabel(f"<b>{html.escape(card.headline)}</b>")
        headline.setWordWrap(True)
        grade = QLabel(
            f"<b style='color:{self.GRADE_COLORS[card.grade]}'>"
            f"{card.grade.value}</b>"
        )
        top = QHBoxLayout()
        top.addWidget(headline, 1)
        top.addWidget(grade, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(top)

        who = " (player)" if card.player else ""
        detail = QLabel(
            f"<span style='color:{RETRIBUTION_DARK.text_dim}'>"
            f"{html.escape(card.detail)}{who}</span>"
        )
        detail.setWordWrap(True)
        layout.addWidget(detail)

        for text in [f"Fault: {fault}" for fault in card.faults] + list(card.lines):
            label = QLabel(text)
            label.setWordWrap(True)
            layout.addWidget(label)


class FlightReportCards(QGroupBox):
    """§108: one graded card per blue flight, player flights first."""

    def __init__(self, cards: list[FlightCard]) -> None:
        super().__init__("Flight report cards")
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setSpacing(14)
        for card in cards:
            body_layout.addWidget(FlightReportCard(card))
        body_layout.addStretch(1)
        self.scroll_area = ContentSizedScrollArea(
            body, max_height=CARDS_HEIGHT, width=CARDS_WIDTH
        )
        self.scroll_area.setMinimumHeight(160)
        layout = QVBoxLayout()
        layout.addWidget(self.scroll_area)
        self.setLayout(layout)


class QDebriefingWindow(QDialog):
    """Two columns: the mission summary and losses, then the report cards.

    Only the lost-units lists and the cards scroll. Everything else is a fixed
    height, so a single column of it is taller than a 1440p screen.
    """

    def __init__(self, debriefing: Debriefing):
        super(QDebriefingWindow, self).__init__()
        self.debriefing = debriefing

        self.setModal(True)
        self.setWindowTitle("Debriefing")
        self.setMinimumSize(300, 200)
        self.setWindowIcon(QIcon("./resources/icon.png"))

        layout = QVBoxLayout()
        self.setLayout(layout)

        title = QLabel("<b>Casualty report</b>")
        layout.addWidget(title)

        columns = QHBoxLayout()
        layout.addLayout(columns, 1)
        summary = QVBoxLayout()
        columns.addLayout(summary, 3)

        impact = MissionImpactContainer(debriefing)
        summary.addWidget(impact)

        # Campaign consequences -- the per-turn Sitrep (losses, base captures,
        # CSAR recoveries, MIA aviators, enemy C2 status, victory progress,
        # squadron arrivals). The engine has computed this digest every turn
        # since §29, but it rendered only on the in-cockpit kneeboard SITREP
        # band; the debrief showed none of it (2026-07-18 UI audit, the top Qt
        # finding).
        sitrep = getattr(debriefing.game, "last_sitrep", None)
        if sitrep is not None and sitrep.has_news:
            consequences = QGroupBox("Campaign consequences")
            consequences_layout = QVBoxLayout()
            for line in sitrep.kneeboard_lines():
                line_label = QLabel(line)
                line_label.setWordWrap(True)
                consequences_layout.addWidget(line_label)
            consequences.setLayout(consequences_layout)
            summary.addWidget(consequences)

        # Cruise missile expenditure (shown post-debit, so "remaining" is the
        # campaign magazine going into next turn; enemy remainders stay hidden).
        expenditures = debrief_expenditures(debriefing.game, debriefing)
        if expenditures:
            expenditure_box = QGroupBox("Cruise missiles expended:")
            expenditure_grid = QGridLayout()
            for row, (group_name, fired, remaining) in enumerate(expenditures):
                expenditure_grid.addWidget(QLabel(group_name), row, 0)
                if remaining is None:
                    detail = f"{fired} fired"
                else:
                    detail = f"{fired} fired, {remaining} remaining"
                expenditure_grid.addWidget(QLabel(detail), row, 1)
            expenditure_box.setLayout(expenditure_grid)
            summary.addWidget(expenditure_box)

        summary.addWidget(RescueReport(debriefing))

        losses = QHBoxLayout()
        summary.addLayout(losses, 1)
        self.player_lost_units = ScrollingCasualtyReportContainer(
            debriefing, player=Player.BLUE
        )
        losses.addWidget(self.player_lost_units, 1)
        self.enemy_lost_units = ScrollingCasualtyReportContainer(
            debriefing, player=Player.RED
        )
        losses.addWidget(self.enemy_lost_units, 1)

        cards = getattr(debriefing.game, "last_flight_cards", [])
        if cards:
            columns.addWidget(FlightReportCards(cards), 2)

        okay = QPushButton("Okay")
        okay.clicked.connect(self.close)
        layout.addWidget(okay)

    def closeEvent(self, event: QCloseEvent) -> None:
        super().closeEvent(event)
        state = self.debriefing.game.check_win_loss()
        GameUpdateSignal.get_instance().gameStateChanged(state)
