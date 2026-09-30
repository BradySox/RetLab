"""RetLab Iran Air Defense Pack: 3rd Khordad, Bavar-373 and five missile launchers.

The type ids here are the contract with the mod's Database lua (see
docs/dev/design/retlab-iran-air-defense-pack-notes.md). These tests hold the
Python side to it: every id has unit data, the toggle strips every id, the
presets reach only era-correct factions, and Skynet knows every radar.
"""

from __future__ import annotations

import dataclasses
import io
import json
from pathlib import Path

import pytest
from dcs.unittype import VehicleType

from game import persistency
from game.dcs.groundunittype import GroundUnitType
from game.factions.faction import Faction
from game.data.radar_db import LAUNCHER_TRACKER_PAIRS, TELARS, UNITS_WITH_RADAR
from game.layout import LAYOUTS
from game.theater.start_generator import ModSettings
from pydcs_extensions import iranairdefensepack as irad

FACTIONS_DIR = Path("resources/factions")
SKYNET = Path("resources/plugins/skynetiads/skynet-iads-compiled.lua")
UNITS_DIR = Path("resources/units/ground_units")

IRAD_IDS = {
    cls.id
    for cls in vars(irad).values()
    if isinstance(cls, type)
    and issubclass(cls, VehicleType)
    and cls.id.startswith("IRAD_")
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


def _irad_units(faction: Faction) -> set[str]:
    return {
        unit.dcs_unit_type.id
        for unit in faction.accessible_units
        if unit.dcs_unit_type.id.startswith("IRAD_")
    }


SSM_IDS = {
    "IRAD_Sejjil_TEL",
    "IRAD_Emad_TEL",
    "IRAD_Kheibar_TEL",
    "IRAD_Fattah2_TEL",
    "IRAD_Shahed238_TEL",
}


def test_the_contract_has_fifteen_units() -> None:
    assert len(IRAD_IDS) == 15
    assert SSM_IDS <= IRAD_IDS


@pytest.mark.parametrize("unit_id", sorted(IRAD_IDS))
def test_every_unit_has_unit_data(unit_id: str) -> None:
    assert (UNITS_DIR / f"{unit_id}.yaml").is_file()


def test_iran_2025_fields_every_unit() -> None:
    faction = _load("CH_iran_2025.json", pack=True)
    presets = {group.name for group in faction.preset_groups}
    assert {"3rd Khordad", "Bavar-373"} <= presets
    assert _irad_units(faction) == IRAD_IDS


def test_iran_2020_fields_nothing_from_after_2021() -> None:
    """The Fattah-2, Kheibar and Shahed 238 were shown in 2023: those are [CH] Iran
    2025's."""
    faction = _load("CH_iran_2020.json", pack=True)
    presets = {group.name for group in faction.preset_groups}
    assert {"3rd Khordad", "Bavar-373"} <= presets
    later = {
        "IRAD_Fattah2_TEL",
        "IRAD_Kheibar_TEL",
        "IRAD_Shahed238_TEL",
    }
    assert _irad_units(faction) == IRAD_IDS - later


def test_iran_2015_gets_3rd_khordad_only() -> None:
    """Bavar-373 entered service in 2019; a 2015 faction must not field it."""
    faction = _load("iran_2015.json", pack=True)
    presets = {group.name for group in faction.preset_groups}
    assert "3rd Khordad" in presets
    assert "Bavar-373" not in presets
    assert not any(
        "Bavar" in unit or "Meraj" in unit or "Hafez" in unit
        for unit in _irad_units(faction)
    )


@pytest.mark.parametrize(
    "name", ["CH_iran_2025.json", "CH_iran_2020.json", "iran_2015.json"]
)
def test_toggle_off_strips_every_unit(name: str) -> None:
    assert _irad_units(_load(name, pack=False)) == set()


def test_3rd_khordad_battery_always_has_a_telar() -> None:
    """The Alam al-Hoda TELs carry no radar, so a site without a TELAR is blind."""
    layout = LAYOUTS.by_name("3rd Khordad Battery")
    groups = {ug.name: ug for ug in layout.all_unit_groups}
    assert groups["Track Radar"].unit_types == [irad.IRAD_3Khordad_TELAR]
    assert not groups["Track Radar"].optional
    assert groups["Launcher"].unit_types == [irad.IRAD_AlamAlHoda_TEL]


def test_skynet_knows_every_unit() -> None:
    source = SKYNET.read_text(encoding="utf-8")
    # The comms shelter is a Skynet connection node by group, not a SAM type, and
    # the missile launchers are not air defense.
    radars = IRAD_IDS - {"IRAD_Rasool_Comms"} - SSM_IDS
    missing = sorted(uid for uid in radars if f"['{uid}']" not in source)
    assert missing == []


def test_one_bavar_launcher_the_str_guides() -> None:
    """One Bavar-373 launcher since 2026-09-30 (DM call): the TEL, in every launcher slot,
    guided by the STR."""
    layout = LAYOUTS.by_name("Bavar-373 Battery")
    groups = {ug.name: ug for ug in layout.all_unit_groups}
    for slot in ("S-300 Site LN1", "S-300 Site LN2"):
        assert groups[slot].unit_types == [irad.IRAD_Bavar373_LN]
    assert LAUNCHER_TRACKER_PAIRS[irad.IRAD_Bavar373_LN] == (irad.IRAD_Bavar373_STR,)


@pytest.mark.parametrize("old_class", ["IRAD_Bavar373_LN_4B", "IRAD_Bavar373_TELAR"])
def test_an_old_save_loads_the_one_bavar_launcher(old_class: str) -> None:
    unpickler = persistency.MigrationUnpickler(io.BytesIO(b""))
    found = unpickler.find_class(
        "pydcs_extensions.iranairdefensepack.iranairdefensepack", old_class
    )
    assert found is irad.IRAD_Bavar373_LN


@pytest.mark.parametrize(
    "old_name",
    [
        "[IRAD] Bavar-373 TEL (Sayyad-4)",
        "[IRAD] Bavar-373 TEL (Sayyad-4B)",
        "[IRAD] Bavar-373-II TELAR",
    ],
)
def test_an_old_bavar_name_resolves_to_the_tel(old_name: str) -> None:
    assert GroundUnitType.named(old_name).dcs_unit_type is irad.IRAD_Bavar373_LN


@pytest.mark.parametrize(
    "layout_name,slot",
    [
        ("comms", "comms1 C2"),
        ("command_center", "CommandCenter C2"),
        ("Early-Warning Radar", "Early-Warning Radar C2"),
    ],
)
def test_rasool_is_an_iranian_c2_van(layout_name: str, slot: str) -> None:
    """The Rasool shelter fills the C2 van slot at comms, command and EWR sites, so a
    Skynet connection node or command center in an Iranian network is a Rasool."""
    layout = LAYOUTS.by_name(layout_name)
    groups = {ug.name: ug for ug in layout.all_unit_groups}
    assert irad.IRAD_Rasool_Comms in groups[slot].unit_types
