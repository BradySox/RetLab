"""The package route: the way in (JOIN -> IP) and out (target -> SPLIT) that every
formation flight in a package flies together.

A NAV point on those legs belongs to the package. Put on one flight alone, that flight
reaches the join early by its own detour and the formation no longer meets. So an edit
here lands on every flight that flies the route, and the points are kept on the
package (PackageWaypoints.ingress_nav / egress_nav), where the planner reads them for
a flight added or recreated later.

Until the player edits a leg it is the planner's: each flight carries the SAM detour
formationattack.package_route_points computes. The first edit seeds the leg from the
primary flight, which is the route the package actually flies.

docs/dev/design/retlab-package-route-notes.md
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional, TYPE_CHECKING

from dcs import Point

from .flightplans.airassault import AirAssaultLayout
from .flightplans.escort import EscortFlightPlan
from .flightplans.formationattack import (
    FormationAttackFlightPlan,
    FormationAttackLayout,
    package_route_points,
)
from .flightplans.navinsert import identity_index
from .flightplans.waypointbuilder import WaypointBuilder
from .flightwaypointtype import FlightWaypointType

if TYPE_CHECKING:
    from .flight import Flight
    from .flightwaypoint import FlightWaypoint
    from .package import Package
    from .packagewaypoints import PackageWaypoints


class Leg(Enum):
    IN = "Way in"
    OUT = "Way out"


#: The package's own points besides the NAVs and the IP (any INGRESS type): a drag
#: of one moves it for every flight (game/server/waypoints/routes.py).
PACKAGE_POINT_TYPES = frozenset(
    {FlightWaypointType.JOIN, FlightWaypointType.SPLIT, FlightWaypointType.REFUEL}
)


class Kind(Enum):
    JOIN = "Join"
    NAV = "Nav"
    IP = "Ingress (IP)"
    TARGET = "Target"
    SPLIT = "Split"


@dataclass(frozen=True)
class RoutePoint:
    """One point of the package route, in the order it is flown."""

    kind: Kind
    position: Point
    #: Where a NAV point sits: its leg and its place along it.
    leg: Optional[Leg] = None
    index: int = 0


def flies_package_route(flight: Flight) -> bool:
    """A formation attack plan with both legs in its route.

    Helicopters join at the IP and fly their own low-level legs; an air assault's
    route leaves both legs out; a custom plan has no structure left to share.
    """
    if flight.is_helo:
        return False
    plan = flight.flight_plan
    return isinstance(plan, FormationAttackFlightPlan) and not isinstance(
        plan.layout, AirAssaultLayout
    )


def route_flights(package: Package) -> list[Flight]:
    """The flights that fly the package route. None unless the primary does."""
    primary = package.primary_flight
    if primary is None or not flies_package_route(primary):
        return []
    return [flight for flight in package.flights if flies_package_route(flight)]


def on_package_route(flight: Flight) -> bool:
    """Whether ``flight`` flies its package's route: an escort in a package whose
    primary flies its own way (an air assault) has no package route to share."""
    return any(other is flight for other in route_flights(flight.package))


def speaks_for_package(flight: Flight) -> bool:
    """Whether a drag of this flight's join, IP, split or refuel moves the package's.

    Upstream let only the primary do it. Any flight on the package route may, so the
    map works whichever flight of the package is selected.
    """
    return flight is flight.package.primary_flight or on_package_route(flight)


def moves_package(flight: Flight, waypoint: FlightWaypoint) -> bool:
    """Whether dragging ``waypoint`` on the map moves it for every flight."""
    package = flight.package
    if package.waypoints is None or not speaks_for_package(flight):
        return False
    found = find(flight, waypoint)
    if found is not None:
        return in_step(package, flight, found[0])
    kind = waypoint.waypoint_type
    return kind in PACKAGE_POINT_TYPES or "INGRESS" in kind.name


def sequence(flight: Flight, leg: Leg) -> list[FlightWaypoint]:
    """The flight's own nav points on ``leg``."""
    layout = flight.flight_plan.layout
    assert isinstance(layout, FormationAttackLayout)
    return layout.ingress_nav if leg is Leg.IN else layout.egress_nav


def leg_of(flight: Flight, nav_list: list[FlightWaypoint]) -> Optional[Leg]:
    """Which package leg ``nav_list`` is in ``flight``'s plan, if it is one."""
    if not on_package_route(flight):
        return None
    for leg in Leg:
        if sequence(flight, leg) is nav_list:
            return leg
    return None


def find(flight: Flight, waypoint: FlightWaypoint) -> Optional[tuple[Leg, int]]:
    """The leg and index of ``waypoint`` on ``flight``'s package route, if it is on it."""
    if not on_package_route(flight):
        return None
    for leg in Leg:
        index = identity_index(sequence(flight, leg), waypoint)
        if index is not None:
            return leg, index
    return None


def package_index(package: Package, flight: Flight, leg: Leg, flight_index: int) -> int:
    """Where ``flight_index`` along the flight's own ``leg`` falls on the package's.

    The same number unless the flight carries a point of its own there, which the
    package does not have and so does not count.
    """
    shared = points(package, leg)
    return sum(
        1
        for waypoint in sequence(flight, leg)[:flight_index]
        if any(waypoint.position == point for point in shared)
    )


def find_on_package(
    package: Package, flight: Flight, waypoint: FlightWaypoint
) -> Optional[tuple[Leg, int]]:
    """``waypoint``'s leg and index on the package route; None if the flight's own."""
    found = find(flight, waypoint)
    if found is None:
        return None
    leg, index = found
    if not any(waypoint.position == point for point in points(package, leg)):
        return None
    return leg, package_index(package, flight, leg, index)


def in_step(package: Package, flight: Flight, leg: Leg) -> bool:
    """Whether the flight's points on ``leg`` are the package's, one for one."""
    return len(sequence(flight, leg)) == len(points(package, leg))


def is_edited(package: Package) -> bool:
    """Whether the player has set either leg, rather than the planner."""
    waypoints = package.waypoints
    return waypoints is not None and (
        waypoints.ingress_nav is not None or waypoints.egress_nav is not None
    )


def points(package: Package, leg: Leg) -> list[Point]:
    """The leg's nav points: the player's, or the primary flight's as planned."""
    waypoints = package.waypoints
    if waypoints is not None:
        edited = _edited(waypoints, leg)
        if edited is not None:
            return list(edited)
    primary = package.primary_flight
    if primary is None or not route_flights(package):
        return []
    return [_copy(waypoint.position) for waypoint in sequence(primary, leg)]


def route_points(package: Package) -> list[RoutePoint]:
    """The route as the package flies it: join, way in, IP, target, way out, split."""
    waypoints = package.waypoints
    if waypoints is None or not route_flights(package):
        return []
    return [
        RoutePoint(Kind.JOIN, waypoints.join),
        *(
            RoutePoint(Kind.NAV, point, Leg.IN, index)
            for index, point in enumerate(points(package, Leg.IN))
        ),
        RoutePoint(Kind.IP, waypoints.ingress),
        RoutePoint(Kind.TARGET, package.target.position),
        *(
            RoutePoint(Kind.NAV, point, Leg.OUT, index)
            for index, point in enumerate(points(package, Leg.OUT))
        ),
        RoutePoint(Kind.SPLIT, waypoints.split),
    ]


def insert_beside(package: Package, row: int) -> Optional[tuple[Leg, int]]:
    """A NAV point halfway along the leg after ``route_points(package)[row]``.

    The IP and the split end their legs, so theirs goes on the leg before them.
    Returns the leg and index it took, or None if there is no such row.
    """
    rows = route_points(package)
    if not 0 <= row < len(rows):
        return None
    point = rows[row]
    if point.kind in (Kind.IP, Kind.SPLIT):
        leg = Leg.IN if point.kind is Kind.IP else Leg.OUT
        index = len(points(package, leg))
        other = rows[row - 1]
    else:
        leg = Leg.OUT if point.kind is Kind.TARGET else point.leg or Leg.IN
        index = 0 if point.kind is not Kind.NAV else point.index + 1
        other = rows[row + 1]
    insert(package, leg, index, point.position.lerp(other.position, 0.5))
    return leg, index


def insert(package: Package, leg: Leg, index: int, position: Point) -> None:
    """A NAV point at ``position``, ``index`` along ``leg``, in every flight."""
    edited = points(package, leg)
    count = len(edited)
    index = max(0, min(index, count))
    edited.insert(index, _copy(position))

    def add(nav_list: list[FlightWaypoint], flight: Flight) -> None:
        nav_list.insert(index, _nav(flight, leg, nav_list, index, position))

    _commit(package, leg, edited, count, add)


def delete(package: Package, leg: Leg, index: int) -> None:
    edited = points(package, leg)
    count = len(edited)
    if not 0 <= index < count:
        return
    del edited[index]

    def remove(nav_list: list[FlightWaypoint], _flight: Flight) -> None:
        del nav_list[index]

    _commit(package, leg, edited, count, remove)


def move(package: Package, leg: Leg, index: int, direction: int) -> bool:
    """One place along ``leg`` (``direction`` -1 or +1). False at either end."""
    edited = points(package, leg)
    target = index + direction
    if not (0 <= index < len(edited) and 0 <= target < len(edited)):
        return False
    edited[index], edited[target] = edited[target], edited[index]

    def swap(nav_list: list[FlightWaypoint], _flight: Flight) -> None:
        nav_list[index], nav_list[target] = nav_list[target], nav_list[index]

    _commit(package, leg, edited, len(edited), swap)
    return True


def set_position(package: Package, leg: Leg, index: int, position: Point) -> None:
    """Move one point, for every flight: a drag on the primary's route."""
    edited = points(package, leg)
    if not 0 <= index < len(edited):
        return
    edited[index] = _copy(position)
    _commit(package, leg, edited, len(edited), None)


def reset(package: Package) -> None:
    """Both legs back to the planner's detour, for every flight."""
    waypoints = package.waypoints
    flights = route_flights(package)
    if waypoints is None or not flights:
        return
    waypoints.ingress_nav = None
    waypoints.egress_nav = None
    planned = package_route_points(package, flights[0].coalition, planned=True)
    for flight in flights:
        for leg, leg_points in zip(Leg, planned):
            nav_list = sequence(flight, leg)
            nav_list[:] = [_planned_nav(flight, point) for point in leg_points]


def _commit(
    package: Package,
    leg: Leg,
    edited: list[Point],
    count: int,
    edit: Optional[Callable[[list[FlightWaypoint], Flight], None]],
) -> None:
    """Store the leg on the package and bring every flight's copy into line with it.

    A flight whose points match the package's count takes the edit itself, which
    keeps its own altitudes and names; one that does not (a point added to it alone)
    is rebuilt from the package's. Either way the positions end up the package's.
    """
    waypoints = package.waypoints
    flights = route_flights(package)
    if waypoints is None or not flights:
        return
    _set_edited(waypoints, leg, edited)
    for flight in flights:
        nav_list = sequence(flight, leg)
        if edit is not None and len(nav_list) == count:
            edit(nav_list, flight)
        if len(nav_list) != len(edited):
            nav_list[:] = [_planned_nav(flight, point) for point in edited]
        for waypoint, point in zip(nav_list, edited):
            waypoint.position = _copy(point)


def _nav(
    flight: Flight,
    leg: Leg,
    nav_list: list[FlightWaypoint],
    index: int,
    position: Point,
) -> FlightWaypoint:
    """A NAV point for ``flight``, at the height of the leg either side of it."""
    before, after = _ends(flight, leg)
    if index > 0:
        before = nav_list[index - 1]
    if index < len(nav_list):
        after = nav_list[index]
    waypoint = WaypointBuilder.nav(_copy(position), max(before.alt, after.alt))
    # The escort builder's rule: AI escorts fly the Escort task off the join.
    waypoint.only_for_player = isinstance(flight.flight_plan, EscortFlightPlan)
    return waypoint


def _planned_nav(flight: Flight, position: Point) -> FlightWaypoint:
    """A NAV point as the planner would build it for ``flight``."""
    builder = WaypointBuilder(flight)
    escort = isinstance(flight.flight_plan, EscortFlightPlan)
    altitude = builder.get_cruise_altitude if escort else builder.get_combat_altitude
    waypoint = builder.nav(_copy(position), altitude)
    waypoint.only_for_player = escort
    return waypoint


def _ends(flight: Flight, leg: Leg) -> tuple[FlightWaypoint, FlightWaypoint]:
    layout = flight.flight_plan.layout
    assert isinstance(layout, FormationAttackLayout)
    if leg is Leg.IN:
        return layout.join, layout.lineup or layout.ingress
    return layout.targets[-1], layout.split


def _edited(waypoints: PackageWaypoints, leg: Leg) -> Optional[list[Point]]:
    return waypoints.ingress_nav if leg is Leg.IN else waypoints.egress_nav


def _set_edited(waypoints: PackageWaypoints, leg: Leg, edited: list[Point]) -> None:
    if leg is Leg.IN:
        waypoints.ingress_nav = edited
    else:
        waypoints.egress_nav = edited


def _copy(point: Point) -> Point:
    return point.new_in_same_map(point.x, point.y)
