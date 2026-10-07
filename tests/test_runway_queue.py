"""A busy field's flights share one runway, so later departures get a longer taxi.

Test 39, Kandahar: 32 jets spawned within 207 s and took 16 minutes median to get
airborne against the flat 8 planned. Always on (DM call 2026-09-23).
docs/dev/design/retlab-startup-times-notes.md.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any, cast

from game.ato.flightplans.flightplan import FlightPlan
from game.ato.runwayqueue import (
    DECK_SECONDS_PER_AIRCRAFT,
    RUNWAY_SECONDS_PER_AIRCRAFT,
)
from game.ato.starttype import StartType

T0 = datetime(2026, 9, 23, 12, 0, 0)
BASE = timedelta(minutes=8)


def _field(**kind: bool) -> SimpleNamespace:
    return SimpleNamespace(
        is_fleet=kind.get("fleet", False),
        is_fob=kind.get("fob", False),
        is_offmap=kind.get("offmap", False),
    )


class _World:
    def __init__(self) -> None:
        self.coalition = SimpleNamespace(
            ato=SimpleNamespace(packages=[]),
            game=SimpleNamespace(settings=SimpleNamespace(player_startup_time=10)),
        )

    def flight(
        self,
        field: SimpleNamespace,
        takeoff: datetime,
        count: int = 2,
        start_type: StartType = StartType.COLD,
        helo: bool = False,
        package: SimpleNamespace | None = None,
        clients: int = 0,
        startup_minutes: int | None = None,
    ) -> SimpleNamespace:
        if package is None:
            package = SimpleNamespace(time_over_target=T0, flights=[])
            self.coalition.ato.packages.append(package)
        flight = SimpleNamespace(
            departure=field,
            start_type=start_type,
            count=count,
            is_helo=helo,
            manually_timed=False,
            manual_takeoff_time=None,
            package=package,
            coalition=self.coalition,
            client_count=clients,
            unit_type=SimpleNamespace(startup_minutes=startup_minutes),
        )
        plan = SimpleNamespace(flight=flight, takeoff_time=lambda: takeoff)
        for name in (
            "estimate_startup",
            "estimate_ground_ops",
            "estimate_takeoff_time",
        ):
            setattr(plan, name, getattr(FlightPlan, name).__get__(plan))
        flight.flight_plan = plan
        package.flights.append(flight)
        return flight


def _ground_ops(flight: SimpleNamespace) -> timedelta:
    return FlightPlan.estimate_ground_ops(cast(Any, flight.flight_plan))


def test_a_jet_holds_the_runway_45_seconds() -> None:
    """Fitted on 494 flown AI groups; 30 s left 21% of busy-field groups late."""
    assert RUNWAY_SECONDS_PER_AIRCRAFT == 45


def test_a_lone_flight_gets_the_base_allowance() -> None:
    world = _World()
    assert _ground_ops(world.flight(_field(), T0)) == BASE


def test_the_second_flight_at_the_same_time_waits_for_the_first() -> None:
    world = _World()
    field = _field()
    first = world.flight(field, T0, count=4)
    second = world.flight(field, T0, count=2)
    assert _ground_ops(first) == BASE
    assert _ground_ops(second) == BASE + timedelta(
        seconds=4 * RUNWAY_SECONDS_PER_AIRCRAFT
    )


def test_waits_accumulate_down_the_departure_order() -> None:
    world = _World()
    field = _field()
    flights = [world.flight(field, T0, count=2) for _ in range(4)]
    slot = timedelta(seconds=2 * RUNWAY_SECONDS_PER_AIRCRAFT)
    assert [_ground_ops(f) for f in flights] == [BASE + slot * n for n in range(4)]


def test_a_flight_after_the_runway_clears_does_not_wait() -> None:
    world = _World()
    field = _field()
    world.flight(field, T0, count=2)
    later = world.flight(
        field, T0 + timedelta(seconds=2 * RUNWAY_SECONDS_PER_AIRCRAFT), count=2
    )
    assert _ground_ops(later) == BASE


def test_the_queue_follows_takeoff_time_not_ato_order() -> None:
    world = _World()
    field = _field()
    late = world.flight(field, T0 + timedelta(seconds=30), count=2)
    world.flight(field, T0, count=2)
    assert _ground_ops(late) == BASE + timedelta(
        seconds=2 * RUNWAY_SECONDS_PER_AIRCRAFT - 30
    )


def test_different_fields_do_not_interact() -> None:
    world = _World()
    world.flight(_field(), T0, count=4)
    assert _ground_ops(world.flight(_field(), T0, count=2)) == BASE


def test_fobs_and_off_map_fields_keep_their_allowance() -> None:
    world = _World()
    for kind, allowance in (
        ({"fob": True}, timedelta(minutes=2)),
        ({"offmap": True}, BASE),
    ):
        field = _field(**kind)
        world.flight(field, T0, count=4)
        assert _ground_ops(world.flight(field, T0)) == allowance


def test_runway_and_air_starts_neither_wait_nor_hold_the_runway() -> None:
    world = _World()
    field = _field()
    runway = world.flight(field, T0, count=4, start_type=StartType.RUNWAY)
    world.flight(field, T0, count=4, start_type=StartType.IN_FLIGHT)
    assert _ground_ops(runway) == timedelta()
    assert _ground_ops(world.flight(field, T0)) == BASE


def test_helicopters_neither_wait_nor_hold_the_runway() -> None:
    world = _World()
    field = _field()
    world.flight(field, T0, count=4, helo=True)
    assert _ground_ops(world.flight(field, T0)) == BASE
    world.flight(field, T0, count=4)
    assert _ground_ops(world.flight(field, T0, helo=True)) == BASE


def test_an_unscheduled_package_neither_waits_nor_holds_the_runway() -> None:
    """Its TOT is the datetime.min sentinel; reading a takeoff from it overflows."""
    world = _World()
    field = _field()
    unscheduled = SimpleNamespace(time_over_target=datetime.min, flights=[])
    world.coalition.ato.packages.append(unscheduled)
    pending = world.flight(field, datetime.min, package=unscheduled)
    assert _ground_ops(pending) == BASE
    assert _ground_ops(world.flight(field, T0)) == BASE


def test_a_flight_not_yet_in_the_ato_queues_behind_those_that_are() -> None:
    world = _World()
    field = _field()
    world.flight(field, T0, count=2)
    draft_package = SimpleNamespace(time_over_target=T0, flights=[])
    draft = world.flight(field, T0, package=draft_package)
    assert _ground_ops(draft) == BASE + timedelta(
        seconds=2 * RUNWAY_SECONDS_PER_AIRCRAFT
    )


def test_a_player_flight_waits_in_the_same_queue_on_top_of_his_startup() -> None:
    """The queue adds to the airframe's startup allowance; it never replaces it."""
    world = _World()
    field = _field()
    world.flight(field, T0, count=4)
    player = world.flight(field, T0, count=2, clients=1, startup_minutes=3)
    wait = timedelta(seconds=4 * RUNWAY_SECONDS_PER_AIRCRAFT)
    assert _ground_ops(player) == BASE + wait
    startup = FlightPlan.startup_time(cast(Any, player.flight_plan))
    assert startup == T0 - timedelta(minutes=3) - BASE - wait - timedelta(seconds=30)


def test_the_obsolete_setting_is_dropped_from_a_save() -> None:
    from game.settings.migration import migrate_legacy_settings

    assert "queue_aware_ground_ops" not in migrate_legacy_settings(
        {"queue_aware_ground_ops": True}
    )


TRAVEL = timedelta(minutes=30)
#: An AI cold start: 2 min startup, the 8 min base taxi and the 30 s roll.
AI_COLD_OVERHEAD = timedelta(minutes=10, seconds=30)


def _scheduled_package(world: _World) -> SimpleNamespace:
    package = SimpleNamespace(time_over_target=T0, flights=[])
    world.coalition.ato.packages.append(package)
    return package


def _asap_flight(
    world: _World, field: SimpleNamespace, package: SimpleNamespace
) -> SimpleNamespace:
    """A flight whose takeoff follows its package's TOT, as a real plan's does."""
    flight = world.flight(field, T0, package=package)
    plan = flight.flight_plan
    plan.takeoff_time = lambda: package.time_over_target - TRAVEL
    plan.tot_waypoint = None
    plan._travel_time_to_waypoint = lambda _destination: TRAVEL
    for name in ("minimum_duration_from_start_to_tot", "startup_time"):
        setattr(plan, name, getattr(FlightPlan, name).__get__(plan))
    return flight


def _asap(package: SimpleNamespace) -> datetime:
    from game.ato.package import Package

    Package.set_tot_asap(cast(Any, package), T0)
    return package.time_over_target


def test_asap_on_a_quiet_field_is_the_flight_time() -> None:
    world = _World()
    package = _scheduled_package(world)
    _asap_flight(world, _field(), package)
    assert _asap(package) == T0 + TRAVEL + AI_COLD_OVERHEAD


def test_asap_gives_the_same_tot_every_time_it_is_asked() -> None:
    """The queue reads each takeoff from the TOT being set, so a one-shot estimate
    flipped between two times. The package dialog saved each one back and recursed
    until Python ran out of stack (RecursionError, 2026-09-27)."""
    world = _World()
    field = _field()
    # Another package takes the runway at the moment this one first could.
    world.flight(field, T0 + AI_COLD_OVERHEAD, count=4)
    package = _scheduled_package(world)
    _asap_flight(world, field, package)
    first = _asap(package)
    assert [_asap(package) for _ in range(3)] == [first] * 3


def test_asap_leaves_the_flight_time_to_wait_for_the_runway() -> None:
    world = _World()
    field = _field()
    world.flight(field, T0 + AI_COLD_OVERHEAD, count=4)
    package = _scheduled_package(world)
    flight = _asap_flight(world, field, package)
    _asap(package)
    assert flight.flight_plan.startup_time() >= T0


def test_estimating_asap_leaves_the_package_tot_alone() -> None:
    """The scheduler asks for the estimate and decides for itself whether to use it."""
    from game.ato.traveltime import TotEstimator

    world = _World()
    field = _field()
    world.flight(field, T0 + AI_COLD_OVERHEAD, count=4)
    package = _scheduled_package(world)
    _asap_flight(world, field, package)
    scheduled = T0 + timedelta(hours=2)
    package.time_over_target = scheduled
    TotEstimator(cast(Any, package)).earliest_tot(T0)
    assert package.time_over_target == scheduled


DECK_BASE = timedelta(minutes=2)


def _deck(jets: int) -> timedelta:
    return timedelta(seconds=jets * DECK_SECONDS_PER_AIRCRAFT)


def test_a_carrier_launches_a_jet_every_75_seconds() -> None:
    """Fitted on 23 flown carrier groups: pairs took 3-4.5 min, 4-ships 6-9."""
    assert DECK_SECONDS_PER_AIRCRAFT == 75


def test_a_lone_carrier_flight_gets_its_own_launch_time() -> None:
    world = _World()
    pair = world.flight(_field(fleet=True), T0, count=2)
    assert _ground_ops(pair) == DECK_BASE + _deck(2)


def test_carrier_flights_queue_behind_each_other() -> None:
    """Test 54: a SEAD 4-ship and two escort pairs all spawned at once."""
    world = _World()
    boat = _field(fleet=True)
    sead = world.flight(boat, T0, count=4)
    escort = world.flight(boat, T0, count=2)
    tomcats = world.flight(boat, T0, count=2)
    # Each waits only for the launches ahead of it, then launches its own.
    assert _ground_ops(sead) == DECK_BASE + _deck(4)
    assert _ground_ops(escort) == DECK_BASE + _deck(2) + _deck(2)
    assert _ground_ops(tomcats) == DECK_BASE + _deck(4) + _deck(2)


def test_a_carrier_and_an_airfield_do_not_share_a_queue() -> None:
    world = _World()
    world.flight(_field(fleet=True), T0, count=4)
    assert _ground_ops(world.flight(_field(), T0, count=2)) == BASE


def test_carrier_helicopters_neither_wait_nor_hold_the_deck() -> None:
    world = _World()
    boat = _field(fleet=True)
    helo = world.flight(boat, T0, count=2, helo=True)
    assert _ground_ops(helo) == DECK_BASE
    assert _ground_ops(world.flight(boat, T0, count=2)) == DECK_BASE + _deck(2)
