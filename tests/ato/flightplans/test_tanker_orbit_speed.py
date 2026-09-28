from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Optional

import pytest

from game.ato.flightplans.shiprecoverytanker import RecoveryTankerFlightPlan
from game.ato.flightplans.theaterrefueling import TheaterRefuelingFlightPlan
from game.utils import Speed, feet, knots, kph


@pytest.mark.parametrize(
    "kias,altitude_ft,expected_ktas",
    [
        (300, 0, 300.0),
        (300, 24000, 425.0),
        (280, 21000, 380.0),
        (250, 40000, 472.0),
    ],
)
def test_calibrated_to_true_airspeed(
    kias: float, altitude_ft: float, expected_ktas: float
) -> None:
    tas = Speed.from_calibrated(knots(kias), feet(altitude_ft))
    assert tas.knots == pytest.approx(expected_ktas, abs=3)


def _plan(
    cls: Any,
    *,
    enabled: bool,
    kias: int = 280,
    own_speed: Optional[Speed] = knots(445),
    max_speed_kph: Optional[float] = 980,
    altitude_ft: float = 24000,
) -> Any:
    settings = SimpleNamespace(
        tanker_orbit_speed_set=enabled, tanker_orbit_speed_kias=kias
    )
    unit_type = SimpleNamespace(
        patrol_speed=own_speed,
        max_speed=kph(max_speed_kph or 0),
        dcs_unit_type=SimpleNamespace(max_speed=max_speed_kph),
    )
    plan = cls.__new__(cls)
    plan.flight = SimpleNamespace(
        coalition=SimpleNamespace(game=SimpleNamespace(settings=settings)),
        unit_type=unit_type,
    )
    plan.layout = SimpleNamespace(patrol_start=SimpleNamespace(alt=feet(altitude_ft)))
    return plan


def test_off_keeps_the_aircraft_speed() -> None:
    plan = _plan(TheaterRefuelingFlightPlan, enabled=False)
    assert plan.patrol_speed == knots(445)


def test_on_flies_the_set_kias_as_true_airspeed() -> None:
    plan = _plan(TheaterRefuelingFlightPlan, enabled=True, kias=275)
    expected = Speed.from_calibrated(knots(275), feet(24000))
    assert plan.patrol_speed == expected


def test_helicopter_tanker_keeps_its_own_speed() -> None:
    # KC-130J: 180 kt TAS at 22,000 ft, ~125 KIAS.
    plan = _plan(
        TheaterRefuelingFlightPlan,
        enabled=True,
        own_speed=knots(180),
        altitude_ft=22000,
    )
    assert plan.patrol_speed == knots(180)


def test_capped_at_the_aircraft_top_speed() -> None:
    # KC-130: 621 km/h top speed, below 300 KIAS at 22,000 ft.
    plan = _plan(
        TheaterRefuelingFlightPlan,
        enabled=True,
        kias=300,
        own_speed=knots(370),
        max_speed_kph=621,
        altitude_ft=22000,
    )
    assert plan.patrol_speed == kph(621)


def test_recovery_tanker_ignores_the_setting() -> None:
    plan = _plan(RecoveryTankerFlightPlan, enabled=True, kias=200)
    assert plan.patrol_speed == knots(445)
