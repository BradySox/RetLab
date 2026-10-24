"""The mission status shows in the main window and hands the map back when done."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from unittest.mock import MagicMock

import pytest

from PySide6.QtWidgets import QApplication, QPushButton

from game.server import EventStream
from qt_ui import liberation_install
from qt_ui.windows.GameUpdateSignal import GameUpdateSignal
from qt_ui.widgets.missionstatuspanel import MissionStatusPanel


def test_abort_finishes_the_panel_and_stops_listening(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(liberation_install, "skyeye_autostart", lambda: True)
    monkeypatch.setattr(GameUpdateSignal, "get_instance", lambda: MagicMock())
    monkeypatch.setattr(EventStream, "put_nowait", lambda self, events: None)
    _app = QApplication.instance() or QApplication([])
    game = MagicMock()
    game.db.flights.objects.items.return_value = []
    game.theater.controlpoints = []
    sim = MagicMock()
    panel = MissionStatusPanel(game, sim)
    finished: list[bool] = []
    panel.finished.connect(lambda: finished.append(True))
    buttons = [button.text() for button in panel.findChildren(QPushButton)]  # type: ignore[var-annotated]
    panel.reset_game_state()
    assert finished == [True]
    sim.wait_for_debriefing.return_value.stop.assert_called()
    assert not panel._listening
    assert "SkyEye log" in buttons
    panel.deleteLater()
