from __future__ import annotations

import threading
from typing import Optional

from PySide6.QtCore import QObject, Qt, Signal, Slot

from game import Game
from game.debriefing import Debriefing
from game.game import TurnState


class GameUpdateSignal(QObject):
    instance = None
    gameupdated = Signal(Game)
    budgetupdated = Signal(Game)
    game_state_changed = Signal(TurnState)
    debriefingReceived = Signal(Debriefing)
    ato_changed = Signal()
    saved_points_changed = Signal()
    # The map's saved-point routes run on the web server's thread; this hands
    # their change notice to the GUI thread (features doc §8).
    _saved_points_relay = Signal()

    game_loaded = Signal(Game)

    def __init__(self):
        super(GameUpdateSignal, self).__init__()
        GameUpdateSignal.instance = self

        self.game_loaded.connect(self.updateGame)
        self._saved_points_relay.connect(
            self._relay_saved_points_changed, Qt.ConnectionType.QueuedConnection
        )

    def notify_saved_points_changed(self) -> None:
        """Emits saved_points_changed on the GUI thread; callable from any thread."""
        if threading.current_thread() is threading.main_thread():
            self.saved_points_changed.emit()
        else:
            self._saved_points_relay.emit()

    @Slot()
    def _relay_saved_points_changed(self) -> None:
        self.saved_points_changed.emit()

    def updateGame(self, game: Optional[Game]):
        # noinspection PyUnresolvedReferences
        self.gameupdated.emit(game)

    def updateBudget(self, game: Game):
        # noinspection PyUnresolvedReferences
        self.budgetupdated.emit(game)

    def sendDebriefing(self, debriefing: Debriefing) -> None:
        # noinspection PyUnresolvedReferences
        self.debriefingReceived.emit(debriefing)

    def gameStateChanged(self, state: TurnState):
        if state in (TurnState.WIN, TurnState.LOSS):
            # noinspection PyUnresolvedReferences
            self.game_state_changed.emit(state)

    def atoChanged(self) -> None:
        self.ato_changed.emit()

    @staticmethod
    def get_instance() -> GameUpdateSignal:
        return GameUpdateSignal.instance
