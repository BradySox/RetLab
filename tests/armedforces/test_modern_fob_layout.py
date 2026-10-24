"""Factions from 2000 on render the HESCO-walled ``modern_fob`` layout; older factions
keep the stock ``fob1``. Same opt-in mechanism as ``vietnam_fob``.
"""

import pytest

from game import persistency
from game.armedforces.armedforces import ArmedForces
from game.armedforces.forcegroup import ForceGroup
from game.data.groups import GroupTask
from game.factions.factionloader import FactionLoader
from game.layout import LAYOUTS


@pytest.fixture(autouse=True)
def _init_persistency(tmp_path_factory: pytest.TempPathFactory) -> None:
    persistency.setup(str(tmp_path_factory.mktemp("saved_games")), False, 0)


def _fob_layout_names(faction_name: str) -> set[str]:
    armed_forces = ArmedForces(FactionLoader()[faction_name])
    names: set[str] = set()
    for group in armed_forces.groups_for_task(GroupTask.FOB):
        names.update(layout.name for layout in group.layouts)
    return names


@pytest.mark.parametrize("faction_name", ["USA 2020", "Russia 2010", "China 2020"])
def test_modern_factions_render_only_modern_fob(faction_name: str) -> None:
    assert _fob_layout_names(faction_name) == {"modern_fob"}


@pytest.mark.parametrize("faction_name", ["USA 1990", "Russia 1990"])
def test_older_factions_keep_stock_fob(faction_name: str) -> None:
    assert _fob_layout_names(faction_name) == {"fob1"}


def test_modern_fob_is_non_generic() -> None:
    layout = LAYOUTS.by_name("modern_fob")
    assert not layout.generic


def test_modern_fob_keeps_fob1_buildings_and_adds_the_wall() -> None:
    faction = FactionLoader()["USA 2020"]
    layout = LAYOUTS.by_name("modern_fob")
    assert layout.usable_by_faction(faction)
    group = ForceGroup.for_layout(layout, faction)
    static_ids = {static.id for static in group.statics}
    assert {".Command Center", "Barracks 2", "Garage small B"} <= static_ids
    assert {"HESCO_wallperimeter_1", "HESCO_watchtower_2", "Tent05"} <= static_ids
    total = sum(len(unit_group.layout_units) for unit_group in layout.all_unit_groups)
    assert 50 <= total <= 70
