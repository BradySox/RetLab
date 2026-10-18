"""CAS follows the §111 battle line: FLOT start and end at the outer battles, up
to 3 battle stops between, and a search circle at each stop."""

from __future__ import annotations

import pickle
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock

import pytest
import shapely
from dcs import Point
from dcs.task import EngageTargetsInZone
from dcs.terrain import Caucasus
from shapely.geometry import Point as ShapelyPoint

import game.ato.flightplans.cas as cas
from game.ato.flightplans.cas import (
    Builder,
    CasFlightPlan,
    CasLayout,
    MAX_BATTLE_STOPS,
    battle_stop_sites,
)
from game.ato.flightplans.tacticaloverlay import cas_overlay
from game.ato.flightwaypoint import FlightWaypoint
from game.ato.flightwaypointtype import FlightWaypointType
from game.missiongenerator.aircraft.waypoints.casingress import (
    CasIngressBuilder,
    CasStopBuilder,
)
from game.missiongenerator.frontlineconflictdescription import (
    FrontLineConflictDescription,
)
from game.theater import FrontLine
from game.theater.frontbattles import BattleSite, FrontBattles
from game.utils import feet, nautical_miles

TERRAIN = Caucasus()


def _point(x: float, y: float) -> Point:
    return Point(x, y, TERRAIN)


def _site(along: float) -> BattleSite:
    return BattleSite(
        x=along,
        y=50_000.0,
        blue_forward=90.0,
        width=8_000.0,
        sector=f"S{int(along)}",
        along=along,
        trace=((along - 4_000.0, 50_000.0), (along + 4_000.0, 50_000.0)),
    )


def _battles(*alongs: float) -> FrontBattles:
    sites = tuple(_site(a) for a in alongs)
    return FrontBattles(tuple((s.x, s.y) for s in sites), sites)


class _FakeWaypointBuilder:
    def __init__(self, flight: Any) -> None:
        self.get_combat_altitude = feet(10000)

    @staticmethod
    def _wp(name: str, position: Point) -> SimpleNamespace:
        return SimpleNamespace(
            name=name, position=position, pretty_name="", description=""
        )

    def takeoff(self, departure: Any) -> SimpleNamespace:
        return self._wp("TAKEOFF", departure.position)

    def land(self, arrival: Any) -> SimpleNamespace:
        return self._wp("LAND", arrival.position)

    def divert(self, divert: Any) -> None:
        return None

    def bullseye(self) -> SimpleNamespace:
        return self._wp("BULLSEYE", _point(0, 0))

    def nav_path(self, *args: Any) -> list[Any]:
        return []

    def cas(self, position: Point, altitude: Any) -> SimpleNamespace:
        return self._wp("CAS", position)

    def ingress(self, kind: Any, position: Point, target: Any) -> SimpleNamespace:
        return self._wp("INGRESS", position)


class _FakeIpSolver:
    def __init__(self, departure: Any, target: Any, *args: Any) -> None:
        self.target = target

    def set_debug_properties(self, *args: Any) -> None:
        pass

    def solve(self) -> Any:
        return shapely.Point(self.target.x - 20_000, self.target.y)

    def dump_debug_info(self) -> None:
        pass


#: The old FLOT bounds the stub returns when no battle line applies.
LEFT, RIGHT = _point(40_000, 60_000), _point(60_000, 60_000)


def _layout(
    monkeypatch: pytest.MonkeyPatch,
    battles: FrontBattles | None,
    departure: Point,
) -> Any:
    monkeypatch.setattr(cas, "WaypointBuilder", _FakeWaypointBuilder)
    monkeypatch.setattr(cas, "IpSolver", _FakeIpSolver)
    monkeypatch.setattr(cas, "waypoint_debug_directory", lambda: Path("."))
    monkeypatch.setattr(cas, "battles_for", lambda theater, front: battles)
    monkeypatch.setattr(
        FrontLineConflictDescription,
        "frontline_bounds",
        classmethod(
            lambda cls, front, theater: SimpleNamespace(
                left_position=LEFT, right_position=RIGHT
            )
        ),
    )
    front = MagicMock(spec=FrontLine)
    front.position = _point(50_000, 50_000)
    front.name = "Front line Gazipasa/Konya FOB"
    home = SimpleNamespace(position=departure, theater=MagicMock())
    flight = SimpleNamespace(
        flight_type=MagicMock(),
        unit_type=SimpleNamespace(dcs_unit_type=SimpleNamespace(helicopter=False)),
        departure=home,
        arrival=home,
        divert=None,
        package=SimpleNamespace(target=front),
        coalition=MagicMock(),
    )
    return Builder(cast(Any, flight)).layout(False)


def _xy(waypoint: Any) -> tuple[float, float]:
    return round(waypoint.position.x), round(waypoint.position.y)


def test_flot_start_and_end_sit_on_the_outer_battles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    battles = _battles(0, 20_000, 40_000, 60_000, 80_000, 100_000)
    layout = _layout(monkeypatch, battles, departure=_point(0, 0))
    assert layout.battle_line
    assert _xy(layout.patrol_start) == (0, 50_000)
    assert _xy(layout.patrol_end) == (100_000, 50_000)
    stops = layout.battle_stops
    assert 0 < len(stops) <= MAX_BATTLE_STOPS
    assert [s.name for s in stops] == [f"BATTLE {n}" for n in (1, 2, 3)]
    assert [s.pretty_name for s in stops] == ["Battle 1", "Battle 2", "Battle 3"]
    xs = [s.position.x for s in stops]
    assert xs == sorted(xs) and 0 < xs[0] and xs[-1] < 100_000
    # Each stop is a real battle, not a point between two.
    assert {_xy(s) for s in stops} <= {(a, 50_000) for a in range(0, 100_001, 20_000)}
    order = list(layout.iter_waypoints())
    start = order.index(layout.patrol_start)
    assert order[start : start + 5] == [layout.patrol_start, *stops, layout.patrol_end]


def test_the_ingress_names_the_front(monkeypatch: pytest.MonkeyPatch) -> None:
    # Test 60's briefing printed the FrontLine object's repr here.
    layout = _layout(monkeypatch, None, departure=_point(0, 0))
    assert (
        layout.ingress.description
        == "Ingress to provide CAS at Front line Gazipasa/Konya FOB"
    )


def test_the_end_nearer_home_is_flot_start(monkeypatch: pytest.MonkeyPatch) -> None:
    battles = _battles(0, 20_000, 40_000, 60_000, 80_000, 100_000)
    layout = _layout(monkeypatch, battles, departure=_point(100_000, 0))
    assert _xy(layout.patrol_start) == (100_000, 50_000)
    assert _xy(layout.patrol_end) == (0, 50_000)
    xs = [s.position.x for s in layout.battle_stops]
    assert xs == sorted(xs, reverse=True)
    assert layout.battle_stops[0].name == "BATTLE 1"


def test_two_battles_have_no_stops_between(monkeypatch: pytest.MonkeyPatch) -> None:
    layout = _layout(monkeypatch, _battles(0, 30_000), departure=_point(0, 0))
    assert layout.battle_line
    assert layout.battle_stops == []
    assert _xy(layout.patrol_start) == (0, 50_000)
    assert _xy(layout.patrol_end) == (30_000, 50_000)


def test_one_battle_spans_its_own_spread(monkeypatch: pytest.MonkeyPatch) -> None:
    layout = _layout(monkeypatch, _battles(50_000), departure=_point(0, 0))
    assert _xy(layout.patrol_start) == (46_000, 50_000)
    assert _xy(layout.patrol_end) == (54_000, 50_000)


def test_without_battles_the_old_bounds_are_kept(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    layout = _layout(monkeypatch, None, departure=_point(0, 0))
    assert not layout.battle_line
    assert layout.battle_stops == []
    assert layout.patrol_start.position is LEFT
    assert layout.patrol_end.position is RIGHT
    assert layout.patrol_start.description == "FLOT boundary"


def test_battles_setting_off_returns_no_battle_line() -> None:
    front = SimpleNamespace(
        coalition=SimpleNamespace(
            game=SimpleNamespace(
                settings=SimpleNamespace(front_line_battles_along_border=False)
            )
        )
    )
    from game.theater.frontbattles import battles_for

    assert battles_for(cast(Any, None), cast(Any, front)) is None


def test_stops_pick_the_battles_nearest_even_spacing() -> None:
    sites = _battles(0, 10_000, 20_000, 50_000, 74_000, 90_000, 100_000).sites
    picked = [s.along for s in battle_stop_sites(sites)]
    assert picked == [20_000, 50_000, 74_000]
    assert battle_stop_sites(sites[:4]) == list(sites[1:3])


def _waypoint(name: str, x: float) -> FlightWaypoint:
    return FlightWaypoint(name, FlightWaypointType.CAS, _point(x, 50_000))


def _cas_layout() -> CasLayout:
    return CasLayout(
        departure=(_waypoint("TAKEOFF", -50_000)),
        custom_waypoints=[],
        arrival=(_waypoint("LAND", -50_000)),
        divert=None,
        bullseye=(_waypoint("BULLSEYE", 0)),
        nav_to=[],
        nav_from=[],
        patrol_start=(_waypoint("FLOT START", 0)),
        patrol_end=(_waypoint("FLOT END", 90_000)),
        ingress=(_waypoint("INGRESS", -20_000)),
        battle_line=True,
        battle_stops=[
            (_waypoint("BATTLE 1", 30_000)),
            (_waypoint("BATTLE 2", 60_000)),
        ],
    )


def test_an_old_save_layout_loads_without_battle_stops() -> None:
    layout = _cas_layout()
    del layout.__dict__["battle_line"]
    del layout.__dict__["battle_stops"]
    loaded = pickle.loads(pickle.dumps(layout))
    assert loaded.battle_line is False
    assert loaded.battle_stops == []
    names = [w.name for w in loaded.iter_waypoints()]
    assert names.index("FLOT END") == names.index("FLOT START") + 1


def _plan(layout: CasLayout) -> CasFlightPlan:
    plan: Any = object.__new__(CasFlightPlan)
    plan.layout = layout
    plan.flight = SimpleNamespace(
        coalition=SimpleNamespace(
            doctrine=SimpleNamespace(cas_duration=timedelta(minutes=30)),
            game=SimpleNamespace(
                settings=SimpleNamespace(cas_engagement_range_distance=10)
            ),
        )
    )
    plan.flight.flight_plan = plan
    return cast(CasFlightPlan, plan)


def test_on_station_time_is_shared_across_the_stops() -> None:
    plan = _plan(_cas_layout())
    stops = plan.layout.on_station
    legs = [plan.total_time_between_waypoints(a, b) for a, b in zip(stops, stops[1:])]
    assert sum(legs, timedelta()) == timedelta(minutes=30)
    assert legs == [timedelta(minutes=10)] * 3
    assert set(stops) <= plan.combat_speed_waypoints


def _tasks_from(builder_type: Any, plan: CasFlightPlan, waypoint: Any) -> list[Any]:
    builder: Any = object.__new__(builder_type)
    builder.flight = plan.flight
    builder.waypoint = waypoint
    builder.register_special_ingress_points = lambda: None
    point = MagicMock()
    builder.add_tasks(point)
    return [call.args[0] for call in point.add_task.call_args_list]


def _centres(tasks: list[Any]) -> list[tuple[float, float]]:
    assert all(isinstance(t, EngageTargetsInZone) for t in tasks)
    radius = int(nautical_miles(10).meters)
    assert all(t.params["zoneRadius"] == radius for t in tasks)
    return [(round(t.params["x"]), round(t.params["y"])) for t in tasks]


def test_the_generator_searches_a_circle_at_each_stop() -> None:
    plan = _plan(_cas_layout())
    layout = plan.layout
    centres = _centres(_tasks_from(CasIngressBuilder, plan, layout.ingress))
    for stop in layout.on_station:
        centres += _centres(_tasks_from(CasStopBuilder, plan, stop))
    assert centres == [(x, 50_000) for x in (0, 30_000, 60_000, 90_000)]


def test_without_a_battle_line_the_search_is_one_circle_mid_flot() -> None:
    layout = _cas_layout()
    layout.battle_line = False
    layout.battle_stops = []
    plan = _plan(layout)
    assert _centres(_tasks_from(CasIngressBuilder, plan, layout.ingress)) == [
        (45_000, 50_000)
    ]
    for stop in layout.on_station:
        assert _tasks_from(CasStopBuilder, plan, stop) == []


def test_the_map_draws_a_circle_per_stop() -> None:
    stops = [_point(x, 0) for x in (0, 60_000, 120_000)]
    overlay = cas_overlay(stops[0], stops[-1], nautical_miles(10), stops=stops)
    assert len(overlay.reach) == 3 and all(r.filled for r in overlay.reach)
    covered = shapely.union_all([r.geometry for r in overlay.reach])
    assert covered.contains(ShapelyPoint(60_000, 0))
    assert not covered.contains(ShapelyPoint(30_000, 0))
