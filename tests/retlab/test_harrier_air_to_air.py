"""The AV-8B flies fighter patrols, last in line, on Sidewinders.

Upstream gives the Harrier no air-to-air task, so a side whose only jet is the
Harrier (the 1982 task force, where it stands in for the Sea Harrier) had no
fighter cover at all. DCS lets an AI AV-8B fly CAP and escort. The fork adds the
four air-to-air lanes at a weight below every jet fighter, so a side with any
real fighter still sends that first, and a BARCAP loadout of four AIM-9L.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from dcs import lua

from game import persistency
from game.ato.flighttype import FlightType
from game.dcs.aircrafttype import AircraftType

HARRIER = "AV-8B Harrier II Night Attack"
UNITS = Path("resources/units/aircraft")
PAYLOADS = Path("resources/customized_payloads/AV8BNA.lua")
AIR_TO_AIR = ("BARCAP", "TARCAP", "Escort", "Fighter sweep")


@pytest.fixture(scope="module")
def harrier(tmp_path_factory: pytest.TempPathFactory) -> AircraftType:
    persistency.setup(str(tmp_path_factory.mktemp("harrier")), False, 16880)
    return AircraftType.named(HARRIER)


def test_the_harrier_can_fly_fighter_patrols(harrier: AircraftType) -> None:
    for task in (
        FlightType.BARCAP,
        FlightType.TARCAP,
        FlightType.ESCORT,
        FlightType.SWEEP,
    ):
        assert harrier.capable_of(task), task.name


def test_every_jet_fighter_outranks_it() -> None:
    harrier = yaml.safe_load((UNITS / "AV8BNA.yaml").read_text(encoding="utf-8"))
    for path in UNITS.glob("*.yaml"):
        if path.stem == "AV8BNA":
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        # Jet age only: the WWII fighters sit at the bottom of the scale.
        if (data.get("introduced") or 0) < 1955:
            continue
        tasks = data.get("tasks") or {}
        # Fighters only: an attack helicopter's Escort is a different lane.
        if "BARCAP" not in tasks:
            continue
        for task in AIR_TO_AIR:
            if task in tasks:
                assert harrier["tasks"][task] < tasks[task], (path.stem, task)


def test_its_patrol_loadout_is_four_aim9l() -> None:
    parsed = lua.loads(PAYLOADS.read_text(encoding="utf-8"))
    payloads = parsed["unitPayloads"]["payloads"].values()
    barcap = next(p for p in payloads if p["name"] == "Retribution BARCAP")
    stores = {pylon["num"]: pylon["CLSID"] for pylon in barcap["pylons"].values()}
    assert stores[1] == stores[8] == "{AIM-9L}"
    assert stores[2] == stores[7] == "{AIM-9L-ON-ADAPTER}"
    # CAP is task 11 in DCS's payload tables.
    assert list(barcap["tasks"].values()) == [11]
