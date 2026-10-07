"""The departure runway or carrier deck as a queue: how long a flight waits
behind the ones ahead.

Always on (DM calls 2026-09-23, deck 2026-10-07). See
docs/dev/design/retlab-startup-times-notes.md, "Runway queue".
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from .starttype import StartType

if TYPE_CHECKING:
    from .flight import Flight

#: Fitted on 494 flown AI groups; errs early, since an AI flight that is early holds.
RUNWAY_SECONDS_PER_AIRCRAFT = 45

#: Fitted on 23 flown carrier groups (pairs 3-4.5 min spawn to airborne, 4-ships
#: 6-9 min, against the flat 2.5 the plan allowed).
DECK_SECONDS_PER_AIRCRAFT = 75

#: Runway and air starts never taxi, so they never join the queue.
_QUEUED_START_TYPES = (StartType.COLD, StartType.WARM)


def _seconds_per_aircraft(flight: Flight) -> int | None:
    """Each jet's hold on the runway or deck; None for a flight that never queues.
    Helicopters lift from their spot."""
    departure = flight.departure
    if (
        flight.start_type not in _QUEUED_START_TYPES
        or flight.is_helo
        or departure.is_fob
        or departure.is_offmap
    ):
        return None
    if departure.is_fleet:
        return DECK_SECONDS_PER_AIRCRAFT
    return RUNWAY_SECONDS_PER_AIRCRAFT


def deck_launch_time(flight: Flight) -> timedelta:
    """The deck crew launching the flight's own jets, one at a time."""
    if not flight.departure.is_fleet or _seconds_per_aircraft(flight) is None:
        return timedelta()
    return timedelta(seconds=flight.count * DECK_SECONDS_PER_AIRCRAFT)


def _planned_takeoff(flight: Flight) -> datetime | None:
    """None while the package is unscheduled: its TOT is the datetime.min sentinel,
    and subtracting a travel time from that overflows."""
    if not (flight.manually_timed and flight.manual_takeoff_time is not None):
        if flight.package.time_over_target == datetime.min:
            return None
    return flight.flight_plan.takeoff_time()


def runway_queue_wait(flight: Flight) -> timedelta:
    """Time ``flight`` holds behind earlier departures from its own field or ship.

    Every parking-start flight of the same coalition leaving the same field takes
    the runway (or the deck) in planned-takeoff order, ``count`` jets at a time. A
    flight's slot opens at its planned takeoff or when the previous slot closes,
    whichever is later.
    """
    seconds_per_aircraft = _seconds_per_aircraft(flight)
    if seconds_per_aircraft is None:
        return timedelta()
    own_takeoff = _planned_takeoff(flight)
    if own_takeoff is None:
        return timedelta()

    departure = flight.departure
    queue: list[tuple[datetime, int, Flight]] = []
    seen_self = False
    order = 0
    for package in flight.coalition.ato.packages:
        for other in package.flights:
            order += 1
            if other is flight:
                seen_self = True
                queue.append((own_takeoff, order, other))
                continue
            if other.departure is not departure or _seconds_per_aircraft(other) is None:
                continue
            takeoff = _planned_takeoff(other)
            if takeoff is not None:
                queue.append((takeoff, order, other))
    if not seen_self:
        # Still being planned, so not in the ATO yet: it queues behind everyone
        # already there with the same takeoff time.
        queue.append((own_takeoff, order + 1, flight))
    queue.sort(key=lambda entry: (entry[0], entry[1]))

    # A runway slot follows a flight's takeoff; a deck flight's own launch is
    # already in its ground ops, so its slot ends at its takeoff.
    from_deck = departure.is_fleet
    free = datetime.min
    for takeoff, _, other in queue:
        hold = timedelta(seconds=other.count * seconds_per_aircraft)
        if from_deck:
            done = max(takeoff, free + hold)
            wait, free = done - takeoff, done
        else:
            slot_start = max(takeoff, free)
            wait, free = slot_start - takeoff, slot_start + hold
        if other is flight:
            return wait
    return timedelta()
