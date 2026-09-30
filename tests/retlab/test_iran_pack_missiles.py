"""The RetLab Iran Air Defense Pack's surface-to-surface launchers, which replaced the
third-party Iranian missile mods on 2026-09-29
(docs/dev/design/retlab-iran-iads-deployment-notes.md, §6).
"""

from __future__ import annotations

import dataclasses
import io
import json
from pathlib import Path

import pytest
import yaml

from dcs.unittype import VehicleType

from game import persistency
from game.dcs.groundunittype import GroundUnitType
from game.factions.faction import Faction
from game.theater.start_generator import ModSettings
from pydcs_extensions import iranairdefensepack as irad

FACTIONS_DIR = Path("resources/factions")
UNITS_DIR = Path("resources/units/ground_units")

SSM_IDS = {
    irad.IRAD_Sejjil_TEL.id,
    irad.IRAD_Emad_TEL.id,
    irad.IRAD_Kheibar_TEL.id,
    irad.IRAD_Fattah2_TEL.id,
    irad.IRAD_Shahed238_TEL.id,
}


@pytest.fixture(autouse=True)
def _init_persistency(tmp_path_factory: pytest.TempPathFactory) -> None:
    persistency.setup(str(tmp_path_factory.mktemp("saved_games")), False, 0)


def _load(name: str, pack: bool) -> Faction:
    with (FACTIONS_DIR / name).open(encoding="utf-8") as data:
        faction = Faction.from_dict(json.load(data))
    settings = dataclasses.replace(
        ModSettings.all_off(),
        iranmilitaryassetspack=True,
        iranairdefensepack=pack,
    )
    faction.apply_mod_settings(settings)
    return faction


def _pack_missiles(faction: Faction) -> set[str]:
    return {
        unit.dcs_unit_type.id
        for unit in faction.missiles
        if unit.dcs_unit_type.id in SSM_IDS
    }


@pytest.mark.parametrize("unit_id", sorted(SSM_IDS))
def test_every_launcher_has_unit_data(unit_id: str) -> None:
    data = yaml.safe_load((UNITS_DIR / f"{unit_id}.yaml").read_text("utf-8"))
    assert data["class"] == "Missile"


def test_iran_2025_fields_every_launcher() -> None:
    assert _pack_missiles(_load("CH_iran_2025.json", pack=True)) == SSM_IDS


def test_iran_2020_fields_the_sejjil_and_emad() -> None:
    """The Fattah-2, Kheibar and Shahed 238 were shown in 2023."""
    assert _pack_missiles(_load("CH_iran_2020.json", pack=True)) == {
        "IRAD_Sejjil_TEL",
        "IRAD_Emad_TEL",
    }


def test_iran_2015_fields_the_sejjil_only() -> None:
    """The Emad (2016), Fattah-2, Shahed 238 and Kheibar (2023) postdate 2015."""
    assert _pack_missiles(_load("iran_2015.json", pack=True)) == {"IRAD_Sejjil_TEL"}


@pytest.mark.parametrize(
    "name", ["CH_iran_2025.json", "CH_iran_2020.json", "iran_2015.json"]
)
def test_toggle_off_strips_every_launcher(name: str) -> None:
    assert _pack_missiles(_load(name, pack=False)) == set()


def test_the_third_party_toggle_is_gone() -> None:
    assert not hasattr(ModSettings.all_off(), "iranmissilemods")


@pytest.mark.parametrize(
    "stem",
    ["scenic_merge", "operation_noisy_cricket", "WRL_Operation_Noisy_Cricket_Redux"],
)
def test_the_2019_2020_iranian_campaigns_preseed_the_pack(stem: str) -> None:
    """The Iranian-red Persian Gulf campaigns dated after the Sejjil-2 (2009) with red
    missile-site markers. The 2005 Scenic Routes predate every launcher here."""
    data = yaml.safe_load(Path(f"resources/campaigns/{stem}.yaml").read_text("utf-8"))
    assert data["settings"]["iranairdefensepack"] is True
    assert "iranmissilemods" not in data["settings"]


@pytest.mark.parametrize(
    "old_class,new_class",
    [
        ("PGIR_Sejjil_Launcher", irad.IRAD_Sejjil_TEL),
        ("PGIR_Emad_Launcher", irad.IRAD_Emad_TEL),
        ("PGIR_Fattah2_Launcher", irad.IRAD_Fattah2_TEL),
        ("PGAD_Shahed238_TEL", irad.IRAD_Shahed238_TEL),
        ("KHEIBAR_TEL_Launcher", irad.IRAD_Kheibar_TEL),
    ],
)
def test_an_old_save_loads_the_pack_launcher(old_class: str, new_class: type) -> None:
    """A save from before 2026-09-29 pickled the deleted third-party classes."""
    unpickler = persistency.MigrationUnpickler(io.BytesIO(b""))
    found = unpickler.find_class(
        "pydcs_extensions.iranmissilemods.iranmissilemods", old_class
    )
    assert found is new_class


@pytest.mark.parametrize(
    "old_name,new_id",
    [
        ("Sejjil-2 MRBM TEL [PG IR]", "IRAD_Sejjil_TEL"),
        ("Emad MRBM TEL [PG IR]", "IRAD_Emad_TEL"),
        ("Fattah-2 HGV TEL [PG IR]", "IRAD_Fattah2_TEL"),
        ("Shahed 238 LM [PG AD]", "IRAD_Shahed238_TEL"),
        ("Kheibar (Khorramshahr-4) TEL", "IRAD_Kheibar_TEL"),
    ],
)
def test_an_old_variant_name_resolves_to_the_pack(old_name: str, new_id: str) -> None:
    assert GroundUnitType.named(old_name).dcs_unit_type.id == new_id


BALLISTIC = [
    irad.IRAD_Sejjil_TEL,
    irad.IRAD_Emad_TEL,
    irad.IRAD_Kheibar_TEL,
    irad.IRAD_Fattah2_TEL,
]


@pytest.mark.parametrize("launcher", BALLISTIC)
def test_a_ballistic_launcher_fires_only_inside_its_motor(
    launcher: type[VehicleType],
) -> None:
    """The pack flies ED's Iskander, 75-400 km (DM call 2026-09-30); RetLab must pick
    targets inside that band or DCS refuses the shot."""
    assert launcher.threat_range == 400000
    assert irad.MISSILE_MIN_RANGE_M[launcher.id] == 75000
