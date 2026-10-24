"""Headless runtime check for train_losses.lua (features doc §123).

DCS sees a train as one unit and fires no dead event when it dies, so the script
polls its health. A dead train reports every cargo name once; a live one reports
nothing.
"""

from __future__ import annotations

from typing import Any

from tests.lua.harness import DcsPluginHarness

PLUGIN = "resources/plugins/base/train_losses.lua"


def _setup(harness: DcsPluginHarness) -> None:
    harness.lua.execute(
        "dead_events = {} dirty_state = false "
        "logger = { info = function(self, msg) end }"
    )
    harness.add_group(
        {
            "name": "Train 001",
            "side": 2,
            "category": 2,
            "units": [{"name": "Train 001-1", "life": 5}],
        }
    )
    harness.lua.globals().retlab_trains = harness.to_lua(
        {"Train 001-1": ["Train 001-1 cargo #1", "Train 001-1 cargo #2"]}
    )
    harness.load_plugin_script(PLUGIN)
    harness.assert_no_lua_errors()


def _dead_events(harness: DcsPluginHarness) -> list[Any]:
    events = harness.to_python(harness.lua.eval("dead_events"))
    if isinstance(events, dict):
        return [events[k] for k in sorted(events)]
    return list(events or [])


def test_a_live_train_reports_nothing() -> None:
    harness = DcsPluginHarness()
    _setup(harness)
    harness.advance_to(60)
    harness.assert_no_lua_errors()
    assert _dead_events(harness) == []


def test_a_dead_train_reports_its_cargo_once() -> None:
    harness = DcsPluginHarness()
    _setup(harness)
    harness.advance_to(10)
    harness.update_unit("Train 001", {"life": -745})
    harness.advance_to(60)
    harness.assert_no_lua_errors()
    assert _dead_events(harness) == ["Train 001-1 cargo #1", "Train 001-1 cargo #2"]
    assert harness.lua.eval("dirty_state") is True
