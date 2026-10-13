"""Tests for the PLAYER_AT_IP fast-forward fix.

PLAYER_AT_IP means "spawn me at my IP", but the default PAUSE combat resolution used to
end the fast-forward at the first combat anywhere in the theater -- which beats a
ground-started player flight to its IP, so it spawned at its configured start. The fix
exempts AI-only combats from pausing a PLAYER_AT_IP fast-forward; player-involving
combats still pause. These exercise that gating predicate with duck-typed fakes.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from game.settings.settings import CombatResolutionMethod, FastForwardStopCondition
from game.sim.aircraftsimulation import AircraftSimulation


def _sim(stop_condition: FastForwardStopCondition) -> Any:
    sim = AircraftSimulation.__new__(AircraftSimulation)
    sim.game = SimpleNamespace(  # type: ignore[assignment]
        settings=SimpleNamespace(fast_forward_stop_condition=stop_condition)
    )
    return sim


def _combat(*client_counts: int) -> Any:
    flights = [SimpleNamespace(client_count=c) for c in client_counts]
    return SimpleNamespace(iter_flights=lambda: iter(flights))


def test_player_at_ip_ai_only_combat_does_not_pause() -> None:
    sim = _sim(FastForwardStopCondition.PLAYER_AT_IP)
    ai_only = _combat(0, 0)
    # PAUSE + PLAYER_AT_IP + no player in the combat -> keeps fast-forwarding to the IP.
    assert not sim._combat_pauses_fast_forward(
        ai_only, CombatResolutionMethod.PAUSE, False
    )


def test_player_at_ip_combat_with_a_player_still_pauses() -> None:
    sim = _sim(FastForwardStopCondition.PLAYER_AT_IP)
    with_player = _combat(0, 2)
    # A player is in this fight -> stop so they fly it (can't be "at the IP" anyway).
    assert sim._combat_pauses_fast_forward(
        with_player, CombatResolutionMethod.PAUSE, False
    )


def test_other_stop_conditions_keep_legacy_pause_on_any_combat() -> None:
    sim = _sim(FastForwardStopCondition.PLAYER_TAKEOFF)
    ai_only = _combat(0, 0)
    # Outside PLAYER_AT_IP the legacy behaviour stands: any combat pauses under PAUSE.
    assert sim._combat_pauses_fast_forward(ai_only, CombatResolutionMethod.PAUSE, False)


def test_resolve_method_or_force_continue_never_pauses() -> None:
    sim = _sim(FastForwardStopCondition.PLAYER_AT_IP)
    with_player = _combat(2)
    assert not sim._combat_pauses_fast_forward(
        with_player, CombatResolutionMethod.RESOLVE, False
    )
    assert not sim._combat_pauses_fast_forward(
        with_player, CombatResolutionMethod.PAUSE, True
    )


def _air_start_loop(stop_condition: FastForwardStopCondition) -> Any:
    """A started game loop whose only player flight is an air start, already flying."""
    from datetime import datetime

    flight = SimpleNamespace(client_count=2, state=SimpleNamespace(in_flight=True))
    loop = SimpleNamespace(
        started=True,
        completed=False,
        ticks=0,
        pause=lambda: None,
        game=SimpleNamespace(
            settings=SimpleNamespace(fast_forward_stop_condition=stop_condition)
        ),
        sim=SimpleNamespace(
            time=datetime(2005, 6, 29, 23),
            aircraft_simulation=SimpleNamespace(iter_flights=lambda: iter([flight])),
        ),
    )

    def tick(suppress_events: bool = False) -> None:
        loop.ticks += 1
        loop.completed = True

    loop.tick = tick
    return loop


def test_player_at_ip_fast_forwards_an_air_start_player_flight() -> None:
    from game.sim.gameloop import GameLoop

    # An air start has no pre-flight state to stop at, but it still has to fly to
    # its IP. The hot-spawn skip used to leave it at its takeoff point.
    loop = _air_start_loop(FastForwardStopCondition.PLAYER_AT_IP)
    GameLoop.run_to_first_contact(loop)
    assert loop.ticks == 1


def test_preflight_stop_conditions_still_skip_an_air_start_player_flight() -> None:
    from game.sim.gameloop import GameLoop

    loop = _air_start_loop(FastForwardStopCondition.PLAYER_STARTUP)
    GameLoop.run_to_first_contact(loop)
    assert loop.ticks == 0
