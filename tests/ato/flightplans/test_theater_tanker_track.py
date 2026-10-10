"""The racetrack every theater tanker flies, and how it moves on the map."""

from __future__ import annotations

import pickle
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from dcs import Point
from dcs.terrain import Caucasus

from game.ato.flighttype import FlightType
from game.ato.flightplans.patrolling import PatrollingLayout
from game.ato.flightplans.refuelingflightplan import TankerBoxLayout
from game.ato.flightplans.theaterrefueling import (
    TANKER_ORBIT_SPACING,
    TANKER_TRACK_LENGTH,
    Builder,
    TheaterRefuelingFlightPlan,
    deconflicted_altitude,
    move_track,
    track_drag_note,
)
from game.ato.flightplans.waypointbuilder import WaypointBuilder
from game.ato.flightwaypoint import FlightWaypoint
from game.ato.flightwaypointtype import FlightWaypointType
from game.utils import feet, nautical_miles

TERRAIN = Caucasus()
ALT = feet(24000)
FLOOR, CEILING = feet(1000), feet(35000)


def _p(x: float, y: float) -> Point:
    return Point(x, y, TERRAIN)


def _wp(name: str, kind: FlightWaypointType) -> FlightWaypoint:
    return FlightWaypoint(name, kind, _p(0, 0), ALT)


class _FakeWaypointBuilder:
    race_track_start = staticmethod(WaypointBuilder.race_track_start)
    race_track_end = staticmethod(WaypointBuilder.race_track_end)
    race_track = WaypointBuilder.race_track
    get_patrol_altitude = ALT

    def __init__(self, _: Any = None) -> None:
        pass

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


def _planned(
    monkeypatch: pytest.MonkeyPatch, others: list[Any], tankers_ahead: int = 0
) -> PatrollingLayout:
    """The layout the planner builds, with the threat boundary 200 NM due east."""
    from game.ato.flightplans import theaterrefueling

    monkeypatch.setattr(theaterrefueling, "WaypointBuilder", _FakeWaypointBuilder)
    threats = SimpleNamespace(
        closest_boundary=lambda _: _p(0, nautical_miles(200).meters),
        threatened=lambda _: False,
    )
    flight = SimpleNamespace(flight_type=FlightType.REFUELING)
    flight.departure = flight.arrival = SimpleNamespace(position=_p(-100000, 0))
    flight.divert = None
    ahead = [
        SimpleNamespace(flight_type=FlightType.REFUELING, laid_out_flight_plan=None)
        for _ in range(tankers_ahead)
    ]
    flight.package = SimpleNamespace(
        target=SimpleNamespace(position=_p(0, 0)), flights=[*ahead, flight]
    )
    flight.coalition = SimpleNamespace(
        game=SimpleNamespace(
            settings=SimpleNamespace(tanker_threat_buffer_min_distance=70)
        ),
        opponent=SimpleNamespace(threat_zone=threats),
        ato=SimpleNamespace(packages=[SimpleNamespace(flights=others), flight.package]),
        doctrine=SimpleNamespace(
            min_combat_altitude=FLOOR, max_combat_altitude=CEILING
        ),
    )
    builder = Builder.__new__(Builder)
    builder.flight = flight  # type: ignore[assignment]
    return builder.layout()


def _track(length_nm: float = 40) -> TheaterRefuelingFlightPlan:
    """A theater tanker plan with a track running east from the origin."""
    plan = TheaterRefuelingFlightPlan.__new__(TheaterRefuelingFlightPlan)
    start = WaypointBuilder.race_track_start(_p(0, 0), ALT)
    end = WaypointBuilder.race_track_end(_p(0, nautical_miles(length_nm).meters), ALT)
    plan.layout = SimpleNamespace(patrol_start=start, patrol_end=end)  # type: ignore[assignment]
    return plan


# ------------------------------------------------------------------ the racetrack
# Flown 2026-10-09 (Kola): on the 30 x 15 NM box a KC-135 with a jet on the boom
# banks 15 degrees, needs about 8 NM a corner, and never flew level.


def test_the_planner_builds_a_40_nm_racetrack(monkeypatch: pytest.MonkeyPatch) -> None:
    layout = _planned(monkeypatch, [])

    assert type(layout) is PatrollingLayout
    route = [w.waypoint_type for w in layout.iter_waypoints()]
    assert route[1:3] == [FlightWaypointType.PATROL_TRACK, FlightWaypointType.PATROL]
    start, end = layout.patrol_start.position, layout.patrol_end.position
    assert TANKER_TRACK_LENGTH == nautical_miles(40)
    assert start.distance_to_point(end) == pytest.approx(
        TANKER_TRACK_LENGTH.meters, abs=1
    )
    # Across the threat axis (the threat is due east), 70 NM short of it.
    assert start.y == pytest.approx(end.y, abs=1)
    assert start.y == pytest.approx(nautical_miles(130).meters, abs=1)
    assert layout.patrol_start.alt == layout.patrol_end.alt == ALT


def test_a_second_tanker_in_the_package_sits_15_nm_further_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = _planned(monkeypatch, [])
    second = _planned(monkeypatch, [], tankers_ahead=1)

    step = first.patrol_start.position.y - second.patrol_start.position.y
    assert step == pytest.approx(TANKER_ORBIT_SPACING.meters, abs=1)


# ------------------------------------------------------------ dragging on the map


def test_dragging_the_start_moves_the_whole_track() -> None:
    plan = _track()
    start, end = plan.layout.patrol_start, plan.layout.patrol_end

    assert move_track(plan, start, _p(5000, -3000))

    assert (start.position.x, start.position.y) == pytest.approx((5000, -3000))
    assert (end.position.x, end.position.y) == pytest.approx(
        (5000, nautical_miles(40).meters - 3000)
    )


def test_dragging_the_end_swings_the_track_around_its_start() -> None:
    plan = _track()
    start, end = plan.layout.patrol_start, plan.layout.patrol_end

    # Dropped 90 NM due north of the start: the end lands 40 NM north of it.
    assert move_track(plan, end, _p(nautical_miles(90).meters, 0))

    assert (start.position.x, start.position.y) == (0, 0)
    assert (end.position.x, end.position.y) == pytest.approx(
        (nautical_miles(40).meters, 0), abs=1
    )


def test_a_swing_keeps_a_track_the_length_it_was() -> None:
    plan = _track(length_nm=25)
    end = plan.layout.patrol_end

    assert move_track(plan, end, _p(-1000, -1000))

    length = plan.layout.patrol_start.position.distance_to_point(end.position)
    assert length == pytest.approx(nautical_miles(25).meters, abs=1)


def test_other_points_and_other_plans_move_alone() -> None:
    plan = _track()
    stray = _wp("NAV", FlightWaypointType.NAV)

    assert not move_track(plan, stray, _p(1, 1))
    package_tanker = SimpleNamespace(layout=plan.layout)
    assert not move_track(package_tanker, plan.layout.patrol_start, _p(1, 1))
    assert (plan.layout.patrol_start.position.x, stray.position.x) == (0, 0)


def test_the_map_tooltip_says_what_each_drag_does() -> None:
    plan = _track()
    stray = _wp("NAV", FlightWaypointType.NAV)

    assert "whole track" in track_drag_note(plan, plan.layout.patrol_start)
    assert "swings" in track_drag_note(plan, plan.layout.patrol_end)
    assert track_drag_note(plan, stray) == ""
    package_tanker = SimpleNamespace(layout=plan.layout)
    assert track_drag_note(package_tanker, plan.layout.patrol_start) == ""


def test_the_map_drag_endpoint_moves_the_whole_track(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from game.server.leaflet import LeafletPoint
    from game.server.waypoints import routes

    plan = _track()
    start, end = plan.layout.patrol_start, plan.layout.patrol_end
    monkeypatch.setattr(
        TheaterRefuelingFlightPlan, "waypoints", [start, end], raising=False
    )
    flight = SimpleNamespace(flight_plan=plan)
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
    lat_lng = _p(4000, 0).latlng()

    routes.set_position(
        uuid4(),
        1,  # the racetrack start
        LeafletPoint(lat=lat_lng.lat, lng=lat_lng.lng),
        game,  # type: ignore[arg-type]
    )

    assert start.position.x == pytest.approx(4000, abs=1)
    assert end.position.x == pytest.approx(4000, abs=1)
    assert tot_updates == [True]
    assert published == [[flight]]


# -------------------------------------------------------------------- old saves


def test_a_saved_box_loads_as_the_racetrack_on_its_front_leg() -> None:
    box = TankerBoxLayout.__new__(TankerBoxLayout)
    front_end = _p(0, nautical_miles(30).meters)
    box.__dict__.update(
        departure=_wp("takeoff", FlightWaypointType.TAKEOFF),
        nav_to=[],
        nav_from=[],
        patrol_start=WaypointBuilder.race_track_start(_p(0, 0), ALT),
        patrol_end=WaypointBuilder.race_track_end(_p(0, 0), ALT),
        box_corners=[
            FlightWaypoint("BOX 2", FlightWaypointType.NAV, front_end, ALT),
            FlightWaypoint("BOX 3", FlightWaypointType.NAV, _p(-9, 9), ALT),
        ],
        arrival=_wp("land", FlightWaypointType.LANDING_POINT),
        divert=None,
        bullseye=_wp("bullseye", FlightWaypointType.BULLSEYE),
        custom_waypoints=[],
    )

    loaded = pickle.loads(pickle.dumps(box))

    assert type(loaded) is PatrollingLayout
    assert not hasattr(loaded, "box_corners")
    assert loaded.patrol_end.position.y == pytest.approx(front_end.y)
    assert loaded.patrol_start.pretty_name == "Race-track start"
    assert loaded.patrol_end.name == "RACETRACK END"
    kinds = [w.waypoint_type for w in loaded.iter_waypoints()]
    assert kinds[1:3] == [FlightWaypointType.PATROL_TRACK, FlightWaypointType.PATROL]


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


# ------------------------------------------------------- altitude between packages
# Anatolian Reach turn 1: the carrier's KC-135 and Akrotiri's MPRS tanker, in two
# packages, flew overlapping tracks at the same 24,000 ft.


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
    other = SimpleNamespace(
        flight_type=FlightType.REFUELING, laid_out_flight_plan=_track()
    )

    layout = _planned(monkeypatch, [other])

    assert layout.patrol_start.alt == feet(26000)
    assert layout.patrol_end.alt == feet(26000)
