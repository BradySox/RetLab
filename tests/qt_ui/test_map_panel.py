"""The map is closed while a mission runs, its status shown instead (row B267)."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from typing import Iterator

import pytest
from PySide6.QtWidgets import QApplication, QWidget

from qt_ui.widgets.map.mappanel import MapPanel


class CountingFactory:
    def __init__(self) -> None:
        self.built: list[QWidget] = []

    def __call__(self) -> QWidget:
        view = QWidget()
        self.built.append(view)
        return view


@pytest.fixture
def factory() -> CountingFactory:
    return CountingFactory()


@pytest.fixture
def panel(factory: CountingFactory) -> Iterator[MapPanel]:
    _app = QApplication.instance() or QApplication([])
    panel = MapPanel(factory)
    panel.show()
    yield panel
    panel.close()
    panel.deleteLater()


def test_the_map_is_built_and_shown_at_start(
    panel: MapPanel, factory: CountingFactory
) -> None:
    assert len(factory.built) == 1
    assert not panel.released
    assert panel.currentWidget() is factory.built[0]


def test_the_status_replaces_the_map_and_the_map_is_rebuilt_after(
    panel: MapPanel, factory: CountingFactory
) -> None:
    first = factory.built[0]
    status = QWidget()
    panel.release(status)
    during = (panel.released, panel.currentWidget() is status)
    gone = panel.indexOf(first) == -1
    panel.restore()
    assert during == (True, True)
    assert gone
    assert panel.indexOf(status) == -1
    assert len(factory.built) == 2
    assert panel.currentWidget() is factory.built[1]
    assert panel.count() == 2


def test_release_without_status_shows_the_note(panel: MapPanel) -> None:
    panel.release()
    assert panel.currentWidget() is panel.placeholder


def test_release_and_restore_are_idempotent(
    panel: MapPanel, factory: CountingFactory
) -> None:
    panel.release()
    panel.release()
    released = panel.released
    panel.restore()
    panel.restore()
    assert released
    assert len(factory.built) == 2
    assert panel.count() == 2
