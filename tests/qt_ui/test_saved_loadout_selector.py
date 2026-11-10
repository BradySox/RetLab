"""The Loadout list offers the player's saved fits under their own names (§128)."""

import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import dcs.planes
import pytest

from game import persistency
from game.ato.flightmember import FlightMember
from game.ato.loadouts import Loadout
from game.data.weapons import Pylon
from game.dcs.aircrafttype import AircraftType
from game.retlab import saved_loadouts

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def app() -> Any:
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_saved_fits_are_listed_after_the_presets(app: Any, tmp_path: Path) -> None:
    from qt_ui.windows.mission.flight.payload.QFlightPayloadTab import (
        DcsLoadoutSelector,
    )

    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16889)
    saved_loadouts.reset_cache()
    viper = next(AircraftType.for_dcs_type(dcs.planes.F_16C_50))
    pylon = next(Pylon.iter_pylons(viper))
    weapon = sorted(pylon.allowed, key=lambda w: w.clsid)[0]
    saved_loadouts.save(viper, "Mine", Loadout("x", {pylon.number: weapon}, None))

    flight: Any = SimpleNamespace(unit_type=viper)
    member = FlightMember(None, Loadout("Saved: Mine", {}, None))
    try:
        selector = DcsLoadoutSelector(flight, member)
        names = [selector.itemText(i) for i in range(selector.count())]
        assert names[-1] == "Saved: Mine"
        assert selector.currentText() == "Saved: Mine"
        assert selector.currentData().pylons == {pylon.number: weapon}
    finally:
        saved_loadouts.reset_cache()
