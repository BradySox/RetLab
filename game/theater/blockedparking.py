"""Parking stands no aircraft is spawned on.

An AI pilot on these stands ejects on the ramp the moment the jet starts to taxi: four
F-15Cs on Hatzerim 131-134 in the 2026-10-17 Syria test, with nothing else within 150 m,
and one on Hatzerim 116 in test 60, 13 s after it spawned.
pydcs lists the stands as ordinary 21 x 15 m slots, so they are held here by name.
"""

from __future__ import annotations

from typing import Iterable

from dcs.terrain.terrain import ParkingSlot

#: Stand names (``ParkingSlot.slot_name``) per (terrain name, airfield name).
BLOCKED_STANDS: dict[tuple[str, str], frozenset[str]] = {
    ("Syria", "Hatzerim"): frozenset({"116", "131", "132", "133", "134"}),
}

#: A non-None ``unit_id`` is how pydcs marks a slot taken.
BLOCKED_UNIT_ID = -1


def blocked_stands(terrain_name: str, airfield_name: str) -> frozenset[str]:
    return BLOCKED_STANDS.get((terrain_name, airfield_name), frozenset())


def occupy_blocked_stands(
    terrain_name: str, airfield_name: str, slots: Iterable[ParkingSlot]
) -> int:
    """Mark the field's blocked stands taken so pydcs never spawns on them."""
    blocked = blocked_stands(terrain_name, airfield_name)
    count = 0
    for slot in slots:
        if slot.slot_name in blocked:
            slot.unit_id = BLOCKED_UNIT_ID
            count += 1
    return count
