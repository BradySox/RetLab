"""Heatblur airframes spawn at a period build quality (features doc §43).

Heatblur's F-4E and A-6E carry "Aircraft Condition" (``Quality``) and "Aircraft Wear
and Tear" (``Wear``). The module default of 100 condition is "showroom/prototype
grade" on Heatblur's own scale (F-4E manual, Mission Editor chapter); 90 is a
standard service jet. Wear follows the squadron's workload: hours flown add to
it, every turn takes some off. A value the player set in the payload tab, or a
saved default, always wins. DCS applies both only to player aircraft.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Callable, Iterable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from game.ato.flight import Flight
    from game.sortierecord import SortieRecord
    from game.squadrons import Squadron

QUALITY_PROPERTY = "Quality"
WEAR_PROPERTY = "Wear"

#: Heatblur's "standard western build".
SERVICE_CONDITION = 90
#: Before 1980: looser builds and wartime maintenance, between Heatblur's 75
#: ("slightly below standard") and 50.
EARLY_CONDITION = 75
EARLY_ERA_ENDS = 1980

#: Wear added per hour flown, spread over the airframes the squadron owns: every
#: jet flying 2 hours a turn adds 20.
WEAR_PER_AIRFRAME_HOUR = 10.0
#: Taken off every turn, flown or not: a squadron at the cap is fresh in 10 turns.
WEAR_RECOVERY_PER_TURN = 5.0
#: Below Heatblur's 100, the point a jet goes back for maintenance.
MAX_WORKLOAD_WEAR = 50.0


def has_condition_properties(dcs_unit_type: Any) -> bool:
    properties = getattr(dcs_unit_type, "properties", None) or {}
    return QUALITY_PROPERTY in properties and WEAR_PROPERTY in properties


def baseline_condition(when: date) -> int:
    return EARLY_CONDITION if when.year < EARLY_ERA_ENDS else SERVICE_CONDITION


def condition_defaults(
    dcs_unit_type: Any, when: date, wear: float = 0.0
) -> dict[str, int]:
    """The values an untouched condition knob spawns with; empty for other jets.

    The generator fills only keys the player left unset, and the payload tab shows
    these in place of the module defaults so the box reads what will fly.
    """
    if not has_condition_properties(dcs_unit_type):
        return {}
    return {QUALITY_PROPERTY: baseline_condition(when), WEAR_PROPERTY: round(wear)}


def next_wear(wear: float, airframe_hours: float, airframes: int) -> float:
    added = WEAR_PER_AIRFRAME_HOUR * airframe_hours / max(airframes, 1)
    return min(MAX_WORKLOAD_WEAR, max(0.0, wear + added - WEAR_RECOVERY_PER_TURN))


def airframe_hours_by_flight(
    records: Iterable["SortieRecord"],
    flight_for: Callable[[str], Optional["Flight"]],
) -> list[tuple["Flight", float]]:
    """Hours each flight's aircraft spent airborne, summed over its aircraft.

    An AI group has one sampled record, so a flight counts its longest record
    once per aircraft.
    """
    longest: dict[int, tuple["Flight", float]] = {}
    for record in records:
        if not record.flew:
            continue
        flight = flight_for(record.unit)
        if flight is None:
            continue
        hours = record.duration / 3600
        if hours > longest.get(id(flight), (flight, 0.0))[1]:
            longest[id(flight)] = (flight, hours)
    return [(flight, hours * flight.count) for flight, hours in longest.values()]


def commit_squadron_wear(
    squadrons: Iterable["Squadron"], flown: list[tuple["Flight", float]]
) -> None:
    """Advance each condition-tracked squadron's wear by one turn."""
    for squadron in squadrons:
        if not has_condition_properties(squadron.aircraft.dcs_unit_type):
            continue
        hours = sum(h for flight, h in flown if flight.squadron is squadron)
        squadron.airframe_wear = next_wear(
            squadron.airframe_wear, hours, squadron.owned_aircraft
        )
