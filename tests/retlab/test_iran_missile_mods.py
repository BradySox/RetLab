"""Third-party Iranian missile mods: the PG Iran IRBM Pack, the PG Iran Air Defense
Pack's Shahed-238 and the Kheibar TEL, supported until the RetLab pack carries its own
launchers (docs/dev/design/retlab-iran-iads-deployment-notes.md).
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest
import yaml
from dcs.unittype import VehicleType

from game import persistency
from game.factions.faction import Faction
from game.theater.start_generator import ModSettings
from pydcs_extensions import iranmissilemods as mods

FACTIONS_DIR = Path("resources/factions")
UNITS_DIR = Path("resources/units/ground_units")

MOD_IDS = {
    cls.id
    for cls in vars(mods).values()
    if isinstance(cls, type) and issubclass(cls, VehicleType) and cls is not VehicleType
}


@pytest.fixture(autouse=True)
def _init_persistency(tmp_path_factory: pytest.TempPathFactory) -> None:
    persistency.setup(str(tmp_path_factory.mktemp("saved_games")), False, 0)


def _load(name: str, on: bool) -> Faction:
    with (FACTIONS_DIR / name).open(encoding="utf-8") as data:
        faction = Faction.from_dict(json.load(data))
    settings = dataclasses.replace(
        ModSettings.all_off(),
        iranmilitaryassetspack=True,
        iranairdefensepack=True,
        iranmissilemods=on,
    )
    faction.apply_mod_settings(settings)
    return faction


def _mod_missiles(faction: Faction) -> set[str]:
    return {
        unit.dcs_unit_type.id
        for unit in faction.missiles
        if unit.dcs_unit_type.id in MOD_IDS
    }


def test_the_module_has_five_launchers() -> None:
    assert len(MOD_IDS) == 5


@pytest.mark.parametrize("unit_id", sorted(MOD_IDS))
def test_every_launcher_has_unit_data(unit_id: str) -> None:
    assert (UNITS_DIR / f"{unit_id}.yaml").is_file()


def test_iran_2020_fields_every_launcher() -> None:
    assert _mod_missiles(_load("CH_iran_2020.json", on=True)) == MOD_IDS


def test_iran_2015_fields_the_sejjil_only() -> None:
    """The Emad (2016), Fattah-2, Shahed-238 and Kheibar (2023) postdate 2015."""
    assert _mod_missiles(_load("iran_2015.json", on=True)) == {"PGIR_Sejjil_Launcher"}


@pytest.mark.parametrize("name", ["CH_iran_2020.json", "iran_2015.json"])
def test_toggle_off_strips_every_launcher(name: str) -> None:
    assert _mod_missiles(_load(name, on=False)) == set()


@pytest.mark.parametrize(
    "stem",
    ["scenic_merge", "operation_noisy_cricket", "WRL_Operation_Noisy_Cricket_Redux"],
)
def test_the_2019_2020_iranian_campaigns_preseed_the_mods(stem: str) -> None:
    """The Iranian-red Persian Gulf campaigns dated after the Sejjil-2 (2009) with red
    missile-site markers. The 2005 Scenic Routes predate every launcher here."""
    data = yaml.safe_load(Path(f"resources/campaigns/{stem}.yaml").read_text("utf-8"))
    assert data["settings"]["iranmissilemods"] is True
