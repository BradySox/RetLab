"""Heatblur jets spawn at a period Aircraft Condition unless the player set one."""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from typing import Any

from dcs.planes import A6E, F_4E_45MC, FA_18C_hornet

from game.missiongenerator.aircraft.flightgroupconfigurator import (
    FlightGroupConfigurator,
)
from game.retlab.airframe_condition import (
    EARLY_CONDITION,
    MAX_WORKLOAD_WEAR,
    SERVICE_CONDITION,
    airframe_hours_by_flight,
    commit_squadron_wear,
    condition_defaults,
    next_wear,
)


def test_heatblur_jets_get_the_period_condition() -> None:
    for jet in (F_4E_45MC, A6E):
        assert condition_defaults(jet, date(2004, 6, 1)) == {
            "Quality": SERVICE_CONDITION,
            "Wear": 0,
        }
        assert condition_defaults(jet, date(1972, 6, 1), 12.6) == {
            "Quality": EARLY_CONDITION,
            "Wear": 13,
        }
    assert condition_defaults(F_4E_45MC, date(1980, 1, 1))["Quality"] == 90


def test_other_jets_are_untouched() -> None:
    assert condition_defaults(FA_18C_hornet, date(2004, 6, 1)) == {}


def _set_up(
    when: date, wear: float, *members: tuple[bool, dict[str, Any]]
) -> list[dict[str, Any]]:
    written: list[dict[str, Any]] = []
    units = []
    for _ in members:
        props: dict[str, Any] = {}
        written.append(props)
        units.append(
            SimpleNamespace(
                unit_type=SimpleNamespace(datalink_networkable=lambda: False),
                set_property=props.__setitem__,
            )
        )
    roster = [
        SimpleNamespace(is_player=player, properties=props, weapon_laser_code=None)
        for player, props in members
    ]
    configurator: Any = SimpleNamespace(
        group=SimpleNamespace(units=units),
        flight=SimpleNamespace(
            unit_type=SimpleNamespace(dcs_unit_type=F_4E_45MC),
            squadron=SimpleNamespace(airframe_wear=wear),
            iter_members=lambda: iter(roster),
        ),
        game=SimpleNamespace(
            date=when, settings=SimpleNamespace(restrict_props_by_date=False)
        ),
    )
    FlightGroupConfigurator.setup_props(configurator)
    return written


def test_player_jets_spawn_at_the_baseline_and_a_set_value_wins() -> None:
    untouched, set_by_player, ai = _set_up(
        date(1972, 6, 1),
        20.0,
        (True, {}),
        (True, {"Quality": 100, "Wear": 0}),
        (False, {}),
    )
    assert untouched == {"Quality": EARLY_CONDITION, "Wear": 20}
    assert set_by_player == {"Quality": 100, "Wear": 0}
    assert ai == {}


def test_wear_climbs_with_hours_and_recovers_each_turn() -> None:
    # 12 jets, all flying 2 hours: +20, less 5 recovery.
    assert next_wear(0.0, 24.0, 12) == 15.0
    assert next_wear(40.0, 48.0, 12) == MAX_WORKLOAD_WEAR
    assert next_wear(12.0, 0.0, 12) == 7.0
    assert next_wear(3.0, 0.0, 12) == 0.0
    assert next_wear(0.0, 4.0, 0) == 35.0


def _record(unit: str, hours: float, moved: bool = True) -> Any:
    return SimpleNamespace(unit=unit, flew=moved, duration=hours * 3600)


def test_a_flight_counts_its_longest_record_once_per_aircraft() -> None:
    four_ship = SimpleNamespace(count=4)
    two_ship = SimpleNamespace(count=2)
    flights = {"a1": four_ship, "a2": four_ship, "b1": two_ship, "parked": two_ship}
    flown = airframe_hours_by_flight(
        [
            _record("a1", 1.5),
            _record("a2", 2.0),
            _record("b1", 1.0),
            _record("parked", 3.0, moved=False),
            _record("unknown", 5.0),
        ],
        flights.get,  # type: ignore[arg-type]
    )
    assert sorted(h for _, h in flown) == [2.0, 8.0]


def test_only_heatblur_squadrons_track_wear() -> None:
    phantoms = SimpleNamespace(
        aircraft=SimpleNamespace(dcs_unit_type=F_4E_45MC),
        owned_aircraft=12,
        airframe_wear=10.0,
    )
    hornets = SimpleNamespace(
        aircraft=SimpleNamespace(dcs_unit_type=FA_18C_hornet),
        owned_aircraft=12,
        airframe_wear=0.0,
    )
    flown: list[Any] = [
        (SimpleNamespace(squadron=phantoms), 24.0),
        (SimpleNamespace(squadron=hornets), 24.0),
    ]
    commit_squadron_wear([phantoms, hornets], flown)  # type: ignore[list-item]
    assert phantoms.airframe_wear == 25.0
    assert hornets.airframe_wear == 0.0
