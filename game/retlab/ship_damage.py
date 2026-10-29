"""§124 carry-over ship damage: a ship keeps its damage between turns.

A damaged ship spawns at its saved health through DCS's native set-life trigger
action, the base plugin reports each ship's life fraction in state.json, and every
turn repairs a set number of points. Ships only: buildings would need scripted
explosions, which the DM ruled out. See docs/dev/retlab-features.md §124.

`SetUnitLifePercent` is adapted from juanjux/dcs-escalation
(game/missiongenerator/persistenthealth.py, LGPL-3.0).
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

from dcs.action import Action, DoScript
from dcs.translation import String
from dcs.triggers import TriggerStart

from game.utils import escape_string_for_lua

if TYPE_CHECKING:
    from dcs import Mission

    from game import Game
    from game.debriefing import Debriefing
    from game.sim import GameUpdateEvents
    from game.unitmap import UnitMap


class SetUnitLifePercent(Action):
    """DCS's "UNIT SET LIFE %" action; it runs outside the DO SCRIPT sandbox."""

    def __init__(self, unit_id: int, fraction: float) -> None:
        super().__init__("a_unit_set_life_percentage")
        # A zero or NaN here would sink the ship at mission start.
        if not 0 < fraction <= 1:
            raise ValueError(f"Ship health must be in (0, 1], got {fraction}")
        self.unit_id = unit_id
        self.percent = fraction * 100
        self.params = [unit_id, self.percent]

    def dict(self) -> dict[str, Any]:
        d = super().dict()
        d["unit"] = self.unit_id
        d["life_percents"] = self.percent
        return d


def repaired(health: float, percent: int) -> float:
    """Repair adds points of full health, not a share of the damage."""
    return min(1.0, health + max(0, percent) / 100)


def parse_ship_health(raw: Any) -> dict[str, float]:
    """The base plugin's ``ship_health`` table; anything malformed is dropped."""
    if not isinstance(raw, dict):
        # Lua's json encodes an empty table as a list.
        return {}
    health: dict[str, float] = {}
    for name, value in raw.items():
        if (
            isinstance(name, str)
            and isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            and 0 <= value <= 1
        ):
            health[name] = float(value)
    return health


def generate_ship_health(game: Game, mission: Mission, unit_map: UnitMap) -> None:
    """Spawn damaged ships at their saved health and name the ships to report."""
    if not game.settings.ship_damage_carry_over:
        return
    names: list[str] = []
    actions: list[SetUnitLifePercent] = []
    for name, mapping in unit_map.theater_objects.items():
        unit = mapping.theater_unit
        if not unit.is_ship or not unit.alive:
            continue
        names.append(name)
        if unit.health < 1:
            actions.append(SetUnitLifePercent(mapping.dcs_unit.id, unit.health))
    if not names:
        return
    trigger = TriggerStart(comment="Ship health (carry-over damage)")
    listed = ", ".join(f'"{escape_string_for_lua(n)}"' for n in names)
    trigger.add_action(DoScript(String(f"ship_health_units = {{{listed}}}")))
    for action in actions:
        trigger.add_action(action)
    mission.triggerrules.triggers.append(trigger)


def commit_ship_damage(
    game: Game, debriefing: Debriefing, events: GameUpdateEvents
) -> None:
    if not game.settings.ship_damage_carry_over:
        return
    for name, fraction in debriefing.state_data.ship_health.items():
        mapping = debriefing.unit_map.theater_units(name)
        if mapping is None:
            continue
        unit = mapping.theater_unit
        # A sinking is scored by the kill path. A ship never heals in a mission,
        # so a higher reading means the set-life action did not take: keep ours.
        if not unit.is_ship or not unit.alive or fraction <= 0:
            continue
        if fraction < unit.health:
            unit.health = fraction
            events.update_tgo(unit.ground_object)


def repair_ship_damage(game: Game, events: GameUpdateEvents) -> None:
    """Once per turn end, skipped turns included."""
    enabled = game.settings.ship_damage_carry_over
    percent = game.settings.ship_damage_repair_percent
    for tgo in game.theater.ground_objects:
        changed = False
        for unit in tgo.units:
            if unit.health >= 1:
                continue
            unit.health = repaired(unit.health, percent) if enabled else 1.0
            changed = True
        if changed:
            events.update_tgo(tgo)
