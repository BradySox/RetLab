"""§125 missile-site targets: a saved aim point for a player's SCUD-type site.

A site with no pick keeps upstream's random enemy base. The site half of
Juan Jose Ruiz's dcs-escalation `game/missiletargets.py` (LGPL-3), reduced to a
pick from a list. See `docs/dev/retlab-features.md` §125.

- Blue sites only; red keeps firing at random.
- Only targets the player can see: `fogofwar.hidden_from`, never a bare
  `hidden_on_player_map`, so the reveal overview cannot leak a command post.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Union
from uuid import UUID

from game.theater.fogofwar import hidden_from
from game.theater.player import Player
from game.theater.theatergroundobject import MissileSiteGroundObject
from pydcs_extensions.iranairdefensepack.iranairdefensepack import (
    MISSILE_MIN_RANGE_M,
)

if TYPE_CHECKING:
    from dcs import Point

    from game import Game
    from game.theater import ControlPoint
    from game.theater.theatergroundobject import TheaterGroundObject

MissileTargetObject = Union["ControlPoint", "TheaterGroundObject"]


@dataclass(frozen=True)
class MissileTargetPick:
    target_id: UUID
    is_base: bool


@dataclass(frozen=True)
class MissileTargetChoice:
    pick: MissileTargetPick
    name: str
    distance_m: float


def site_range(site: MissileSiteGroundObject) -> tuple[float, float]:
    """(minimum, maximum) metres of the site's living launchers; (0, 0) if none."""
    minimum = 0.0
    maximum = 0.0
    for group in site.groups:
        for unit in group.units:
            if not unit.alive:
                continue
            reach = float(getattr(unit.type, "threat_range", 0) or 0)
            if reach <= 0:
                continue
            maximum = max(maximum, reach)
            minimum = max(minimum, float(MISSILE_MIN_RANGE_M.get(unit.type.id, 0)))
    return minimum, maximum


def can_pick(game: Game, site: TheaterGroundObject) -> bool:
    return (
        isinstance(site, MissileSiteGroundObject)
        and site.is_friendly(Player.BLUE)
        and not site.is_dead()
    )


def _in_range(site: MissileSiteGroundObject, point: Point) -> bool:
    minimum, maximum = site_range(site)
    return minimum <= site.position.distance_to_point(point) < maximum


def _still_valid(target: MissileTargetObject, is_base: bool) -> bool:
    if is_base:
        return target.captured is Player.RED  # type: ignore[union-attr]
    tgo: TheaterGroundObject = target  # type: ignore[assignment]
    return (
        tgo.control_point.captured is Player.RED
        and not tgo.sea_object
        and not tgo.is_control_point
        and not tgo.is_dead()
        and not hidden_from(Player.BLUE, tgo)
    )


def _lookup(game: Game, pick: MissileTargetPick) -> Optional[MissileTargetObject]:
    if pick.is_base:
        for cp in game.theater.controlpoints:
            if cp.id == pick.target_id:
                return cp
        return None
    try:
        return game.db.tgos.get(pick.target_id)
    except KeyError:
        return None


def choices(game: Game, site: MissileSiteGroundObject) -> list[MissileTargetChoice]:
    """Every enemy base and visible enemy land site in range, nearest first."""
    result: list[MissileTargetChoice] = []
    for cp in game.theater.controlpoints:
        if cp.captured is not Player.RED:
            continue
        if _in_range(site, cp.position):
            result.append(
                MissileTargetChoice(
                    MissileTargetPick(cp.id, True),
                    f"Base: {cp.name}",
                    site.position.distance_to_point(cp.position),
                )
            )
        for tgo in cp.ground_objects:
            if _still_valid(tgo, False) and _in_range(site, tgo.position):
                result.append(
                    MissileTargetChoice(
                        MissileTargetPick(tgo.id, False),
                        tgo.obj_name,
                        site.position.distance_to_point(tgo.position),
                    )
                )
    result.sort(key=lambda c: (c.distance_m, c.name))
    return result


def aim_point(game: Game, site: MissileSiteGroundObject) -> Optional[Point]:
    """The pick's position this mission, or None to fall back to random fire."""
    pick = site.missile_target
    if pick is None or not can_pick(game, site):
        return None
    target = _lookup(game, pick)
    if target is None or not _still_valid(target, pick.is_base):
        return None
    if not _in_range(site, target.position):
        return None
    return target.position


def target_name(game: Game, pick: MissileTargetPick) -> Optional[str]:
    target = _lookup(game, pick)
    if target is None:
        return None
    if pick.is_base:
        return f"Base: {target.name}"
    return target.obj_name  # type: ignore[union-attr]


def release_spent_picks(game: Game) -> None:
    """Turn end: a dead or captured target frees its site back to random fire."""
    for cp in game.theater.controlpoints:
        for site in cp.ground_objects:
            if not isinstance(site, MissileSiteGroundObject):
                continue
            pick = site.missile_target
            if pick is None:
                continue
            target = _lookup(game, pick)
            if (
                target is None
                or not site.is_friendly(Player.BLUE)
                or not _still_valid(target, pick.is_base)
            ):
                site.missile_target = None
