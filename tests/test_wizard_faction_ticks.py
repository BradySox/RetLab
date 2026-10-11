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
    assert "self.calendar.clicked.connect" in source
