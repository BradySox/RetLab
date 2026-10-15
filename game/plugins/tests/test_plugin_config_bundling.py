from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from game.missiongenerator.luagenerator import LuaGenerator
from game.plugins.luaplugin import LuaPlugin

# --- Bundled plugin-config loads (the DCS dropped-trigger guard) --------------
#
# DCS silently drops some mission-start DoScriptFile triggers on a heavy mission
# (Red Tide: the vietnamops config load never ran while
# adjacent, identically-wired ones did). Plugin config loads are therefore
# deferred and bundled into one trigger.


def _bundling_gen() -> tuple[LuaGenerator, MagicMock]:
    """Return a real LuaGenerator with a mock mission (returned separately so the
    mock's assert_* helpers stay visible to mypy)."""
    gen = LuaGenerator.__new__(LuaGenerator)
    mission = MagicMock()
    gen.mission = mission
    gen.plugin_scripts = []
    gen._deferred_plugin_loads = []
    return gen, mission


def test_deferred_config_load_queues_without_its_own_trigger() -> None:
    gen, mission = _bundling_gen()
    gen.inject_plugin_script(
        "vietnamops", "vietnamops-config.lua", "vietnamops-config", defer=True
    )
    # Resource is registered (map ordering stays stable) but NO trigger yet.
    mission.map_resource.add_resource_file.assert_called_once()
    mission.triggerrules.triggers.append.assert_not_called()
    assert len(gen._deferred_plugin_loads) == 1


def test_non_deferred_load_still_emits_its_own_trigger() -> None:
    gen, mission = _bundling_gen()
    gen.inject_plugin_script("vietnamops", "vietnamops-config.lua", "vietnamops-config")
    mission.triggerrules.triggers.append.assert_called_once()
    assert gen._deferred_plugin_loads == []


def test_flush_bundles_all_deferred_loads_into_one_trigger() -> None:
    gen, mission = _bundling_gen()
    for ident, script, mnem in (
        ("vietnamops", "vietnamops-config.lua", "vietnamops-config"),
        ("gpsjamming", "gpsjamming-config.lua", "gpsjamming-config"),
    ):
        gen.inject_plugin_script(ident, script, mnem, defer=True)
    mission.triggerrules.triggers.append.assert_not_called()
    gen.flush_deferred_plugin_scripts()
    # Exactly one trigger carrying both loads, in queue order.
    mission.triggerrules.triggers.append.assert_called_once()
    trigger = mission.triggerrules.triggers.append.call_args.args[0]
    assert len(trigger.actions) == 2
    assert gen._deferred_plugin_loads == []


def test_flush_is_a_noop_when_nothing_deferred() -> None:
    gen, mission = _bundling_gen()
    gen.flush_deferred_plugin_scripts()
    mission.triggerrules.triggers.append.assert_not_called()


def test_inject_configuration_defers_the_config_script() -> None:
    """The wiring: a real plugin's config work order must load with defer=True."""
    from game.plugins.luaplugin import LuaPluginDefinition

    definition = LuaPluginDefinition.from_json(
        "gpsjamming", Path("resources/plugins/gpsjamming/plugin.json")
    )
    plugin = LuaPlugin.__new__(LuaPlugin)
    plugin.definition = definition
    plugin.identifier = "gpsjamming"
    gen = MagicMock()
    plugin.inject_configuration(gen)
    gen.inject_plugin_script.assert_called_once()
    assert gen.inject_plugin_script.call_args.kwargs.get("defer") is True
