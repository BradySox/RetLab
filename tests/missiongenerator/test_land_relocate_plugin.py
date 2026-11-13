from __future__ import annotations

from typing import cast

from dcs import Mission
from dcs.action import DoScriptFile
from dcs.triggers import TriggerStart

from game import Game
from game.missiongenerator.luagenerator import LuaGenerator
from game.missiongenerator.missiondata import MissionData
from game.plugins import LuaPluginManager


def _base_work_order_files() -> list[str]:
    base = next(
        p for p in LuaPluginManager.plugins() if p.definition.identifier == "base"
    )
    return [work_order.filename for work_order in base.definition.work_orders]


def test_land_relocate_registered_in_base_plugin() -> None:
    assert "land_relocate.lua" in _base_work_order_files()


def test_land_relocate_loaded_after_moose() -> None:
    files = _base_work_order_files()
    assert files.index("land_relocate.lua") > files.index("moose.lua")


def test_base_plugin_loads_no_mist() -> None:
    # MIST was removed 2026-11-12 (retlab-mist-removal-notes.md); only Skynet's
    # own compatibility file defines a `mist` table now.
    files = _base_work_order_files()
    assert not [f for f in files if "mist" in f.lower()]


def test_land_relocate_injected_as_doscriptfile() -> None:
    mission = Mission()
    # inject_plugins only touches self.mission, self.plugin_scripts and (in the
    # fork's late-init pass) self.mission_data, so the game argument is unused
    # and an empty MissionData suffices.
    generator = LuaGenerator(cast(Game, None), mission, MissionData())

    generator.inject_plugins()

    assert "land_relocate" in generator.plugin_scripts
    load_triggers = [
        trigger
        for trigger in mission.triggerrules.triggers
        if isinstance(trigger, TriggerStart) and trigger.comment == "Load land_relocate"
    ]
    assert len(load_triggers) == 1
    assert any(isinstance(action, DoScriptFile) for action in load_triggers[0].actions)
