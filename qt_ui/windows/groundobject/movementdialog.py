"""Pick an armor detachment and a destination, preview the route, dispatch (§131).

Adapted from juanjux/dcs-escalation qt_ui/windows/groundobject/movementdialog.py
(LGPL-3.0). The map picker is not ported; a position is typed as coordinates.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from dcs import Point
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from game.coordinates import parse_latlng
from game.groundmovement.dispatch import dispatch_armor
from game.groundmovement.journey import GroundPosition
from game.groundmovement.orders import DestinationKind, MovementDestination
from game.groundmovement.planning import (
    armor_movement_options,
    movement_destination,
    preview_armor_movement,
)
from game.groundmovement.settings import METERS_PER_MILE
from game.server import EventStream
from game.sim.gameupdateevents import GameUpdateEvents
from game.theater.player import Player
from game.theater.theatergroundobject import IadsGroundObject

if TYPE_CHECKING:
    from game import Game
    from game.groundmovement.planning import ArmorMovementPreview
    from game.theater.controlpoint import ControlPoint

BLOCKED_STYLE = "QLabel { color: #f0b429; font-weight: bold; }"


class ArmorMovementDialog(QDialog):
    def __init__(
        self,
        game: Game,
        source_id: UUID,
        owner: Player,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.game = game
        self.turn = game.turn
        self.source_id = source_id
        self.owner = owner
        self.preview: ArmorMovementPreview | None = None
        self.is_sam = isinstance(game.db.tgos.get(source_id), IadsGroundObject)
        self.setWindowTitle("Move SAM site" if self.is_sam else "Move armor")
        self.setMinimumWidth(560)
        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "The whole site moves together, with its own trucks."
                if self.is_sam
                else "Pick the units to send. Trucks to tow the guns are added for you."
            )
        )
        options = armor_movement_options(game, source_id, owner)
        self.units: dict[int, QCheckBox] = {}
        holder = QWidget()
        rows = QVBoxLayout(holder)
        for unit in options.units:
            kind = "tows guns" if unit.can_tow else unit.mobility.replace("_", " ")
            checkbox = QCheckBox(f"{unit.name} ({kind})")
            checkbox.setEnabled(unit.selectable and not self.is_sam)
            checkbox.setChecked(self.is_sam)
            if not unit.selectable:
                checkbox.setToolTip("Already moving, or this unit cannot drive")
            checkbox.toggled.connect(self.invalidate)
            self.units[unit.id] = checkbox
            rows.addWidget(checkbox)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(holder)
        scroll.setMinimumHeight(150)
        scroll.setMaximumHeight(260)
        layout.addWidget(scroll)
        if not self.is_sam:
            select_row = QHBoxLayout()
            for title, checked in (("Select all", True), ("Clear", False)):
                button = QPushButton(title)
                button.clicked.connect(
                    lambda _=False, value=checked: self.select_all(value)
                )
                select_row.addWidget(button)
            layout.addLayout(select_row)
        for warning in options.warnings:
            text = QLabel(warning)
            text.setWordWrap(True)
            text.setStyleSheet(BLOCKED_STYLE)
            layout.addWidget(text)

        self.kind = QComboBox()
        for title, dest_kind in (
            (
                "A point on the map (stays there as its own group)",
                DestinationKind.POSITION,
            ),
            ("A friendly base (joins its reserve)", DestinationKind.BASE),
            ("A front line (reinforces the base behind it)", DestinationKind.FRONTLINE),
        ):
            if self.is_sam and dest_kind is not DestinationKind.POSITION:
                continue
            self.kind.addItem(title, dest_kind)
        layout.addWidget(self.kind)
        self.target = QComboBox()
        layout.addWidget(self.target)
        coordinates = QHBoxLayout()
        self.coordinates = QLineEdit()
        self.coordinates.setPlaceholderText(
            "Coordinates in friendly ground (copy them from the map)"
        )
        coordinates.addWidget(self.coordinates, 1)
        self.paste = QPushButton("Paste")
        self.paste.clicked.connect(
            lambda: self.coordinates.setText(QApplication.clipboard().text())
        )
        coordinates.addWidget(self.paste)
        layout.addLayout(coordinates)

        self.details = QLabel("Pick units and a destination, then preview the route.")
        self.details.setWordWrap(True)
        self.details.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.details)
        layout.addWidget(
            QLabel("Columns move after each mission, one turn's distance at a time.")
        )
        buttons = QHBoxLayout()
        self.preview_button = QPushButton("Preview route")
        self.preview_button.setEnabled(options.enabled)
        self.preview_button.clicked.connect(self.calculate)
        self.dispatch_button = QPushButton("Send")
        self.dispatch_button.setProperty("style", "btn-success")
        self.dispatch_button.setEnabled(False)
        self.dispatch_button.clicked.connect(self.dispatch)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        for button in (self.preview_button, self.dispatch_button, cancel):
            buttons.addWidget(button)
        layout.addLayout(buttons)
        self.kind.currentIndexChanged.connect(self.change_kind)
        self.target.currentIndexChanged.connect(self.invalidate)
        self.coordinates.textChanged.connect(self.invalidate)
        self.change_kind()

    def select_all(self, checked: bool) -> None:
        for checkbox in self.units.values():
            if checkbox.isEnabled():
                checkbox.setChecked(checked)

    def invalidate(self) -> None:
        self.preview = None
        self.dispatch_button.setEnabled(False)
        self.set_details("Preview the route before sending.")

    def set_details(self, text: str, *, blocked: bool = False) -> None:
        self.details.setStyleSheet(BLOCKED_STYLE if blocked else "")
        self.details.setText(f"Can't move: {text}" if blocked else text)

    def change_kind(self) -> None:
        kind = self.kind.currentData()
        position = kind is DestinationKind.POSITION
        self.target.setVisible(not position)
        self.coordinates.setVisible(position)
        self.paste.setVisible(position)
        self.target.clear()
        if not position:
            for base in sorted(self.game.theater.controlpoints, key=lambda cp: cp.name):
                opponents: list[ControlPoint | None] = (
                    list(base.front_lines)
                    if kind is DestinationKind.FRONTLINE
                    else [None]
                )
                for opponent in opponents:
                    try:
                        destination = movement_destination(
                            self.game,
                            self.owner,
                            kind,
                            base_id=base.id,
                            opposing_base_id=(
                                opponent.id if opponent is not None else None
                            ),
                        )
                    except (ValueError, PermissionError):
                        continue
                    title = (
                        f"{base.name} / {opponent.name}"
                        if opponent is not None
                        else base.name
                    )
                    self.target.addItem(title, destination)
        self.invalidate()

    def selected_ids(self) -> list[int]:
        return [i for i, checkbox in self.units.items() if checkbox.isChecked()]

    def destination(self) -> MovementDestination:
        kind = self.kind.currentData()
        if kind is not DestinationKind.POSITION:
            destination = self.target.currentData()
            if not isinstance(destination, MovementDestination):
                raise ValueError("there is no destination of that kind")
            return destination
        latlng = parse_latlng(self.coordinates.text())
        if latlng is None:
            raise ValueError("enter coordinates, or paste them from the map")
        point = Point.from_latlng(latlng, self.game.theater.terrain)
        return movement_destination(
            self.game, self.owner, kind, position=GroundPosition(point.x, point.y)
        )

    def calculate(self) -> None:
        self.invalidate()
        try:
            if self.game.turn != self.turn:
                raise ValueError("the turn changed; close and reopen this window")
            result = preview_armor_movement(
                self.game,
                self.source_id,
                self.owner,
                self.selected_ids(),
                self.destination(),
            )
        except (ValueError, PermissionError) as exc:
            self.set_details(str(exc), blocked=True)
            return
        self.preview = result
        added = set(result.manifest.unit_ids) - set(self.selected_ids())
        trucks = ", ".join(self.units[i].text() for i in sorted(added)) or "none"
        lines = [
            f"{len(result.manifest.unit_ids)} units move, "
            f"{len(result.remaining_unit_ids)} stay.",
            f"Trucks added to tow: {trucks}.",
            f"Road {result.road_distance_m / METERS_PER_MILE:.0f} mi, "
            f"off-road {result.offroad_distance_m / METERS_PER_MILE:.0f} mi; "
            f"about {result.arrival_in_turns} turn(s).",
            "A towed gun is lost if its truck is destroyed.",
            *result.warnings,
        ]
        self.set_details("\n".join(lines))
        self.dispatch_button.setEnabled(True)

    def dispatch(self) -> None:
        if self.preview is None:
            return
        self.dispatch_button.setEnabled(False)
        events = GameUpdateEvents()
        try:
            if self.game.turn != self.turn:
                raise ValueError("the turn changed; preview again")
            dispatch_armor(
                self.game,
                self.source_id,
                self.owner,
                self.selected_ids(),
                self.preview.destination,
                events,
            )
        except (ValueError, PermissionError) as exc:
            self.preview = None
            self.set_details(str(exc), blocked=True)
            return
        EventStream.put_nowait(events)
        self.accept()
