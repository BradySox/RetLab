"""The package route: a NAV point on the way in or out lands on every flight.

A point on one flight alone sends it to the join early by its own detour, and the
package no longer meets (2026-09-27: "there should be a package waypoint edit").
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Optional, cast

import pytest
from dcs import Point
from dcs.terrain import Caucasus

from game.ato import packageroute
from game.ato.flightplans.escort import EscortFlightPlan
from game.ato.flightplans.formationattack import (
    FormationAttackBuilder,
    FormationAttackLayout,
)
from game.ato.flightplans.strike import StrikeFlightPlan
from game.ato.flightwaypoint import FlightWaypoint
from game.ato.flightwaypointtype import FlightWaypointType as T
from game.ato.packageroute import Leg
from game.ato.packagewaypoints import PackageWaypoints
from game.utils import feet

TERRAIN = Caucasus()


def _point(north_nm: float, east_nm: float = 0) -> Point:
    return Point(north_nm * 1852, east_nm * 1852, TERRAIN)


def _wp(name: str, kind: T, north_nm: float, alt_ft: int) -> FlightWaypoint:
    return FlightWaypoint(name, kind, _point(north_nm), feet(alt_ft))


def _layout(
    alt_ft: int, lineup: bool, ingress_nav: int = 0, egress_nav: int = 0
) -> FormationAttackLayout:
    return FormationAttackLayout(
        departure=_wp("TAKEOFF", T.TAKEOFF, 0, 0),
        hold=_wp("HOLD", T.LOITER, 5, alt_ft),
        nav_to=[],
        join=_wp("JOIN", T.JOIN, 20, alt_ft),
        ingress_nav=[_wp("NAV", T.NAV, 30 + i, alt_ft) for i in range(ingress_nav)],
        lineup=_wp("NAV", T.NAV, 40, alt_ft) if lineup else None,
        ingress=_wp("INGRESS", T.INGRESS_STRIKE, 50, alt_ft),
        targets=[_wp("TARGET", T.TARGET_POINT, 60, 0)],
        egress_nav=[_wp("NAV", T.NAV, 70 + i, alt_ft) for i in range(egress_nav)],
        split=_wp("SPLIT", T.SPLIT, 80, alt_ft),
        refuel=None,
        nav_from=[],
        arrival=_wp("LANDING", T.LANDING_POINT, 0, 0),
        divert=None,
        bullseye=_wp("BULLSEYE", T.BULLSEYE, 200, 0),
        custom_waypoints=[],
    )


def _flight(
    plan_type: type[Any], layout: FormationAttackLayout, helo: bool = False
) -> SimpleNamespace:
    # A real plan type, so the route's isinstance checks see what the game builds.
    plan = object.__new__(plan_type)
    plan.layout = layout
    flight = SimpleNamespace(is_helo=helo, flight_plan=plan, coalition=None)
    plan.flight = flight
    return flight


class _Package(SimpleNamespace):
    @property
    def primary_flight(self) -> Any:
        return self.flights[0] if self.flights else None


def _package(ingress_nav: int = 0, egress_nav: int = 0) -> _Package:
    """A strike (primary) at 25,000 ft, its escort at 30,000 and a helicopter."""
    strike = _flight(StrikeFlightPlan, _layout(25000, True, ingress_nav, egress_nav))
    escort = _flight(EscortFlightPlan, _layout(30000, False, ingress_nav, egress_nav))
    helo = _flight(StrikeFlightPlan, _layout(500, False), helo=True)
    waypoints = PackageWaypoints(
        _point(20), _point(50), _point(52), _point(80), _point(90)
    )
    target = SimpleNamespace(position=_point(60), name="AARDWOLF")
    package = _Package(
        flights=[strike, escort, helo], waypoints=waypoints, target=target
    )
    for flight in package.flights:
        flight.package = package
    return package


def _navs(package: _Package, leg: Leg) -> list[list[FlightWaypoint]]:
    return [packageroute.sequence(cast(Any, f), leg) for f in package.flights[:2]]


def _route(package: _Package) -> list[Any]:
    return packageroute.route_flights(cast(Any, package))


def test_the_route_is_flown_by_the_formation_flights_not_the_helicopter() -> None:
    package = _package()
    assert _route(package) == package.flights[:2]


def test_no_route_when_the_primary_does_not_fly_one() -> None:
    package = _package()
    package.flights.reverse()  # the helicopter leads
    assert _route(package) == []
    packageroute.insert(cast(Any, package), Leg.IN, 0, _point(30, 5))
    assert package.waypoints.ingress_nav is None


def test_a_point_on_the_way_in_lands_on_every_flight() -> None:
    package = _package()
    where = _point(30, 5)
    packageroute.insert(cast(Any, package), Leg.IN, 0, where)
    strike, escort = _navs(package, Leg.IN)
    assert [w.position for w in strike] == [where]
    assert [w.position for w in escort] == [where]
    assert package.waypoints.ingress_nav == [where]
    assert package.waypoints.egress_nav is None


def test_each_flight_flies_the_point_at_its_own_height() -> None:
    package = _package()
    packageroute.insert(cast(Any, package), Leg.IN, 0, _point(30, 5))
    strike, escort = _navs(package, Leg.IN)
    assert strike[0].alt == feet(25000)
    assert escort[0].alt == feet(30000)


def test_the_escorts_point_is_for_players_as_the_planner_makes_it() -> None:
    package = _package()
    packageroute.insert(cast(Any, package), Leg.OUT, 0, _point(70, 5))
    strike, escort = _navs(package, Leg.OUT)
    assert strike[0].only_for_player is False
    assert escort[0].only_for_player is True


def test_the_first_edit_starts_from_the_primarys_route() -> None:
    package = _package(ingress_nav=2)
    planned = [w.position for w in _navs(package, Leg.IN)[0]]
    packageroute.insert(cast(Any, package), Leg.IN, 1, _point(31, 5))
    assert package.waypoints.ingress_nav == [planned[0], _point(31, 5), planned[1]]
    for navs in _navs(package, Leg.IN):
        assert [w.position for w in navs] == package.waypoints.ingress_nav


def test_the_package_keeps_its_own_copy_of_each_point() -> None:
    package = _package()
    where = _point(30, 5)
    packageroute.insert(cast(Any, package), Leg.IN, 0, where)
    strike, escort = _navs(package, Leg.IN)
    assert strike[0].position is not where
    assert strike[0].position is not escort[0].position


def test_a_point_is_deleted_from_every_flight() -> None:
    package = _package(egress_nav=2)
    packageroute.delete(cast(Any, package), Leg.OUT, 0)
    assert package.waypoints.egress_nav == [_point(71)]
    for navs in _navs(package, Leg.OUT):
        assert [w.position for w in navs] == [_point(71)]


def test_a_point_moves_along_its_leg_for_every_flight() -> None:
    package = _package(ingress_nav=2)
    first = [navs[0] for navs in _navs(package, Leg.IN)]
    assert packageroute.move(cast(Any, package), Leg.IN, 0, 1) is True
    assert [navs[1] for navs in _navs(package, Leg.IN)] == first
    assert packageroute.move(cast(Any, package), Leg.IN, 1, 1) is False


def test_dragging_one_point_moves_it_for_every_flight() -> None:
    package = _package(ingress_nav=1)
    packageroute.set_position(cast(Any, package), Leg.IN, 0, _point(33, 9))
    for navs in _navs(package, Leg.IN):
        assert navs[0].position == _point(33, 9)


def test_a_flight_out_of_step_is_rebuilt_from_the_package(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A point put on one flight alone does not survive a package edit."""
    package = _package()
    strike, escort = package.flights[:2]
    packageroute.sequence(escort, Leg.IN).append(_wp("PRIVATE", T.NAV, 35, 1000))
    monkeypatch.setattr(
        packageroute,
        "_planned_nav",
        lambda flight, where: FlightWaypoint("NAV", T.NAV, where, feet(30000)),
    )
    packageroute.insert(cast(Any, package), Leg.IN, 0, _point(30, 5))
    assert [w.position for w in packageroute.sequence(escort, Leg.IN)] == [
        _point(30, 5)
    ]


def test_find_is_by_identity() -> None:
    package = _package(ingress_nav=1, egress_nav=1)
    strike = package.flights[0]
    way_out = packageroute.sequence(strike, Leg.OUT)[0]
    way_out.position = packageroute.sequence(strike, Leg.IN)[0].position
    assert packageroute.find(strike, way_out) == (Leg.OUT, 0)
    assert packageroute.find(strike, strike.flight_plan.layout.join) is None


def test_a_flights_own_list_names_its_leg() -> None:
    package = _package()
    strike, _, helo = package.flights
    layout = strike.flight_plan.layout
    assert packageroute.leg_of(strike, layout.ingress_nav) is Leg.IN
    assert packageroute.leg_of(strike, layout.egress_nav) is Leg.OUT
    assert packageroute.leg_of(strike, layout.nav_to) is None
    assert packageroute.leg_of(helo, helo.flight_plan.layout.ingress_nav) is None


def test_reset_hands_both_legs_back_to_the_planner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package = _package()
    packageroute.insert(cast(Any, package), Leg.IN, 0, _point(30, 5))
    planned = ([_point(33)], [_point(73), _point(74)])
    monkeypatch.setattr(packageroute, "package_route_points", lambda *_, **__: planned)
    monkeypatch.setattr(
        packageroute,
        "_planned_nav",
        lambda flight, where: FlightWaypoint("NAV", T.NAV, where, feet(20000)),
    )
    packageroute.reset(cast(Any, package))
    assert package.waypoints.ingress_nav is None
    assert package.waypoints.egress_nav is None
    for navs in _navs(package, Leg.IN):
        assert [w.position for w in navs] == [_point(33)]
    for navs in _navs(package, Leg.OUT):
        assert [w.position for w in navs] == [_point(73), _point(74)]


def test_a_flight_built_later_flies_the_players_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A flight added or recreated after the edit reads the package's points."""
    from game.ato.flightplans import formationattack
    from game.ato.flightplans.waypointbuilder import WaypointBuilder

    def no_detour(*_: Any) -> list[Point]:
        raise AssertionError("an edited leg is not re-planned")

    monkeypatch.setattr(formationattack, "package_detour", no_detour)
    waypoints = PackageWaypoints(
        _point(20), _point(50), _point(52), _point(80), _point(90)
    )
    waypoints.ingress_nav = [_point(30, 5)]
    waypoints.egress_nav = []
    builder = SimpleNamespace(
        flight=SimpleNamespace(is_helo=False),
        package=SimpleNamespace(waypoints=waypoints),
        coalition=None,
    )
    ingress, egress = FormationAttackBuilder._sam_detours(
        cast(Any, builder), cast(Any, WaypointBuilder), feet(25000), False
    )
    assert [w.position for w in ingress] == [_point(30, 5)]
    assert ingress[0].position is not waypoints.ingress_nav[0]
    assert egress == []


def test_an_old_save_has_no_route_of_its_own() -> None:
    """Saves made before the field existed read the class default."""
    waypoints = PackageWaypoints.__new__(PackageWaypoints)
    waypoints.__dict__.update(
        join=_point(20),
        ingress=_point(50),
        initial=_point(52),
        split=_point(80),
        refuel=_point(90),
    )
    ingress_nav: Optional[list[Point]] = waypoints.ingress_nav
    assert ingress_nav is None
    assert waypoints.egress_nav is None


class _Events:
    def __init__(self) -> None:
        self.updated: list[Any] = []

    def update_flight(self, flight: Any) -> "_Events":
        self.updated.append(flight)
        return self


def test_dragging_the_primarys_point_on_the_map_moves_the_package() -> None:
    from game.server.waypoints.routes import update_package_waypoints

    package = _package(ingress_nav=1)
    strike, escort, _ = package.flights
    dragged = packageroute.sequence(strike, Leg.IN)[0]
    dragged.position = _point(34, 7)
    events = _Events()
    update_package_waypoints(dragged, cast(Any, strike), cast(Any, events))
    assert packageroute.sequence(escort, Leg.IN)[0].position == _point(34, 7)
    assert package.waypoints.ingress_nav == [_point(34, 7)]
    assert events.updated == [escort]


def test_dragging_an_escorts_point_moves_the_package_too() -> None:
    """Upstream let only the primary move the package; the map works from any flight."""
    from game.server.waypoints.routes import update_package_waypoints

    package = _package(ingress_nav=1)
    strike, escort, _ = package.flights
    dragged = packageroute.sequence(escort, Leg.IN)[0]
    dragged.position = _point(34, 7)
    events = _Events()
    update_package_waypoints(dragged, cast(Any, escort), cast(Any, events))
    assert packageroute.sequence(strike, Leg.IN)[0].position == _point(34, 7)
    assert package.waypoints.ingress_nav == [_point(34, 7)]
    assert events.updated == [strike]


def test_a_helicopters_point_is_its_own() -> None:
    """A helicopter flies no package route, so its drag moves nothing else."""
    from game.server.waypoints.routes import update_package_waypoints

    package = _package(ingress_nav=1)
    strike, _, helo = package.flights
    join = helo.flight_plan.layout.join
    join.position = _point(22, 9)
    update_package_waypoints(join, cast(Any, helo), cast(Any, _Events()))
    assert package.waypoints.join == _point(20)
    assert strike.flight_plan.layout.join.position == _point(20)


def test_a_flights_own_point_does_not_count_along_the_package_leg() -> None:
    package = _package(ingress_nav=2)
    escort = package.flights[1]
    navs = packageroute.sequence(escort, Leg.IN)
    navs.insert(1, _wp("PRIVATE", T.NAV, 30.5, 30000))
    assert packageroute.package_index(cast(Any, package), escort, Leg.IN, 2) == 1
    assert packageroute.find_on_package(cast(Any, package), escort, navs[2]) == (
        Leg.IN,
        1,
    )
    assert packageroute.find_on_package(cast(Any, package), escort, navs[1]) is None


def test_deleting_past_the_end_of_a_leg_changes_nothing() -> None:
    package = _package(egress_nav=1)
    packageroute.delete(cast(Any, package), Leg.OUT, 3)
    assert package.waypoints.egress_nav is None
    assert len(packageroute.sequence(package.flights[0], Leg.OUT)) == 1


def _kinds(package: _Package) -> list[str]:
    return [p.kind.name for p in packageroute.route_points(cast(Any, package))]


def test_the_route_reads_in_the_order_it_is_flown() -> None:
    package = _package(ingress_nav=1, egress_nav=2)
    assert _kinds(package) == ["JOIN", "NAV", "IP", "TARGET", "NAV", "NAV", "SPLIT"]
    rows = packageroute.route_points(cast(Any, package))
    assert [(r.leg, r.index) for r in rows if r.leg] == [
        (Leg.IN, 0),
        (Leg.OUT, 0),
        (Leg.OUT, 1),
    ]


def test_no_route_rows_when_the_package_has_no_route() -> None:
    package = _package()
    package.flights.reverse()
    assert packageroute.route_points(cast(Any, package)) == []
    assert packageroute.insert_beside(cast(Any, package), 0) is None


def test_a_point_after_the_join_goes_halfway_to_the_ip() -> None:
    package = _package()
    assert packageroute.insert_beside(cast(Any, package), 0) == (Leg.IN, 0)
    assert package.waypoints.ingress_nav == [_point(35)]
    assert _kinds(package) == ["JOIN", "NAV", "IP", "TARGET", "SPLIT"]


def test_the_ip_takes_its_point_on_the_leg_before_it() -> None:
    package = _package(ingress_nav=1)
    assert packageroute.insert_beside(cast(Any, package), 2) == (Leg.IN, 1)
    assert package.waypoints.ingress_nav == [_point(30), _point(40)]


def test_the_target_opens_the_way_out() -> None:
    package = _package()
    assert packageroute.insert_beside(cast(Any, package), 2) == (Leg.OUT, 0)
    assert package.waypoints.egress_nav == [_point(70)]


def test_the_split_takes_its_point_on_the_leg_before_it() -> None:
    package = _package(egress_nav=1)
    assert packageroute.insert_beside(cast(Any, package), 4) == (Leg.OUT, 1)
    assert package.waypoints.egress_nav == [_point(70), _point(75)]


def test_a_point_the_primary_carries_alone_moves_alone() -> None:
    from game.server.waypoints.routes import update_package_waypoints

    package = _package(ingress_nav=1)
    strike, escort, _ = package.flights
    packageroute.insert(cast(Any, package), Leg.IN, 1, _point(32))
    private = _wp("PRIVATE", T.NAV, 33, 25000)
    packageroute.sequence(strike, Leg.IN).append(private)
    private.position = _point(34, 7)
    update_package_waypoints(private, cast(Any, strike), cast(Any, _Events()))
    assert package.waypoints.ingress_nav == [_point(30), _point(32)]
    assert [w.position for w in packageroute.sequence(escort, Leg.IN)] == [
        _point(30),
        _point(32),
    ]
