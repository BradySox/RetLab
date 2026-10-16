"""The AI twin of a player flight (§113).

The twin is built from the real Flight through :func:`ai_twin_view`, which makes
the flight look like an AI air start of its player seats for the length of the
block, so the spawner, configurator and waypoint generator need no twin branch of
their own. docs/dev/design/retlab-ai-fill-notes.md.
"""

from __future__ import annotations

import copy
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import Any, TYPE_CHECKING

from dcs.unitgroup import FlyingGroup

from game.ato.flightmember import FlightMember
from game.ato.flightstate import WaitingForStart
from game.ato.starttype import StartType

if TYPE_CHECKING:
    from game.ato import Flight


#: The twin's group name is the client group's with this in front. The client
#: name's first "|" field still ends in the task, which the QRA filter reads.
TWIN_PREFIX = "AI "

#: FlightWaypoint fields the waypoint generator writes for the kneeboard. The
#: twin's pass would overwrite the client flight's values.
_WAYPOINT_FIELDS = ("tot", "min_fuel", "fuel_planned")


class AiTwinSeat(FlightMember):
    """A player seat, flown by the AI: the same pilot, loadout and properties."""

    def __init__(self, seat: FlightMember) -> None:
        super().__init__(seat.pilot, seat.loadout)
        self.__dict__.update(seat.__dict__)

    @property
    def is_player(self) -> bool:
        return False


def twin_group_name(client_group_name: str) -> str:
    return f"{TWIN_PREFIX}{client_group_name}"


def player_units(flight: Flight, group: FlyingGroup[Any]) -> list[Any]:
    """The client group's units in the player seats, in seat order."""
    return [
        unit
        for unit, member in zip(group.units, flight.iter_members())
        if member.is_player
    ]


@contextmanager
def ai_twin_view(flight: Flight, mission_start: datetime) -> Iterator[None]:
    """Show the generator the flight as an AI air start of its player seats.

    A flight still on the ground at mission start spawns in the air over its
    departure at its planned takeoff time; one already airborne spawns where the
    client group does. Everything is put back when the block ends, including the
    waypoint TOTs and fuel the client flight's kneeboard reads.
    """
    roster = flight.roster
    start_type = flight.start_type
    state = flight.state
    group_id = flight.group_id
    waypoints = list(flight.flight_plan.waypoints)
    saved = [
        {name: getattr(point, name, None) for name in _WAYPOINT_FIELDS}
        for point in waypoints
    ]

    twin_roster = copy.copy(roster)
    twin_roster.members = [AiTwinSeat(m) for m in roster.members if m.is_player]
    airborne = (
        state.spawn_type is StartType.IN_FLIGHT and not state.is_waiting_for_start
    )
    try:
        flight.roster = twin_roster
        flight.start_type = StartType.IN_FLIGHT
        if not airborne:
            takeoff = max(flight.flight_plan.takeoff_time(), mission_start)
            flight.set_state(WaitingForStart(flight, flight.squadron.settings, takeoff))
        yield
    finally:
        flight.roster = roster
        flight.start_type = start_type
        flight.set_state(state)
        flight.group_id = group_id
        for point, values in zip(waypoints, saved):
            for name, value in values.items():
                setattr(point, name, value)


def copy_identity(client_units: list[Any], twin: FlyingGroup[Any]) -> None:
    """Give the twin the client seats' callsigns and board numbers.

    Only one of the two ever flies, so the package hears the callsign it was
    briefed on either way.
    """
    for twin_unit, client_unit in zip(twin.units, client_units):
        twin_unit.callsign = client_unit.callsign
        callsign_dict = client_unit.callsign_dict
        twin_unit.callsign_dict = (
            dict(callsign_dict) if isinstance(callsign_dict, dict) else callsign_dict
        )
        twin_unit.onboard_num = client_unit.onboard_num
