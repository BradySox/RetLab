"""The Mi-24P's outboard pylons take the ATGM stores that come with an adapter.

DCS gives the Hind two ATGM store families: the wingtip rails (pylons 1 and 6)
take `{2x9M120_Ataka_V}` and its siblings, and the outboard wing pylons (2 and
5) take the `..._with_adapter` ids (`CoreMods/aircraft/Mi-24P/Mi-24P.lua`,
`wingtips` and `outboard`). The presets put the wingtip id on all four, and the
Hind has no `replace_deprecated_loadout_with` table to swap it. Test 55 logged
"Pylon 2 cannot equip 2 x 9M120 Ataka" for the Escort flight.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
from dcs.helicopters import Mi_24P
from dcs.payloads import PayloadDirectories
from dcs.unittype import FlyingType

from game.ato.flighttype import FlightType
from game.ato.loadouts import Loadout
from game.data.weapons import Pylon
from game.dcs.aircrafttype import AircraftType

PAYLOADS_DIR = Path(__file__).parents[2] / "resources" / "customized_payloads"

#: The tasks Mi-24P.yaml declares that resolve a preset from the payload file.
TASKS = [
    FlightType.CAS,
    FlightType.BAI,
    FlightType.ESCORT,
    FlightType.OCA_AIRCRAFT,
]


@pytest.fixture(autouse=True)
def payload_dirs() -> None:
    PayloadDirectories.set_fallback(PAYLOADS_DIR)
    FlyingType._payload_cache = None  # type: ignore[assignment]


def _aircraft() -> AircraftType:
    return cast(
        AircraftType,
        SimpleNamespace(dcs_unit_type=Mi_24P, has_built_in_target_pod=False),
    )


@pytest.mark.parametrize("task", TASKS, ids=lambda t: t.value)
def test_every_store_is_one_its_pylon_takes(task: FlightType) -> None:
    loadout = Loadout.default_for_task_and_aircraft(task, Mi_24P)
    assert loadout.pylons, f"{task.value} resolved an empty loadout"
    for number, weapon in loadout.pylons.items():
        if weapon is None:
            continue
        pylon = Pylon.for_aircraft(_aircraft(), number)
        assert pylon.can_equip(weapon), (
            f"{task.value} ({loadout.name}): pylon {number} cannot take "
            f"{weapon.name} ({weapon.clsid})"
        )


def test_no_preset_puts_a_wingtip_atgm_on_an_outboard_pylon() -> None:
    for payload in Mi_24P.load_payloads().values():
        for pylon in payload["pylons"].values():
            if pylon["num"] in (2, 5) and "Ataka" in pylon["CLSID"]:
                assert pylon["CLSID"].endswith(
                    "_with_adapter}"
                ), f"{payload['name']}: pylon {pylon['num']} has {pylon['CLSID']}"
