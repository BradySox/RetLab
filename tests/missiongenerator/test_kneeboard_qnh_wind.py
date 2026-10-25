"""Mission Info keeps QNH and the surface wind when the Departure page has the weather.

The weather block was dropped from Mission Info (2026-06) whenever the recon
Departure page carries it. Pilots set the altimeter and read the takeoff wind off
Mission Info, so those two stay on it either way (2026-10-25).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

from game.missiongenerator.kneeboard import BriefingPage, FlightPlanBuilder
from game.utils import inches_hg, knots


def _page(omit_weather: bool) -> BriefingPage:
    page = BriefingPage.__new__(BriefingPage)
    page.omit_weather = omit_weather
    page.theater = None  # no elevation lookup: raw QNH, no QFE line
    page.flight = MagicMock()
    page.flight.departure.airfield_name = "Shindand"
    page.weather = SimpleNamespace(  # type: ignore[assignment]
        atmospheric=SimpleNamespace(
            qnh=inches_hg(29.92),
            temperature_celsius=15.0,
            turbulence_per_10cm=0.0,
        ),
        wind=SimpleNamespace(
            at_0m=SimpleNamespace(direction=180, speed=knots(10).meters_per_second),
        ),
        clouds=None,
    )
    return page


def test_altimeter_lines_carry_qnh_in_inches_and_hectopascals() -> None:
    assert _page(omit_weather=True)._altimeter_lines() == ["QNH: 29.92 inHg (1013 hPa)"]


def test_surface_wind_line_is_the_direction_the_wind_blows_from() -> None:
    # DCS stores the direction the wind blows to; the card prints where it is from.
    assert _page(omit_weather=True)._surface_wind_line() == "Surface wind: 0° / 10kts"


def _point(heading: float) -> Any:
    return SimpleNamespace(
        distance_to_point=lambda other: 1000.0,
        heading_between_point=lambda other: heading,
    )


def _wp(heading_out: float) -> Any:
    return SimpleNamespace(
        display_name="Nav",
        alt=0,
        position=_point(heading_out),
        tot=None,
        departure_time=None,
        fuel_planned=None,
        min_fuel=None,
        waypoint_type=None,
        marks_ground_for_player=True,
    )


def test_brg_column_is_the_true_course_into_each_waypoint() -> None:
    units = SimpleNamespace(
        distance_short=lambda d: 0.0,
        distance_long=lambda d: 1.0,
        speed=lambda s: 0.0,
        mass=lambda m: 0.0,
    )
    builder = FlightPlanBuilder(units)  # type: ignore[arg-type]
    builder.add_waypoint(0, _wp(heading_out=-5.0))
    builder.add_waypoint(1, _wp(heading_out=0.0))
    rows = builder.build()
    assert rows[0][4] == "-"
    # The leg from waypoint 0 heads -5 degrees, printed as a three-digit course.
    assert rows[1][4] == "355"
