"""Stands where AI pilots eject on the ramp are never handed out.

Hatzerim 131-134: four F-15Cs ejected there as they began to taxi on 2026-10-17.
Hatzerim 116: one more in test 60.
"""

from __future__ import annotations

from dcs.planes import F_15C
from dcs.terrain import Syria

from game.theater.blockedparking import (
    BLOCKED_STANDS,
    blocked_stands,
    occupy_blocked_stands,
)


def _airport(terrain: Syria, name: str):  # type: ignore[no-untyped-def]
    return next(a for a in terrain.airport_list() if a.name == name)


def test_every_blocked_stand_exists_in_pydcs() -> None:
    terrain = Syria()
    for (terrain_name, airfield), stands in BLOCKED_STANDS.items():
        assert terrain_name == terrain.name
        names = {s.slot_name for s in _airport(terrain, airfield).parking_slots}
        assert stands <= names, f"{airfield} has no stand {sorted(stands - names)}"


def test_hatzerim_blocked_stands_are_never_free() -> None:
    terrain = Syria()
    hatzerim = _airport(terrain, "Hatzerim")
    for slot in hatzerim.parking_slots:
        slot.unit_id = None
    before = {s.slot_name for s in hatzerim.free_parking_slots(F_15C)}
    assert {"116", "131", "132", "133", "134"} <= before

    taken = occupy_blocked_stands(terrain.name, hatzerim.name, hatzerim.parking_slots)

    after = {s.slot_name for s in hatzerim.free_parking_slots(F_15C)}
    assert taken == 5
    assert after == before - {"116", "131", "132", "133", "134"}


def test_other_fields_are_untouched() -> None:
    terrain = Syria()
    ramat_david = _airport(terrain, "Ramat David")
    assert blocked_stands(terrain.name, ramat_david.name) == frozenset()
    assert (
        occupy_blocked_stands(terrain.name, "Ramat David", ramat_david.parking_slots)
        == 0
    )
