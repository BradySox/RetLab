"""Carrier and LHA groups sail the faction's own supply ship in a group of its own."""

import json
from pathlib import Path

import pytest
from dcs.ships import HandyWind, Dry_cargo_ship_1

from game import persistency
from game.armedforces.forcegroup import ForceGroup
from game.factions.faction import Faction
from game.layout import LAYOUTS

SUPPLY_SLOTS = {
    "Carrier Group": "Carrier Group 2",
    "Carrier Group with Frigate escort": "Carrier Group 2",
    "Carrier Strike Group 8": "Carrier Strike Group 8 3",
    "LHA Group": "LHA Group 2",
    "LHA Group with Frigate escort": "LHA Group 2",
}


@pytest.fixture(autouse=True)
def _init_persistency(tmp_path_factory: pytest.TempPathFactory) -> None:
    persistency.setup(str(tmp_path_factory.mktemp("saved_games")), False, 0)


def _faction(name: str, cargo_ship: str) -> Faction:
    data = json.loads(
        Path(f"resources/factions/{name}.json").read_text(encoding="utf-8")
    )
    data["cargo_ship"] = cargo_ship
    return Faction.from_dict(data)


@pytest.mark.parametrize("layout_name", sorted(SUPPLY_SLOTS))
def test_the_supply_ship_is_its_own_dcs_group(layout_name: str) -> None:
    layout = LAYOUTS.by_name(layout_name)
    owners = [
        g.group_name
        for g in layout.groups
        for u in g.unit_groups
        if u.name == SUPPLY_SLOTS[layout_name]
    ]
    assert owners == ["Supply"]
    (slot,) = [u for u in layout.all_unit_groups if u.name == SUPPLY_SLOTS[layout_name]]
    assert slot.faction_supply_ship and slot.optional


@pytest.mark.parametrize(
    "faction_name,cargo_ship,dcs_type",
    [
        ("usn_1985", "Bulker Handy Wind", HandyWind),
        ("russia_2010", "Bulker Yakushev", Dry_cargo_ship_1),
    ],
)
def test_a_carrier_force_group_fields_the_factions_supply_ship(
    faction_name: str, cargo_ship: str, dcs_type: type
) -> None:
    faction = _faction(faction_name, cargo_ship)
    layout = LAYOUTS.by_name("Carrier Group")
    (slot,) = [u for u in layout.all_unit_groups if u.name == "Carrier Group 2"]
    force_group = ForceGroup.for_layout(layout, faction)
    assert force_group.dcs_unit_types_for_group(slot) == [dcs_type]
