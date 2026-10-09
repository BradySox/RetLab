"""A flight can tank at a theater tanker between its hold and its join."""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any, cast

import pytest
from dcs import Point
from dcs.terrain import Caucasus

from game.ato.flight import Flight
from game.ato.flightplans.formationattack import (
    FormationAttackFlightPlan,
    FormationAttackLayout,
)
from game.ato.flightplans.strike import Builder as StrikeBuilder
from game.ato.flightwaypoint import FlightWaypoint
from game.ato.flightwaypointtype import FlightWaypointType
from game.missiongenerator.aircraft.waypoints.refuel import RefuelPointBuilder
from game.missiongenerator.refuelrendezvous import PlannedTanker, refuel_rendezvous
from game.utils import Speed, knots

JOIN_TIME = datetime(2026, 10, 7, 8, 0, 0)


def _wp(name: str, kind: FlightWaypointType, north_nm: float) -> FlightWaypoint:
    return FlightWaypoint(name, kind, Point(0, north_nm * 1852, Caucasus()))


def _layout(with_refuel: bool) -> FormationAttackLayout:
    nav = FlightWaypointType.NAV
    return FormationAttackLayout(
        departure=_wp("TAKEOFF", FlightWaypointType.TAKEOFF, 0),
        hold=_wp("HOLD", FlightWaypointType.LOITER, 10),
        nav_to=[],
        join=_wp("JOIN", FlightWaypointType.JOIN, 50),
        ingress=_wp("INGRESS", FlightWaypointType.INGRESS_STRIKE, 80),
        targets=[_wp("TGT", FlightWaypointType.TARGET_POINT, 90)],
        split=_wp("SPLIT", FlightWaypointType.SPLIT, 50),
        refuel=_wp("REFUEL", FlightWaypointType.REFUEL, 30),
        nav_from=[],
        arrival=_wp("LAND", FlightWaypointType.LANDING_POINT, 0),
        divert=None,
        bullseye=_wp("BULLSEYE", nav, 0),
        custom_waypoints=[],
        pre_push_refuel=(
            _wp("REFUEL", FlightWaypointType.REFUEL, 30) if with_refuel else None
        ),
    )


class _Plan(FormationAttackFlightPlan):
    """Flies 400 kt everywhere and joins at a fixed time."""

    def __init__(self, layout: FormationAttackLayout, size: int = 2) -> None:
        self.flight = cast(
            Flight, SimpleNamespace(roster=SimpleNamespace(max_size=size))
        )
        self.layout = layout

    def speed_between_waypoints(self, a: FlightWaypoint, b: FlightWaypoint) -> Speed:
        return knots(400)

    @property
    def join_time(self) -> datetime:
        return JOIN_TIME


def _leg(nm: float) -> timedelta:
    return timedelta(hours=nm / 400 * 1.05)


def test_the_route_goes_hold_refuel_join() -> None:
    layout = _layout(with_refuel=True)
    names = [w.name for w in layout.iter_waypoints()]
    assert names[:4] == ["TAKEOFF", "HOLD", "REFUEL", "JOIN"]
    # The stop after the strike is still there until the builder drops it.
    assert names.count("REFUEL") == 2


def test_the_leg_out_of_the_tanker_carries_the_tanking_time() -> None:
    plan = _Plan(_layout(with_refuel=True), size=2)
    refuel = plan.layout.pre_push_refuel
    assert refuel is not None
    # 4 minutes a jet plus 1, the package tanker's own figure.
    assert plan.tanking_time == timedelta(minutes=9)
    assert plan.total_time_between_waypoints(refuel, plan.layout.join) == _leg(
        20
    ) + timedelta(minutes=9)


def test_the_flight_leaves_hold_early_enough_to_tank() -> None:
    plan = _Plan(_layout(with_refuel=True), size=2)
    refuel = plan.layout.pre_push_refuel
    # Hold -> tanker 20 NM, 9 min on the boom, tanker -> join 20 NM.
    expected_push = JOIN_TIME - _leg(20) - timedelta(minutes=9) - _leg(20)
    assert plan.push_time == expected_push
    assert plan.tot_for_waypoint(refuel) == expected_push + _leg(20)


def test_without_the_box_the_push_is_unchanged() -> None:
    plan = _Plan(_layout(with_refuel=False))
    # Hold straight to join, 40 NM.
    assert plan.push_time == JOIN_TIME - _leg(40)


def test_deleting_the_stop_clears_it() -> None:
    layout = _layout(with_refuel=True)
    refuel = layout.pre_push_refuel
    assert refuel is not None
    assert layout.delete_waypoint(refuel)
    assert layout.pre_push_refuel is None
    assert layout.refuel is not None


def test_an_old_save_reads_as_no_stop() -> None:
    layout = FormationAttackLayout.__new__(FormationAttackLayout)
    layout.__setstate__({})
    assert layout.pre_push_refuel is None


def _tanker(theater: bool, north_nm: float) -> PlannedTanker:
    point = Point(0, north_nm * 1852, Caucasus())
    return PlannedTanker(
        blue=cast(Any, True),
        aircraft_type=cast(Any, None),
        orbit_start=point,
        orbit_end=point,
        recovery=False,
        theater=theater,
    )


def test_only_a_theater_tanker_is_up_before_the_push() -> None:
    receiver = cast(Any, SimpleNamespace(can_refuel_from=lambda _t: True))
    planned = Point(0, 30 * 1852, Caucasus())
    package_tanker = _tanker(theater=False, north_nm=31)
    theater_tanker = _tanker(theater=True, north_nm=60)

    after = refuel_rendezvous(receiver, True, planned, [package_tanker, theater_tanker])
    before = refuel_rendezvous(
        receiver, True, planned, [package_tanker, theater_tanker], theater_only=True
    )

    assert after == package_tanker.orbit_start
    assert before == theater_tanker.orbit_start
    assert (
        refuel_rendezvous(receiver, True, planned, [package_tanker], theater_only=True)
        is None
    )


@pytest.mark.parametrize("margin, dropped", [(500.0, True), (-500.0, False)])
def test_the_stop_after_the_strike_stays_only_when_needed(
    monkeypatch: pytest.MonkeyPatch, margin: float, dropped: bool
) -> None:
    layout = _layout(with_refuel=True)
    post = layout.refuel
    seen: list[Any] = []

    def brief(_flight: Any) -> Any:
        seen.append(layout.refuel)
        return SimpleNamespace(margin_lbs=margin)

    monkeypatch.setattr("game.retlab.fuel_brief.fuel_brief_for", brief)
    builder = cast(Any, StrikeBuilder.__new__(StrikeBuilder))
    builder.flight = None
    builder._flight_plan = SimpleNamespace(layout=layout)

    assert builder._post_refuel_unneeded() is dropped
    # The fuel walk ran without the after-strike stop, then it was put back.
    assert seen == [None]
    assert layout.refuel is post


def test_no_check_without_a_stop_before_the_push(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "game.retlab.fuel_brief.fuel_brief_for",
        lambda _f: pytest.fail("no fuel walk expected"),
    )
    builder = cast(Any, StrikeBuilder.__new__(StrikeBuilder))
    builder.flight = None
    builder._flight_plan = SimpleNamespace(layout=_layout(with_refuel=False))
    assert builder._post_refuel_unneeded() is False


@pytest.mark.parametrize("pre_push, stop", [(True, 0.9), (False, 0.5)])
def test_ai_fills_up_before_the_push(pre_push: bool, stop: float) -> None:
    layout = _layout(with_refuel=True)
    waypoint = layout.pre_push_refuel if pre_push else layout.refuel
    point_builder = cast(Any, RefuelPointBuilder.__new__(RefuelPointBuilder))
    point_builder.waypoint = waypoint
    point_builder.flight = SimpleNamespace(flight_plan=SimpleNamespace(layout=layout))
    assert point_builder._stop_fuel() == stop


def test_typed_minutes_replace_the_automatic_figure() -> None:
    plan = _Plan(_layout(with_refuel=True), size=4)
    assert plan.tanking_time == timedelta(minutes=17)
    cast(Any, plan.flight).tanking_minutes = 25
    assert plan.tanking_time == timedelta(minutes=25)
    # Hold -> tanker 20 NM, 25 min on the boom, tanker -> join 20 NM.
    assert plan.push_time == JOIN_TIME - _leg(20) - timedelta(minutes=25) - _leg(20)
    cast(Any, plan.flight).tanking_minutes = None
    assert plan.tanking_time == timedelta(minutes=17)


def test_an_old_flight_reads_as_automatic_minutes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from game.ato import flight as flight_module

    monkeypatch.setattr(flight_module, "Uninitialized", lambda *_: None)
    flight = Flight.__new__(Flight)
    flight.__setstate__({"squadron": SimpleNamespace(settings=None), "roster": None})
    assert flight.tanking_minutes is None
