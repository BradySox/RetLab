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

from game.ato.flighttype import FlightType
from game.ato.starttype import StartType
from game.ato.traveltime import TotEstimator

if TYPE_CHECKING:
    from game import Game
    from game.ato import Flight, Package

#: Past this, flights clamp to mission start as before rather than the mission
#: running half an hour of empty sky.
EARLY_START_CAP = timedelta(minutes=30)

#: ASAP support launches at the mission's own start, early or not, so a tanker is up
#: before the flights that start early to reach it (DM call 2026-10-08).
_SUPPORT_TASKS = frozenset(
    {
        FlightType.REFUELING,
        FlightType.AEWC,
        FlightType.ABCCC,
        FlightType.BARCAP,
    }
)

#: Moving support can reorder a runway queue and push another flight's startup
#: ahead of the start just chosen. One more pass settles a real field.
_SETTLE_PASSES = 4

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


def launches_with_mission(package: Package) -> bool:
    return (
        getattr(package, "auto_asap", False)
        and getattr(package, "primary_task", None) in _SUPPORT_TASKS
    )


def _station(package: Package) -> int:
    return id(getattr(package, "target", None))


def _leads_a_cap_station(package: Package) -> bool:
    return launches_with_mission(package) and package.primary_task is FlightType.BARCAP


def _relief_waves(packages: list[Package]) -> list[Package]:
    """The BARCAP waves the scheduler chained behind a station's ASAP wave."""
    led = {_station(p) for p in packages if _leads_a_cap_station(p)}
    return [
        p
        for p in packages
        if getattr(p, "primary_task", None) is FlightType.BARCAP
        and not launches_with_mission(p)
        and _station(p) in led
    ]


def _flights_that_set_the_start(game: Game) -> Iterable[Flight]:
    # ASAP support is timed off the start, so it cannot also set it. Nor can a
    # relief wave, which moves with its station's first one: one left starting
    # before the turn clock would hold every later generation early.
    for coalition in (game.blue, game.red):
        packages = list(coalition.ato.packages)
        timed_off_the_start = {id(p) for p in _relief_waves(packages)}
        for package in packages:
            if launches_with_mission(package) or id(package) in timed_off_the_start:
                continue
            yield from package.flights


def mission_start_time(game: Game) -> datetime:
    turn_start = game.conditions.start_time
    return turn_start - early_start_shift(turn_start, _flights_that_set_the_start(game))


def retime_asap_support(game: Game, mission_start: datetime) -> None:
    """Re-run ASAP for support packages from the mission start, not the turn clock.

    Recomputed every generation, so removing whatever started the mission early
    puts support back on the turn clock. A station's relief CAP waves move by as
    much as its first wave did, so the handover the scheduler planned still holds.
    """
    for coalition in (game.blue, game.red):
        packages = list(coalition.ato.packages)
        reliefs = _relief_waves(packages)
        moved: dict[int, timedelta] = {}
        for package in packages:
            if not launches_with_mission(package):
                continue
            before = package.time_over_target
            package.set_tot_asap(mission_start)
            if package.primary_task is FlightType.BARCAP and before != datetime.min:
                moved.setdefault(_station(package), package.time_over_target - before)
        for relief in reliefs:
            delta = moved.get(_station(relief))
            if delta is None or relief.time_over_target == datetime.min:
                continue
            # Never earlier than it can fly from the mission start: nothing else
            # would start the mission for it.
            relief.time_over_target = max(
                relief.time_over_target + delta,
                TotEstimator(relief).earliest_tot(mission_start),
            )


def settle_mission_start(game: Game) -> datetime:
    """Choose the mission start and time support off it; returns the start.

    The start only ever moves earlier here and never past the cap, so this ends.
    """
    start = mission_start_time(game)
    retime_asap_support(game, start)
    for _ in range(_SETTLE_PASSES):
        earlier = mission_start_time(game)
        if earlier >= start:
            break
        start = earlier
        retime_asap_support(game, start)
    return start
