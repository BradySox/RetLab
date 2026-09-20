"""A plugin's early-pass script cannot read its own options at file scope.

``scriptsWorkOrders`` files are each emitted as their own mission-start trigger
BEFORE the plugin's configuration trigger creates ``dcsRetribution.plugins.<id>``
(``LuaPlugin.inject_scripts`` runs before ``inject_configuration``). A file-scope
read of that table in an early-pass script therefore always sees nil, and the
option it feeds is inert in the UI with nothing anywhere saying so.

That is how ``ai_reaction``'s DEBUG toggle shipped inert (found 2026-09-20 while
tracing load order for the freeze investigation). Option-reading scripts belong in
``configurationWorkOrders``, which are bundled after every config trigger; a script
that must load early and still wants its options defers the read into a scheduled
function, as ``c130j_mission_systems.lua`` does.

The check is a column-0 heuristic: a top-level Lua statement starts at the left
margin in every script in this tree, and a read inside a function body is indented.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

PLUGINS = Path("resources/plugins")


def file_scope_own_config_reads(lua: str, plugin_id: str) -> list[int]:
    """1-based lines where an unindented, non-comment statement reads the table."""
    pattern = re.compile(r"dcsRetribution\.plugins\." + re.escape(plugin_id) + r"\b")
    hits = []
    for number, line in enumerate(lua.splitlines(), start=1):
        if not line or line[0].isspace() or line.lstrip().startswith("--"):
            continue
        if pattern.search(line):
            hits.append(number)
    return hits


def _early_pass_scripts() -> list[tuple[str, Path]]:
    found = []
    for manifest in sorted(PLUGINS.glob("*/plugin.json")):
        data = json.loads(manifest.read_text(encoding="utf-8"))
        for order in data.get("scriptsWorkOrders", []):
            if order.get("file"):
                found.append((manifest.parent.name, manifest.parent / order["file"]))
    return found


def test_there_are_early_pass_scripts_to_check() -> None:
    assert len(_early_pass_scripts()) > 3


@pytest.mark.parametrize(
    "plugin_id, script", _early_pass_scripts(), ids=lambda v: getattr(v, "name", v)
)
def test_early_pass_script_never_reads_its_options_at_file_scope(
    plugin_id: str, script: Path
) -> None:
    lua = script.read_text(encoding="utf-8", errors="replace")
    hits = file_scope_own_config_reads(lua, plugin_id)
    assert not hits, (
        f"{script} is a scriptsWorkOrders file but reads dcsRetribution.plugins."
        f"{plugin_id} at file scope (lines {hits}). That table is created by the "
        "config trigger, which runs AFTER every early-pass script, so the read is "
        "always nil and the option is inert. Move the file to "
        "configurationWorkOrders, or defer the read into a scheduled function."
    )


def test_the_heuristic_catches_the_ai_reaction_shape() -> None:
    """The exact shape that shipped inert: a file-scope ``if`` on the table."""
    lua = (
        "local DEBUG = false\n"
        "if dcsRetribution and dcsRetribution.plugins and dcsRetribution.plugins.p then\n"
        "    DEBUG = dcsRetribution.plugins.p.DEBUG == true\n"
        "end\n"
    )
    assert file_scope_own_config_reads(lua, "p") == [2]


def test_the_heuristic_allows_a_deferred_read_and_comments() -> None:
    lua = (
        "-- dcsRetribution.plugins.p is written AFTER this script loads\n"
        "timer.scheduleFunction(function()\n"
        "    local c = dcsRetribution.plugins.p\n"
        "end, nil, timer.getTime())\n"
    )
    assert file_scope_own_config_reads(lua, "p") == []


def test_ai_reaction_is_a_configuration_work_order() -> None:
    data = json.loads(
        (PLUGINS / "ai_reaction" / "plugin.json").read_text(encoding="utf-8")
    )
    config_files = [o.get("file") for o in data.get("configurationWorkOrders", [])]
    assert "ai_reaction.lua" in config_files
    assert not data.get("scriptsWorkOrders")
