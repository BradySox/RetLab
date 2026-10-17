"""An escort holds where its package's shooters start their run.

The IP sits 7-9 nm from the target. Since a stand-off shooter starts its run at
its own launch range, holding the escorts at the IP put them deeper into the
defenses than the jets they protect: a Patriot DEAD's escorts held 7 nm from it
while the Kh-59M shooters turned 62 nm out (Desert Trident turn 1, 2026-10-16).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Optional

import pytest
from dcs import Point
from dcs.terrain import Caucasus

from game.ato.flighttype import FlightType
from game.ato.packagewaypoints import PackageWaypoints
from game.utils import Distance, nautical_miles

TERRAIN = Caucasus()


def _point(north_nm: float, east_nm: float = 0) -> Point:
    return Point(north_nm * 1852, east_nm * 1852, TERRAIN)


def _flight(task: FlightType, standoff: Optional[Distance]) -> Any:
    return SimpleNamespace(flight_type=task, max_standoff_range=standoff)


def _package(
    *flights: Any,
    primary: FlightType = FlightType.DEAD,
    ingress_nm: float = 62,
    ip_nm: float = 8,
) -> Any:
    # Target at the origin, ingress and IP due north of it, as get_initial_point
    # lays them out.
    return SimpleNamespace(
        target=SimpleNamespace(name="TARGET", position=_point(0)),
        flights=list(flights),
        primary_task=primary,
        waypoints=SimpleNamespace(ingress=_point(ingress_nm), initial=_point(ip_nm)),
    )


def _shooters(*ranges: Optional[Distance]) -> Any:
    return _package(*(_flight(FlightType.DEAD, r) for r in ranges))


def _hold_nm(package: Any) -> float:
    hold = PackageWaypoints.escort_hold_point(package)
    return hold.distance_to_point(package.target.position) / 1852


def test_a_shooter_with_no_ranged_weapon_keeps_the_ip() -> None:
    package = _shooters(None)
    assert PackageWaypoints.escort_hold_point(package) is package.waypoints.initial


def test_a_shooter_that_fires_inside_the_ip_keeps_the_ip() -> None:
    # A 6 nm Maverick shooter flies past the IP to fire, so the IP is still right.
    package = _shooters(nautical_miles(6))
    assert PackageWaypoints.escort_hold_point(package) is package.waypoints.initial


def test_a_stand_off_shooter_pulls_the_hold_out_to_its_launch_range() -> None:
    assert _hold_nm(_shooters(nautical_miles(30))) == pytest.approx(30)


def test_the_hold_never_goes_past_the_ingress() -> None:
    # The ingress is capped at 60% of the leg, so a weapon range longer than the
    # ingress distance would put the hold behind the join.
    assert _hold_nm(_shooters(nautical_miles(150))) == pytest.approx(62)


def test_the_hold_stays_on_the_ingress_bearing() -> None:
    hold = PackageWaypoints.escort_hold_point(_shooters(nautical_miles(30)))
    assert hold.y == pytest.approx(0, abs=1)
    assert hold.x > 0


def test_the_shortest_shooter_sets_the_hold() -> None:
    package = _shooters(nautical_miles(60), nautical_miles(25))
    assert _hold_nm(package) == pytest.approx(25)


def test_one_shooter_without_a_ranged_weapon_keeps_the_ip() -> None:
    # It flies to the target, and its escorts must be there with it.
    package = _shooters(nautical_miles(60), None)
    assert PackageWaypoints.escort_hold_point(package) is package.waypoints.initial


def test_an_escorts_anti_radar_missile_does_not_move_a_bomb_strikes_hold() -> None:
    package = _package(
        _flight(FlightType.STRIKE, None),
        _flight(FlightType.SEAD_ESCORT, nautical_miles(25)),
        _flight(FlightType.ESCORT, None),
        primary=FlightType.STRIKE,
    )
    assert PackageWaypoints.escort_hold_point(package) is package.waypoints.initial


def test_the_escorts_own_range_is_ignored_on_a_stand_off_package() -> None:
    # The Patriot DEAD: Kh-59M shooters, Kh-58U SEAD escorts. The shooters set it.
    package = _package(
        _flight(FlightType.DEAD, nautical_miles(62)),
        _flight(FlightType.SEAD_ESCORT, nautical_miles(25)),
        _flight(FlightType.ESCORT, None),
    )
    assert _hold_nm(package) == pytest.approx(62)


def _sead_flight(has_arm: bool = True, task: FlightType = FlightType.SEAD) -> Any:
    flight = SimpleNamespace(
        flight_type=task,
        # A HARM's authored range: what put the old hold out on the ingress.
        max_standoff_range=nautical_miles(80),
        coalition=SimpleNamespace(
            game=SimpleNamespace(
                settings=SimpleNamespace(sead_threat_buffer_min_distance=40)
            )
        ),
        any_member_has_weapon_of_type=lambda _weapon: has_arm,
    )
    return flight


def _sead_package(*flights: Any, threat_nm: float = 25) -> Any:
    package = _package(*flights, primary=flights[0].flight_type, ingress_nm=75)
    site = SimpleNamespace(threat_range=lambda: nautical_miles(threat_nm))
    package.target.strike_targets = [site]
    for flight in flights:
        flight.package = package
    return package


def test_a_sead_packages_escorts_hold_at_the_sead_search_point() -> None:
    # Plain SEAD works from 0.8x the SAM's threat range with an ARM, not from
    # its HARM's 80 nm authored range out on the ingress.
    package = _sead_package(_sead_flight(), _flight(FlightType.ESCORT, None))
    assert _hold_nm(package) == pytest.approx(20)


def test_a_sead_sweeps_escorts_hold_at_its_sweep_point() -> None:
    package = _sead_package(_sead_flight(task=FlightType.SEAD_SWEEP))
    assert _hold_nm(package) == pytest.approx(20)


def test_the_nearest_sead_search_point_sets_the_hold() -> None:
    # A SEAD flight without an ARM stands off at 1.1x; the ARM shooter goes closer.
    package = _sead_package(_sead_flight(has_arm=False), _sead_flight())
    assert _hold_nm(package) == pytest.approx(20)


def test_a_sead_search_point_inside_the_ip_keeps_the_ip() -> None:
    package = _sead_package(_sead_flight(), threat_nm=5)
    assert PackageWaypoints.escort_hold_point(package) is package.waypoints.initial
