"""Where Insert NAV point puts a new point: in a leg beside the selected waypoint.

A layout keeps its insertable points in a few lists (the transit legs, a strike's way
in and out, a custom plan's own list). A list is only right for the new point if the
point would sit next to the selected waypoint in the route; a list whose place in the
route is elsewhere puts the point on the far side of a fixed waypoint and the route
zigzags through it. So each candidate is tried in place and kept only if it lands
next to the anchor: after it first, then before it.

Waypoints compare by value (FlightWaypoint is a dataclass), so every lookup here is by
identity: two NAV points planned at the same place are still two waypoints.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence, TYPE_CHECKING

from .waypointbuilder import WaypointBuilder
from ..flightwaypointtype import FlightWaypointType

if TYPE_CHECKING:
    from .flightplan import Layout
    from ..flightwaypoint import FlightWaypoint

#: Not route legs: a nav point beside these would be flown after landing.
NOT_ON_ROUTE = frozenset({FlightWaypointType.BULLSEYE, FlightWaypointType.DIVERT})


@dataclass(frozen=True)
class NavInsert:
    """A nav point and the slot it goes in: ``sequence[index]``."""

    sequence: list[FlightWaypoint]
    index: int
    waypoint: FlightWaypoint

    def apply(self) -> None:
        self.sequence.insert(self.index, self.waypoint)


def identity_index(
    sequence: Sequence[FlightWaypoint], item: FlightWaypoint
) -> Optional[int]:
    for index, candidate in enumerate(sequence):
        if candidate is item:
            return index
    return None


def nav_insert_next_to(layout: Layout, anchor: FlightWaypoint) -> Optional[NavInsert]:
    """The slot for a nav point beside ``anchor``, or None if the plan has none.

    The point goes halfway along the leg it lands in. Nothing is changed: the caller
    applies the result, or asks first.
    """
    if anchor.waypoint_type in NOT_ON_ROUTE:
        return None
    route = layout.waypoints
    at = identity_index(route, anchor)
    if at is None:
        return None
    after = route[at + 1] if at + 1 < len(route) else None
    for sequence in layout.nav_sequences():
        own = identity_index(sequence, anchor)
        slot = NavInsert(
            sequence,
            0 if own is None else own + 1,
            WaypointBuilder.nav_midpoint(anchor, after),
        )
        if _lands_beside(layout, slot, anchor, 1):
            return slot
    if at == 0:
        return None
    before = route[at - 1]
    for sequence in layout.nav_sequences():
        own = identity_index(sequence, anchor)
        slot = NavInsert(
            sequence,
            len(sequence) if own is None else own,
            WaypointBuilder.nav_midpoint(before, anchor),
        )
        if _lands_beside(layout, slot, anchor, -1):
            return slot
    return None


def _lands_beside(
    layout: Layout, slot: NavInsert, anchor: FlightWaypoint, side: int
) -> bool:
    """Whether the point would be the next (``side`` 1) or previous (-1) waypoint."""
    slot.apply()
    try:
        route = layout.waypoints
        at = identity_index(route, slot.waypoint)
        neighbour = None if at is None else at - side
        return (
            neighbour is not None
            and 0 <= neighbour < len(route)
            and route[neighbour] is anchor
        )
    finally:
        del slot.sequence[slot.index]
