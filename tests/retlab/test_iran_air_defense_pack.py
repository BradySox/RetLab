"""RetLab Iran Air Defense Pack: 3rd Khordad and Bavar-373.

The type ids here are the contract with the mod's Database lua (see
docs/dev/design/retlab-iran-air-defense-pack-notes.md). These tests hold the
Python side to it: every id has unit data, the toggle strips every id, the
presets reach only era-correct factions, and Skynet knows every radar.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest
from dcs.unittype import VehicleType

from game import persistency
from game.factions.faction import Faction
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


def test_the_contract_has_twelve_units() -> None:
    assert len(IRAD_IDS) == 12


@pytest.mark.parametrize("unit_id", sorted(IRAD_IDS))
def test_every_unit_has_unit_data(unit_id: str) -> None:
    assert (UNITS_DIR / f"{unit_id}.yaml").is_file()


def test_modern_iran_fields_both_systems() -> None:
    faction = _load("CH_iran_2020.json", pack=True)
    presets = {group.name for group in faction.preset_groups}
    assert {"3rd Khordad", "Bavar-373", "Bavar-373-II"} <= presets
    assert _irad_units(faction) == IRAD_IDS


def test_iran_2015_gets_3rd_khordad_only() -> None:
    """Bavar-373 entered service in 2019; a 2015 faction must not field it."""
    faction = _load("iran_2015.json", pack=True)
    presets = {group.name for group in faction.preset_groups}
    assert "3rd Khordad" in presets
    assert "Bavar-373" not in presets
    assert "Bavar-373-II" not in presets
    assert not any(
        "Bavar" in unit or "Meraj" in unit or "Hafez" in unit
        for unit in _irad_units(faction)
    )


@pytest.mark.parametrize("name", ["CH_iran_2020.json", "iran_2015.json"])
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
    # The comms shelter is a Skynet connection node by group, not a SAM type.
    radars = IRAD_IDS - {"IRAD_Rasool_Comms"}
    missing = sorted(uid for uid in radars if f"['{uid}']" not in source)
    assert missing == []


def test_bavar_ii_launchers_are_the_telars() -> None:
    """Every Bavar-373-II launcher slot is a TELAR, and the one STR is not doubled:
    the TELARs are the guidance redundancy."""
    layout = LAYOUTS.by_name("Bavar-373-II Battery (Single Radar)")
    groups = {ug.name: ug for ug in layout.all_unit_groups}
    for slot in ("S-300 Site LN1", "S-300 Site LN2"):
        assert groups[slot].unit_types == [irad.IRAD_Bavar373_TELAR]
    assert groups["S-300 Site TR"].unit_count == [1]


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
