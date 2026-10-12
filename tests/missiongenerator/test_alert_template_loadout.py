"""An alert (QRA) template carries the fit its flight would carry in the ATO.

The template is spawned by ``FlightGroupSpawner.create_intercept_template`` and
never passes through ``FlightGroupConfigurator``, so it kept the payload pydcs
picks for the type's default task. In test 56 (2026-10-11) that was four inert
practice bombs and a captive Sidewinder on the F-15E alert pair, and empty
pylons on the Mirage F1 pair. Every scramble clone copies the template.
"""

from __future__ import annotations

import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Type

import dcs
import pytest
from dcs import planes
from dcs.payloads import PayloadDirectories
from dcs.terrain import Caucasus
from dcs.unittype import FlyingType

from game.ato.flighttype import FlightType
from game.ato.loadouts import Loadout
from game.missiongenerator.aircraft.flightgroupspawner import FlightGroupSpawner

PAYLOADS_DIR = Path(__file__).parents[2] / "resources" / "customized_payloads"

ALERT_TYPES = ["F-15ESE", "Mirage-F1EQ", "JF-17", "MiG-29A"]


@pytest.fixture(autouse=True)
def payload_dirs() -> None:
    PayloadDirectories.set_fallback(PAYLOADS_DIR)
    FlyingType._payload_cache = None  # type: ignore[assignment]


def _template(dcs_type: Type[FlyingType]) -> Any:
    """A two-ship built the way _generate_at_airfield builds the template."""
    mission = dcs.mission.Mission(terrain=Caucasus())
    dcs_type.load_payloads()
    return mission.flight_group_from_airport(
        country=mission.country("USA"),
        name="Intercept|Batumi|test",
        aircraft_type=dcs_type,
        airport=mission.terrain.airports["Batumi"],
        maintask=None,
        group_size=2,
    )


def _spawner(dcs_type: Type[FlyingType], loadout: Loadout, by_date: bool) -> Any:
    unit_type = SimpleNamespace(dcs_unit_type=dcs_type, has_built_in_target_pod=False)
    game = SimpleNamespace(
        settings=SimpleNamespace(restrict_weapons_by_date=by_date),
        date=datetime.date(2012, 5, 16),
    )
    members = [SimpleNamespace(loadout=loadout), SimpleNamespace(loadout=loadout)]
    spawner = FlightGroupSpawner.__new__(FlightGroupSpawner)
    spawner.flight = SimpleNamespace(  # type: ignore[assignment]
        unit_type=unit_type,
        coalition=SimpleNamespace(game=game, faction=None),
        iter_members=lambda: iter(members),
    )
    return spawner


def _stores(unit: Any) -> dict[int, str]:
    return {number: store["CLSID"] for number, store in unit.pylons.items()}


@pytest.mark.parametrize("type_id", ALERT_TYPES)
def test_the_template_carries_the_barcap_fit(type_id: str) -> None:
    dcs_type = planes.plane_map[type_id]
    loadout = Loadout.default_for_task_and_aircraft(FlightType.BARCAP, dcs_type)
    expected = {n: w.clsid for n, w in loadout.pylons.items() if w is not None}
    assert expected, f"{type_id} has no BARCAP preset"

    group = _template(dcs_type)
    _spawner(dcs_type, loadout, by_date=False)._arm_alert_template(group)

    assert len(group.units) == 2
    for unit in group.units:
        assert _stores(unit) == expected


def test_the_f15e_default_is_not_what_an_alert_jet_flies() -> None:
    """The fault itself: pydcs's default F-15E payload is not the BARCAP fit. If
    this starts failing, pydcs changed and the arming step is only a safeguard."""
    dcs_type = planes.plane_map["F-15ESE"]
    loadout = Loadout.default_for_task_and_aircraft(FlightType.BARCAP, dcs_type)
    expected = {n: w.clsid for n, w in loadout.pylons.items() if w is not None}
    assert _stores(_template(dcs_type).units[0]) != expected


def test_an_airframe_with_no_preset_keeps_the_pydcs_default() -> None:
    dcs_type = planes.plane_map["F-15ESE"]
    group = _template(dcs_type)
    before = [_stores(unit) for unit in group.units]

    spawner = _spawner(dcs_type, Loadout.empty_loadout(), by_date=False)
    spawner._arm_alert_template(group)

    assert [_stores(unit) for unit in group.units] == before


def test_date_limits_apply_to_the_template() -> None:
    """2012 with weapon dates on: nothing newer than the campaign rides along."""
    from game.data.weapons import Weapon

    dcs_type = planes.plane_map["F-15ESE"]
    loadout = Loadout.default_for_task_and_aircraft(FlightType.BARCAP, dcs_type)
    group = _template(dcs_type)
    _spawner(dcs_type, loadout, by_date=True)._arm_alert_template(group)

    for unit in group.units:
        stores = _stores(unit)
        assert stores
        for clsid in stores.values():
            weapon = Weapon.with_clsid(clsid)
            assert weapon is not None
            year = weapon.weapon_group.introduction_year
            assert year is None or year <= 2012
