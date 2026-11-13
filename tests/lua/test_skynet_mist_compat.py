"""The Skynet MIST compatibility file (resources/plugins/skynetiads/skynet-mist-compat.lua).

RetLab is removing MIST (docs/dev/design/retlab-mist-removal-notes.md). Skynet stays as
vendored and gets this file instead. These tests pin that it defines every mist.* function
the compiled Skynet calls, stays out of the way while the real MIST is loaded, and that
the functions Skynet's timers and shoot-and-scoot lean on behave like MIST's.
"""

from __future__ import annotations

import re
from pathlib import Path

from tests.lua.harness import DcsPluginHarness

REPO = Path(__file__).resolve().parents[2]
COMPAT = "resources/plugins/skynetiads/skynet-mist-compat.lua"
ENGINE = "resources/plugins/skynetiads/skynet-iads-compiled.lua"

# What env.mission carries that the compat reads: one group with one unit, one zone.
_MISSION = """
env.getValueDictByKey = function(key) return key end
env.mission = {
    coalition = { red = { country = { {
        vehicle = { group = { {
            name = "SAM-1", groupId = 7, units = { { name = "SAM-1-u1" } },
        } } },
    } } } },
    triggers = { zones = { { name = "Scoot", x = 1000, y = 2000, radius = 300 } } },
}
"""


def _compat() -> DcsPluginHarness:
    h = DcsPluginHarness()
    h.lua.execute(_MISSION)
    h.load_plugin_script(COMPAT)
    return h


def _mist_calls_in_skynet() -> set[str]:
    source = (REPO / ENGINE).read_text(encoding="utf-8")
    return set(re.findall(r"\bmist\.([A-Za-z0-9_.]+?)(?=[(\[\s,)])", source))


def test_every_mist_function_skynet_calls_is_defined() -> None:
    h = _compat()
    lookup = h.lua.eval(
        "function(path) local v = mist"
        " for part in string.gmatch(path, '[^.]+') do"
        " if type(v) ~= 'table' then return nil end v = v[part] end"
        " return type(v) end"
    )
    missing = sorted(p for p in _mist_calls_in_skynet() if lookup(p) is None)
    assert missing == []


def test_inert_while_the_real_mist_is_loaded() -> None:
    h = DcsPluginHarness()
    h.lua.execute(_MISSION)
    h.lua.execute("mist = { marker = true }")
    h.load_plugin_script(COMPAT)
    assert h.lua.eval("mist.marker") is True
    assert h.lua.eval("mist.scheduleFunction") is None


def test_a_repeating_function_runs_until_removed() -> None:
    h = _compat()
    h.lua.execute(
        "ticks = {}"
        " taskId = mist.scheduleFunction(function(tag) table.insert(ticks, tag) end,"
        " {'x'}, 1, 5)"
    )
    h.advance_to(12)
    assert h.to_python(h.lua.eval("ticks")) == ["x", "x", "x"]
    assert h.lua.eval("mist.removeFunction(taskId)") is True
    h.advance_to(30)
    assert len(h.to_python(h.lua.eval("ticks"))) == 3
    h.assert_no_lua_errors()


def test_an_error_is_logged_and_the_repeat_carries_on() -> None:
    h = _compat()
    h.lua.execute(
        "count = 0 mist.scheduleFunction(function() count = count + 1"
        " error('boom') end, nil, 1, 5)"
    )
    h.advance_to(12)
    assert h.lua.eval("count") == 3
    errors = h.records("errors")
    assert len(errors) == 3 and all("boom" in e for e in errors)


def test_a_scoot_drives_from_the_lead_into_the_zone() -> None:
    h = _compat()
    h.add_group(
        {
            "name": "SAM-1",
            "side": 1,
            "category": 2,
            "units": [{"name": "SAM-1-u1", "type": "Kub 1S91 str", "x": 0, "z": 0}],
        }
    )
    h.lua.execute(
        "mist.groupToRandomZone(Group.getByName('SAM-1'),"
        " { point = { x = 5000, y = 0, z = 5000 }, radius = 1 }, 'Diamond', nil, 80, true)"
    )
    tasks = [t for t in h.records("controllerTasks") if t["taskId"] == "Mission"]
    assert len(tasks) == 1
    # Lead, a nudge, the 50 m offset, then the zone itself (MIST's off-road shape).
    assert tasks[0]["routePoints"] == 4
    assert abs(tasks[0]["routeX"] - 5000) <= 1 and abs(tasks[0]["routeY"] - 5000) <= 1
    assert abs(tasks[0]["routeSpeed"] - 80 / 3.6) < 0.01
    h.assert_no_lua_errors()


def test_a_random_point_stays_inside_the_ring() -> None:
    h = _compat()
    h.lua.execute(
        "worst = { lo = 1e9, hi = 0 } for i = 1, 500 do"
        " local p = mist.getRandPointInCircle({ x = 0, y = 0, z = 0 }, 400, 100)"
        " local d = math.sqrt(p.x ^ 2 + p.y ^ 2)"
        " worst.lo = math.min(worst.lo, d) worst.hi = math.max(worst.hi, d) end"
    )
    assert h.lua.eval("worst.lo") >= 100 and h.lua.eval("worst.hi") <= 400


def test_name_lookups_come_from_the_mission() -> None:
    h = _compat()
    assert h.lua.eval("mist.DBs.groupsByName['SAM-1']") is True
    assert h.lua.eval("mist.DBs.unitsByName['SAM-1-u1']") is True
    assert h.lua.eval("mist.DBs.zonesByName['Scoot'].point.z") == 2000
    assert h.lua.eval("mist.DBs.zonesByName['Scoot'].radius") == 300


def test_skynet_loads_on_the_compat_alone() -> None:
    h = _compat()
    h.set_retribution_config()
    h.load_plugin_script(ENGINE)
    assert h.lua.eval("SkynetIADS ~= nil") is True
    h.assert_no_lua_errors()
