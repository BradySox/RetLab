"""A store loaded from a save is an equal copy of the listed one, not the same object."""

from __future__ import annotations

import os
import pickle

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from datetime import date
from types import SimpleNamespace
from typing import Any

import pytest

from game.ato.flightmember import FlightMember
from game.ato.loadouts import Loadout
from game.data.weapons import Pylon, Weapon, WeaponGroup, WeaponType


@pytest.fixture(scope="module")
def app() -> Any:
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _store(name: str, clsid: str) -> Weapon:
    weapon = Weapon(clsid, WeaponGroup("Test", WeaponType.UNKNOWN, None, None))
    object.__setattr__(
        weapon, "pydcs_data", {"name": name, "clsid": clsid, "weight": 100}
    )
    return weapon


@pytest.mark.parametrize("name", ["GBU-12", "Captive GBU-12"])
def test_reopened_flight_keeps_pylon_settings_and_lists_the_store_once(
    app: Any, name: str
) -> None:
    from qt_ui.windows.mission.flight.payload.QPylonEditor import QPylonEditor

    bomb = _store(name, "bomb")
    pylon = Pylon(1, {bomb, _store("AIM-9M", "missile")})
    settings = {1: {"laser_code": 1688}}
    loadout = pickle.loads(
        pickle.dumps(Loadout("Custom", {1: bomb}, None, True, settings))
    )
    loaded = loadout.pylons[1]
    assert loaded == bomb and loaded is not bomb

    member = FlightMember(None, loadout)
    game: Any = SimpleNamespace(
        settings=SimpleNamespace(
            restrict_weapons_by_date=False, apply_target_overrides_to_loadouts=False
        ),
        date=date(2000, 1, 1),
    )
    flight: Any = SimpleNamespace(
        squadron=SimpleNamespace(coalition=SimpleNamespace(faction=SimpleNamespace())),
        unit_type=None,
    )
    editor = QPylonEditor(game, flight, member, pylon)
    editor.set_from(loadout)

    combo = editor.weapon_combo
    names = [combo.itemText(i) for i in range(combo.count())]
    assert names.count(name) == 1
    assert combo.currentData() == bomb
    assert loadout.pylon_settings == {1: {"laser_code": 1688}}


def test_switching_the_member_keeps_each_members_pylon_settings(app: Any) -> None:
    from qt_ui.windows.mission.flight.payload.QPylonEditor import QPylonEditor

    bomb = _store("GBU-12", "bomb")
    missile = _store("AIM-9M", "missile")
    pylon = Pylon(1, {bomb, missile})
    lead = FlightMember(None, Loadout("Custom", {1: bomb}, None, True, {1: {"c": 1}}))
    wing = FlightMember(
        None, Loadout("Custom", {1: missile}, None, True, {1: {"c": 2}})
    )
    game: Any = SimpleNamespace(
        settings=SimpleNamespace(
            restrict_weapons_by_date=False, apply_target_overrides_to_loadouts=False
        ),
        date=date(2000, 1, 1),
    )
    flight: Any = SimpleNamespace(
        squadron=SimpleNamespace(coalition=SimpleNamespace(faction=SimpleNamespace())),
        unit_type=None,
    )
    editor = QPylonEditor(game, flight, lead, pylon)

    editor.set_flight_member(wing)
    assert editor.weapon_combo.currentData() == missile
    editor.set_flight_member(lead)

    assert editor.weapon_combo.currentData() == bomb
    assert lead.loadout.pylon_settings == {1: {"c": 1}}
    assert wing.loadout.pylon_settings == {1: {"c": 2}}
    assert lead.loadout.pylons[1] == bomb and wing.loadout.pylons[1] == missile
