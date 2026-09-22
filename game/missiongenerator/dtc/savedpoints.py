"""Where the player's saved points land in the cockpit (§102).

One answer for the cartridge builders and the kneeboard, so the number printed beside a
point is the number the jet gives it. Saved points follow the flight plan, ride only
with a cartridge that carries the route, and take route sequence 2. See
docs/dev/design/retlab-my-aircraft-notes.md.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Sequence

if TYPE_CHECKING:
    from game.ato.savedpoints import SavedPoint
    from game.missiongenerator.aircraft.flightdata import FlightData
    from game.settings import Settings

#: WYPT_NAV.lua caps the set at 59; 58 and 59 are left to HOME and the bullseye.
HORNET_LAST_POINT = 57
#: STPT 25 is the bullseye (viper.MAX_STEERPOINTS); the support anchors fill what
#: the route and the saved points leave.
VIPER_LAST_POINT = 24


def cartridge_route_length(flight: FlightData) -> int:
    """How many cockpit numbers the cartridge's route takes: row 0 is not emitted."""
    from game.missiongenerator.dtc.hornet import HORNET_UNIT_TYPE, MAX_WAYPOINTS
    from game.missiongenerator.dtc.viper import (
        MAX_ROUTE_STEERPOINTS,
        VIPER_UNIT_TYPE,
    )

    flown = max(len(flight.waypoints) - 1, 0)
    aircraft = flight.aircraft_type.dcs_unit_type.id
    if aircraft == HORNET_UNIT_TYPE:
        return min(flown, MAX_WAYPOINTS)
    if aircraft == VIPER_UNIT_TYPE:
        return min(flown, MAX_ROUTE_STEERPOINTS)
    return flown


def carries_saved_points(flight: FlightData, settings: Settings) -> bool:
    """Whether this flight's cartridge will hold its saved points at all."""
    from game.missiongenerator.dtc.hornet import HORNET_UNIT_TYPE
    from game.missiongenerator.dtc.viper import VIPER_UNIT_TYPE

    if flight.aircraft_type.dcs_unit_type.id not in (
        HORNET_UNIT_TYPE,
        VIPER_UNIT_TYPE,
    ):
        return False
    if not flight.friendly.is_blue or not flight.client_units:
        return False
    options = flight.dtc_options
    return options.resolve_enabled(settings.dtc_data_cartridges) and options.route


def cockpit_numbers(
    flight: FlightData, points: Sequence[SavedPoint]
) -> list[Optional[int]]:
    """The cartridge number each saved point gets, None for one with no room left."""
    from game.missiongenerator.dtc.hornet import HORNET_UNIT_TYPE

    first = cartridge_route_length(flight) + 1
    last = (
        HORNET_LAST_POINT
        if flight.aircraft_type.dcs_unit_type.id == HORNET_UNIT_TYPE
        else VIPER_LAST_POINT
    )
    return [
        number if number <= last else None
        for number in range(first, first + len(points))
    ]


def kneeboard_numbers(flight: FlightData, settings: Settings) -> list[Optional[int]]:
    """What the kneeboard prints beside each saved point.

    The cartridge's number when there is one, the A-10's CDU number, and otherwise the
    next number after the kneeboard's own route rows (which count from 0).
    """
    from game.missiongenerator.a10cdu import AIRCRAFT as A10, numbers_for

    points = flight.saved_points
    if carries_saved_points(flight, settings):
        return cockpit_numbers(flight, points)
    if flight.aircraft_type.dcs_unit_type.id in A10 and flight.client_units:
        return list(numbers_for(len(flight.waypoints), len(points)))
    start = len(flight.waypoints)
    return list(range(start, start + len(points)))
