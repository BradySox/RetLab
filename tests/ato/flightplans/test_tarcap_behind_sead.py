"""tarcap_behind_sead: a TARCAP does not reach the target before its package's SEAD.

Test 40: SARDINE's F-15C TARCAP started 2 min before the package's join, over the
SA-11 the package was fragged to suppress, and all four died 17 min before the
SEAD sweep's TOT.
"""

from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any

from dcs import Point
from dcs.terrain import Caucasus

from game.ato.flightplans.tarcap import TarCapFlightPlan, TarCapLayout
from game.ato.flighttype import FlightType
from game.ato.flightwaypoint import FlightWaypoint
from game.ato.flightwaypointtype import FlightWaypointType

T0 = datetime(2002, 6, 28, 0, 0, 0)
JOIN = T0 + timedelta(seconds=1904)
SEAD_TOT = T0 + timedelta(seconds=2771)


def _wp(name: str, kind: FlightWaypointType) -> FlightWaypoint:
    return FlightWaypoint(name, kind, Point(0, 0, Caucasus()))


def _tarcap(on: bool, sead_types: tuple[FlightType, ...]) -> TarCapFlightPlan:
    others = [
        SimpleNamespace(flight_type=t, flight_plan=SimpleNamespace(tot=SEAD_TOT))
        for t in sead_types
    ]
    package: Any = SimpleNamespace(
        time_over_target=SEAD_TOT, escort_start_time=JOIN, flights=others
    )
    flight: Any = SimpleNamespace(
        package=package,
        coalition=SimpleNamespace(
            game=SimpleNamespace(settings=SimpleNamespace(tarcap_behind_sead=on))
        ),
    )
    layout = TarCapLayout(
        departure=_wp("dep", FlightWaypointType.TAKEOFF),
        custom_waypoints=[],
        arrival=_wp("arr", FlightWaypointType.LANDING_POINT),
        divert=None,
        bullseye=_wp("bull", FlightWaypointType.BULLSEYE),
        nav_to=[],
        nav_from=[],
        patrol_start=_wp("ps", FlightWaypointType.PATROL_TRACK),
        patrol_end=_wp("pe", FlightWaypointType.PATROL),
        refuel=None,
    )
    plan = TarCapFlightPlan(flight, layout)
    package.flights.append(SimpleNamespace(flight_type=FlightType.TARCAP))
    return plan


def test_stock_tarcap_starts_before_the_join() -> None:
    plan = _tarcap(False, (FlightType.SEAD_SWEEP,))
    assert plan.patrol_start_time == JOIN - timedelta(minutes=2)


def test_tarcap_waits_for_the_packages_sead() -> None:
    plan = _tarcap(True, (FlightType.SEAD_SWEEP, FlightType.SEAD_ESCORT))
    assert plan.patrol_start_time == SEAD_TOT


def test_a_package_without_suppression_is_unchanged() -> None:
    plan = _tarcap(True, (FlightType.STRIKE,))
    assert plan.patrol_start_time == JOIN - timedelta(minutes=2)
