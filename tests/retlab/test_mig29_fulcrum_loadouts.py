"""The MiG-29A module's presets use the module's own store ids.

The payload file shipped as a copy of the Flaming Cliffs MiG-29A's, with that
jet's CLSIDs. The full module (`MiG-29 Fulcrum`) takes its own ids on every
pylon. DCS swaps the old ones at mission load through the module's
`replace_deprecated_loadout_with` table, so the jets flew armed, but every Take
Off logged "Pylon N cannot equip ..." six times per flight (test 55: 48 lines)
and the presets depended on that swap. The ids here are the ones that table
maps to.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
from dcs.payloads import PayloadDirectories
from dcs.planes import MiG_29_Fulcrum
from dcs.unittype import FlyingType

from game.ato.flighttype import FlightType
from game.ato.loadouts import Loadout
from game.data.weapons import Pylon
from game.dcs.aircrafttype import AircraftType

PAYLOADS_DIR = Path(__file__).parents[2] / "resources" / "customized_payloads"

#: The tasks MiG-29 Fulcrum.yaml declares.
A2A_TASKS = [
    FlightType.BARCAP,
    FlightType.TARCAP,
    FlightType.ESCORT,
    FlightType.SWEEP,
]
A2G_TASKS = [
    FlightType.CAS,
    FlightType.BAI,
    FlightType.STRIKE,
    FlightType.OCA_AIRCRAFT,
    FlightType.OCA_RUNWAY,
]

R_73 = "{MISSILE_R-73_APU-73}"
R_27R = "{MISSILE_R-27R_APU-470}"


@pytest.fixture(autouse=True)
def payload_dirs() -> None:
    PayloadDirectories.set_fallback(PAYLOADS_DIR)
    FlyingType._payload_cache = None  # type: ignore[assignment]


def _aircraft() -> AircraftType:
    return cast(
        AircraftType,
        SimpleNamespace(dcs_unit_type=MiG_29_Fulcrum, has_built_in_target_pod=False),
    )


@pytest.mark.parametrize("task", A2A_TASKS + A2G_TASKS, ids=lambda t: t.value)
def test_every_store_is_one_its_pylon_takes(task: FlightType) -> None:
    loadout = Loadout.default_for_task_and_aircraft(task, MiG_29_Fulcrum)
    assert loadout.pylons, f"{task.value} resolved an empty loadout"
    for number, weapon in loadout.pylons.items():
        if weapon is None:
            continue
        pylon = Pylon.for_aircraft(_aircraft(), number)
        assert pylon.can_equip(weapon), (
            f"{task.value} ({loadout.name}): pylon {number} cannot take "
            f"{weapon.name} ({weapon.clsid})"
        )


@pytest.mark.parametrize("task", A2A_TASKS, ids=lambda t: t.value)
def test_air_to_air_tasks_carry_four_r73_and_two_r27r(task: FlightType) -> None:
    loadout = Loadout.default_for_task_and_aircraft(task, MiG_29_Fulcrum)
    stores = [w.clsid for w in loadout.pylons.values() if w is not None]
    assert stores.count(R_73) == 4
    assert stores.count(R_27R) == 2
