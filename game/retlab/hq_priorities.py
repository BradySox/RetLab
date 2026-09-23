"""HQ priority targets (§103) — what losing each enemy target costs the enemy.

Design: docs/dev/design/retlab-hq-priority-targets-notes.md. The objective half of
juanjux's High Command, without its prizes.

- Each target is measured in its own family's unit, from numbers the game already
  keeps (no exchange rate between a factory's income and a SAM's price).
- Ranked only within its §93 family. Unmeasured targets stay neutral.
- A weight on BLUE's auto-planner, never a fence, and gentler than §93 so the
  player's own emphasis outranks HQ's. Red's planner never reads it.
- Sites hidden on blue's map are neither ranked nor weighted (§3 fog).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Iterator, Optional

from game.config import REWARDS
from game.retlab.region_priorities import family_of
from game.theater.player import Player

if TYPE_CHECKING:
    from game import Game
    from game.theater.theatergroundobject import TheaterGroundObject

#: Sort-key factors for the top and bottom third of a family. §93 uses 0.5/2.0.
TOP_FACTOR = 0.75
BOTTOM_FACTOR = 1.25

#: Below this many measured targets a family is not ranked.
MIN_RANKED = 3


@dataclass(frozen=True)
class Importance:
    """What losing a target costs the enemy. `score` is None when unmeasured."""

    score: Optional[float]
    reason: str


@dataclass(frozen=True)
class Standing:
    importance: Importance
    family: str
    rank: int
    of: int
    factor: float


def _offensive_package_ceiling(alive: int, total: int) -> int:
    from game.retlab.c2_decapitation import (
        FULL_OFFENSIVE_PACKAGE_CAP,
        MIN_OFFENSIVE_PACKAGES,
    )

    if total <= 0 or alive >= total:
        return FULL_OFFENSIVE_PACKAGE_CAP
    return max(
        MIN_OFFENSIVE_PACKAGES, round(FULL_OFFENSIVE_PACKAGE_CAP * alive / total)
    )


def _command_post(tgo: Any, game: Game) -> Importance:
    from game.retlab.c2_decapitation import _command_centers

    if not getattr(game.settings, "c2_decapitation_effects", False):
        return Importance(None, "Command post (command-post effects are off)")
    alive, total = _command_centers(tgo.coalition, game.theater)
    now = _offensive_package_ceiling(alive, total)
    after = _offensive_package_ceiling(alive - 1, total)
    return Importance(
        float(now - after),
        f"Enemy offensive package ceiling falls from {now} to {after}",
    )


def _ammo_depot(tgo: Any) -> Importance:
    cp = tgo.control_point
    active = cp.active_ammo_depots_count
    remaining = max(0, active - tgo.alive_unit_count())
    lost = cp.deployable_front_line_units_with(
        active
    ) - cp.deployable_front_line_units_with(remaining)
    return Importance(
        float(lost), f"{lost} front-line vehicles the enemy could no longer field"
    )


def _motorpool(tgo: Any) -> Importance:
    from game.ground_forces.ai_ground_planner import reserve_armor_for

    vehicles = sum(reserve_armor_for(tgo.control_point).values())
    return Importance(float(vehicles), f"{vehicles} reserve vehicles")


def _income(tgo: Any, game: Game) -> Importance:
    buildings = sum(1 for unit in tgo.statics if unit.alive)
    income = REWARDS[tgo.category] * buildings * game.settings.enemy_income_multiplier
    return Importance(income, f"${income:.1f}M a turn of enemy income")


def importance_of(tgo: Any, game: Game) -> Optional[Importance]:
    """The measure for one target, or None when no family governs it."""
    family = family_of(tgo)
    if family is None:
        return None
    category = tgo.category
    if category == "commandcenter":
        return _command_post(tgo, game)
    if category == "ammo":
        return _ammo_depot(tgo)
    if category == "motorpool":
        return _motorpool(tgo)
    if category in REWARDS:
        return _income(tgo, game)
    if family in ("Command and control", "Infrastructure"):
        return Importance(None, "No measure for this kind of target yet")
    value = tgo.value
    return Importance(float(value), f"${value}M of equipment")


def _enemy_targets(game: Game) -> Iterator[TheaterGroundObject]:
    from game.theater.fogofwar import hidden_from

    for cp in game.theater.controlpoints:
        if cp.captured is not Player.RED:
            continue
        for tgo in cp.ground_objects:
            if tgo.is_dead() or getattr(tgo, "is_control_point", False):
                continue
            if hidden_from(Player.BLUE, tgo):
                continue
            yield tgo


def _factor(higher: int, lower: int, of: int) -> float:
    """Top third ranks closer, bottom third farther; ties share a tier."""
    if of < MIN_RANKED:
        return 1.0
    third = math.ceil(of / 3)
    if higher < third:
        return TOP_FACTOR
    if lower < third:
        return BOTTOM_FACTOR
    return 1.0


class HqStandings:
    """Blue's view of every visible enemy target's standing, built once."""

    def __init__(self, game: Game) -> None:
        by_family: dict[str, list[tuple[TheaterGroundObject, Importance]]] = {}
        self._standings: dict[int, Standing] = {}
        for tgo in _enemy_targets(game):
            importance = importance_of(tgo, game)
            if importance is None:
                continue
            family = family_of(tgo)
            assert family is not None
            by_family.setdefault(family, []).append((tgo, importance))

        for family, entries in by_family.items():
            scores = [i.score for _, i in entries if i.score is not None]
            distinct = len(set(scores))
            for tgo, importance in entries:
                if importance.score is None:
                    self._standings[id(tgo)] = Standing(importance, family, 0, 0, 1.0)
                    continue
                higher = sum(1 for s in scores if s > importance.score)
                lower = sum(1 for s in scores if s < importance.score)
                factor = 1.0
                if distinct > 1:
                    factor = _factor(higher, lower, len(scores))
                self._standings[id(tgo)] = Standing(
                    importance, family, higher + 1, len(scores), factor
                )

    def standing(self, tgo: Any) -> Optional[Standing]:
        return self._standings.get(id(tgo))

    def factor(self, tgo: Any) -> float:
        standing = self.standing(tgo)
        return 1.0 if standing is None else standing.factor


def planning_enabled(game: Game, is_blue: bool) -> bool:
    return is_blue and bool(getattr(game.settings, "hq_priority_targets", False))


def why_it_matters(tgo: Any, game: Game, viewer: Player) -> Optional[str]:
    """The Target Intel line, or None when blue should not see one."""
    if viewer is not Player.BLUE or tgo.control_point.captured is not Player.RED:
        return None
    if not tgo.known_for(viewer):
        return "Unknown (not engaged)"
    standing = HqStandings(game).standing(tgo)
    if standing is None:
        return None
    importance = standing.importance
    if importance.score is None or standing.of < 2:
        return importance.reason
    return (
        f"{importance.reason}. #{standing.rank} of {standing.of} "
        f"{standing.family.lower()} targets"
    )
