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
from game.ato.runwayqueue import RUNWAY_SECONDS_PER_AIRCRAFT
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


def test_ships_fobs_and_off_map_fields_keep_their_allowance() -> None:
    world = _World()
    for kind, allowance in (
        ({"fleet": True}, timedelta(minutes=2)),
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
