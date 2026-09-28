"""Editing a route from the map: a double-click adds a point, a right-click deletes one.

The DM, 2026-09-28, on the Package route window: "I will never type in cords for
points, I wanna move the points on the map."
"""

from __future__ import annotations

from typing import Any, cast

import pytest

from game.ato import packageroute, routeedit
from game.ato.flightwaypointtype import FlightWaypointType as T
from game.ato.packageroute import Leg
from tests.ato.test_package_route import _package, _point, _wp


def _map_package(ingress_nav: int = 0) -> Any:
    """The shared fixture, with the way home off to the east so it does not lie
    on top of the way out and every click has one nearest leg."""
    package = _package(ingress_nav=ingress_nav)
    for flight in package.flights:
        flight.flight_plan.layout.arrival.position = _point(0, 30)
    return package


def _positions(flight: Any, leg: Leg) -> list[Any]:
    return [w.position for w in packageroute.sequence(flight, leg)]


def test_a_click_on_the_way_in_adds_the_point_to_every_flight() -> None:
    package = _map_package()
    strike, escort, _ = package.flights
    moved = routeedit.insert_nav_at(strike, _point(30, 2))
    assert moved == [strike, escort]
    assert _positions(strike, Leg.IN) == [_point(30, 2)]
    assert _positions(escort, Leg.IN) == [_point(30, 2)]
    assert package.waypoints.ingress_nav == [_point(30, 2)]


def test_a_click_on_an_escorts_way_out_adds_it_to_the_package() -> None:
    package = _map_package()
    strike, escort, _ = package.flights
    routeedit.insert_nav_at(escort, _point(68, 0.5))
    assert _positions(strike, Leg.OUT) == [_point(68, 0.5)]
    assert package.waypoints.egress_nav == [_point(68, 0.5)]


def test_a_click_on_the_transit_leg_changes_that_flight_only() -> None:
    package = _map_package()
    strike, escort, _ = package.flights
    moved = routeedit.insert_nav_at(strike, _point(12, 1))
    assert moved == [strike]
    assert [w.position for w in strike.flight_plan.layout.nav_to] == [_point(12, 1)]
    assert escort.flight_plan.layout.nav_to == []


def test_a_click_on_the_attack_run_is_refused_with_the_reason() -> None:
    package = _map_package()
    strike = package.flights[0]
    with pytest.raises(routeedit.RouteEditRefused, match="INGRESS to TARGET"):
        routeedit.insert_nav_at(strike, _point(55, 1))


def test_the_new_point_flies_at_the_height_of_its_leg() -> None:
    package = _map_package()
    strike = package.flights[0]
    routeedit.insert_nav_at(strike, _point(12, 1))
    assert strike.flight_plan.layout.nav_to[0].alt == strike.flight_plan.layout.join.alt


def test_deleting_a_package_point_takes_it_from_every_flight() -> None:
    package = _map_package()
    strike, escort, _ = package.flights
    routeedit.insert_nav_at(strike, _point(30, 2))
    moved = routeedit.delete_nav(escort, packageroute.sequence(escort, Leg.IN)[0])
    assert moved == [strike, escort]
    assert _positions(strike, Leg.IN) == []
    assert package.waypoints.ingress_nav == []


def test_a_flights_own_point_is_deleted_from_it_alone() -> None:
    package = _map_package(ingress_nav=1)
    strike, escort, _ = package.flights
    private = _wp("PRIVATE", T.NAV, 33, 30000)
    packageroute.sequence(escort, Leg.IN).append(private)
    assert routeedit.delete_nav(escort, private) == [escort]
    assert _positions(escort, Leg.IN) == [_point(30)]
    assert _positions(strike, Leg.IN) == [_point(30)]


def test_a_fixed_point_is_not_deleted_from_the_map() -> None:
    package = _map_package()
    strike = package.flights[0]
    assert not routeedit.is_deletable(strike, strike.flight_plan.layout.join)
    with pytest.raises(routeedit.RouteEditRefused, match="drag it to move it"):
        routeedit.delete_nav(strike, strike.flight_plan.layout.join)


def test_the_map_is_told_what_each_point_does(monkeypatch: pytest.MonkeyPatch) -> None:
    from game.server.waypoints import models

    monkeypatch.setattr(models, "timing_info", lambda _flight, _idx: "")
    package = _map_package(ingress_nav=1)
    strike = package.flights[0]
    layout = strike.flight_plan.layout
    routeedit.insert_nav_at(strike, _point(12, 1))

    def flags(waypoint: Any) -> tuple[bool, bool]:
        js = models.FlightWaypointJs.for_waypoint(waypoint, cast(Any, strike), 1)
        return js.deletable, js.package_point

    assert flags(layout.ingress_nav[0]) == (True, True)
    assert flags(layout.join) == (False, True)
    assert flags(layout.ingress) == (False, True)
    assert flags(layout.nav_to[0]) == (True, False)
    assert flags(layout.targets[0]) == (False, False)
