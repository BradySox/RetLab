"""Deals the mission's anti-ship flights across the ships of one sea group.

DCS's AttackGroup lets the AI pick one hull at a time, and an anti-ship missile
flies for minutes, so every flight emptied onto the same ship: 128 of 160
Harpoons at one carrier and three escorts never attacked (Tacview, 2026-10-11).
See docs/dev/design/retlab-antiship-deal-notes.md.

- The deal runs across every package in the ATO, not per package. The
  auto-planner sends two flights per package; dealt alone, each package would
  put both on the same ship.
- The top SAM ship and each carrier take two flights before an escort takes
  one. Arrivals of 8 to 16 missiles were shot down; 32 together got through.
"""

from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING

from game.ato.flighttype import FlightType
from game.data.units import UnitClass

if TYPE_CHECKING:
    from game.ato import Flight
    from game.theater import TheaterGroundObject, TheaterUnit

CARRIER_CLASSES = (UnitClass.AIRCRAFT_CARRIER, UnitClass.HELICOPTER_CARRIER)

#: Flights a ship takes before the deal moves down the line.
FLIGHTS_ON_CAPITAL_SHIP = 2
FLIGHTS_ON_ESCORT = 1


def sea_group_for(target: Any) -> Optional[TheaterGroundObject]:
    """The ship group a package target resolves to; None for a cargo ship."""
    from game.theater import NavalControlPoint, TheaterGroundObject

    if isinstance(target, NavalControlPoint):
        return target.find_main_tgo()
    if isinstance(target, TheaterGroundObject):
        return target
    return None


def _is_carrier(ship: TheaterUnit) -> bool:
    try:
        unit_type = ship.unit_type
    except StopIteration:
        return False
    return unit_type is not None and unit_type.unit_class in CARRIER_CLASSES


def ships_in_line(tgo: TheaterGroundObject) -> list[TheaterUnit]:
    """Living ships in attack order.

    The escort with the longest-reach SAM (it shoots the missiles down), then
    the carriers, then the rest by SAM reach.
    """
    ships = [unit for unit in tgo.units if unit.is_ship and unit.alive]
    carriers = [ship for ship in ships if _is_carrier(ship)]
    escorts = [ship for ship in ships if not _is_carrier(ship)]
    # sorted() is stable, so equal reach keeps the group's own order.
    escorts.sort(key=lambda ship: -ship.threat_range().meters)
    if escorts and escorts[0].threat_range().meters > 0:
        return [escorts[0], *carriers, *escorts[1:]]
    return [*carriers, *escorts]


def flights_wanted(line: list[TheaterUnit], ship: TheaterUnit) -> int:
    top_sam_ship = line[0] if line and not _is_carrier(line[0]) else None
    if ship is top_sam_ship or _is_carrier(ship):
        return FLIGHTS_ON_CAPITAL_SHIP
    return FLIGHTS_ON_ESCORT


def ship_order_for(nth_flight: int, line: list[TheaterUnit]) -> list[TheaterUnit]:
    """The line, rotated to start at the ship the nth flight is dealt.

    The ships after its own are the fallback: DCS skips a task on a sunk unit.
    """
    if not line:
        return []
    slots = [
        index
        for index, ship in enumerate(line)
        for _ in range(flights_wanted(line, ship))
    ]
    first = slots[nth_flight % len(slots)]
    return line[first:] + line[:first]


def antiship_flights_against(flight: Flight, tgo: TheaterGroundObject) -> list[Flight]:
    """Every anti-ship flight in this flight's ATO bound for the sea group.

    Ordered by package time over target, then by ATO order, so the result is the
    same from whichever flight asks.
    """
    flights = [
        candidate
        for package in flight.coalition.ato.packages
        for candidate in package.flights
        if candidate.flight_type == FlightType.ANTISHIP
    ]
    # Resolved only for anti-ship packages: find_main_tgo raises for a naval
    # control point with no ship group, and every CAP over a carrier targets one.
    flights = [f for f in flights if sea_group_for(f.package.target) is tgo]
    flights.sort(key=lambda f: f.package.time_over_target)
    return flights


def ships_for_flight(flight: Flight) -> list[TheaterUnit]:
    """The ships this flight attacks, its own first. Empty for a cargo ship."""
    tgo = sea_group_for(flight.package.target)
    if tgo is None:
        return []
    line = ships_in_line(tgo)
    flights = antiship_flights_against(flight, tgo)
    nth = next((i for i, other in enumerate(flights) if other is flight), 0)
    return ship_order_for(nth, line)
