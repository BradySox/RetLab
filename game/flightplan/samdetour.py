"""Nav points that take a package's straight legs around SAM rings it need not enter.

JOIN -> INGRESS and TARGET -> SPLIT are straight lines, and the coalition navmesh
treats every overlapping ring as one blob, so it cannot help inside one. Here the
navmesh is rebuilt without the rings the package has to enter anyway (those covering
the target or a leg's end point) and the leg is routed through that. Gated by
``route_around_sams``.
"""

from __future__ import annotations

from typing import Iterable, TYPE_CHECKING

from dcs.mapping import Point
from shapely.geometry import LineString, Point as ShapelyPoint, Polygon
from shapely.ops import unary_union

from game.navmesh import NavMesh, NavMeshError
from game.threatzones import ThreatZones
from game.utils import nautical_miles

if TYPE_CHECKING:
    from game.ato.package import Package
    from game.coalition import Coalition
    from game.theater import ConflictTheater

#: Same floor ThreatZones.for_threats applies: shorter systems are not avoided.
MIN_THREAT_RANGE = nautical_miles(3)
#: A leg end point this close inside a ring's edge does not pin the ring. Joins and
#: splits are placed on the threat edge and then nudged up to 1 NM.
EDGE_TOLERANCE = nautical_miles(5)
#: A detour longer than this multiple of the straight leg is not flown.
MAX_LENGTH_FACTOR = 2.0

RingKey = tuple[float, float, float]


class SamRing:
    def __init__(self, x: float, y: float, radius: float) -> None:
        self.key: RingKey = (round(x), round(y), round(radius))
        self.center = ShapelyPoint(x, y)
        self.radius = radius
        self.shape: Polygon = self.center.buffer(radius)

    def must_enter(self, point: ShapelyPoint) -> bool:
        return self.center.distance(point) < self.radius - EDGE_TOLERANCE.meters


def sam_rings(coalition: Coalition) -> list[SamRing]:
    """The opponent's air-defence rings, one per site at its longest reach."""
    game = coalition.game
    cap = nautical_miles(game.settings.max_threat_range)
    rings = []
    for cp in game.theater.control_points_for(coalition.opponent.player):
        for tgo in cp.ground_objects:
            if not tgo.has_aa:
                continue
            threat_range = min(tgo.max_threat_range(), cap)
            if threat_range > MIN_THREAT_RANGE:
                rings.append(
                    SamRing(tgo.position.x, tgo.position.y, threat_range.meters)
                )
    return rings


def _exposure(points: list[ShapelyPoint], rings: list[SamRing]) -> float:
    line = LineString(points)
    return sum(line.intersection(ring.shape).length for ring in rings)


_mesh_cache: dict[tuple[int, frozenset[RingKey]], NavMesh] = {}


def _mesh(theater: ConflictTheater, rings: list[SamRing]) -> NavMesh:
    key = (id(theater), frozenset(r.key for r in rings))
    if key not in _mesh_cache:
        if len(_mesh_cache) > 32:
            _mesh_cache.clear()
        zones = ThreatZones(
            theater,
            airbases=Polygon(),
            air_defenses=unary_union([r.shape for r in rings]),
            radar_sam_threats=Polygon(),
        )
        _mesh_cache[key] = NavMesh.from_threat_zones(zones, theater)
    return _mesh_cache[key]


def _prune(points: list[ShapelyPoint], rings: list[SamRing]) -> list[ShapelyPoint]:
    """Drop turn points that buy no less exposure than cutting the corner."""
    kept = [points[0]]
    for current, nxt in zip(points[1:-1], points[2:]):
        via = _exposure([kept[-1], current, nxt], rings)
        if _exposure([kept[-1], nxt], rings) > via:
            kept.append(current)
    kept.append(points[-1])
    return kept


def detour(
    theater: ConflictTheater,
    start: Point,
    end: Point,
    rings: list[SamRing],
    must_enter: Iterable[Point] = (),
) -> list[Point]:
    """Nav points for start -> end that go round every ring it need not enter.

    Empty when the straight leg is clear, or when the detour is too long or no
    less exposed than flying straight.
    """
    a = ShapelyPoint(start.x, start.y)
    b = ShapelyPoint(end.x, end.y)
    fixed = [a, b] + [ShapelyPoint(p.x, p.y) for p in must_enter]
    avoid = [r for r in rings if not any(r.must_enter(p) for p in fixed)]
    straight_exposure = _exposure([a, b], avoid)
    if straight_exposure == 0:
        return []
    try:
        path = _mesh(theater, avoid).shortest_path(start, end)
    except NavMeshError:
        return []
    points = _prune(
        [a, *(ShapelyPoint(p.x, p.y) for p in path[1:-1]), b],
        avoid,
    )
    if LineString(points).length > LineString([a, b]).length * MAX_LENGTH_FACTOR:
        return []
    if _exposure(points, avoid) >= straight_exposure:
        return []
    return [start.new_in_same_map(p.x, p.y) for p in points[1:-1]]


def package_detour(
    package: Package, coalition: Coalition, start: Point, end: Point
) -> list[Point]:
    """``detour`` for one of a package's straight legs, or [] when the gate is off."""
    if not coalition.game.settings.route_around_sams:
        return []
    return detour(
        coalition.game.theater,
        start,
        end,
        sam_rings(coalition),
        [package.target.position],
    )
