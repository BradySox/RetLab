"""The mission starts early enough that a queued ground start makes its TOT.

A startup before the turn's clock used to clamp to mission start (test 39's
PORCUPINE departed 0:00:00). The mission now begins up to 30 min early; the turn
clock and every TOT stay put. docs/dev/design/retlab-startup-times-notes.md.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any, cast

from game.ato.flightstate import StartUp, WaitingForStart
from game.ato.starttype import StartType
from game.sim.missionsimulation import MissionSimulation
from game.sim.missionstart import EARLY_START_CAP, early_start_shift

TURN = datetime(2026, 9, 23, 12, 0, 0)
AI_STARTUP = timedelta(minutes=2)


class _Flight(SimpleNamespace):
    def set_state(self, state: Any) -> None:
        self.state = state


def _flight(
    startup: datetime,
    start_type: StartType = StartType.COLD,
    tot: datetime = TURN + timedelta(hours=1),
) -> Any:
    flight = _Flight(
        start_type=start_type,
        client_count=0,
        manually_timed=False,
        manual_takeoff_time=None,
        package=SimpleNamespace(time_over_target=tot),
        state=None,
    )
    flight.flight_plan = SimpleNamespace(
        startup_time=lambda: startup,
        takeoff_time=lambda: startup + timedelta(minutes=10),
        estimate_startup=lambda: AI_STARTUP,
    )
    return flight


def _shift(*flights: Any) -> timedelta:
    return early_start_shift(TURN, cast(Any, flights))


def test_no_shortfall_leaves_the_start_alone() -> None:
    assert _shift(_flight(TURN), _flight(TURN + timedelta(minutes=5))) == timedelta()


def test_a_shortfall_under_the_cap_moves_the_start_by_exactly_that() -> None:
    shortfall = timedelta(minutes=12, seconds=30)
    assert _shift(_flight(TURN - shortfall), _flight(TURN)) == shortfall


def test_a_shortfall_over_the_cap_moves_the_start_by_the_cap() -> None:
    assert _shift(_flight(TURN - timedelta(minutes=50))) == EARLY_START_CAP
    assert EARLY_START_CAP == timedelta(minutes=30)


def test_air_starts_and_unscheduled_packages_do_not_move_the_start() -> None:
    air = _flight(TURN - timedelta(minutes=20), start_type=StartType.IN_FLIGHT)
    unscheduled = _flight(TURN - timedelta(minutes=20), tot=datetime.min)
    assert _shift(air, unscheduled) == timedelta()


def test_runway_and_warm_starts_count() -> None:
    warm = _flight(TURN - timedelta(minutes=4), start_type=StartType.WARM)
    runway = _flight(TURN - timedelta(minutes=6), start_type=StartType.RUNWAY)
    assert _shift(warm, runway) == timedelta(minutes=6)


def _game(blue: list[Any], red: list[Any]) -> Any:
    def coalition(flights: list[Any]) -> SimpleNamespace:
        return SimpleNamespace(
            ato=SimpleNamespace(packages=[SimpleNamespace(flights=flights)])
        )

    return SimpleNamespace(
        conditions=SimpleNamespace(start_time=TURN),
        settings=SimpleNamespace(),
        blue=coalition(blue),
        red=coalition(red),
    )


def test_the_simulation_begins_early_and_no_flight_is_pre_activated() -> None:
    """Both sides count; nobody inside the window is pre-activated, and the turn
    clock, TOTs and takeoff times are untouched."""
    blue_late = _flight(TURN - timedelta(minutes=9))
    blue_on_time = _flight(TURN + timedelta(minutes=5))
    red_later = _flight(TURN - timedelta(minutes=14))
    game = _game([blue_late, blue_on_time], [red_later])
    tots = [f.package.time_over_target for f in (blue_late, blue_on_time, red_later)]
    takeoffs = [f.flight_plan.takeoff_time() for f in (blue_late, blue_on_time)]

    sim = MissionSimulation(game)
    sim.begin_simulation()

    assert sim.time == TURN - timedelta(minutes=14)
    assert game.conditions.start_time == TURN
    for flight in (blue_late, blue_on_time):
        assert isinstance(flight.state, WaitingForStart)
        assert flight.state.start_time == flight.flight_plan.startup_time()
    # The earliest starts its engines at the new mission start: its own time.
    assert isinstance(red_later.state, StartUp)
    assert red_later.state.completion_time == sim.time + AI_STARTUP
    assert [
        f.package.time_over_target for f in (blue_late, blue_on_time, red_later)
    ] == tots
    assert [f.flight_plan.takeoff_time() for f in (blue_late, blue_on_time)] == (
        takeoffs
    )


def test_past_the_cap_flights_clamp_as_before() -> None:
    too_early = _flight(TURN - timedelta(minutes=45))
    game = _game([too_early], [])

    sim = MissionSimulation(game)
    sim.begin_simulation()

    assert sim.time == TURN - EARLY_START_CAP
    # Pre-activated as today: already under way when the mission begins.
    assert isinstance(too_early.state, StartUp)
    assert too_early.state.completion_time == TURN - timedelta(minutes=43)
