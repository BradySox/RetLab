"""The plan's fuel walk: ground time, holds and low legs (2026-11-16).

Measured against flown F-4E sorties, the old walk charged a flat taxi, no hold
and the cruise or combat rate on a low attack, and came out about half the burn.
"""

from datetime import timedelta

import pytest
from dcs import Point
from dcs.terrain import Caucasus

from game.ato.flightwaypoint import FlightWaypoint
from game.ato.flightwaypointtype import FlightWaypointType
from game.dcs.aircrafttype import FuelConsumption
from game.utils import Distance, Speed, feet, knots

from .test_patrol_timing import T0, _FixedPatrolPlan, _make_patrol_plan

_MEASURED = FuelConsumption(
    taxi=250,
    climb=46.0,
    cruise=25.0,
    combat=32.0,
    min_safe=2000,
    ground_ppmin=40.0,
    low=46.0,
)
_FLAT = FuelConsumption(taxi=250, climb=46.0, cruise=25.0, combat=32.0, min_safe=2000)
_NM = 1852.0


def _at(
    nm: float,
    alt: Distance = feet(20000),
    kind: FlightWaypointType = FlightWaypointType.NAV,
) -> FlightWaypoint:
    return FlightWaypoint("wp", kind, Point(nm * _NM, 0, Caucasus()), alt=alt)


class _GroundPlan(_FixedPatrolPlan):
    def takeoff_time(self):  # type: ignore[no-untyped-def]
        return T0

    def startup_time(self):  # type: ignore[no-untyped-def]
        return T0 - timedelta(minutes=18, seconds=30)


class _HoldPlan(_FixedPatrolPlan):
    """Five minutes waiting on the leg out of the arrival stand-in, at 420 kt."""

    def total_time_between_waypoints(self, a, b):  # type: ignore[no-untyped-def]
        travel = self.travel_time_between_waypoints(a, b)
        if a.name == "hold":
            return travel + timedelta(minutes=5)
        return travel

    def speed_between_waypoints(self, a, b) -> Speed:  # type: ignore[no-untyped-def]
        return knots(420)


def test_ground_time_is_charged_by_the_minute() -> None:
    plan = _make_patrol_plan(_GroundPlan)
    assert plan.ground_fuel_lbs(_MEASURED) == pytest.approx(18.5 * 40)


def test_an_airframe_without_a_ground_rate_keeps_the_flat_taxi() -> None:
    plan = _make_patrol_plan(_GroundPlan)
    assert plan.ground_fuel_lbs(_FLAT) == 250


def test_ground_charge_never_drops_below_the_taxi() -> None:
    class _HotStart(_GroundPlan):
        def startup_time(self):  # type: ignore[no-untyped-def]
            return T0 - timedelta(minutes=2)

    plan = _make_patrol_plan(_HotStart)
    assert plan.ground_fuel_lbs(_MEASURED) == 250


def test_a_hold_is_charged_as_miles_flown_waiting() -> None:
    plan = _make_patrol_plan(_HoldPlan)
    hold = _at(0)
    hold.name = "hold"
    onward = _at(10)
    # 10 NM of leg plus 5 min at 420 kt = 35 NM of orbit.
    burn = plan.fuel_consumption_between_points(hold, onward, _MEASURED)
    assert burn == pytest.approx((10 + 35) * 25.0)
    assert plan.fuel_consumption_between_points(onward, _at(20), _MEASURED) == (
        pytest.approx(10 * 25.0)
    )


def test_low_legs_burn_at_the_low_rate() -> None:
    plan = _make_patrol_plan()
    low_a, low_b = _at(0, feet(500)), _at(10, feet(500))
    assert plan.fuel_rate_to_between_points(low_a, low_b, _MEASURED) == 46.0
    # One end high: the dive from altitude is not a low leg.
    assert plan.fuel_rate_to_between_points(_at(0), low_b, _MEASURED) == 25.0
    # An approach to land is not a low leg.
    landing = _at(10, feet(500), FlightWaypointType.LANDING_POINT)
    assert plan.fuel_rate_to_between_points(low_a, landing, _MEASURED) == 25.0
    # No measured low rate: unchanged.
    assert plan.fuel_rate_to_between_points(low_a, low_b, _FLAT) == 25.0


def test_yaml_reads_the_optional_rates() -> None:
    base = dict(taxi=250, climb_ppm=46, cruise_ppm=25, combat_ppm=32, min_safe=2000)
    assert FuelConsumption.from_data(base) == _FLAT
    assert (
        FuelConsumption.from_data({**base, "ground_ppmin": 40, "low_ppm": 46})
        == _MEASURED
    )
