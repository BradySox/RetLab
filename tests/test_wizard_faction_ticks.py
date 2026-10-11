"""New game wizard: a unit unticked on the faction page stays unticked.

Adding a unit rebuilds the tick boxes, and the rebuild used to tick every one
again. Ported from CleeeCATCH/dcs-retribution.
"""

from __future__ import annotations

import inspect
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from typing import Any, Iterator

import pytest

from game import persistency
from game.factions import FACTIONS


@pytest.fixture(scope="module")
def qapp() -> Iterator[Any]:
    from PySide6.QtWidgets import QApplication

    yield QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _init_persistency(tmp_path_factory: pytest.TempPathFactory) -> None:
    persistency.setup(
        str(tmp_path_factory.mktemp("saved_games")),
        prefer_liberation_payloads=False,
        port=0,
    )


def test_rebuilding_the_same_faction_keeps_unticked_units(qapp: Any) -> None:
    from qt_ui.windows.newgame.WizardPages.QFactionSelection import QFactionUnits

    faction = FACTIONS["Bluefor Modern"]
    page = QFactionUnits(faction)
    name = sorted(page.checkboxes)[0]
    page.checkboxes[name].setChecked(False)

    page.updateFaction(faction)

    assert not page.checkboxes[name].isChecked()
    others = [cb for key, cb in page.checkboxes.items() if key != name]
    assert others and all(cb.isChecked() for cb in others)


def test_another_faction_starts_fully_ticked(qapp: Any) -> None:
    from qt_ui.windows.newgame.WizardPages.QFactionSelection import QFactionUnits

    page = QFactionUnits(FACTIONS["Bluefor Modern"])
    for cb in page.checkboxes.values():
        cb.setChecked(False)

    page.updateFaction(FACTIONS["Russia 2010"])

    assert all(cb.isChecked() for cb in page.checkboxes.values())


def test_the_start_date_calendar_is_never_disabled() -> None:
    """The stylesheet draws a disabled calendar like an enabled one, so a click on
    it did nothing while Use preset was ticked."""
    from qt_ui.windows.newgame.WizardPages import QTheaterConfiguration

    source = inspect.getsource(QTheaterConfiguration)
    assert "calendar.setDisabled" not in source


def test_a_date_picked_by_click_or_keyboard_leaves_preset_mode(qapp: Any) -> None:
    from PySide6.QtCore import QDate, Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QCheckBox, QTableView

    from qt_ui.widgets.QLiberationCalendar import QLiberationCalendar
    from qt_ui.windows.newgame.WizardPages.QTheaterConfiguration import (
        bind_start_date,
    )

    calendar = QLiberationCalendar()
    preset = QCheckBox()
    preset.setChecked(True)
    set_date = bind_start_date(calendar, preset)

    # A date the page sets itself (a preset, a campaign's own) keeps the box.
    set_date(QDate(1995, 6, 1))
    assert calendar.selectedDate() == QDate(1995, 6, 1)
    assert preset.isChecked()

    view: Any = calendar.findChild(QTableView)
    QTest.keyClick(view, Qt.Key.Key_Right)
    assert calendar.selectedDate() == QDate(1995, 6, 2)
    assert not preset.isChecked()

    preset.setChecked(True)
    calendar.clicked.emit(calendar.selectedDate())
    assert not preset.isChecked()
