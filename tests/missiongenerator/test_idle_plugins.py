from __future__ import annotations

import json
import re
from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from game.missiongenerator import luagenerator
from game.missiongenerator.idleplugins import (
    DATA_GATED_PLUGINS,
    MissionWork,
    idle_reason,
)
from game.missiongenerator.luagenerator import LuaGenerator

PLUGINS = Path("resources/plugins")

BUSY = MissionWork(
    data_keys=frozenset(DATA_GATED_PLUGINS.values()),
    carriers=1,
    ew_c130j_flights=1,
    csar_active=True,
    iads_nodes=5,
    logistics_flights=1,
    jtacs=1,
)
IDLE = MissionWork(
    data_keys=frozenset(),
    carriers=0,
    ew_c130j_flights=0,
    csar_active=False,
    iads_nodes=0,
    logistics_flights=0,
    jtacs=0,
)

ALWAYS_LOADED = ("base", "splashdamage3", "ai_reaction", "intercept", "profiler")


def test_a_busy_mission_loads_every_plugin() -> None:
    for plugin_id in json.loads((PLUGINS / "plugins.json").read_text()):
        assert idle_reason(plugin_id, BUSY) is None, plugin_id


@pytest.mark.parametrize("plugin_id", ALWAYS_LOADED)
def test_core_plugins_load_even_in_an_idle_mission(plugin_id: str) -> None:
    assert idle_reason(plugin_id, IDLE) is None


@pytest.mark.parametrize(
    "plugin_id, busy_field",
    [
        ("airboss", {"carriers": 0}),
        ("c130j", {"ew_c130j_flights": 0}),
        ("opscsar", {"csar_active": False}),
        ("skynetiads", {"iads_nodes": 0}),
        ("lotatc", {"iads_nodes": 0}),
    ],
)
def test_each_rule_turns_off_only_its_plugin(
    plugin_id: str, busy_field: dict[str, object]
) -> None:
    work = replace(BUSY, **busy_field)  # type: ignore[arg-type]
    assert idle_reason(plugin_id, work) is not None
    assert idle_reason("base", work) is None


def test_ctld_stays_for_a_jtac_or_a_transport_flight() -> None:
    assert idle_reason("ctld", replace(IDLE, jtacs=1)) is None
    assert idle_reason("ctld", replace(IDLE, logistics_flights=1)) is None
    assert idle_reason("ctld", IDLE) is not None


@pytest.mark.parametrize("plugin_id, table", sorted(DATA_GATED_PLUGINS.items()))
def test_data_gated_plugin_reads_its_table(plugin_id: str, table: str) -> None:
    """The script must gate on the table the rule checks, and Python must write it."""
    assert plugin_id in json.loads((PLUGINS / "plugins.json").read_text())
    lua = "".join(
        p.read_text(encoding="utf-8") for p in (PLUGINS / plugin_id).glob("*.lua")
    )
    assert f"dcsRetribution.{table}" in lua
    writers = [
        p
        for p in Path("game").rglob("*.py")
        if re.search(rf'add_item\("{table}"\)', p.read_text(encoding="utf-8"))
    ]
    assert writers, f"nothing writes dcsRetribution.{table}"


def test_inject_plugins_leaves_out_an_idle_plugin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    airboss, base = MagicMock(identifier="airboss"), MagicMock(identifier="base")
    airboss.enabled = base.enabled = True
    monkeypatch.setattr(
        luagenerator.LuaPluginManager, "plugins", staticmethod(lambda: [airboss, base])
    )
    gen = LuaGenerator.__new__(LuaGenerator)
    gen.mission = MagicMock()
    gen.plugin_scripts = []
    gen._deferred_plugin_loads = []
    gen._mission_work = IDLE
    gen.inject_plugins()
    airboss.inject_scripts.assert_not_called()
    base.inject_scripts.assert_called_once()


def test_inject_plugins_without_mission_data_loads_everything(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    airboss = MagicMock(identifier="airboss")
    airboss.enabled = True
    monkeypatch.setattr(
        luagenerator.LuaPluginManager, "plugins", staticmethod(lambda: [airboss])
    )
    gen = LuaGenerator.__new__(LuaGenerator)
    gen.mission = MagicMock()
    gen.plugin_scripts = []
    gen._deferred_plugin_loads = []
    gen.inject_plugins()
    airboss.inject_scripts.assert_called_once()
