"""CH Germany 1.5.0 and the 2026-10-29 mod version bumps (ported from Escalation)."""

from __future__ import annotations

import dataclasses
import io
import json
from pathlib import Path

import pytest
from dcs.unittype import VehicleType
from dcs.vehicles import Armor

from game import persistency
from game.data.radar_db import LAUNCHER_TRACKER_PAIRS, TRACK_RADARS
from game.dcs.groundunittype import GroundUnitType
from game.factions.faction import Faction
from game.theater.start_generator import ModSettings
from pydcs_extensions import germanymilitaryassetspack as demap
from pydcs_extensions import usamilitaryassetspack as usamap

UNITS_DIR = Path("resources/units/ground_units")
PAYLOADS = Path("resources/customized_payloads/F-22A.lua")

GERMAN_VEHICLES = {
    cls.id
    for cls in vars(demap).values()
    if isinstance(cls, type)
    and issubclass(cls, VehicleType)
    and cls.__module__.endswith("germanymilitaryassetspack")
}


@pytest.fixture(autouse=True)
def _init_persistency(tmp_path_factory: pytest.TempPathFactory) -> None:
    persistency.setup(str(tmp_path_factory.mktemp("saved_games")), False, 0)


def _blufor_current(german: bool) -> Faction:
    with Path("resources/factions/blufor_current.json").open(
        encoding="utf-8-sig"
    ) as data:
        faction = Faction.from_dict(json.load(data))
    faction.apply_mod_settings(
        dataclasses.replace(
            ModSettings.all_off(),
            usamilitaryassetspack=True,
            ukmilitaryassetspack=True,
            swedishmilitaryassetspack=True,
            germanymilitaryassetspack=german,
        )
    )
    return faction


def _german_units(faction: Faction) -> set[str]:
    ids = {u.dcs_unit_type.id for u in faction.accessible_units}
    return ids & (GERMAN_VEHICLES | {"CH_F124"})


def test_the_pack_declares_its_24_vehicles() -> None:
    assert len(GERMAN_VEHICLES) == 24


@pytest.mark.parametrize("unit_id", sorted(GERMAN_VEHICLES))
def test_every_vehicle_has_unit_data(unit_id: str) -> None:
    assert (UNITS_DIR / f"{unit_id}.yaml").exists()


def test_kat1_left_the_usa_pack() -> None:
    assert not hasattr(usamap, "CH_MIM104_ANMPQ53_KAT1")


def test_blufor_current_fields_the_german_units_when_ticked() -> None:
    assert "CH_Leopard2A7V" in _german_units(_blufor_current(german=True))
    assert "CH_F124" in _german_units(_blufor_current(german=True))


def test_toggle_off_strips_every_german_unit() -> None:
    assert _german_units(_blufor_current(german=False)) == set()


def test_kat1_radar_guides_the_hemtt_launchers() -> None:
    assert demap.CH_MIM104_ANMPQ53_KAT1 in TRACK_RADARS
    for launcher in (
        usamap.CH_MIM104_M903_PAC2,
        usamap.CH_MIM104_M903_PAC3,
        usamap.CH_MIM104_M903_PAC2_HEMTT,
        usamap.CH_MIM104_M903_PAC3_HEMTT,
    ):
        assert demap.CH_MIM104_ANMPQ53_KAT1 in LAUNCHER_TRACKER_PAIRS[launcher]


@pytest.mark.parametrize(
    "name",
    [
        "CH_MIM104_M901_PAC2_KAT1",
        "CH_MIM104_ANMPQ53_KAT1",
        "CH_MIM104_ECS_KAT1",
        "CH_MIM104_EPP_KAT1",
    ],
)
def test_an_old_save_finds_kat1_in_the_german_pack(name: str) -> None:
    unpickler = persistency.MigrationUnpickler(io.BytesIO(b""))
    found = unpickler.find_class(
        "pydcs_extensions.usamilitaryassetspack.usamilitaryassetspack", name
    )
    assert found is getattr(demap, name)


def test_an_old_save_moves_the_frenchpack_mephisto_to_dcs() -> None:
    unpickler = persistency.MigrationUnpickler(io.BytesIO(b""))
    found = unpickler.find_class(
        "pydcs_extensions.frenchpack.frenchpack", "VAB_MEPHISTO"
    )
    assert found is Armor.VAB_Mephisto
    assert GroundUnitType.named("VAB Mephisto Frenchpack").dcs_unit_type is (
        Armor.VAB_Mephisto
    )


def test_f22_loadouts_use_no_store_the_mod_removed() -> None:
    """2.1.0 removed the combined AMRAAM + IRST pod stores on stations 4 and 8."""
    text = PAYLOADS.read_text(encoding="utf-8")
    assert "_IRST_" not in text
    assert text.count('"{F22_IRST}"') == text.count('["name"] = "Retribution ')
