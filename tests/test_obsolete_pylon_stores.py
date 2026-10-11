"""A store DCS has retired on a station is never offered, preset or flown."""

import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from dcs import Mission, Point, planes
from dcs.planes import B_52H
from dcs.terrain import Caucasus

from game.ato.flightmember import FlightMember
from game.ato.flighttype import FlightType
from game.ato.loadouts import Loadout
from game.data.weapons import (
    OBSOLETE_PYLON_STORES,
    Pylon,
    Weapon,
    is_obsolete_store,
)
from game.missiongenerator.aircraft.flightgroupconfigurator import (
    FlightGroupConfigurator,
)

BAY_HARPOONS = "{46ACDCF8-5451-4E26-BDDB-E78D5830E93C}"
WING_HARPOONS_L = "{HSAB_4x_AGM84D_L}"
WING_HARPOONS_R = "{HSAB_4x_AGM84D_R}"
BAY_JDAMS = "{CSRL_GBU31V1}"

ANTISHIP_WITH_BAY = {
    "Retribution Anti-ship": {
        "name": "Retribution Anti-ship",
        "pylons": {
            1: {"CLSID": WING_HARPOONS_R, "num": 3},
            2: {"CLSID": WING_HARPOONS_L, "num": 1},
            3: {"CLSID": BAY_HARPOONS, "num": 2},
        },
    }
}


def _b52() -> Any:
    return SimpleNamespace(dcs_unit_type=B_52H, has_built_in_target_pod=False)


def _clsids(weapons: Any) -> set[str]:
    return {w.clsid for w in weapons}


def test_bay_harpoons_are_not_offered_and_the_wing_racks_are() -> None:
    bay = _clsids(Pylon.for_aircraft(_b52(), 2).allowed)
    assert BAY_HARPOONS not in bay
    assert BAY_JDAMS in bay
    assert WING_HARPOONS_L in _clsids(Pylon.for_aircraft(_b52(), 1).allowed)
    assert WING_HARPOONS_R in _clsids(Pylon.for_aircraft(_b52(), 3).allowed)


def test_a_saved_preset_resolves_without_the_bay_rack(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        B_52H, "load_payloads", classmethod(lambda cls: ANTISHIP_WITH_BAY)
    )
    monkeypatch.setattr(B_52H, "payloads", ANTISHIP_WITH_BAY)
    expected = {1: WING_HARPOONS_L, 3: WING_HARPOONS_R}
    default = Loadout.default_for_task_and_aircraft(FlightType.ANTISHIP, B_52H)
    listed = next(Loadout.iter_for_aircraft(_b52()))
    for loadout in (default, listed):
        assert loadout.name == "Retribution Anti-ship"
        assert {n: w.clsid for n, w in loadout.pylons.items() if w} == expected


def test_a_loadout_from_an_old_save_flies_the_bay_empty() -> None:
    mission = Mission(Caucasus())
    group = mission.flight_group(
        mission.country("USA"),
        "Harpoon test",
        B_52H,
        airport=None,
        position=Point(-200000, 600000, mission.terrain),
        group_size=1,
    )
    generator = FlightGroupConfigurator.__new__(FlightGroupConfigurator)
    generator.game = SimpleNamespace(settings=SimpleNamespace(restrict_weapons_by_date=False))  # type: ignore[assignment]
    generator.flight = _b52_flight()
    loadout = Loadout(
        "Old save",
        {
            1: Weapon.with_clsid(WING_HARPOONS_L),
            2: Weapon.with_clsid(BAY_HARPOONS),
            3: Weapon.with_clsid(WING_HARPOONS_R),
        },
        None,
    )
    unit = group.units[0]
    generator.setup_payload(unit, FlightMember(None, loadout))
    assert {n: p["CLSID"] for n, p in unit.pylons.items()} == {
        1: WING_HARPOONS_L,
        3: WING_HARPOONS_R,
    }


def _b52_flight() -> Any:
    return SimpleNamespace(unit_type=_b52())


def test_every_row_names_a_store_pydcs_still_lists() -> None:
    # A row for a store pydcs has dropped filters nothing and should be deleted.
    for unit_id, stations in OBSOLETE_PYLON_STORES.items():
        unit_type = planes.plane_map[unit_id]
        for station, clsids in stations.items():
            listed = {
                value[1]["clsid"]
                for pylon in vars(unit_type).values()
                if isinstance(pylon, type) and pylon.__name__.startswith("Pylon")
                for value in vars(pylon).values()
                if isinstance(value, tuple) and value[0] == station
            }
            assert clsids <= listed, (unit_id, station)
            for clsid in clsids:
                assert is_obsolete_store(unit_id, station, clsid)
                assert not is_obsolete_store(unit_id, station + 100, clsid)


def test_the_table_matches_installed_dcs() -> None:
    """The B-52H is the only aircraft with an obsolete store; checked 2026-10-11."""
    path = Path("E:/DCS World/CoreMods/tech/HeavyMetalCore/Database/Aircraft/B_52H.lua")
    if not path.is_file():
        pytest.skip("DCS is not installed here")
    marked = set(
        re.findall(
            r'CLSID\s*=\s*"([^"]+)"\s*,\s*obsolete\s*=\s*true',
            path.read_text(encoding="utf-8", errors="replace"),
        )
    )
    assert marked == set().union(*OBSOLETE_PYLON_STORES["B-52H"].values())
