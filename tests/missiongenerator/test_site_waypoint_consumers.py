"""What still reads each unit once Strike and DEAD fly one steerpoint per site."""

from datetime import datetime
from types import SimpleNamespace
from typing import Any

from dcs.mapping import Point
from dcs.terrain import Caucasus

from game.ato.flightwaypoint import FlightWaypoint
from game.ato.flightwaypointtype import FlightWaypointType
from game.missiongenerator.briefinggenerator import format_waypoint_time
from game.missiongenerator.dtc.tomcat import _aimpoints
from game.missiongenerator.kneeboard import StrikeTaskPage
from game.theater.theatergroup import TheaterUnit


def _unit(name: str, x: float, y: float) -> TheaterUnit:
    unit = TheaterUnit.__new__(TheaterUnit)
    unit.name = name
    unit.type = SimpleNamespace(name=name)  # type: ignore[assignment]
    unit.position = Point(x, y, Caucasus())  # type: ignore[assignment]
    return unit


def _site(units: list[TheaterUnit]) -> FlightWaypoint:
    waypoint = FlightWaypoint(
        "STRIKE Depot",
        FlightWaypointType.TARGET_POINT,
        Point(0, 0, Caucasus()),
        pretty_name="STRIKE Depot",
    )
    waypoint.targets = units
    return waypoint


def test_tomcat_jdam_gets_a_point_per_unit_of_a_site() -> None:
    units = [_unit("Bunker", 100, 200), _unit("Hangar", 300, 400)]
    points = _aimpoints(_site(units))
    assert [p.position for p in points] == [u.position for u in units]
    assert [p.display_name for p in points] == ["Bunker", "Hangar"]
    assert all(p.waypoint_type is FlightWaypointType.TARGET_POINT for p in points)


def test_tomcat_jdam_keeps_a_plain_target_waypoint() -> None:
    waypoint = _site([])
    assert _aimpoints(waypoint) == [waypoint]


def test_strike_page_lists_every_unit_under_the_site_stpt() -> None:
    units = [_unit("Bunker", 100, 200), _unit("Hangar", 300, 400)]
    route = FlightWaypoint("IP", FlightWaypointType.INGRESS_STRIKE, Point(0, 0, None))  # type: ignore[arg-type]
    page: Any = StrikeTaskPage.__new__(StrikeTaskPage)
    page.flight = SimpleNamespace(waypoints=[route, _site(units)])
    assert list(page.aimpoints) == [
        (1, "Bunker", units[0].position),
        (1, "Hangar", units[1].position),
    ]


def test_briefing_waypoint_times_are_whole_seconds() -> None:
    waypoint = FlightWaypoint("TGT", FlightWaypointType.TARGET_POINT, Point(0, 0, None))  # type: ignore[arg-type]
    waypoint.tot = datetime(2026, 9, 29, 16, 48, 45, 990669)
    assert format_waypoint_time(waypoint, "Depart ") == "16:48:45 "
    waypoint.tot = None
    waypoint.departure_time = datetime(2026, 9, 29, 16, 54, 51, 164485)
    assert format_waypoint_time(waypoint, "Depart ") == "Depart  16:54:51 "
