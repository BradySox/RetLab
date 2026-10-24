"""Sector war step 2: who holds each sector, saved with the game (§111).

The front line sits where its route crosses from blue sectors into red, and a
base belongs to whoever holds its sector. Owners are kept by sector name, so a
save stays readable if a later landmap fix renumbers the sectors.
See docs/dev/design/retlab-sector-war-notes.md.
"""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING, Any, Optional

import numpy as np
import numpy.typing as npt

from game.theater.frontbattles import battle_stretch_m
from game.theater.player import Player
from game.theater.sectors import (
    BLUE,
    NM,
    RED,
    SectorMap,
    Territory,
    build_territory,
    land_control_points,
    sector_map_for,
    territory_from_labels,
)

if TYPE_CHECKING:
    from game import Game
    from dcs.mapping import Point

    from game.theater import ConflictTheater, ControlPoint, FrontLine

#: A won battle reaches at least this far from the front for sectors to take.
TAKE_REACH_M = 15.0 * NM
#: Spacing of the samples taken along a front's route to find the crossing.
ROUTE_SAMPLE_M = 0.25 * NM


class SectorWar:
    def __init__(self, owners: dict[str, int]) -> None:
        #: Sector name to BLUE or RED. A sector nobody holds is left out.
        self.owners = owners
        #: Bumped on every change, so cached shapes and front positions refresh.
        self.version = 0

    @classmethod
    def start(cls, theater: ConflictTheater) -> SectorWar:
        """Owners from the step 1 territory: bases and the fronts as placed."""
        sector_map = sector_map_for(theater)
        territory = build_territory(theater, sector_map)
        owners = {
            sector_map.sectors[sector_id].name: side
            for sector_id, side in sector_map.owners(territory).items()
            if side is not None
        }
        war = cls(owners)
        war.sync_bases(theater)
        return war

    def owner_array(self, sector_map: SectorMap) -> npt.NDArray[Any]:
        return np.array(
            [self.owners.get(sector.name, -1) for sector in sector_map.sectors],
            dtype=np.int32,
        )

    def territory(self, sector_map: SectorMap) -> Territory:
        owners = self.owner_array(sector_map)
        sector_labels = sector_map.labels
        labels = np.where(
            sector_labels >= 0, owners[np.maximum(sector_labels, 0)], -1
        ).astype(np.int32)
        return territory_from_labels(sector_map.raster, labels)

    def owner_key(self) -> tuple[tuple[str, int], ...]:
        """The owners as a cache key. Not `version`: the shape caches outlive a
        game, and a reloaded save can reach the same version with other owners."""
        return tuple(sorted(self.owners.items()))

    def set_owner(self, sector_name: str, side: int) -> bool:
        if self.owners.get(sector_name) == side:
            return False
        self.owners[sector_name] = side
        self.version += 1
        return True

    def sync_bases(self, theater: ConflictTheater) -> None:
        """Each base's own sector follows the base, after a capture in the mission."""
        by_base = _base_sectors(sector_map_for(theater))
        for cp in land_control_points(theater):
            name = by_base.get(cp.id)
            if name is None or cp.captured.is_neutral:
                continue
            self.set_owner(name, BLUE if cp.captured.is_blue else RED)

    def claim_base(self, theater: ConflictTheater, cp: ControlPoint) -> None:
        """A base taken in the mission takes its own sector with it."""
        name = _base_sectors(sector_map_for(theater)).get(cp.id)
        if name is not None and not cp.captured.is_neutral:
            self.set_owner(name, BLUE if cp.captured.is_blue else RED)

    def take_sectors(self, front: FrontLine, winner: Player, count: int) -> list[str]:
        """The winner takes `count` of the loser's sectors nearest the front.

        Only a sector touching the winner's ground can be taken, so a win pushes
        the border rather than opening a pocket behind it.
        """
        theater = front.coalition.game.theater
        sector_map = sector_map_for(theater)
        neighbours = sector_neighbours(sector_map)
        won = BLUE if winner.is_blue else RED
        lost = RED if won == BLUE else BLUE
        reach = max(battle_stretch_m(front) / 2, TAKE_REACH_M)
        x, y = front.position.x, front.position.y
        taken: list[str] = []
        for _ in range(count):
            candidates = []
            for sector in sector_map.sectors:
                if self.owners.get(sector.name) != lost:
                    continue
                if not any(
                    self.owners.get(sector_map.sectors[other].name) == won
                    for other in neighbours[sector.id]
                ):
                    continue
                distance = math.hypot(sector.seed[0] - x, sector.seed[1] - y)
                if distance <= reach:
                    candidates.append((distance, sector.name))
            if not candidates:
                break
            _, name = min(candidates)
            self.set_owner(name, won)
            taken.append(name)
        return taken

    def fallen_bases(
        self, theater: ConflictTheater
    ) -> list[tuple[ControlPoint, Player]]:
        """Bases whose own sector the other side now holds."""
        by_base = _base_sectors(sector_map_for(theater))
        fallen = []
        for cp in land_control_points(theater):
            name = by_base.get(cp.id)
            if name is None or cp.captured.is_neutral:
                continue
            side = self.owners.get(name)
            if side is None:
                continue
            holder = Player.BLUE if side == BLUE else Player.RED
            if holder != cp.captured:
                fallen.append((cp, holder))
        return fallen

    def route_progress(self, front: FrontLine) -> Optional[float]:
        """Metres from blue's base to where the route enters red's sectors.

        None when the route never meets a sector either side holds.
        """
        sector_map = sector_map_for(front.coalition.game.theater)
        length = front.route_length
        last_blue: Optional[float] = None
        distance = 0.0
        while distance <= length:
            point = front.point_along_route_from_blue(min(distance, length - 1.0))
            sector = sector_map.sector_at(point.x, point.y)
            side = None if sector is None else self.owners.get(sector.name)
            if side == RED:
                if last_blue is None:
                    return 0.0
                return (last_blue + distance) / 2
            if side == BLUE:
                last_blue = distance
            distance += ROUTE_SAMPLE_M
        if last_blue is None:
            return None
        return length


def road_is_cut(theater: ConflictTheater, a: ControlPoint, b: ControlPoint) -> bool:
    """True when the road between two friendly bases runs through enemy sectors.

    A cut road carries no convoys, so its bases lose supply over it (§90 rung A).
    """
    try:
        route = list(a.convoy_route_to(b))
    except KeyError:
        return False
    return _route_is_cut(theater, a, route)


def rail_is_cut(theater: ConflictTheater, a: ControlPoint, b: ControlPoint) -> bool:
    """True when the rail line between two friendly bases runs through enemy sectors."""
    route = a.rail_lines.get(b)
    if route is None:
        return False
    return _route_is_cut(theater, a, list(route))


def _route_is_cut(
    theater: ConflictTheater, a: ControlPoint, route: list[Point]
) -> bool:
    war = war_for(theater)
    if war is None or a.captured.is_neutral:
        return False
    enemy = RED if a.captured.is_blue else BLUE
    sector_map = sector_map_for(theater)
    for start, end in zip(route, route[1:]):
        length = start.distance_to_point(end)
        steps = max(1, int(length // ROUTE_SAMPLE_M))
        for i in range(steps + 1):
            point = start + (end - start) * (i / steps)
            sector = sector_map.sector_at(point.x, point.y)
            if sector is not None and war.owners.get(sector.name) == enemy:
                return True
    return False


def war_for(theater: ConflictTheater) -> Optional[SectorWar]:
    """The theater's sector war when it is on, else None."""
    for cp in theater.controlpoints:
        coalition = getattr(cp, "_coalition", None)
        if coalition is None:
            continue
        return war_of(coalition.game)
    return None


def war_of(game: Game) -> Optional[SectorWar]:
    if not getattr(game.settings, "sector_war", False):
        return None
    return getattr(game, "sector_war", None)


def ensure(game: Game) -> None:
    """Start the war on a new game; keep base sectors in step with captures."""
    if not getattr(game.settings, "sector_war", False):
        return
    try:
        if game.sector_war is None:
            game.sector_war = SectorWar.start(game.theater)
        else:
            game.sector_war.sync_bases(game.theater)
    except Exception:
        logging.exception("Sector war could not start; fronts stay on strength")


def _base_sectors(sector_map: SectorMap) -> dict[Any, str]:
    return {
        sector.control_point_id: sector.name
        for sector in sector_map.sectors
        if sector.control_point_id is not None
    }


_neighbour_cache: dict[int, tuple[SectorMap, list[set[int]]]] = {}


def sector_neighbours(sector_map: SectorMap) -> list[set[int]]:
    """For each sector, the sectors sharing an edge with it on the grid."""
    cached = _neighbour_cache.get(id(sector_map))
    if cached is not None and cached[0] is sector_map:
        return cached[1]
    raster = sector_map.raster
    result: list[set[int]] = [set() for _ in sector_map.sectors]
    if raster.rows:
        grid = sector_map.labels.reshape(raster.rows, raster.cols)
        for a, b in (
            (grid[:-1, :], grid[1:, :]),
            (grid[:, :-1], grid[:, 1:]),
        ):
            mask = (a != b) & (a >= 0) & (b >= 0)
            pairs = np.unique(np.stack([a[mask], b[mask]], axis=1), axis=0)
            for left, right in pairs.tolist():
                result[left].add(right)
                result[right].add(left)
    _neighbour_cache.clear()
    _neighbour_cache[id(sector_map)] = (sector_map, result)
    return result
