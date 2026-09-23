"""A plugin with no checkbox (``skipUI``) is always on.

Vietnam Ops lost its checkbox 2026-09-23: its settings are the gate, and a
second gate only ever failed silently (the §36 lesson). A save or preseed that
stored False must not strand a plugin the UI can no longer switch back on.
"""

from __future__ import annotations

import json
from pathlib import Path

from game.plugins.luaplugin import LuaPlugin
from game.settings import Settings

PLUGINS = Path("resources/plugins")


def _plugin(name: str) -> LuaPlugin:
    plugin = LuaPlugin.from_json(name, PLUGINS / name / "plugin.json")
    assert plugin is not None
    plugin.set_settings(Settings())
    return plugin


def test_a_hidden_plugin_ignores_a_stored_false() -> None:
    plugin = _plugin("vietnamops")
    assert not plugin.show_in_ui
    plugin.set_value(False)
    assert plugin.enabled


def test_a_visible_plugin_still_obeys_its_checkbox() -> None:
    plugin = _plugin("gpsjamming")
    assert plugin.show_in_ui
    plugin.set_value(False)
    assert not plugin.enabled


def test_every_hidden_plugin_defaults_on() -> None:
    """A hidden plugin that shipped default-off would now silently turn on."""
    for path in PLUGINS.glob("*/plugin.json"):
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if data.get("skipUI"):
            assert data.get("defaultValue") is True, path
