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
    SERVICE_CONDITION,
    condition_defaults,
)


def test_heatblur_jets_get_the_period_condition() -> None:
    for jet in (F_4E_45MC, A6E):
        assert condition_defaults(jet, date(2004, 6, 1)) == {
            "Quality": SERVICE_CONDITION
        }
        assert condition_defaults(jet, date(1972, 6, 1)) == {"Quality": EARLY_CONDITION}
    assert condition_defaults(F_4E_45MC, date(1980, 1, 1)) == {"Quality": 90}


def test_other_jets_are_untouched() -> None:
    assert condition_defaults(FA_18C_hornet, date(2004, 6, 1)) == {}


def _set_up(when: date, *members: tuple[bool, dict[str, Any]]) -> list[dict[str, Any]]:
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
        date(1972, 6, 1), (True, {}), (True, {"Quality": 100}), (False, {})
    )
    assert untouched == {"Quality": EARLY_CONDITION}
    assert set_by_player == {"Quality": 100}
    assert ai == {}
