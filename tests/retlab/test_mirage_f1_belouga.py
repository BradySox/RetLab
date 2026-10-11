"""The Mirage F1's cluster-bomb presets name a store DCS has.

Eight Mirage F1 preset files put `{BLG66_BELOUGA}` on pylons 2, 3, 5 and 6 of
their DEAD and OCA/Aircraft presets. DCS has no store by that id: Aerges'
`CoreMods/aircraft/Mirage-F1/Payloads.lua` declares the Belouga as
`id_BLG66_BELOUGA = "{BLG66_AC}"` (the variable carries the old name, the id
does not) and adds it to pylons 2 to 6. The id resolved to no weapon, so the
whole preset was dropped and the jet flew a fallback fit. `{BLG66_BELOUGA_AC}`
on the Mirage 2000C is a different, valid store.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Type, cast

import pytest
from dcs import planes
from dcs.payloads import PayloadDirectories
from dcs.unittype import FlyingType

from game.ato.flighttype import FlightType
from game.ato.loadouts import Loadout
from game.data.weapons import Pylon
from game.dcs.aircrafttype import AircraftType

PAYLOADS_DIR = Path(__file__).parents[2] / "resources" / "customized_payloads"

VARIANTS = [
    "Mirage-F1B",
    "Mirage-F1BE",
    "Mirage-F1C-200",
    "Mirage-F1CE",
    "Mirage-F1CT",
    "Mirage-F1EE",
    "Mirage-F1M-CE",
    "Mirage-F1M-EE",
]
TASKS = [FlightType.OCA_AIRCRAFT, FlightType.DEAD]
BELOUGA = "{BLG66_AC}"


@pytest.fixture(autouse=True)
def payload_dirs() -> None:
    PayloadDirectories.set_fallback(PAYLOADS_DIR)
    FlyingType._payload_cache = None  # type: ignore[assignment]


def _aircraft(dcs_type: Type[FlyingType]) -> AircraftType:
    return cast(
        AircraftType,
        SimpleNamespace(dcs_unit_type=dcs_type, has_built_in_target_pod=False),
    )


@pytest.mark.parametrize("variant", VARIANTS)
@pytest.mark.parametrize("task", TASKS, ids=lambda t: t.value)
def test_the_cluster_bomb_preset_resolves_and_fits(
    variant: str, task: FlightType
) -> None:
    dcs_type = planes.plane_map[variant]
    loadout = Loadout.default_for_task_and_aircraft(task, dcs_type)

    assert loadout.name == f"Retribution {task.value}"
    stores = {n: w for n, w in loadout.pylons.items() if w is not None}
    assert sorted(n for n, w in stores.items() if w.clsid == BELOUGA) == [2, 3, 5, 6]
    for number, weapon in stores.items():
        assert Pylon.for_aircraft(_aircraft(dcs_type), number).can_equip(
            weapon
        ), f"{variant} {task.value}: pylon {number} cannot take {weapon.clsid}"


def test_no_mirage_f1_preset_names_the_store_that_does_not_exist() -> None:
    for path in PAYLOADS_DIR.glob("Mirage-F1*.lua"):
        assert '"{BLG66_BELOUGA}"' not in path.read_text(encoding="utf-8"), path.name
