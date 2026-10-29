"""The player-only runway line-up (ALIGN) waypoint and departure hold (§126)."""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any, Optional

import pytest
from dcs.mapping import Point
from dcs.terrain import Syria

from game.ato.flightplans import alignpoint
from game.runways import runway_centerline
from game.utils import Heading, feet, nautical_miles

START = datetime(2026, 10, 29, 8, 0)
TERRAIN = Syria()


class _Airfield:
    """The parts of an Airfield the module uses."""

    def __init__(self, heading: int = 90, runway: str = "09") -> None:
        self.name = "Incirlik"
        self.theater = SimpleNamespace(terrain=TERRAIN)
        self.airport = None
        self.position = Point(0, 0, TERRAIN)
        self._runway = SimpleNamespace(
            runway_heading=Heading.from_degrees(heading), runway_name=runway
        )

    def active_runway(self, theater: Any, conditions: Any, dynamic: Any) -> Any:
        return self._runway


class _Carrier:
    """The parts of a NavalControlPoint the module uses."""

    def __init__(self, deck_angle: float = 9.0, sea: bool = True) -> None:
        self.name = "CVN-72"
        self.position = Point(0, 0, TERRAIN)
        self.theater = SimpleNamespace(is_in_sea=lambda point: sea)
        unit = SimpleNamespace(
            alive=True, unit_type=SimpleNamespace(landing_deck_angle=deck_angle)
        )
        self.ground_objects = [SimpleNamespace(groups=[SimpleNamespace(units=[unit])])]


@pytest.fixture(autouse=True)
def the_types(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make the doubles pass the isinstance checks."""
    import game.theater.controlpoint as controlpoint

    monkeypatch.setattr(controlpoint, "Airfield", _Airfield)
    monkeypatch.setattr(controlpoint, "NavalControlPoint", _Carrier)


def _flight(
    field: Any,
    *,
    players: int = 1,
    lineup: bool = True,
    hold: bool = True,
    helicopter: bool = False,
    wind_toward: float = 0.0,
    wind_mps: float = 0.0,
    threatened: bool = False,
) -> Any:
    settings = SimpleNamespace(player_runway_lineup=lineup, player_departure_hold=hold)
    conditions = SimpleNamespace(
        start_time=START,
        weather=SimpleNamespace(
            wind=SimpleNamespace(
                at_0m=SimpleNamespace(direction=wind_toward, speed=wind_mps)
            )
        ),
    )
    return SimpleNamespace(
        arrival=field,
        departure=field,
        is_helo=helicopter,
        client_count=players,
        coalition=SimpleNamespace(
            game=SimpleNamespace(settings=settings, conditions=conditions),
            doctrine=SimpleNamespace(hold_distance=nautical_miles(25)),
            opponent=SimpleNamespace(
                threat_zone=SimpleNamespace(threatened=lambda point: threatened)
            ),
        ),
    )


def _plan(minutes_to_landing: Optional[int] = 60) -> Any:
    nav_from: list[Any] = []
    landing = (
        START + timedelta(minutes=minutes_to_landing)
        if minutes_to_landing is not None
        else None
    )
    return SimpleNamespace(
        layout=SimpleNamespace(nav_from=nav_from), landing_time=landing
    )


def _bearing_and_range(origin: Point, point: Point) -> tuple[float, float]:
    return (
        origin.heading_between_point(point),
        origin.distance_to_point(point) / nautical_miles(1).meters,
    )


def test_ai_flights_get_nothing() -> None:
    flight = _flight(_Airfield(), players=0)
    assert alignpoint.align_waypoint(flight, _plan()) is None
    assert alignpoint.hold_point(flight) is None


def test_each_setting_turns_its_point_off() -> None:
    assert (
        alignpoint.align_waypoint(_flight(_Airfield(), lineup=False), _plan()) is None
    )
    assert alignpoint.hold_point(_flight(_Airfield(), hold=False)) is None


def test_airfield_lineup_is_15_nm_out_on_final() -> None:
    field = _Airfield(heading=90)
    waypoint = alignpoint.align_waypoint(_flight(field), _plan())
    assert waypoint is not None
    bearing, distance = _bearing_and_range(field.position, waypoint.position)
    assert bearing == pytest.approx(270, abs=0.1)
    assert distance == pytest.approx(15, abs=0.01)
    assert waypoint.alt.feet == pytest.approx(4500)
    assert waypoint.alt_type == "RADIO"
    assert waypoint.only_for_player


def test_helicopters_line_up_2_nm_out_at_the_floor() -> None:
    field = _Airfield()
    waypoint = alignpoint.align_waypoint(_flight(field, helicopter=True), _plan())
    assert waypoint is not None
    _, distance = _bearing_and_range(field.position, waypoint.position)
    assert distance == pytest.approx(2, abs=0.01)
    assert waypoint.alt == feet(1500)


def test_a_field_without_runways_gets_nothing() -> None:
    flight = _flight(_Airfield(runway=""))
    assert alignpoint.align_waypoint(flight, _plan()) is None
    assert alignpoint.hold_point(flight) is None


def test_the_localizer_centerline_wins_over_the_rounded_heading(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    field = _Airfield(heading=90)
    field.airport = object()  # type: ignore[assignment]
    center = Point(1000, 0, TERRAIN)
    monkeypatch.setattr(alignpoint, "runway_centerline", lambda *_: (center, 96.0))
    flight = _flight(field)
    waypoint = alignpoint.align_waypoint(flight, _plan())
    hold = alignpoint.hold_point(flight)
    assert waypoint is not None and hold is not None
    assert _bearing_and_range(center, waypoint.position)[0] == pytest.approx(
        276, abs=0.1
    )
    assert _bearing_and_range(center, hold)[0] == pytest.approx(96, abs=0.1)


def test_adana_centerline_is_the_beam_not_the_pydcs_heading() -> None:
    theater: Any = SimpleNamespace(terrain=TERRAIN)
    airport = TERRAIN.airports["Adana Sakirpasa"]
    axis = runway_centerline(theater, airport, "05")
    assert axis is not None
    center, course = axis
    # pydcs says 050; the ILS localizer beam is 055.8.
    assert course == pytest.approx(55.8, abs=0.05)
    assert center.distance_to_point(airport.position) < 500


def test_carrier_lineup_is_50_nm_astern_on_the_angled_deck() -> None:
    carrier = _Carrier(deck_angle=9.0)
    # Calm: the ship steams into the (absent) wind on 180 at 25 kt for an hour.
    flight = _flight(carrier, wind_toward=0.0, wind_mps=0.0)
    waypoint = alignpoint.align_waypoint(flight, _plan(60))
    assert waypoint is not None
    brc, speed, deck = alignpoint.carrier_course(flight, carrier)  # type: ignore[arg-type]
    assert (brc, speed, deck) == (pytest.approx(180), pytest.approx(25), 9.0)
    recovery = carrier.position.point_from_heading(180, nautical_miles(25).meters)
    bearing, distance = _bearing_and_range(recovery, waypoint.position)
    assert bearing == pytest.approx((180 - 9 + 180) % 360, abs=0.1)
    assert distance == pytest.approx(50, abs=0.01)
    assert waypoint.alt == feet(6000)


def test_the_ship_stops_at_the_end_of_its_leg() -> None:
    carrier = _Carrier()
    flight = _flight(carrier)
    long = alignpoint.align_waypoint(flight, _plan(300))
    longer = alignpoint.align_waypoint(flight, _plan(600))
    assert long is not None and longer is not None
    assert long.position.distance_to_point(longer.position) < 1


def test_an_untimed_plan_measures_from_the_ship_as_it_starts() -> None:
    carrier = _Carrier(deck_angle=0.0)
    waypoint = alignpoint.align_waypoint(_flight(carrier), _plan(None))
    assert waypoint is not None
    _, distance = _bearing_and_range(carrier.position, waypoint.position)
    assert distance == pytest.approx(50, abs=0.01)


def test_hold_is_straight_out_the_runway_at_the_doctrine_distance() -> None:
    field = _Airfield(heading=90)
    hold = alignpoint.hold_point(_flight(field))
    assert hold is not None
    bearing, distance = _bearing_and_range(field.position, hold)
    assert bearing == pytest.approx(90, abs=0.1)
    assert distance == pytest.approx(25, abs=0.01)


def test_hold_inside_a_threat_ring_keeps_the_usual_hold() -> None:
    assert alignpoint.hold_point(_flight(_Airfield(), threatened=True)) is None


def test_carrier_hold_is_ahead_on_its_course() -> None:
    carrier = _Carrier()
    hold = alignpoint.hold_point(_flight(carrier, wind_toward=0.0, wind_mps=0.0))
    assert hold is not None
    bearing, distance = _bearing_and_range(carrier.position, hold)
    assert bearing == pytest.approx(180, abs=0.1)
    assert distance == pytest.approx(25, abs=0.01)


def test_update_align_follows_the_seats() -> None:
    field = _Airfield()
    plan = _plan()
    flight = _flight(field)
    alignpoint.update_align(flight, plan)
    alignpoint.update_align(flight, plan)
    assert [w.name for w in plan.layout.nav_from] == ["ALIGN"]
    flight.client_count = 0
    alignpoint.update_align(flight, plan)
    assert plan.layout.nav_from == []


def test_a_plan_without_a_nav_leg_home_is_left_alone() -> None:
    alignpoint.update_align(_flight(_Airfield()), SimpleNamespace(layout=object()))
    alignpoint.update_align(_flight(_Airfield()), None)
