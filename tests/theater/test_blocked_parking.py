"""Stands where AI pilots eject on the ramp are never handed out.

Hatzerim 131-134: four F-15Cs ejected there as they began to taxi on 2026-10-17.
Hatzerim 116: one more in test 60. 158: the stand survey (test 61).
Diyarbakir 116 and 117: two Su-27s ejected there on 2026-10-18; 79: the Turkish survey.
Bitburg 142: an F-15C pilot ejected there in test 65 (2026-10-26).
"""

from __future__ import annotations

from dcs.planes import F_4E_45MC, F_15C
from dcs.terrain import Syria
from dcs.terrain.germanycoldwar import GermanyColdWar
from dcs.terrain.terrain import Terrain

from game.theater.blockedparking import (
    BLOCKED_STANDS,
    blocked_stands,
    occupy_blocked_stands,
)


def _airport(terrain: Terrain, name: str):  # type: ignore[no-untyped-def]
    return next(a for a in terrain.airport_list() if a.name == name)


def test_every_blocked_stand_exists_in_pydcs() -> None:
    terrains = {t.name: t for t in (Syria(), GermanyColdWar())}
    for (terrain_name, airfield), stands in BLOCKED_STANDS.items():
        terrain = terrains[terrain_name]
        names = {s.slot_name for s in _airport(terrain, airfield).parking_slots}
        assert stands <= names, f"{airfield} has no stand {sorted(stands - names)}"


def test_hatzerim_blocked_stands_are_never_free() -> None:
    terrain = Syria()
    hatzerim = _airport(terrain, "Hatzerim")
    for slot in hatzerim.parking_slots:
        slot.unit_id = None
    before = {s.slot_name for s in hatzerim.free_parking_slots(F_15C)}
    assert {"116", "131", "132", "133", "134", "158"} <= before

    taken = occupy_blocked_stands(terrain.name, hatzerim.name, hatzerim.parking_slots)

    after = {s.slot_name for s in hatzerim.free_parking_slots(F_15C)}
    assert taken == 6
    assert after == before - {"116", "131", "132", "133", "134", "158"}


def test_diyarbakir_blocked_stands_are_never_free() -> None:
    terrain = Syria()
    diyarbakir = _airport(terrain, "Diyarbakir")
    for slot in diyarbakir.parking_slots:
        slot.unit_id = None
    before = {s.slot_name for s in diyarbakir.free_parking_slots(F_4E_45MC)}
    assert {"79", "116", "117"} <= before

    taken = occupy_blocked_stands(
        terrain.name, diyarbakir.name, diyarbakir.parking_slots
    )

    after = {s.slot_name for s in diyarbakir.free_parking_slots(F_4E_45MC)}
    assert taken == 3
    assert after == before - {"79", "116", "117"}


def test_other_fields_are_untouched() -> None:
    terrain = Syria()
    ramat_david = _airport(terrain, "Ramat David")
    assert blocked_stands(terrain.name, ramat_david.name) == frozenset()
    assert (
        occupy_blocked_stands(terrain.name, "Ramat David", ramat_david.parking_slots)
        == 0
    )


def test_bitburg_142_is_never_free() -> None:
    terrain = GermanyColdWar()
    bitburg = _airport(terrain, "Bitburg")
    for slot in bitburg.parking_slots:
        slot.unit_id = None
    assert "142" in {s.slot_name for s in bitburg.free_parking_slots(F_15C)}
    assert occupy_blocked_stands(terrain.name, "Bitburg", bitburg.parking_slots) == 1
    assert "142" not in {s.slot_name for s in bitburg.free_parking_slots(F_15C)}
