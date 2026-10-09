"""A CAP can tank at a theater tanker on its way to station."""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any, cast

import pytest
from dcs import Point
from dcs.terrain import Caucasus

from game.ato.flight import Flight
from game.ato.flightplans.barcap import BarCapFlightPlan, BarCapLayout
from game.ato.flightplans.ibuilder import IBuilder
from game.ato.flightplans.tarcap import Builder as TarCapBuilder
from game.ato.flightplans.tarcap import TarCapLayout
from game.ato.flightwaypoint import FlightWaypoint
from game.ato.flightwaypointtype import FlightWaypointType
from game.ato.tankeravailability import post_refuel_shortfall
from game.utils import Speed, knots

STATION = datetime(2026, 10, 7, 11, 26, 5)


def _wp(name: str, kind: FlightWaypointType, north_nm: float) -> FlightWaypoint:
    return FlightWaypoint(name, kind, Point(0, north_nm * 1852, Caucasus()))


def _layout(with_refuel: bool) -> BarCapLayout:
    return BarCapLayout(
        departure=_wp("TAKEOFF", FlightWaypointType.TAKEOFF, 0),
        nav_to=[],
        nav_from=[],
        patrol_start=_wp("RACETRACK START", FlightWaypointType.PATROL_TRACK, 60),
        patrol_end=_wp("RACETRACK END", FlightWaypointType.PATROL, 80),
        arrival=_wp("LAND", FlightWaypointType.LANDING_POINT, 0),
        divert=None,
        bullseye=_wp("BULLSEYE", FlightWaypointType.BULLSEYE, 0),
        custom_waypoints=[],
        pre_push_refuel=(
            _wp("REFUEL", FlightWaypointType.REFUEL, 40) if with_refuel else None
        ),
    )


class _Plan(BarCapFlightPlan):
    """Flies 400 kt everywhere and comes on station at a fixed time."""

    def __init__(self, layout: BarCapLayout, size: int = 2) -> None:
        self.flight = cast(
            Flight, SimpleNamespace(roster=SimpleNamespace(max_size=size))
        )
        self.layout = layout

    def speed_between_waypoints(self, a: FlightWaypoint, b: FlightWaypoint) -> Speed:
        return knots(400)

    @property
    def patrol_start_time(self) -> datetime:
        return STATION


def _leg(nm: float) -> timedelta:
    return timedelta(hours=nm / 400 * 1.05)


def test_the_route_goes_takeoff_refuel_station() -> None:
    names = [w.name for w in _layout(with_refuel=True).iter_waypoints()]
    assert names[:4] == ["TAKEOFF", "REFUEL", "RACETRACK START", "RACETRACK END"]
    assert names.count("TAKEOFF") == 1
    assert [w.name for w in _layout(with_refuel=False).iter_waypoints()][:2] == [
        "TAKEOFF",
        "RACETRACK START",
    ]


def test_the_station_time_stays_and_the_tanker_time_is_before_it() -> None:
    layout = _layout(with_refuel=True)
    plan = _Plan(layout, size=2)
    refuel = layout.pre_push_refuel
    assert refuel is not None
    # 20 NM from the tanker to station, after 9 min on the boom.
    assert plan.tot_for_waypoint(refuel) == STATION - _leg(20) - timedelta(minutes=9)
    assert plan.tot_for_waypoint(layout.patrol_start) == STATION


def test_deleting_the_stop_clears_it() -> None:
    layout = _layout(with_refuel=True)
    refuel = layout.pre_push_refuel
    assert refuel is not None
    assert layout.delete_waypoint(refuel)
    assert layout.pre_push_refuel is None


def test_an_old_tarcap_save_reads_as_no_stop() -> None:
    layout = TarCapLayout.__new__(TarCapLayout)
    layout.__setstate__(cast(dict[str, Any], {"refuel": None}))
    assert layout.pre_push_refuel is None


def _tarcap_layout(post: bool) -> TarCapLayout:
    return TarCapLayout(
        departure=_wp("TAKEOFF", FlightWaypointType.TAKEOFF, 0),
        nav_to=[],
        nav_from=[],
        patrol_start=_wp("RACETRACK START", FlightWaypointType.PATROL_TRACK, 60),
        patrol_end=_wp("RACETRACK END", FlightWaypointType.PATROL, 80),
        refuel=_wp("REFUEL", FlightWaypointType.REFUEL, 30) if post else None,
        arrival=_wp("LAND", FlightWaypointType.LANDING_POINT, 0),
        divert=None,
        bullseye=_wp("BULLSEYE", FlightWaypointType.BULLSEYE, 0),
        custom_waypoints=[],
        pre_push_refuel=_wp("REFUEL", FlightWaypointType.REFUEL, 40),
    )


@pytest.mark.parametrize("margin, kept", [(500.0, False), (-500.0, True)])
def test_a_tarcap_keeps_its_stop_off_station_only_when_needed(
    monkeypatch: pytest.MonkeyPatch, margin: float, kept: bool
) -> None:
    monkeypatch.setattr(
        "game.retlab.fuel_brief.fuel_brief_for",
        lambda _f: SimpleNamespace(margin_lbs=margin),
    )
    builder = cast(Any, TarCapBuilder.__new__(TarCapBuilder))
    builder.flight = None

    def build(self: Any, dump_debug_info: bool = False) -> None:
        layout = _tarcap_layout(post=not self._drop_post_refuel)
        self._flight_plan = SimpleNamespace(layout=layout)

    monkeypatch.setattr(IBuilder, "regenerate", build)
    builder.regenerate()
    assert (builder.built.layout.refuel is not None) is kept


def test_the_shortfall_names_the_pounds_and_puts_the_stop_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    layout = _tarcap_layout(post=True)
    post = layout.refuel
    seen: list[Any] = []

    def brief(_flight: Any) -> Any:
        seen.append(layout.refuel)
        return SimpleNamespace(margin_lbs=-927.4)

    monkeypatch.setattr("game.retlab.fuel_brief.fuel_brief_for", brief)
    assert post_refuel_shortfall(cast(Flight, None), layout) == pytest.approx(927.4)
    assert seen == [None]
    assert layout.refuel is post
    layout.pre_push_refuel = None
    assert post_refuel_shortfall(cast(Flight, None), layout) is None
