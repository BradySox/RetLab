"""The departure runway as a queue: how long a flight waits behind the ones ahead.

Gated on ``queue_aware_ground_ops``. See
docs/dev/design/retlab-startup-times-notes.md, "Runway queue".
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from .starttype import StartType

if TYPE_CHECKING:
    from .flight import Flight

#: Test 39, Kandahar: 32 jets off one runway at about 2 a minute.
RUNWAY_SECONDS_PER_AIRCRAFT = 30

#: Runway and air starts never taxi, so they never join the queue.
_QUEUED_START_TYPES = (StartType.COLD, StartType.WARM)


def queues_for_runway(flight: Flight) -> bool:
    """Helicopters lift from their spot and never take the runway."""
    departure = flight.departure
    return (
        flight.start_type in _QUEUED_START_TYPES
        and not flight.is_helo
        and not departure.is_fleet
        and not departure.is_fob
        and not departure.is_offmap
    )


def _planned_takeoff(flight: Flight) -> datetime | None:
    """None while the package is unscheduled: its TOT is the datetime.min sentinel,
    and subtracting a travel time from that overflows."""
    if not (flight.manually_timed and flight.manual_takeoff_time is not None):
        if flight.package.time_over_target == datetime.min:
            return None
    return flight.flight_plan.takeoff_time()


def runway_queue_wait(flight: Flight) -> timedelta:
    """Time ``flight`` holds short behind earlier departures from its own field.

    Every parking-start flight of the same coalition leaving the same field takes
    the runway in planned-takeoff order, ``count`` jets at a time. A flight's slot
    opens at its planned takeoff or when the previous slot closes, whichever is
    later.
    """
    if not queues_for_runway(flight):
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
            if other.departure is not departure or not queues_for_runway(other):
                continue
            takeoff = _planned_takeoff(other)
            if takeoff is not None:
                queue.append((takeoff, order, other))
    if not seen_self:
        # Still being planned, so not in the ATO yet: it queues behind everyone
        # already there with the same takeoff time.
        queue.append((own_takeoff, order + 1, flight))
    queue.sort(key=lambda entry: (entry[0], entry[1]))

    runway_free = datetime.min
    for takeoff, _, other in queue:
        slot_start = max(takeoff, runway_free)
        if other is flight:
            return slot_start - takeoff
        runway_free = slot_start + timedelta(
            seconds=other.count * RUNWAY_SECONDS_PER_AIRCRAFT
        )
    return timedelta()
