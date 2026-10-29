"""Runway line-up (ALIGN) waypoint and departure hold for player flights.

Adapted from juanjux/dcs-escalation's alignpoint.py (LGPL-3.0). Player flights only:
the 2026-10-26 runway probes showed AI ignore the app's runway pick in light wind.
The runway is RunwayAssigner's into-wind pick, the one the kneeboard names first; a
carrier's is its §88 angled-deck course. docs/dev/retlab-features.md §126.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Optional, TYPE_CHECKING

from dcs.mapping import Point

from game.ato.flightwaypoint import FlightWaypoint
from game.ato.flightwaypointtype import FlightWaypointType
from game.flightplan.carriercruisesolver import solve_carrier_cruise
from game.runways import RunwayData, runway_centerline
from game.utils import Distance, feet, knots, meters, mps, nautical_miles

if TYPE_CHECKING:
    from game.ato.flight import Flight
    from game.theater import ControlPoint

ALIGN_NAME = "ALIGN"
AIRFIELD_DISTANCE = nautical_miles(15)
CARRIER_DISTANCE = nautical_miles(50)
HELICOPTER_DISTANCE = nautical_miles(2)
#: A 3-degree glideslope is about 300 ft per NM; the cap is a Case III marshal.
FEET_PER_NAUTICAL_MILE = 300.0
MIN_ALTITUDE = feet(1500)
MAX_ALTITUDE = feet(6000)
#: The leg lengths GenericCarrierGenerator.steam_into_wind tries, longest first; the
#: ship stops at the end of the one that stays at sea.
CARRIER_LEGS_M = (100000, 80000, 60000, 40000, 20000)


def altitude_for(distance: Distance) -> Distance:
    """Height above the field on a three-degree slope from that distance."""
    on_the_slope = feet(distance.nautical_miles * FEET_PER_NAUTICAL_MILE)
    return max(MIN_ALTITUDE, min(MAX_ALTITUDE, on_the_slope))


def _for_players(flight: Flight, setting: str) -> bool:
    return flight.client_count > 0 and bool(
        getattr(flight.coalition.game.settings, setting, False)
    )


def _airfield_runway(flight: Flight, field: ControlPoint) -> Optional[RunwayData]:
    runway = field.active_runway(field.theater, flight.coalition.game.conditions, {})
    # A field with no runways in its data returns a nameless stub.
    return runway if runway.runway_name else None


def _airfield_axis(field: ControlPoint, runway: RunwayData) -> tuple[Point, float]:
    airport = getattr(field, "airport", None)
    if airport is not None:
        axis = runway_centerline(field.theater, airport, runway.runway_name)
        if axis is not None:
            return axis
    return field.position, runway.runway_heading.degrees


def _deck_angle(carrier: ControlPoint) -> float:
    for ground_object in carrier.ground_objects:
        for group in ground_object.groups:
            for unit in group.units:
                if unit.alive:
                    return float(getattr(unit.unit_type, "landing_deck_angle", 0.0))
    return 0.0


def carrier_course(flight: Flight, carrier: ControlPoint) -> tuple[float, float, float]:
    """The ship's course (BRC), its speed in knots and its landing deck angle."""
    wind = flight.coalition.game.conditions.weather.wind.at_0m
    deck_angle = _deck_angle(carrier)
    result = solve_carrier_cruise(wind.direction, mps(wind.speed).knots, deck_angle)
    return result.heading, max(0.0, result.carrier_speed), deck_angle


def _carrier_leg(carrier: ControlPoint, brc: float) -> Distance:
    for length in CARRIER_LEGS_M:
        end = carrier.position.point_from_heading(brc, length)
        if carrier.theater.is_in_sea(end):
            return meters(length)
    return meters(0)


def _time_to_landing(flight: Flight, plan: Any) -> timedelta:
    # A plan built before its package has a TOT cannot give a landing time; the
    # point then sits on the same bearing, only closer to the ship.
    try:
        delay = plan.landing_time - flight.coalition.game.conditions.start_time
    except Exception:
        return timedelta()
    return delay if delay > timedelta() else timedelta()


def _airfield_waypoint(flight: Flight, field: ControlPoint) -> Optional[FlightWaypoint]:
    runway = _airfield_runway(flight, field)
    if runway is None:
        return None
    distance = HELICOPTER_DISTANCE if flight.is_helo else AIRFIELD_DISTANCE
    origin, course = _airfield_axis(field, runway)
    return FlightWaypoint(
        ALIGN_NAME,
        FlightWaypointType.NAV,
        origin.point_from_heading((course + 180) % 360, distance.meters),
        altitude_for(distance),
        alt_type="RADIO",
        description=f"Established on final for {field.name} runway {runway.runway_name}",
        pretty_name="Line up with the runway",
        only_for_player=True,
    )


def _carrier_waypoint(
    flight: Flight, carrier: ControlPoint, plan: Any
) -> FlightWaypoint:
    brc, speed_kt, deck_angle = carrier_course(flight, carrier)
    steamed = min(
        knots(speed_kt).meters_per_second
        * _time_to_landing(flight, plan).total_seconds(),
        _carrier_leg(carrier, brc).meters,
    )
    recovery = carrier.position.point_from_heading(brc, steamed)
    # The landing area is angled to port of the ship's course.
    final_bearing = (brc - deck_angle) % 360
    distance = HELICOPTER_DISTANCE if flight.is_helo else CARRIER_DISTANCE
    return FlightWaypoint(
        ALIGN_NAME,
        FlightWaypointType.NAV,
        recovery.point_from_heading((final_bearing + 180) % 360, distance.meters),
        altitude_for(distance),
        alt_type="RADIO",
        description=(
            f"{carrier.name} final bearing {final_bearing:03.0f}, "
            f"{distance.nautical_miles:.0f} NM astern of where it will be"
        ),
        pretty_name="Line up with the deck",
        only_for_player=True,
    )


def align_waypoint(flight: Flight, plan: Any) -> Optional[FlightWaypoint]:
    """The ALIGN waypoint for this flight, or None if it does not get one."""
    from game.theater.controlpoint import Airfield, NavalControlPoint

    if not _for_players(flight, "player_runway_lineup"):
        return None
    arrival = flight.arrival
    if isinstance(arrival, Airfield):
        return _airfield_waypoint(flight, arrival)
    if isinstance(arrival, NavalControlPoint):
        return _carrier_waypoint(flight, arrival, plan)
    return None


def hold_point(flight: Flight) -> Optional[Point]:
    """Straight out the departure runway, or None to keep the usual hold."""
    from game.theater.controlpoint import Airfield, NavalControlPoint

    if not _for_players(flight, "player_departure_hold"):
        return None
    departure = flight.departure
    if isinstance(departure, Airfield):
        runway = _airfield_runway(flight, departure)
        if runway is None:
            return None
        origin, course = _airfield_axis(departure, runway)
    elif isinstance(departure, NavalControlPoint):
        origin = departure.position
        course, _, _ = carrier_course(flight, departure)
    else:
        return None
    point = origin.point_from_heading(
        course, flight.coalition.doctrine.hold_distance.meters
    )
    if flight.coalition.opponent.threat_zone.threatened(point):
        return None
    return point


def update_align(flight: Flight, plan: Any) -> None:
    """Add, replace or drop the plan's ALIGN waypoint to match the flight's seats."""
    nav_from = getattr(getattr(plan, "layout", None), "nav_from", None)
    if nav_from is None:
        # A layout with no nav leg home, e.g. a custom plan.
        return
    nav_from[:] = [w for w in nav_from if w.name != ALIGN_NAME]
    waypoint = align_waypoint(flight, plan)
    if waypoint is not None:
        nav_from.append(waypoint)
