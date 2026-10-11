"""The mission starts early enough that a queued ground start makes its TOT.

A startup before the turn's clock used to clamp to mission start (test 39's
PORCUPINE departed 0:00:00). The mission now begins up to 30 min early; the turn
clock and every TOT stay put. docs/dev/design/retlab-startup-times-notes.md.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any, cast

import pytest

from game.ato.flightstate import StartUp, WaitingForStart
from game.ato.flighttype import FlightType
from game.ato.starttype import StartType
from game.sim.missionsimulation import MissionSimulation
from game.sim import missionstart
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


class _AsapPackage(SimpleNamespace):
    """An ASAP package whose one flight starts at whatever ``now`` ASAP was run at."""

    asap_from: datetime | None

    def set_tot_asap(self, now: datetime) -> None:
        self.asap_from = now
        self.time_over_target = now + timedelta(minutes=20)
        for flight in self.flights:
            flight.flight_plan.startup_time = lambda: now


def _asap(task: FlightType) -> Any:
    package = _AsapPackage(
        auto_asap=True, primary_task=task, flights=[], asap_from=None
    )
    flight = _flight(TURN)
    flight.package = package
    package.flights.append(flight)
    package.set_tot_asap(TURN)
    package.asap_from = None
    return package


def _game_of(packages: list[Any]) -> Any:
    return SimpleNamespace(
        conditions=SimpleNamespace(start_time=TURN),
        settings=SimpleNamespace(),
        blue=SimpleNamespace(ato=SimpleNamespace(packages=packages)),
        red=SimpleNamespace(ato=SimpleNamespace(packages=[])),
    )


def test_asap_support_launches_at_the_early_start() -> None:
    """Test 55 prep: a pre-push refuel started the mission 16 min early while the
    tanker waited for the turn clock, so the strike reached an empty box."""
    early = SimpleNamespace(flights=[_flight(TURN - timedelta(minutes=16))])
    tanker = _asap(FlightType.REFUELING)
    awacs = _asap(FlightType.AEWC)
    cap = _asap(FlightType.BARCAP)
    dead = _asap(FlightType.DEAD)
    game = _game_of([early, tanker, awacs, cap, dead])

    sim = MissionSimulation(game)
    sim.begin_simulation()

    assert sim.time == TURN - timedelta(minutes=16)
    for support in (tanker, awacs, cap):
        assert support.asap_from == sim.time
    assert dead.asap_from is None


def test_asap_support_never_holds_the_start_early_itself() -> None:
    """Re-timed support starts before the turn clock; once the flight that needed
    the early start is gone, the next generation is back on the turn clock."""
    early = SimpleNamespace(flights=[_flight(TURN - timedelta(minutes=16))])
    cap = _asap(FlightType.BARCAP)
    packages = [early, cap]
    game = _game_of(packages)
    MissionSimulation(game).begin_simulation()
    assert cap.flights[0].flight_plan.startup_time() == TURN - timedelta(minutes=16)

    packages.remove(early)
    sim = MissionSimulation(game)
    sim.begin_simulation()

    assert sim.time == TURN
    assert cap.asap_from == TURN


TRANSIT = timedelta(minutes=20)
HANDOVER = timedelta(minutes=45)


class _TransitTotEstimator:
    def __init__(self, package: Any) -> None:
        self.package = package

    def earliest_tot(self, now: datetime) -> datetime:
        return now + TRANSIT


@pytest.fixture(autouse=True)
def _stub_tot_estimator(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(missionstart, "TotEstimator", _TransitTotEstimator)


def _cap_station(relief_after: timedelta = HANDOVER) -> tuple[Any, Any]:
    """A station's ASAP first wave and the relief the scheduler chained to it."""
    station = object()
    first = _asap(FlightType.BARCAP)
    first.target = station
    relief = SimpleNamespace(
        auto_asap=False,
        primary_task=FlightType.BARCAP,
        target=station,
        time_over_target=first.time_over_target + relief_after,
        flights=[],
    )
    flight = _flight(TURN)
    flight.package = relief
    flight.flight_plan.startup_time = lambda: relief.time_over_target - TRANSIT
    relief.flights.append(flight)
    return first, relief


def _startups(*packages: Any) -> list[datetime]:
    return [f.flight_plan.startup_time() for p in packages for f in p.flights]


def test_a_relief_cap_wave_moves_with_its_first_wave() -> None:
    """The first wave launched with the early start and its relief stayed on the
    turn clock: a 20 min early start left the station empty for 20 min."""
    early = SimpleNamespace(flights=[_flight(TURN - timedelta(minutes=20))])
    first, relief = _cap_station()
    other_first, other_relief = _cap_station()
    packages = [early, first, relief, other_first, other_relief]
    game = _game_of(packages)

    sim = MissionSimulation(game)
    sim.begin_simulation()

    assert sim.time == TURN - timedelta(minutes=20)
    for lead, wave in ((first, relief), (other_first, other_relief)):
        assert wave.time_over_target - lead.time_over_target == HANDOVER

    # Removing what started the mission early puts the whole station back.
    packages.remove(early)
    sim = MissionSimulation(game)
    sim.begin_simulation()
    assert sim.time == TURN
    assert relief.time_over_target == TURN + TRANSIT + HANDOVER


def test_a_relief_wave_never_holds_the_start_early_itself() -> None:
    """A relief due minutes after the first wave starts before the turn clock once
    shifted. It is timed off the start, so it must not set the next one."""
    early = SimpleNamespace(flights=[_flight(TURN - timedelta(minutes=20))])
    first, relief = _cap_station(relief_after=timedelta(minutes=5))
    packages = [early, first, relief]
    game = _game_of(packages)
    sim = MissionSimulation(game)
    sim.begin_simulation()
    assert _startups(relief) == [TURN - timedelta(minutes=15)]

    packages.remove(early)
    sim = MissionSimulation(game)
    sim.begin_simulation()
    assert sim.time == TURN
    assert _startups(relief) == [TURN + timedelta(minutes=5)]


def test_a_relief_wave_is_never_timed_before_it_can_fly() -> None:
    # Chained tighter than its transit allows: the shift stops at the earliest
    # TOT from the mission start, since nothing else starts the mission for it.
    early = SimpleNamespace(flights=[_flight(TURN - timedelta(minutes=20))])
    first, relief = _cap_station()
    relief.time_over_target = TURN + TRANSIT
    game = _game_of([early, first, relief])

    sim = MissionSimulation(game)
    sim.begin_simulation()

    assert relief.time_over_target == sim.time + TRANSIT
    assert min(_startups(relief)) >= sim.time


def _queued_behind(tanker: Any, jump: timedelta) -> Any:
    """A flight the runway queue starts ``jump`` before the turn clock once the
    tanker ahead of it launches early."""
    flight = _flight(TURN)
    flight.flight_plan.startup_time = lambda: (
        TURN - jump if tanker.flights[0].flight_plan.startup_time() < TURN else TURN
    )
    return SimpleNamespace(flights=[flight])


def test_the_start_is_taken_again_after_support_is_retimed() -> None:
    """Retimed support jumped the runway queue after the start was fixed, and the
    jet behind it got a startup up to 2.3 min before the mission began."""
    early = SimpleNamespace(flights=[_flight(TURN - timedelta(minutes=16))])
    tanker = _asap(FlightType.REFUELING)
    queued = _queued_behind(tanker, timedelta(minutes=18))
    game = _game_of([early, tanker, queued])

    sim = MissionSimulation(game)
    sim.begin_simulation()

    assert sim.time == TURN - timedelta(minutes=18)
    assert tanker.asap_from == sim.time
    assert min(_startups(early, tanker, queued)) >= sim.time


def test_the_second_look_at_the_start_keeps_the_cap() -> None:
    early = SimpleNamespace(flights=[_flight(TURN - timedelta(minutes=29))])
    tanker = _asap(FlightType.REFUELING)
    queued = _queued_behind(tanker, timedelta(minutes=33))
    game = _game_of([early, tanker, queued])

    sim = MissionSimulation(game)
    sim.begin_simulation()

    assert sim.time == TURN - EARLY_START_CAP
    assert tanker.asap_from == sim.time


def test_queue_jump_and_relief_shift_settle_together() -> None:
    """No startup before the start and no CAP gap, and a second generation of the
    same plan changes nothing."""
    early = SimpleNamespace(flights=[_flight(TURN - timedelta(minutes=16))])
    tanker = _asap(FlightType.REFUELING)
    queued = _queued_behind(tanker, timedelta(minutes=18))
    first, relief = _cap_station()
    game = _game_of([early, tanker, queued, first, relief])

    sim = MissionSimulation(game)
    sim.begin_simulation()

    def picture() -> tuple[Any, ...]:
        return (
            sim.time,
            first.time_over_target,
            relief.time_over_target,
            *_startups(early, tanker, queued, first, relief),
        )

    settled = picture()
    assert sim.time == TURN - timedelta(minutes=18)
    assert min(_startups(early, tanker, queued, first, relief)) >= sim.time
    assert relief.time_over_target - first.time_over_target == HANDOVER

    sim = MissionSimulation(game)
    sim.begin_simulation()
    assert picture() == settled
