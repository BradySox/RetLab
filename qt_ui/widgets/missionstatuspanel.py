from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PySide6 import QtCore
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QMovie, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressDialog,
    QPushButton,
    QTextBrowser,
    QWidget,
)
from jinja2 import Environment, FileSystemLoader, select_autoescape

from game import Game
from game.ato.flightstate import Uninitialized
from game.debriefing import Debriefing
from game.finaldebriefing import final_debriefing
from game.theater import Player
from game.profiling import logged_duration
from game.retlab.skyeye_launcher import stop_skyeye
from game.server import EventStream
from game.sim import GameUpdateEvents
from qt_ui import liberation_install
from qt_ui.simcontroller import SimController
from qt_ui.windows.GameUpdateSignal import GameUpdateSignal


class DebriefingFileWrittenSignal(QObject):
    instance = None
    debriefingReceived = Signal(Debriefing)

    def __init__(self):
        super(DebriefingFileWrittenSignal, self).__init__()
        DebriefingFileWrittenSignal.instance = self

    def sendDebriefing(self, debriefing: Debriefing):
        self.debriefingReceived.emit(debriefing)

    @staticmethod
    def get_instance() -> DebriefingFileWrittenSignal:
        return DebriefingFileWrittenSignal.instance


DebriefingFileWrittenSignal()


class MissionStatusPanel(QWidget):
    """The mission's losses and Accept/Abort, shown in the map's place while it runs."""

    #: The mission was accepted or aborted; the main window brings the map back.
    finished = Signal()

    def __init__(
        self,
        game: Game,
        sim_controller: SimController,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent=parent)
        self.game = game
        self.sim_controller = sim_controller

        self.initUi()
        DebriefingFileWrittenSignal.get_instance().debriefingReceived.connect(
            self.updateLayout
        )
        self._listening = True
        self.wait_thread = sim_controller.wait_for_debriefing(
            lambda debriefing: self.on_debriefing_update(debriefing)
        )

    def initUi(self):
        self.layout = QGridLayout()

        header = QLabel(self)
        header.setGeometry(0, 0, 655, 106)
        pixmap = QPixmap("./resources/ui/conflict.png")
        header.setPixmap(pixmap)
        self.layout.addWidget(header, 0, 1)

        self.gridLayout = QGridLayout()

        jinja = Environment(
            loader=FileSystemLoader("resources/ui/templates"),
            autoescape=select_autoescape(
                disabled_extensions=("",),
                default_for_string=True,
                default=True,
            ),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.instructions_text = QTextBrowser()
        self.instructions_text.setHtml(
            jinja.get_template("mission_start_EN.j2").render()
        )
        self.instructions_text.setOpenExternalLinks(True)
        self.gridLayout.addWidget(self.instructions_text, 1, 0)

        progress = QLabel("")
        progress.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        progress_bar = QMovie("./resources/ui/loader.gif")
        progress.setMovie(progress_bar)

        self.actions = QGroupBox("Actions :")
        self.actions_layout = QHBoxLayout()
        self.actions.setLayout(self.actions_layout)

        self.manually_submit = QPushButton("Manually Submit [Advanced users]")
        self.manually_submit.clicked.connect(self.submit_manually)
        self.actions_layout.addWidget(self.manually_submit)
        self.cancel = QPushButton("Abort mission")
        self.cancel.clicked.connect(self.reset_game_state)
        self.actions_layout.addWidget(self.cancel)
        self._add_skyeye_log_button(self.actions_layout)
        self.gridLayout.addWidget(self.actions, 2, 0)

        self.actions2 = QGroupBox("Actions :")
        self.actions2_layout = QHBoxLayout()
        self.actions2.setLayout(self.actions2_layout)
        self.manually_submit2 = QPushButton("Manually Submit [Advanced users]")
        self.manually_submit2.clicked.connect(self.submit_manually)
        self.actions2_layout.addWidget(self.manually_submit2)
        self.cancel2 = QPushButton("Abort mission")
        self.cancel2.clicked.connect(self.reset_game_state)
        self.actions2_layout.addWidget(self.cancel2)
        self._add_skyeye_log_button(self.actions2_layout)
        self.proceed = QPushButton("Accept results")
        self.proceed.setProperty("style", "btn-success")
        self.proceed.clicked.connect(self.process_debriefing)
        self.actions2_layout.addWidget(self.proceed)

        progress_bar.start()
        self.layout.addLayout(self.gridLayout, 1, 1)
        # A centered column the old window's width, the rest of the map area empty.
        self.layout.setColumnStretch(0, 1)
        self.layout.setColumnStretch(2, 1)
        self.layout.setColumnMinimumWidth(1, 655)
        self.layout.setRowStretch(2, 1)
        self.setLayout(self.layout)

    def _add_skyeye_log_button(self, layout: QHBoxLayout) -> None:
        if not liberation_install.skyeye_autostart():
            return
        button = QPushButton("SkyEye log")
        button.clicked.connect(self.show_skyeye_log)
        layout.addWidget(button)

    def show_skyeye_log(self) -> None:
        from qt_ui.windows.SkyEyeLogDialog import SkyEyeLogDialog

        SkyEyeLogDialog(self).show()

    @staticmethod
    def add_update_row(
        description: str, blue: int, red: int, layout: QGridLayout
    ) -> None:
        row = layout.rowCount()
        layout.addWidget(QLabel(f"<b>{description}</b>"), row, 0)
        layout.addWidget(QLabel(f"{blue}"), row, 1)
        layout.addWidget(QLabel(f"{red}"), row, 2)

    def updateLayout(self, debriefing: Debriefing) -> None:
        updateBox = QGroupBox("Mission status")
        update_layout = QGridLayout()
        updateBox.setLayout(update_layout)
        self.debriefing = debriefing

        blue = debriefing.loss_counts(Player.BLUE)
        red = debriefing.loss_counts(Player.RED)

        update_layout.addWidget(
            QLabel(f"<b>{debriefing.player_country} (OwnFor)</b>"), 0, 1
        )
        update_layout.addWidget(
            QLabel(f"<b>{debriefing.enemy_country} (OpFor)</b>"), 0, 2
        )

        rows = [
            ("Aircraft lost", blue.aircraft, red.aircraft),
            ("Front line units lost", blue.front_line, red.front_line),
            ("Motorpool units lost", blue.motorpool, red.motorpool),
            ("Convoy units lost", blue.convoy, red.convoy),
            ("Shipping cargo lost", blue.cargo_ships, red.cargo_ships),
            ("Airlift cargo lost", blue.airlift_cargo, red.airlift_cargo),
            ("Ground Objects lost", blue.ground_objects, red.ground_objects),
            ("Scenery Objects lost", blue.scenery, red.scenery),
            ("Bases lost", blue.bases_lost, red.bases_lost),
            ("Runways destroyed", blue.runways_destroyed, red.runways_destroyed),
            ("Pilots rescued (CSAR)", blue.pilots_rescued, red.pilots_rescued),
        ]
        for label, blue_count, red_count in rows:
            self.add_update_row(label, blue_count, red_count, update_layout)

        # Clear previous content of the window
        for i in reversed(range(self.gridLayout.count())):
            try:
                self.gridLayout.itemAt(i).widget().setParent(None)
            except:
                logging.exception("Failed to clear window")

        # Set new window content
        self.gridLayout.addWidget(updateBox, 0, 0)

        if not debriefing.state_data.mission_ended:
            self.gridLayout.addWidget(QLabel("<b>Mission is being played</b>"), 1, 0)
            self.gridLayout.addWidget(self.actions, 2, 0)
        else:
            self.gridLayout.addWidget(QLabel("<b>Mission is over</b>"), 1, 0)
            self.gridLayout.addWidget(self.actions2, 2, 0)

    def on_debriefing_update(self, debriefing: Debriefing) -> None:
        try:
            logging.info("On Debriefing update")
            logging.debug(debriefing)
            DebriefingFileWrittenSignal.get_instance().sendDebriefing(debriefing)
        except Exception:
            logging.exception("Got an error while sending debriefing")

    def process_debriefing(self):
        if self._process_turn():
            stop_skyeye()
            self._finish()

    def _process_turn(self) -> bool:
        # Turn processing blocks the UI for a while; without feedback the user
        # can't tell whether the mission end was missed or is just being
        # processed. Show an indeterminate busy dialog meanwhile.
        progress = QProgressDialog(
            "End of Mission Detected, processing Mission Data",
            "",
            0,
            0,
            self,
        )
        progress.setWindowTitle("Processing")
        progress.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)
        progress.setCancelButton(None)
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.show()
        QApplication.processEvents()
        try:
            with logged_duration("Turn processing"):
                debriefing = self._debriefing_to_commit()
                if debriefing is None:
                    logging.error("No mission results to commit; turn not processed.")
                    return False
                self.debriefing = debriefing
                self.sim_controller.process_results(debriefing)
                self.game.pass_turn()

                GameUpdateSignal.get_instance().sendDebriefing(debriefing)
                GameUpdateSignal.get_instance().updateGame(self.game)
        finally:
            progress.close()
        return True

    def _debriefing_to_commit(self) -> Optional[Debriefing]:
        """Re-read state.json now rather than trusting the watcher's snapshot.

        The poll thread stops at the first state.json carrying ``mission_ended``,
        which can be a stale file from the previous mission -- see
        game/finaldebriefing.py for the flown case where that silently dropped a
        whole sortie's strike kills.
        """
        return final_debriefing(
            getattr(self, "debriefing", None),
            lambda: self.sim_controller.debrief_current_state(
                Path("state.json"), force_end=True
            ),
        )

    def _stop_listening(self) -> None:
        if self.wait_thread is not None:
            self.wait_thread.stop()
        if self._listening:
            self._listening = False
            DebriefingFileWrittenSignal.get_instance().debriefingReceived.disconnect(
                self.updateLayout
            )

    def _finish(self) -> None:
        # Disconnected here: a panel left listening rebuilt its layout on every
        # later mission's updates.
        self._stop_listening()
        self.finished.emit()

    def submit_manually(self):
        file = QFileDialog.getOpenFileName(
            self,
            "Select the mission results file (state.json)",
            filter="json(*.json)",
            dir=".",
        )
        if file[0] != "":
            logging.debug("Processing manually submitted %s", file[0])
            # Stop the current waiting thread as we manually submit the results
            self.wait_thread.stop()
            self.on_debriefing_update(
                self.sim_controller.debrief_current_state(Path(file[0]), force_end=True)
            )

    def reset_game_state(self):
        # Not stop_skyeye(): aborting to replan and Take off again kept killing a
        # SkyEye the player was mid-flight with (2026-10-20).
        self.sim_controller.set_game(self.game)
        events = GameUpdateEvents()
        for _, f in self.game.db.flights.objects.items():
            f.state = Uninitialized(f, self.game.settings)
            events.update_flight(f)
        for cp in self.game.theater.controlpoints:
            cp.release_parking_slots()
        GameUpdateSignal.get_instance().updateGame(self.game)
        EventStream().put_nowait(events)
        self._finish()
