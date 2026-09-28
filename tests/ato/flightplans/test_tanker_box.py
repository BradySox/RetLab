"""The experimental four-point tanker box (``tanker_box_orbit``)."""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest
from dcs import Point
from dcs.mission import Mission
from dcs.drawing.drawings import StandardLayer
from dcs.terrain import Caucasus

from game.ato.flighttype import FlightType
from game.ato.flightplans.refuelingflightplan import TankerBoxLayout, orbit_leg_end
from game.ato.flightplans.theaterrefueling import (
    TANKER_BOX_DEPTH,
    Builder,
    TheaterRefuelingFlightPlan,
)
from game.ato.flightplans.waypointbuilder import WaypointBuilder
from game.ato.flightwaypoint import FlightWaypoint
from game.ato.flightwaypointtype import FlightWaypointType
from game.missiongenerator.aircraft.waypoints.racetrackend import (
    RaceTrackEndBuilder,
)
from game.missiongenerator.drawingsgenerator import DrawingsGenerator
from game.theater.player import Player
from game.utils import Heading, feet, knots, nautical_miles

TERRAIN = Caucasus()
NOW = datetime(2020, 1, 1, 12, 0, 0)
ALT = feet(24000)


def _p(x: float, y: float) -> Point:
    return Point(x, y, TERRAIN)


def _wp(name: str, kind: FlightWaypointType) -> FlightWaypoint:
    return FlightWaypoint(name, kind, _p(0, 0), ALT)


class _FakeWaypointBuilder:
    nav = staticmethod(WaypointBuilder.nav)
    race_track_start = staticmethod(WaypointBuilder.race_track_start)
    race_track_end = staticmethod(WaypointBuilder.race_track_end)

    def takeoff(self, _: Any) -> FlightWaypoint:
        return _wp("takeoff", FlightWaypointType.TAKEOFF)

    def land(self, _: Any) -> FlightWaypoint:
        return _wp("land", FlightWaypointType.LANDING_POINT)

    def divert(self, _: Any) -> None:
        return None

    def bullseye(self) -> FlightWaypoint:
        return _wp("bullseye", FlightWaypointType.BULLSEYE)

    def nav_path(self, a: Point, b: Point, alt: Any) -> list[FlightWaypoint]:
        return []


def _box() -> TankerBoxLayout:
    builder = Builder.__new__(Builder)
    builder.flight = SimpleNamespace(  # type: ignore[assignment]
        departure=SimpleNamespace(position=_p(-100000, 0)),
        arrival=SimpleNamespace(position=_p(-100000, 0)),
        divert=None,
    )
    # Front leg 40 NM along y; the threat is +x, so the box extends to -x.
    return builder._box_layout(
        _FakeWaypointBuilder(),  # type: ignore[arg-type]
        _p(0, 0),
        _p(0, nautical_miles(40).meters),
        Heading.from_degrees(180),
        ALT,
    )


def test_the_box_front_leg_is_the_racetrack_and_it_extends_back() -> None:
    box = _box()
    depth = TANKER_BOX_DEPTH.meters
    b, c, d = (w.position for w in box.box_corners)
    assert (b.x, b.y) == pytest.approx((0, nautical_miles(40).meters))
    assert (c.x, c.y) == pytest.approx((-depth, nautical_miles(40).meters), abs=1)
    assert (d.x, d.y) == pytest.approx((-depth, 0), abs=1)
    assert box.patrol_end.position.distance_to_point(box.patrol_start.position) < 1


def test_the_route_runs_start_corners_end() -> None:
    box = _box()
    route = [w.name for w in box.iter_waypoints()]
    assert route[1:6] == ["BOX 1", "BOX 2", "BOX 3", "BOX 4", "BOX END"]
    assert box.patrol_start.waypoint_type is FlightWaypointType.PATROL_TRACK
    assert box.patrol_end.waypoint_type is FlightWaypointType.PATROL
    assert all(w.waypoint_type is FlightWaypointType.NAV for w in box.box_corners)


def _plan(box: TankerBoxLayout) -> TheaterRefuelingFlightPlan:
    settings = SimpleNamespace(
        desired_tanker_on_station_time=timedelta(minutes=60),
        tanker_orbit_speed_set=False,
    )
    plan = TheaterRefuelingFlightPlan.__new__(TheaterRefuelingFlightPlan)
    plan.flight = SimpleNamespace(  # type: ignore[assignment]
        coalition=SimpleNamespace(game=SimpleNamespace(settings=settings)),
        unit_type=SimpleNamespace(patrol_speed=knots(420)),
    )
    plan.layout = box
    plan.tot_offset = timedelta()
    plan.travel_time_between_waypoints = lambda a, b: timedelta(  # type: ignore[method-assign]
        hours=a.position.distance_to_point(b.position) / 1852 / 420
    )
    return plan


def test_the_box_legs_add_up_to_the_on_station_time() -> None:
    box = _box()
    plan = _plan(box)
    legs = [box.patrol_start, *box.box_corners, box.patrol_end]
    total = sum(
        (plan.total_time_between_waypoints(a, b) for a, b in zip(legs, legs[1:])),
        timedelta(),
    )
    assert total == pytest.approx(timedelta(minutes=60), abs=timedelta(seconds=1))


def test_the_box_charges_a_full_station_of_fuel() -> None:
    box = _box()
    plan = _plan(box)
    legs = [box.patrol_start, *box.box_corners, box.patrol_end]
    burned = sum(
        plan.fuel_burn_distance_between_points(a, b).nautical_miles
        for a, b in zip(legs, legs[1:])
    )
    assert burned == pytest.approx(420, abs=1)


def test_receivers_meet_the_box_on_its_front_leg() -> None:
    box = _box()
    assert orbit_leg_end(box) is box.box_corners[0]
    racetrack = SimpleNamespace(patrol_end="end")
    assert orbit_leg_end(racetrack) == "end"


def test_the_box_end_loops_back_to_the_first_corner_while_on_station() -> None:
    box = _box()
    plan = _plan(box)
    plan.flight.package = SimpleNamespace(time_over_target=NOW + timedelta(minutes=30))  # type: ignore[assignment]
    builder = RaceTrackEndBuilder.__new__(RaceTrackEndBuilder)
    builder.flight = SimpleNamespace(flight_plan=plan)  # type: ignore[assignment]
    builder.now = NOW
    # Takeoff, BOX 1, BOX 2-4, BOX END: DCS indices 1-6.
    points = [SimpleNamespace(speed=0.0) for _ in range(6)]
    builder.group = SimpleNamespace(points=points)  # type: ignore[assignment]
    end = SimpleNamespace(tasks=[])
    end.add_task = end.tasks.append

    builder._loop_box(end)  # type: ignore[arg-type]

    (loop,) = end.tasks
    action = loop.params["task"]["params"]["action"]["params"]
    assert action == {"goToWaypointIndex": 3, "fromWaypointIndex": 6}
    stop = int((plan.patrol_end_time - NOW).total_seconds())
    assert loop.params["condition"]["condition"] == f"return timer.getTime() < {stop}"
    assert [p.speed for p in points[2:]] == [knots(420).meters_per_second] * 4
    assert points[1].speed == 0.0


def test_the_f10_marker_draws_the_box() -> None:
    m = Mission(Caucasus())
    box = _box()
    tanker = SimpleNamespace(
        flight_type=FlightType.REFUELING,
        friendly=Player.BLUE,
        waypoints=[box.patrol_start, *box.box_corners, box.patrol_end],
        group_name="Tanker 1",
        callsign="ARCO",
        aircraft_type=SimpleNamespace(display_name="KC-135"),
        patrol_speed=knots(420),
    )
    mission_data = SimpleNamespace(tankers=[], awacs=[], flights=[tanker])
    gen = DrawingsGenerator(m, SimpleNamespace(), mission_data)  # type: ignore[arg-type]
    gen.generate_support_orbits()

    orbit = next(
        o
        for o in m.drawings.get_layer(StandardLayer.Blue).objects
        if o.name == "ARCO orbit"
    )
    xs = [orbit.position.x + p.x for p in orbit.points]
    ys = [orbit.position.y + p.y for p in orbit.points]
    # Encloses every corner, not a circle at the start.
    assert min(xs) < -TANKER_BOX_DEPTH.meters < 0 < max(xs)
    assert min(ys) < 0 < nautical_miles(40).meters < max(ys)
