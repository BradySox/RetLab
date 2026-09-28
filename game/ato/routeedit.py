"""Editing a flight's route from the map: add a NAV point where the route is clicked,
delete one from its marker.

On the package route (packageroute.py) both land on every flight that flies it; the
map is where the package's route is shaped. Anything else changes this flight only.
docs/dev/design/retlab-package-route-notes.md
"""

from __future__ import annotations

import math
from typing import Optional, TYPE_CHECKING

from dcs import Point

from . import packageroute
from .flightplans.navinsert import NOT_ON_ROUTE, identity_index, nav_insert_on_leg

if TYPE_CHECKING:
    from .flight import Flight
    from .flightwaypoint import FlightWaypoint


class RouteEditRefused(Exception):
    """An edit the plan cannot take. The message is for the player."""


def drawn_legs(flight: Flight) -> list[tuple[FlightWaypoint, FlightWaypoint]]:
    """The legs the map draws: the route without the bullseye and the divert."""
    drawn = [
        waypoint
        for waypoint in flight.flight_plan.waypoints
        if waypoint.waypoint_type not in NOT_ON_ROUTE
    ]
    return list(zip(drawn, drawn[1:]))


def nearest_leg(
    flight: Flight, point: Point
) -> Optional[tuple[FlightWaypoint, FlightWaypoint]]:
    legs = drawn_legs(flight)
    if not legs:
        return None
    return min(legs, key=lambda leg: _distance(point, leg[0].position, leg[1].position))


def is_deletable(flight: Flight, waypoint: FlightWaypoint) -> bool:
    """A NAV or custom point; the plan's fixed points go only with a custom plan."""
    return any(
        identity_index(sequence, waypoint) is not None
        for sequence in flight.flight_plan.layout.nav_sequences()
    )


def insert_nav_at(flight: Flight, position: Point) -> list[Flight]:
    """A NAV point at ``position`` on the leg nearest it. Returns the flights moved."""
    leg = nearest_leg(flight, position)
    if leg is None:
        raise RouteEditRefused("This flight has no route to add a point to.")
    start, end = leg
    slot = nav_insert_on_leg(flight.flight_plan.layout, start, end, position)
    if slot is None:
        raise RouteEditRefused(
            f"The plan flies straight from {_label(start)} to {_label(end)}, so a "
            "point cannot go on that leg."
        )
    package = flight.package
    package_leg = packageroute.leg_of(flight, slot.sequence)
    if package_leg is not None:
        index = packageroute.package_index(package, flight, package_leg, slot.index)
        packageroute.insert(package, package_leg, index, position)
        return packageroute.route_flights(package)
    slot.apply()
    return [flight]


def delete_nav(flight: Flight, waypoint: FlightWaypoint) -> list[Flight]:
    """Delete a NAV or custom point. Returns the flights changed."""
    package = flight.package
    on_package = packageroute.find_on_package(package, flight, waypoint)
    if on_package is not None:
        leg, index = on_package
        packageroute.delete(package, leg, index)
        return packageroute.route_flights(package)
    for sequence in flight.flight_plan.layout.nav_sequences():
        at = identity_index(sequence, waypoint)
        if at is not None:
            del sequence[at]
            return [flight]
    raise RouteEditRefused(
        f"{_label(waypoint)} is one of the plan's fixed points: drag it to move it. "
        "Removing it needs a custom plan (the flight's Waypoints tab)."
    )


def _label(waypoint: FlightWaypoint) -> str:
    return waypoint.display_name or waypoint.name


def _distance(point: Point, a: Point, b: Point) -> float:
    dx, dy = b.x - a.x, b.y - a.y
    length_squared = dx * dx + dy * dy
    t = 0.0
    if length_squared > 0:
        t = ((point.x - a.x) * dx + (point.y - a.y) * dy) / length_squared
        t = max(0.0, min(1.0, t))
    return math.hypot(point.x - (a.x + t * dx), point.y - (a.y + t * dy))
