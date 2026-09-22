"""Where the player's saved points land in the cockpit (§102).

One answer for the cartridge builders and the kneeboard, so the number printed beside a
point is the number the jet gives it. See docs/dev/design/retlab-my-aircraft-notes.md.

- Hornet, Viper, Apache: after the route, on a second route sequence. They write the
  whole navigation set, so points ride only with the Route section.
- Tomcat: flight plan 3 of its own, numbered from 1; the route section is not needed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Sequence

if TYPE_CHECKING:
    from game.ato.flightwaypoint import FlightWaypoint
    from game.ato.savedpoints import SavedPoint
    from game.missiongenerator.aircraft.flightdata import FlightData
    from game.settings import Settings

#: WYPT_NAV.lua caps the set at 59; 58 and 59 are left to HOME and the bullseye.
HORNET_LAST_POINT = 57
#: STPT 25 is the bullseye (viper.MAX_STEERPOINTS); the support anchors fill what
#: the route and the saved points leave.
VIPER_LAST_POINT = 24
#: WPTHZ owns 1-50 (apache.MAX_WAYPOINTS).
APACHE_LAST_POINT = 50
#: A Tomcat plan holds 50 waypoints (tomcat.MAX_WAYPOINTS).
TOMCAT_LAST_POINT = 50
#: The Tomcat plan the saved points take: plan 1 is the ME route, plan 2 ours.
TOMCAT_SAVED_PLAN = 3


def _types() -> tuple[str, str, str, str]:
    from game.missiongenerator.dtc.apache import APACHE_UNIT_TYPE
    from game.missiongenerator.dtc.hornet import HORNET_UNIT_TYPE
    from game.missiongenerator.dtc.tomcat import TOMCAT_UNIT_TYPE
    from game.missiongenerator.dtc.viper import VIPER_UNIT_TYPE

    return HORNET_UNIT_TYPE, VIPER_UNIT_TYPE, TOMCAT_UNIT_TYPE, APACHE_UNIT_TYPE


def is_skipped(flight: FlightData, waypoint: FlightWaypoint) -> bool:
    """A waypoint the planner left out of this flight's cartridge (the DTC tab)."""
    return waypoint.waypoint_type.name in flight.dtc_options.skipped_waypoints


def kept_waypoints(flight: FlightData) -> list[FlightWaypoint]:
    """The flight plan the cartridge writes: row 0 (the spawn) and skipped types
    left out."""
    return [w for w in flight.waypoints[1:] if not is_skipped(flight, w)]


def carries_route(flight: FlightData, settings: Settings) -> bool:
    """Whether the jet's steerpoints come from this flight's cartridge route."""
    hornet, viper, _tomcat, apache = _types()
    if flight.aircraft_type.dcs_unit_type.id not in (hornet, viper, apache):
        return False
    if not flight.friendly.is_blue or not flight.client_units:
        return False
    options = flight.dtc_options
    return options.resolve_enabled(settings.dtc_data_cartridges) and options.route


def route_numbers(flight: FlightData, settings: Settings) -> list[str]:
    """The number the kneeboard's route table prints on each waypoint row.

    The row index normally. When the cartridge carries the route, a skipped row
    reads "-" and the rest close up, as they do in the jet.
    """
    if not carries_route(flight, settings) or not flight.dtc_options.skipped_waypoints:
        return [str(index) for index in range(len(flight.waypoints))]
    numbers = ["0"] if flight.waypoints else []
    number = 0
    for waypoint in flight.waypoints[1:]:
        if is_skipped(flight, waypoint):
            numbers.append("-")
        else:
            number += 1
            numbers.append(str(number))
    return numbers


def cartridge_route_length(flight: FlightData) -> int:
    """How many cockpit numbers the cartridge's route takes: row 0 is not emitted."""
    from game.missiongenerator.dtc.hornet import MAX_WAYPOINTS
    from game.missiongenerator.dtc.viper import MAX_ROUTE_STEERPOINTS

    hornet, viper, tomcat, apache = _types()
    flown = len(kept_waypoints(flight))
    aircraft = flight.aircraft_type.dcs_unit_type.id
    if aircraft == tomcat:
        return 0
    if not flight.dtc_options.route:
        return 0
    if aircraft == hornet:
        return min(flown, MAX_WAYPOINTS)
    if aircraft == viper:
        return min(flown, MAX_ROUTE_STEERPOINTS)
    if aircraft == apache:
        return min(flown, APACHE_LAST_POINT)
    return flown


def carries_saved_points(flight: FlightData, settings: Settings) -> bool:
    """Whether this flight's cartridge will hold its saved points at all."""
    aircraft = flight.aircraft_type.dcs_unit_type.id
    if aircraft not in _types():
        return False
    if not flight.friendly.is_blue or not flight.client_units:
        return False
    options = flight.dtc_options
    if not options.resolve_enabled(settings.dtc_data_cartridges):
        return False
    if not options.saved_points:
        return False
    return aircraft == _types()[2] or options.route


def _last_point(aircraft: str) -> int:
    hornet, viper, tomcat, apache = _types()
    return {
        hornet: HORNET_LAST_POINT,
        viper: VIPER_LAST_POINT,
        tomcat: TOMCAT_LAST_POINT,
        apache: APACHE_LAST_POINT,
    }[aircraft]


def cockpit_numbers(
    flight: FlightData, points: Sequence[SavedPoint]
) -> list[Optional[int]]:
    """The cartridge number of each navigation point; None for one that did not
    fit or is not a navigation point (an orbit goes elsewhere)."""
    number = cartridge_route_length(flight) + 1
    last = _last_point(flight.aircraft_type.dcs_unit_type.id)
    numbers: list[Optional[int]] = []
    for point in points:
        if not point.kind.is_navigation:
            numbers.append(None)
            continue
        numbers.append(number if number <= last else None)
        number += 1
    return numbers


def kneeboard_numbers(flight: FlightData, settings: Settings) -> list[Optional[int]]:
    """What the kneeboard prints beside each saved point.

    The cartridge's number when there is one, the A-10's CDU number, and otherwise the
    next number after the kneeboard's own route rows (which count from 0).
    """
    from game.missiongenerator.a10cdu import AIRCRAFT as A10, numbers_for

    points = flight.saved_points
    if carries_saved_points(flight, settings):
        return cockpit_numbers(flight, points)
    navigation = [p for p in points if p.kind.is_navigation]
    if flight.aircraft_type.dcs_unit_type.id in A10 and flight.client_units:
        numbers = iter(numbers_for(len(flight.waypoints), len(navigation)))
    else:
        start = len(flight.waypoints)
        numbers = iter(range(start, start + len(navigation)))
    return [next(numbers) if p.kind.is_navigation else None for p in points]


#: A player orbit drawn as a box is this wide, the SA page's CAP diameter.
ORBIT_BOX_WIDTH_M = 5 * 1852.0

#: One player shape: its name, its (x, y) corners, and whether it closes.
Shape = tuple[str, list[tuple[float, float]], bool]


def racetrack_box(point: SavedPoint) -> list[tuple[float, float]]:
    """An orbit's four corners: the leg from the point along its heading, widened."""
    import math

    end_x, end_y = point.orbit_end()
    rad = math.radians(point.heading_deg + 90)
    half = ORBIT_BOX_WIDTH_M / 2
    dx, dy = half * math.cos(rad), half * math.sin(rad)
    return [
        (point.x + dx, point.y + dy),
        (end_x + dx, end_y + dy),
        (end_x - dx, end_y - dy),
        (point.x - dx, point.y - dy),
    ]


def player_shapes(flight: FlightData, orbits_as_boxes: bool) -> list[Shape]:
    """The player's orbits (as boxes, where the jet has no orbit element) and then
    their drawings, as the DTC tab allows."""
    from game.ato.savedpoints import PointKind

    options = flight.dtc_options
    shapes: list[Shape] = []
    if orbits_as_boxes and options.saved_points:
        for point in flight.saved_points:
            if point.kind is PointKind.ORBIT:
                shapes.append((point.name, racetrack_box(point), True))
    if options.drawings:
        for drawing in flight.saved_drawings:
            if len(drawing.points) >= 2:
                shapes.append((drawing.name, list(drawing.points), drawing.closed))
    return shapes


def closed_ring(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """The corners with the first repeated, for a line element that cannot close."""
    return points + points[:1] if points and points[0] != points[-1] else points


def saved_orbits(flight: FlightData) -> list[SavedPoint]:
    from game.ato.savedpoints import PointKind

    if not flight.dtc_options.saved_points:
        return []
    return [p for p in flight.saved_points if p.kind is PointKind.ORBIT]
