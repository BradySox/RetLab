"""Start the generated mission early enough that every ground start makes its TOT.

The runway queue (§104) moves a busy field's late starters earlier; one that lands
before the turn's clock used to be clamped to mission start and fly late. Only the
simulated and generated mission start moves -- ``conditions.start_time`` (the §47
turn clock and weather) and every TOT stay put. Always on (DM call 2026-09-23).
docs/dev/design/retlab-startup-times-notes.md, "Early mission start".
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable, Optional, TYPE_CHECKING

from game.ato.starttype import StartType

if TYPE_CHECKING:
    from game import Game
    from game.ato import Flight

#: Past this, flights clamp to mission start as before rather than the mission
#: running half an hour of empty sky.
EARLY_START_CAP = timedelta(minutes=30)

#: Air starts join mid-route and need no spawn lead.
_GROUND_STARTS = (StartType.COLD, StartType.WARM, StartType.RUNWAY)


def _scheduled(flight: Flight) -> bool:
    if flight.manually_timed and flight.manual_takeoff_time is not None:
        return True
    return flight.package.time_over_target != datetime.min


def earliest_ground_startup(flights: Iterable[Flight]) -> Optional[datetime]:
    starts = [
        flight.flight_plan.startup_time()
        for flight in flights
        if flight.start_type in _GROUND_STARTS and _scheduled(flight)
    ]
    return min(starts) if starts else None


def early_start_shift(turn_start: datetime, flights: Iterable[Flight]) -> timedelta:
    """How far before ``turn_start`` the mission must begin, at most the cap."""
    earliest = earliest_ground_startup(flights)
    if earliest is None or earliest >= turn_start:
        return timedelta()
    return min(turn_start - earliest, EARLY_START_CAP)


def _all_flights(game: Game) -> Iterable[Flight]:
    for coalition in (game.blue, game.red):
        for package in coalition.ato.packages:
            yield from package.flights


def mission_start_time(game: Game) -> datetime:
    turn_start = game.conditions.start_time
    return turn_start - early_start_shift(turn_start, _all_flights(game))
