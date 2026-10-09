"""The four-point box every theater tanker flies."""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from dcs import Point
from dcs.mission import Mission
from dcs.drawing.drawings import StandardLayer
from dcs.terrain import Caucasus

from game.ato.flighttype import FlightType
from game.ato.flightplans.refuelingflightplan import (
    TankerBoxLayout,
    move_box,
    orbit_leg_end,
)
from game.ato.flightplans.theaterrefueling import (
    TANKER_BOX_DEPTH,
    Builder,
    TheaterRefuelingFlightPlan,
    deconflicted_altitude,
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
    )
    plan = TheaterRefuelingFlightPlan.__new__(TheaterRefuelingFlightPlan)
    plan.flight = SimpleNamespace(  # type: ignore[assignment]
        coalition=SimpleNamespace(game=SimpleNamespace(settings=settings)),
        unit_type=SimpleNamespace(patrol_speed=knots(420)),
        orbit_speed_kias=None,
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
    # DCS draws the outline open, so the ring must end where it started.
    assert (orbit.points[0].x, orbit.points[0].y) == (
        orbit.points[-1].x,
        orbit.points[-1].y,
    )


@pytest.mark.parametrize("dragged", range(5))
def test_dragging_any_box_point_moves_the_whole_box(dragged: int) -> None:
    box = _box()
    points = [box.patrol_start, *box.box_corners, box.patrol_end]
    before = [(p.position.x, p.position.y) for p in points]
    target = points[dragged]
    to = _p(target.position.x + 5000, target.position.y - 3000)

    assert move_box(box, target, to)

    after = [(p.position.x, p.position.y) for p in points]
    assert after == pytest.approx([(x + 5000, y - 3000) for x, y in before])


def test_a_point_outside_the_box_is_not_moved_with_it() -> None:
    box = _box()
    stray = _wp("NAV", FlightWaypointType.NAV)
    assert not move_box(box, stray, _p(1, 1))
    assert not move_box(SimpleNamespace(), box.patrol_start, _p(1, 1))
    assert (box.patrol_start.position.x, box.patrol_start.position.y) == (0, 0)


def test_the_map_drag_endpoint_moves_the_whole_box(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from game.server.leaflet import LeafletPoint
    from game.server.waypoints import routes

    box = _box()
    points = [box.patrol_start, *box.box_corners, box.patrol_end]
    flight = SimpleNamespace(flight_plan=SimpleNamespace(layout=box, waypoints=points))
    game = SimpleNamespace(
        db=SimpleNamespace(flights=SimpleNamespace(get=lambda _: flight)),
        theater=SimpleNamespace(terrain=TERRAIN),
    )
    tot_updates: list[bool] = []
    published: list[Any] = []
    monkeypatch.setattr(
        routes,
        "_package_model",
        lambda _: SimpleNamespace(update_tot=lambda: tot_updates.append(True)),
    )
    monkeypatch.setattr(routes, "_publish", published.append)
    to = _p(box.box_corners[1].position.x + 4000, box.box_corners[1].position.y)
    lat_lng = to.latlng()

    routes.set_position(
        uuid4(),
        3,  # BOX 3, the second corner
        LeafletPoint(lat=lat_lng.lat, lng=lat_lng.lng),
        game,  # type: ignore[arg-type]
    )

    assert box.patrol_start.position.x == pytest.approx(4000, abs=1)
    assert box.patrol_end.position.x == pytest.approx(4000, abs=1)
    assert tot_updates == [True]
    assert published == [[flight]]


def test_an_old_save_drops_the_box_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    from game.ato import flight as flight_module

    monkeypatch.setattr(flight_module, "Uninitialized", lambda *_: None)
    flight = flight_module.Flight.__new__(flight_module.Flight)
    flight.__setstate__(
        {
            "squadron": SimpleNamespace(settings=None),
            "roster": None,
            "tanker_box": False,
            "orbit_speed_kias": 270,
        }
    )
    assert "tanker_box" not in flight.__dict__
    assert flight.orbit_speed_kias == 270


def test_the_planner_builds_a_30_by_15_nm_box(monkeypatch: pytest.MonkeyPatch) -> None:
    from game.ato.flightplans import theaterrefueling

    class _Builder(_FakeWaypointBuilder):
        def __init__(self, _: Any) -> None:
            pass

        get_patrol_altitude = ALT

    monkeypatch.setattr(theaterrefueling, "WaypointBuilder", _Builder)
    # The threat boundary is 200 NM due east of the anchor, which is unthreatened.
    threats = SimpleNamespace(
        closest_boundary=lambda _: _p(0, nautical_miles(200).meters),
        threatened=lambda _: False,
    )
    settings = SimpleNamespace(tanker_threat_buffer_min_distance=70)
    flight = SimpleNamespace(flight_type=FlightType.REFUELING)
    flight.departure = flight.arrival = SimpleNamespace(position=_p(-100000, 0))
    flight.divert = None
    flight.package = SimpleNamespace(
        target=SimpleNamespace(position=_p(0, 0)), flights=[flight]
    )
    flight.coalition = SimpleNamespace(
        game=SimpleNamespace(settings=settings),
        opponent=SimpleNamespace(threat_zone=threats),
        ato=SimpleNamespace(packages=[flight.package]),
        doctrine=SimpleNamespace(
            min_combat_altitude=feet(1000), max_combat_altitude=feet(35000)
        ),
    )
    builder = Builder.__new__(Builder)
    builder.flight = flight  # type: ignore[assignment]

    box = builder.layout()

    a = box.patrol_start.position
    b, c, _ = (w.position for w in box.box_corners)
    assert a.distance_to_point(b) == pytest.approx(nautical_miles(30).meters, abs=1)
    assert b.distance_to_point(c) == pytest.approx(nautical_miles(15).meters, abs=1)
    # The box extends away from the threat (west, toward -y).
    assert c.y < b.y
    assert box.patrol_start.alt == ALT


# ------------------------------------------------------- altitude between packages
# Anatolian Reach turn 1: the carrier's KC-135 and Akrotiri's MPRS tanker, in two
# packages, flew overlapping boxes at the same 24,000 ft.

FLOOR, CEILING = feet(1000), feet(35000)


def test_a_lone_tanker_keeps_its_altitude() -> None:
    assert deconflicted_altitude(ALT, [], FLOOR, CEILING) == ALT


def test_a_taken_altitude_moves_the_tanker_up_2000_ft() -> None:
    assert deconflicted_altitude(ALT, [feet(24000)], FLOOR, CEILING) == feet(26000)


def test_a_close_altitude_counts_as_taken() -> None:
    assert deconflicted_altitude(ALT, [feet(25000)], FLOOR, CEILING) == feet(22000)


def test_the_ceiling_sends_it_down_instead() -> None:
    taken = [feet(24000)]
    assert deconflicted_altitude(ALT, taken, FLOOR, feet(25000)) == feet(22000)


def test_three_tankers_stack_2000_ft_apart() -> None:
    taken = [feet(24000), feet(26000), feet(22000)]
    assert deconflicted_altitude(ALT, taken, FLOOR, CEILING) == feet(28000)


def test_the_planner_steps_clear_of_another_packages_tanker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from game.ato.flightplans import theaterrefueling

    class _Builder(_FakeWaypointBuilder):
        def __init__(self, _: Any) -> None:
            pass

        get_patrol_altitude = ALT

    monkeypatch.setattr(theaterrefueling, "WaypointBuilder", _Builder)
    other_plan = TheaterRefuelingFlightPlan.__new__(TheaterRefuelingFlightPlan)
    other_plan.layout = _box()
    other = SimpleNamespace(
        flight_type=FlightType.REFUELING, laid_out_flight_plan=other_plan
    )
    threats = SimpleNamespace(
        closest_boundary=lambda _: _p(0, nautical_miles(200).meters),
        threatened=lambda _: False,
    )
    flight = SimpleNamespace(flight_type=FlightType.REFUELING)
    flight.departure = flight.arrival = SimpleNamespace(position=_p(-100000, 0))
    flight.divert = None
    flight.package = SimpleNamespace(
        target=SimpleNamespace(position=_p(0, 0)), flights=[flight]
    )
    flight.coalition = SimpleNamespace(
        game=SimpleNamespace(
            settings=SimpleNamespace(tanker_threat_buffer_min_distance=70)
        ),
        opponent=SimpleNamespace(threat_zone=threats),
        ato=SimpleNamespace(
            packages=[SimpleNamespace(flights=[other]), flight.package]
        ),
        doctrine=SimpleNamespace(
            min_combat_altitude=FLOOR, max_combat_altitude=CEILING
        ),
    )
    builder = Builder.__new__(Builder)
    builder.flight = flight  # type: ignore[assignment]

    box = builder.layout()

    assert box.patrol_start.alt == feet(26000)
    assert all(w.alt == feet(26000) for w in box.box_corners)
