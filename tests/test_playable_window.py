"""The My aircraft window (§102) builds offscreen, and old saves load with no points."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from types import SimpleNamespace
from typing import Iterator

import pytest
from PySide6.QtWidgets import QApplication

from game.squadrons.squadron import Squadron


@pytest.fixture(scope="module", autouse=True)
def _qt_app() -> Iterator[QApplication]:
    app = QApplication.instance() or QApplication([])
    assert isinstance(app, QApplication)
    yield app


def test_the_window_opens_with_no_game_and_says_so() -> None:
    from qt_ui.windows.playable import PlayableAircraftDialog

    dialog = PlayableAircraftDialog(SimpleNamespace(game=None))
    assert dialog.windowTitle() == "My aircraft"
    assert [dialog.tabs.tabText(i) for i in range(dialog.tabs.count())] == [
        "Saved points",
        "Loadout",
        "DTC",
    ]
    assert dialog.selected is None
    assert dialog.empty.isVisibleTo(dialog)
    assert not dialog.splitter.isVisibleTo(dialog)


def test_a_squadron_saved_before_the_feature_has_no_points() -> None:
    squadron = Squadron.__new__(Squadron)
    squadron.__setstate__({"name": "VFA-83"})
    assert squadron.saved_points == []
