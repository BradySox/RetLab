"""Headless runtime check for silent_atc.lua (features doc §132).

Every land airfield and FARP is set silent at mission start; a carrier is not.
"""

from __future__ import annotations

from tests.lua.harness import DcsPluginHarness

PLUGIN = "resources/plugins/base/silent_atc.lua"

_AIRBASES = """
silent_calls = {}
Airbase = Airbase or {}
Airbase.Category = { AIRDROME = 0, HELIPAD = 1, SHIP = 2 }
local function base(name, category)
    return {
        getName = function(self) return name end,
        getDesc = function(self) return { category = category } end,
        setRadioSilentMode = function(self, silent) silent_calls[name] = silent end,
    }
end
world.getAirbases = function()
    return {
        base("Ramat David", Airbase.Category.AIRDROME),
        base("FARP Alpha", Airbase.Category.HELIPAD),
        base("CVN-73 George Washington", Airbase.Category.SHIP),
    }
end
"""


def test_land_towers_go_silent_and_carriers_do_not() -> None:
    harness = DcsPluginHarness()
    harness.lua.execute(_AIRBASES)
    harness.load_plugin_script(PLUGIN)
    harness.assert_no_lua_errors()
    calls = harness.to_python(harness.lua.eval("silent_calls"))
    assert calls == {"Ramat David": True, "FARP Alpha": True}


def test_no_airbase_api_is_a_no_op() -> None:
    harness = DcsPluginHarness()
    harness.lua.execute("world.getAirbases = nil")
    harness.load_plugin_script(PLUGIN)
    harness.assert_no_lua_errors()
