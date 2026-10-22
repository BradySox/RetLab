"""The map is hidden while the mission window is open and always comes back (row B267)."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from typing import Iterator

import pytest
from PySide6.QtWidgets import QApplication, QWidget

from qt_ui.widgets.map.mappanel import MapPanel, map_released


@pytest.fixture
def panel() -> Iterator[MapPanel]:
    _app = QApplication.instance() or QApplication([])
    map_view = QWidget()
    panel = MapPanel(map_view)
    panel.show()
    yield panel
    panel.close()
    panel.deleteLater()


def test_the_map_is_shown_by_default(panel: MapPanel) -> None:
    assert not panel.released
    assert panel.map_view.isVisible()
    assert not panel.placeholder.isVisible()


def test_the_map_is_hidden_inside_the_block_and_shown_after(panel: MapPanel) -> None:
    with map_released(panel):
        during = (panel.released, panel.map_view.isVisible())
        assert panel.placeholder.isVisible()
    assert during == (True, False)
    assert (panel.released, panel.map_view.isVisible()) == (False, True)


def test_the_map_comes_back_when_the_block_raises(panel: MapPanel) -> None:
    with pytest.raises(RuntimeError):
        with map_released(panel):
            raise RuntimeError("debrief failed")
    assert panel.map_view.isVisible()


def test_release_and_restore_are_idempotent(panel: MapPanel) -> None:
    panel.release()
    panel.release()
    released = panel.released
    panel.restore()
    panel.restore()
    assert released
    assert panel.map_view.isVisible()


def test_no_panel_is_a_no_op() -> None:
    ran = False
    with map_released(None):
        ran = True
    assert ran
