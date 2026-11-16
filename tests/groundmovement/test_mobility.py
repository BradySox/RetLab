"""Ground movement stage 1: every unit's mobility data loads and means one thing."""

import logging
from types import SimpleNamespace
from typing import Any

import pytest

from game.data.units import UnitClass
from game.dcs.groundunittype import GroundUnitType
from game.groundmovement.mobility import (
    GroundMobility,
    MobilityMode,
    movement_mobility,
)


@pytest.fixture(scope="module")
def units() -> list[GroundUnitType]:
    logging.disable(logging.CRITICAL)
    try:
        GroundUnitType._load_all()
    finally:
        logging.disable(logging.NOTSET)
    return list(GroundUnitType._by_name.values())


def test_every_unit_file_loads_its_mobility(units: list[GroundUnitType]) -> None:
    assert units
    assert all(isinstance(u.ground_mobility, GroundMobility) for u in units)


def test_tractors_drive_themselves(units: list[GroundUnitType]) -> None:
    tractors = [u for u in units if u.ground_mobility.can_tow]
    assert tractors
    assert all(u.ground_mobility.mode is MobilityMode.SELF_PROPELLED for u in tractors)


def test_tanks_drive_and_a_towed_gun_needs_a_truck(
    units: list[GroundUnitType],
) -> None:
    by_name = {u.variant_id: u for u in units}
    assert movement_mobility(by_name["M1A2 Abrams"]).mode is MobilityMode.SELF_PROPELLED
    towed = [u for u in units if u.ground_mobility.mode is MobilityMode.TOWED]
    assert towed


def test_an_undrivable_unit_is_fixed_whatever_its_data_says(
    units: list[GroundUnitType],
) -> None:
    for unit in units:
        if not unit.mobile:
            assert movement_mobility(unit).mode is MobilityMode.FIXED, unit.variant_id


def _fake(unit_class: UnitClass, mobility: GroundMobility) -> Any:
    return SimpleNamespace(unit_class=unit_class, mobile=True, ground_mobility=mobility)


@pytest.mark.parametrize("unit_class", [UnitClass.INFANTRY, UnitClass.MANPAD])
def test_infantry_walks_and_never_tows(unit_class: UnitClass) -> None:
    mobility = movement_mobility(_fake(unit_class, GroundMobility()))
    assert mobility == GroundMobility(MobilityMode.SELF_PROPELLED)


def test_unreviewed_is_unknown() -> None:
    assert GroundMobility.from_data(None).mode is MobilityMode.UNKNOWN


@pytest.mark.parametrize(
    "data",
    [
        {"mode": "towed", "can_tow": True},
        {"mode": "hovering"},
        {"mode": "towed", "speed": 3},
        "self_propelled",
        {"mode": "self_propelled", "can_tow": "yes"},
    ],
)
def test_bad_data_is_refused(data: Any) -> None:
    with pytest.raises(ValueError):
        GroundMobility.from_data(data)
