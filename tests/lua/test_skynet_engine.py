"""Headless checks on the compiled Skynet engine itself, not the config bridge.

Test 38 (2026-09-22): a red Mi-24P crashed at t=347 and a blue radar kept
reporting its wreck. `target.object` was non-nil but no longer existed, so
`getTypeName` raised "Static doesn't exist" inside `getDetectedTargets` -- 174
times, every contact cycle for the rest of the mission -- and each raise
aborted `SkynetIADS.evaluateContacts` part-way, so no SAM was cued or sent
dark by that network again.

The real compiled file is loaded; only the radar element around the method is
faked, since a live one needs a DCS world.
"""

from __future__ import annotations

from tests.lua.harness import DcsPluginHarness

ENGINE = "resources/plugins/skynetiads/skynet-iads-compiled.lua"

RADAR = """
Controller = Controller or {}
Controller.Detection = Controller.Detection or { RADAR = 4 }
timer.getAbsTime = timer.getAbsTime or function() return timer.getTime() end

local function wreck()
    local o = {}
    function o:isExist() return false end
    function o:getTypeName() error("Static doesn't exist") end
    function o:getName() error("Static doesn't exist") end
    return o
end

local function bandit()
    local o = {}
    function o:isExist() return true end
    function o:getTypeName() return "MiG-29A" end
    function o:getName() return "Bandit" end
    function o:getPosition() return { p = { x = 0, y = 5000, z = 0 } } end
    return o
end

-- refresh reads velocity and altitude through MIST; the guard sits before it.
SkynetIADSContact.refresh = function() end

function detect(objects)
    local targets = {}
    for _, kind in ipairs(objects) do
        table.insert(targets, { object = (kind == "wreck") and wreck() or bandit() })
    end
    local radar = {
        cachedTargetsCurrentAge = -1000, cachedTargetsMaxAge = 1,
        goLiveTime = -1000, noCacheActiveForSecondsAfterGoLive = 0,
    }
    function radar:hasWorkingPowerSource() return true end
    function radar:isDestroyed() return false end
    function radar:isTargetInRange() return true end
    function radar:getController()
        return { getDetectedTargets = function() return targets end }
    end
    local ok, result = pcall(SkynetIADSAbstractRadarElement.getDetectedTargets, radar)
    if not ok then return "error: " .. tostring(result) end
    local names = {}
    for _, contact in ipairs(result) do table.insert(names, contact:getName()) end
    return table.concat(names, ",")
end
"""


def _harness() -> DcsPluginHarness:
    harness = DcsPluginHarness()
    harness.set_retribution_config()
    harness.load_plugin_script(ENGINE)
    harness.lua.execute(RADAR)
    return harness


def test_a_wreck_the_radar_still_reports_is_skipped() -> None:
    harness = _harness()
    assert harness.lua.eval('detect({"wreck"})') == ""


def test_a_wreck_does_not_hide_the_live_contacts_behind_it() -> None:
    harness = _harness()
    assert harness.lua.eval('detect({"bandit", "wreck", "bandit"})') == "Bandit,Bandit"
