"""§124 carry-over ship damage — the campaign side.

Pins that a ship's saved health only ever falls from a mission report, rises by
the repair setting at the turn end, and reaches the mission as DCS's native
set-life action with a percentage, never a zero that would sink it at start.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from dcs import Mission

from game.retlab.ship_damage import (
    SetUnitLifePercent,
    commit_ship_damage,
    generate_ship_health,
    parse_ship_health,
    repair_ship_damage,
    repaired,
)


class _Events:
    def __init__(self) -> None:
        self.tgos: list[Any] = []

    def update_tgo(self, tgo: Any) -> None:
        self.tgos.append(tgo)


def _ship(health: float = 1.0, alive: bool = True, is_ship: bool = True) -> Any:
    unit = SimpleNamespace(health=health, alive=alive, is_ship=is_ship)
    unit.ground_object = SimpleNamespace(units=[unit])
    return unit


def _settings(on: bool = True, percent: int = 34) -> Any:
    return SimpleNamespace(
        ship_damage_carry_over=on, ship_damage_repair_percent=percent
    )


def _game(units: list[Any], on: bool = True, percent: int = 34) -> Any:
    tgos = [u.ground_object for u in units]
    return SimpleNamespace(
        settings=_settings(on, percent),
        theater=SimpleNamespace(ground_objects=tgos),
    )


def _debriefing(health: dict[str, float], units: dict[str, Any]) -> Any:
    def theater_units(name: str) -> Any:
        unit = units.get(name)
        return None if unit is None else SimpleNamespace(theater_unit=unit)

    return SimpleNamespace(
        state_data=SimpleNamespace(ship_health=health),
        unit_map=SimpleNamespace(theater_units=theater_units),
    )


def test_the_native_action_carries_a_percentage() -> None:
    action = SetUnitLifePercent(249, 0.65)
    d = action.dict()
    assert d["predicate"] == "a_unit_set_life_percentage"
    assert d["unit"] == 249
    assert d["life_percents"] == pytest.approx(65)


@pytest.mark.parametrize("value", [0, -0.5, 1.5, float("nan"), float("inf")])
def test_a_value_that_would_sink_or_overfill_a_ship_is_refused(value: float) -> None:
    with pytest.raises(ValueError):
        SetUnitLifePercent(249, value)


def test_repair_adds_points_of_full_health() -> None:
    assert repaired(0.40, 34) == pytest.approx(0.74)
    assert repaired(0.74, 34) == 1.0
    assert repaired(0.40, 0) == pytest.approx(0.40)


def test_the_state_table_drops_anything_malformed() -> None:
    raw = {"a": 0.5, "b": 1.5, "c": "x", "d": True, "e": float("nan"), "f": 0}
    assert parse_ship_health(raw) == {"a": 0.5, "f": 0.0}
    # Lua's json writes an empty table as a list.
    assert parse_ship_health([]) == {}
    assert parse_ship_health(None) == {}


def test_a_report_lowers_saved_health_and_never_raises_it() -> None:
    hit, unapplied = _ship(1.0), _ship(0.5)
    events = _Events()
    commit_ship_damage(
        _game([hit, unapplied]),
        _debriefing(
            {"hit": 0.6, "unapplied": 1.0}, {"hit": hit, "unapplied": unapplied}
        ),
        events,  # type: ignore[arg-type]
    )
    assert hit.health == pytest.approx(0.6)
    # DCS did not apply the set-life action: the ship keeps its saved damage.
    assert unapplied.health == 0.5
    assert events.tgos == [hit.ground_object]


def test_a_sunk_ship_and_a_non_ship_are_left_to_their_own_paths() -> None:
    sunk, vehicle = _ship(1.0, alive=False), _ship(1.0, is_ship=False)
    commit_ship_damage(
        _game([sunk, vehicle]),
        _debriefing({"sunk": 0.3, "vehicle": 0.3}, {"sunk": sunk, "vehicle": vehicle}),
        _Events(),  # type: ignore[arg-type]
    )
    assert sunk.health == 1.0
    assert vehicle.health == 1.0


def test_nothing_is_recorded_with_the_setting_off() -> None:
    ship = _ship(1.0)
    commit_ship_damage(
        _game([ship], on=False),
        _debriefing({"ship": 0.3}, {"ship": ship}),
        _Events(),  # type: ignore[arg-type]
    )
    assert ship.health == 1.0


def test_the_turn_end_repairs_damaged_ships() -> None:
    damaged, whole = _ship(0.40), _ship(1.0)
    events = _Events()
    repair_ship_damage(_game([damaged, whole]), events)  # type: ignore[arg-type]
    assert damaged.health == pytest.approx(0.74)
    assert whole.health == 1.0
    assert events.tgos == [damaged.ground_object]


def test_turning_the_setting_off_restores_every_ship() -> None:
    damaged = _ship(0.40)
    repair_ship_damage(_game([damaged], on=False), _Events())  # type: ignore[arg-type]
    assert damaged.health == 1.0


def test_the_mission_spawns_damaged_ships_at_their_health() -> None:
    mission = Mission()
    damaged, whole, sunk = _ship(0.5), _ship(1.0), _ship(0.5, alive=False)
    vehicle = _ship(0.5, is_ship=False)
    mapping = {
        "Cruiser": SimpleNamespace(
            theater_unit=damaged, dcs_unit=SimpleNamespace(id=11)
        ),
        "Frigate": SimpleNamespace(theater_unit=whole, dcs_unit=SimpleNamespace(id=12)),
        "Sunk": SimpleNamespace(theater_unit=sunk, dcs_unit=SimpleNamespace(id=13)),
        "Tank": SimpleNamespace(theater_unit=vehicle, dcs_unit=SimpleNamespace(id=14)),
    }
    unit_map = SimpleNamespace(theater_objects=mapping)
    generate_ship_health(_game([]), mission, unit_map)  # type: ignore[arg-type]

    (trigger,) = mission.triggerrules.triggers
    script, *native = trigger.actions
    assert '"Cruiser", "Frigate"' in str(script.dict())
    assert [(a.dict()["unit"], a.dict()["life_percents"]) for a in native] == [
        (11, 50.0)
    ]


def test_the_mission_carries_nothing_with_the_setting_off() -> None:
    mission = Mission()
    mapping = {
        "Cruiser": SimpleNamespace(
            theater_unit=_ship(0.5), dcs_unit=SimpleNamespace(id=11)
        )
    }
    generate_ship_health(
        _game([], on=False), mission, SimpleNamespace(theater_objects=mapping)  # type: ignore[arg-type]
    )
    assert mission.triggerrules.triggers == []
