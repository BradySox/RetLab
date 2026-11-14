"""Nav points that take a flight's straight legs around SAM rings it need not enter.

The coalition navmesh merges enemy fighter range and every SAM ring into one blob and
flies straight once inside it, so rings deep in enemy ground were ignored. Here each
leg is rerouted on a mesh of the rings alone, minus those it has to enter anyway
(covering the target or a leg's end point). Every fixed-wing flight's transit legs
get this (``WaypointBuilder.nav_path``), and a package's JOIN -> INGRESS and
TARGET -> SPLIT legs. Blue avoids only the sites it knows. Gated by
``route_around_sams``. Details: docs/dev/retlab-features.md section 69, Route around SAMs.
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
    from game.ato.flight import Flight
    from game.ato.package import Package
    from game.coalition import Coalition
    from game.theater import ConflictTheater

#: Same floor ThreatZones.for_threats applies: shorter systems are not avoided.
MIN_THREAT_RANGE = nautical_miles(3)
#: A leg end point this close inside a ring's edge does not pin the ring. Joins and
#: splits are placed on the threat edge and then nudged up to 1 NM.
EDGE_TOLERANCE = nautical_miles(5)
#: A detour longer than this multiple of the straight leg is not flown.
MAX_LENGTH_FACTOR = 1.5

RingKey = tuple[float, float, float]


class SamRing:
    def __init__(self, x: float, y: float, radius: float, name: str = "") -> None:
        self.key: RingKey = (round(x), round(y), round(radius))
        self.name = name
        self.center = ShapelyPoint(x, y)
        self.radius = radius
        self.shape: Polygon = self.center.buffer(radius)

    def must_enter(self, point: ShapelyPoint) -> bool:
        return self.center.distance(point) < self.radius - EDGE_TOLERANCE.meters


#: Sites die, are repaired and are found only between turns, so the rings hold for
#: a turn; every transit leg of every flight asks.
_rings_cache: dict[tuple[int, int, str], list[SamRing]] = {}


def sam_rings(coalition: Coalition) -> list[SamRing]:
    """The opponent's air-defence rings, one per site at its longest reach.

    Blue's are the sites it knows: a bend round an unseen site would give it away.
    Red plans on ground truth.
    """
    game = coalition.game
    key = (id(game), game.turn, coalition.player.name)
    if key not in _rings_cache:
        if len(_rings_cache) > 8:
            _rings_cache.clear()
        _rings_cache[key] = _sam_rings(coalition)
    return _rings_cache[key]


def _sam_rings(coalition: Coalition) -> list[SamRing]:
    from game.theater.fogofwar import fog_intact

    game = coalition.game
    cap = nautical_miles(game.settings.max_threat_range)
    viewer = coalition.player if coalition.player.is_blue else None
    rings = []
    with fog_intact():
        for cp in game.theater.control_points_for(coalition.opponent.player):
            for tgo in cp.ground_objects:
                if not tgo.has_aa or not tgo.known_for(viewer):
                    continue
                threat_range = min(tgo.max_threat_range(), cap)
                if threat_range > MIN_THREAT_RANGE:
                    rings.append(
                        SamRing(
                            tgo.position.x,
                            tgo.position.y,
                            threat_range.meters,
                            tgo.name,
                        )
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


def flight_detour(flight: Flight, points: list[Point]) -> list[Point]:
    """``points`` (a nav path, ends included) with each leg bent round the rings.

    Unchanged when the gate is off, for a helicopter, or with no ring in the way.
    """
    if len(points) < 2 or flight.is_helo:
        return points
    coalition = flight.coalition
    if not coalition.game.settings.route_around_sams:
        return points
    rings = sam_rings(coalition)
    if not rings:
        return points
    must_enter = [flight.package.target.position]
    routed = [points[0]]
    for start, end in zip(points, points[1:]):
        routed.extend(detour(coalition.game.theater, start, end, rings, must_enter))
        routed.append(end)
    return routed


def rings_crossed(flight: Flight) -> list[str]:
    """Known enemy sites whose ring this flight's route still crosses.

    Rings covering the target or a route point are left out: the flight is meant
    to be there.
    """
    if flight.is_helo or flight.flight_plan is None:
        return []
    route = [
        w.position
        for w in flight.flight_plan.iter_waypoints()
        if w.waypoint_type.name != "BULLSEYE"
    ]
    if len(route) < 2:
        return []
    fixed = [ShapelyPoint(p.x, p.y) for p in route] + [
        ShapelyPoint(flight.package.target.position.x, flight.package.target.position.y)
    ]
    line = LineString([(p.x, p.y) for p in route])
    return sorted(
        {
            ring.name
            for ring in sam_rings(flight.coalition)
            if ring.name
            and line.intersects(ring.shape)
            and not any(ring.must_enter(p) for p in fixed)
        }
    )


def package_ring_warnings(package: Package) -> list[str]:
    """One line per flight whose route still crosses a known SAM ring."""
    lines = []
    for flight in package.flights:
        sites = rings_crossed(flight)
        if sites:
            lines.append(
                f"{flight.flight_type.value} ({flight.unit_type.display_name}) "
                f"crosses the SAM ring at {', '.join(sites)}"
            )
    return lines
