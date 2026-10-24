"""A flight's stands sit side by side, lead nearest the departure runway end.

Test 64: pydcs gave a Spangdahlem four-ship stands 48-51, spread 270 m across the
junction; the wingmen met the lead nose to nose and all four froze.
"""

from __future__ import annotations

import math
from types import SimpleNamespace
from typing import Any, Optional, cast

import dcs.mission
from dcs.planes import F_4E_45MC
from dcs.terrain.germanycoldwar import GermanyColdWar

from game.ato.starttype import StartType
from game.missiongenerator.aircraft.flightgroupspawner import FlightGroupSpawner
from game.missiongenerator.aircraft.parkingcluster import (
    _spread,
    cluster_parking_slots,
    runway_thresholds,
)
from game.runways import RunwayData
from game.utils import Heading

RUNWAY_23 = 230.0


def _spangdahlem() -> Any:
    return GermanyColdWar().airports["Spangdahlem"]


def _to_threshold(slot: Any, threshold: tuple[float, float]) -> float:
    return math.hypot(slot.position.x - threshold[0], slot.position.y - threshold[1])


def test_four_ship_is_tight_with_lead_nearest_the_runway_end() -> None:
    airport = _spangdahlem()
    slots = cluster_parking_slots(airport, F_4E_45MC, 4, RUNWAY_23)
    assert slots is not None and len(slots) == 4
    assert _spread(slots) < 120
    threshold = runway_thresholds(airport, RUNWAY_23)[0]
    distances = [_to_threshold(s, threshold) for s in slots]
    assert distances == sorted(distances)


def test_pydcs_pick_was_the_scattered_one() -> None:
    airport = _spangdahlem()
    assert _spread(airport.free_parking_slots(F_4E_45MC)[:4]) > 120


def test_departure_heading_decides_the_lead() -> None:
    airport = _spangdahlem()
    for heading in (RUNWAY_23, 50.0):
        slots = cluster_parking_slots(airport, F_4E_45MC, 4, heading)
        assert slots is not None
        threshold = runway_thresholds(airport, heading)[0]
        lead = _to_threshold(slots[0], threshold)
        assert all(lead <= _to_threshold(s, threshold) for s in slots[1:])


def test_every_four_ship_on_a_filling_field_stays_tight() -> None:
    airport = _spangdahlem()
    for _ in range(8):
        slots = cluster_parking_slots(airport, F_4E_45MC, 4, RUNWAY_23)
        assert slots is not None
        assert _spread(slots) < 120
        for slot in slots:
            slot.unit_id = 1


def test_falls_back_to_pydcs_when_no_cluster_fits() -> None:
    airport = _spangdahlem()
    keep = {"37", "55", "65", "90"}
    for slot in airport.parking_slots:
        if slot.slot_name not in keep:
            slot.unit_id = 1
    assert cluster_parking_slots(airport, F_4E_45MC, 4, RUNWAY_23) is None
    assert cluster_parking_slots(airport, F_4E_45MC, 5, RUNWAY_23) is None


def test_single_ship_keeps_the_pydcs_pick() -> None:
    assert cluster_parking_slots(_spangdahlem(), F_4E_45MC, 1, RUNWAY_23) is None


def test_taken_and_blocked_stands_are_never_chosen() -> None:
    airport = _spangdahlem()
    first = cluster_parking_slots(airport, F_4E_45MC, 4, RUNWAY_23)
    assert first is not None
    for slot in first:
        slot.unit_id = -1
    second = cluster_parking_slots(airport, F_4E_45MC, 4, RUNWAY_23)
    assert second is not None
    assert not {s.slot_name for s in first} & {s.slot_name for s in second}


def test_same_inputs_same_stands() -> None:
    def names(heading: Optional[float]) -> list[list[str]]:
        airport = _spangdahlem()
        out = []
        for _ in range(5):
            slots = cluster_parking_slots(airport, F_4E_45MC, 4, heading)
            assert slots is not None
            out.append([s.slot_name for s in slots])
            for slot in slots:
                slot.unit_id = 1
        return out

    assert names(RUNWAY_23) == names(RUNWAY_23)
    assert names(None) == names(None)


def _spawner(
    mission: dcs.mission.Mission, count: int
) -> tuple[FlightGroupSpawner, Any]:
    runway = RunwayData("Spangdahlem", Heading.from_degrees(230), "23")
    game = SimpleNamespace(theater=None, conditions=None)
    spawner = FlightGroupSpawner.__new__(FlightGroupSpawner)
    spawner.flight = cast(
        Any,
        SimpleNamespace(
            unit_type=SimpleNamespace(dcs_unit_type=F_4E_45MC),
            count=count,
            callsign=None,
            state=SimpleNamespace(spawn_type=StartType.COLD),
            coalition=SimpleNamespace(game=game),
        ),
    )
    spawner.country = mission.country("USA")
    spawner.mission = mission
    airfield = SimpleNamespace(
        airport=mission.terrain.airports["Spangdahlem"],
        name="Spangdahlem",
        active_runway=lambda *_: runway,
    )
    return spawner, airfield


def test_spawned_group_parks_on_the_cluster() -> None:
    mission = dcs.mission.Mission(terrain=GermanyColdWar())
    spawner, airfield = _spawner(mission, 4)
    group = spawner._generate_at_airfield("Dodge 8", airfield)
    stands = [unit.parking_id for unit in group.units]
    airport = mission.terrain.airports["Spangdahlem"]
    by_name = {s.slot_name: s for s in airport.parking_slots}
    slots = [by_name[name] for name in stands]
    assert _spread(slots) < 120
    threshold = runway_thresholds(airport, RUNWAY_23)[0]
    assert _to_threshold(slots[0], threshold) == min(
        _to_threshold(s, threshold) for s in slots
    )
