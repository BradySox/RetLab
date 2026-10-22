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

import pytest

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


# The fixes taken from juanjux/Skynet-IADS and Skynet 3.3.0 (2026-10-16).
FAKES = """
Object = Object or {}
Object.Category = Object.Category or { UNIT = 1, WEAPON = 2, STATIC = 3 }
Unit.Category = Unit.Category or {}
Unit.Category.AIRPLANE = 0
Unit.Category.HELICOPTER = 1
Unit.Category.GROUND_UNIT = 2
Unit.Category.SHIP = 3
Unit.Category.STRUCTURE = 4
Weapon.Category.TORPEDO = 4
AI.Option.Air = AI.Option.Air or {
    id = { ROE = 0 }, val = { ROE = { WEAPON_FREE = 0, WEAPON_HOLD = 4 } },
}
mist = mist or {}
mist.scheduleFunction = function() return 1 end
mist.removeFunction = function() end

-- A DCS object: a destroyed one raises from getCategory, as DCS does.
function dcsObject(objectCategory, destroyed)
    local o = { category = objectCategory, destroyed = destroyed }
    return o
end
Object.getCategory = function(o)
    if o.destroyed then error("Unit doesn't exist") end
    return o.category
end

function contactOf(objectCategory, descCategory, destroyed)
    local c = setmetatable({}, { __index = SkynetIADSContact })
    c.typeName = "Thing"
    c.harmState = SkynetIADSContact.HARM_UNKNOWN
    local object = dcsObject(objectCategory, destroyed)
    function c:getDCSRepresentation() return object end
    function c:getDesc() return { category = descCategory } end
    return c
end

-- A radar element with only what goDark, goLive and relocateNow ask of it.
function element()
    local log = { ai = {}, emission = {} }
    local controller = {}
    function controller:setOnOff(on) table.insert(log.ai, on) end
    function controller:setOption() end
    local group = {}
    function group:enableEmission(on) table.insert(log.emission, on) end
    local e = setmetatable({
        aiState = true, pointDefences = {}, goLiveConstraints = {},
        mobilePhase = SkynetIADSSamSite.MOBILE_PHASE_SHOOT,
        dataBaseSupportedTypesCanFireOnMarch = false,
        iads = { getDebugSettings = function() return {} end },
    }, { __index = SkynetIADSSamSite })
    function e:hasWorkingPowerSource() return true end
    function e:isDestroyed() return false end
    function e:getController() return controller end
    function e:getDCSRepresentation() return group end
    function e:getDetectedTargets() return {} end
    function e:hasMissilesInFlight() return false end
    function e:hasRemainingAmmo() return true end
    function e:stopScanningForHARMs() end
    function e:scanForHarms() end
    return e, log
end
"""


def _fixed() -> DcsPluginHarness:
    harness = _harness()
    harness.lua.execute(FAKES)
    return harness


def test_a_destroyed_contact_reads_unknown_instead_of_raising() -> None:
    harness = _fixed()
    assert (
        harness.lua.eval("contactOf(Object.Category.UNIT, 0, true):getTypeName()")
        == "UNKNOWN"
    )
    assert (
        harness.lua.eval("contactOf(Object.Category.UNIT, 0, false):getTypeName()")
        == "Thing"
    )


@pytest.mark.parametrize(
    "object_category,desc_category,airborne",
    [
        ("WEAPON", "Weapon.Category.BOMB", True),  # 3, the same as a ship
        ("WEAPON", "Weapon.Category.MISSILE", True),
        ("WEAPON", "Weapon.Category.ROCKET", True),
        ("WEAPON", "Weapon.Category.SHELL", False),
        ("UNIT", "Unit.Category.AIRPLANE", True),
        ("UNIT", "Unit.Category.HELICOPTER", True),
        ("UNIT", "Unit.Category.SHIP", False),
        ("UNIT", "Unit.Category.GROUND_UNIT", False),
    ],
)
def test_bombs_reach_the_sam_sites_and_ships_do_not(
    object_category: str, desc_category: str, airborne: bool
) -> None:
    harness = _fixed()
    contact = f"contactOf(Object.Category.{object_category}, {desc_category}, false)"
    assert harness.lua.eval(f"SkynetIADS.isAirborneContact({contact})") is airborne


def test_a_radar_that_sees_the_harm_later_still_rolls_its_chance() -> None:
    harness = _fixed()
    harness.lua.execute("""
        detector = SkynetIADSHARMDetection:create({})
        harm = { radars = { "first" } }
        function harm:getAbstractRadarElementsDetected() return self.radars end
    """)
    assert harness.lua.eval("#detector:getNewRadarsThatHaveDetectedContact(harm)") == 1
    harness.lua.execute('table.insert(harm.radars, "second")')
    new = harness.lua.eval("detector:getNewRadarsThatHaveDetectedContact(harm)")
    assert list(new.values()) == ["second"]
    assert harness.lua.eval("#detector:getNewRadarsThatHaveDetectedContact(harm)") == 0


def test_a_first_sighting_does_not_end_the_harm_scan() -> None:
    harness = _fixed()
    harness.lua.execute("""
        informed = {}
        local function contact(name, speed)
            local c = { name = name, speed = speed, state = nil }
            function c:getGroundSpeedInKnots() return self.speed end
            function c:getSimpleAltitudeProfile() return {} end
            function c:getAbstractRadarElementsDetected() return { "radar" } end
            function c:isIdentifiedAsHARM() return self.state == SkynetIADSContact.HARM end
            function c:setHARMState(state) self.state = state end
            function c:getAge() return 0 end
            return c
        end
        detector = SkynetIADSHARMDetection:create({
            getDebugSettings = function() return {} end,
        })
        function detector:getDetectionProbability() return 100 end
        function detector:shallReactToHARM() return true end
        function detector:informRadarsOfHARM(c) table.insert(informed, c.name) end
        detector:setContacts({ contact("new", 0), contact("harm", 1200) })
        detector:evaluateContacts()
    """)
    assert list(harness.lua.eval("informed").values()) == ["harm"]


def test_a_site_hiding_from_a_harm_turns_its_ai_off_until_it_goes_live() -> None:
    harness = _fixed()
    harness.lua.execute("""
        site, log = element()
        site.harmSilenceID = 1
        site:goDark()
        site.harmSilenceID = nil
        site:goLive()
    """)
    assert list(harness.lua.eval("log.ai").values()) == [False, True]
    assert list(harness.lua.eval("log.emission").values()) == [False, True]


def test_a_mobile_site_hiding_from_a_harm_can_still_drive() -> None:
    harness = _fixed()
    harness.lua.execute("""
        aiAtMove = nil
        site, log = element()
        site.harmSilenceID = 1
        site:goDark()
        land.getSurfaceType = function() return 1 end
        land.SurfaceType = { ROAD = 3 }
        mist.groupToRandomZone = function() aiAtMove = log.ai[#log.ai] end
        site:relocateNow({ point = { x = 0, y = 0, z = 0 } })
    """)
    assert harness.lua.eval("aiAtMove") is True
    assert list(harness.lua.eval("log.emission").values()) == [False]


# Test 63 (2026-10-21): a Box Spring 82 NM away, behind the Taurus, was the SA-11's only
# cover. Skynet counted it by range alone, so the site waited dark all mission for a
# track that radar never got.
COVER = """
lineOfSight = {}
land.isVisible = function(from, to)
    table.insert(lineOfSight, { from = from.y, to = to.y })
    return not DcsHarness.losBlocked
end

local function radarAt(x, y, z)
    local radar = {}
    function radar:isExist() return true end
    function radar:getDCSRepresentation()
        return { getPosition = function() return { p = { x = x, y = y, z = z } } end }
    end
    return radar
end

function cover(parentClass)
    local parent = setmetatable({}, parentClass)
    parent.children = {}
    function parent:getRadars() return { radarAt(0, 1157, 0) } end
    function parent:addChildRadar(c) table.insert(self.children, c) end
    local site = setmetatable({}, SkynetIADSSamSite)
    site.parents = {}
    function site:getRadars() return { radarAt(152000, 5, 0) } end
    function site:addParentRadar(p) table.insert(self.parents, p) end
    SkynetIADS.buildRadarAssociation(nil, parent, site)
    return #parent.children + #site.parents
end
"""


def _cover() -> DcsPluginHarness:
    harness = _fixed()
    harness.lua.execute(COVER)
    return harness


def test_a_ground_radar_that_sees_over_the_site_covers_it() -> None:
    harness = _cover()
    harness.lua.execute("DcsHarness.terrainHeight = 200")
    assert harness.lua.eval("cover(SkynetIADSEWRadar)") == 2
    sight = harness.lua.eval("lineOfSight[1]")
    assert sight["from"] == 1167  # the radar plus its mast
    assert sight["to"] == 3248  # 10,000 ft over the ground at the site


def test_a_ground_radar_behind_terrain_leaves_the_site_to_fight_alone() -> None:
    harness = _cover()
    harness.lua.execute("DcsHarness.losBlocked = true")
    assert harness.lua.eval("cover(SkynetIADSEWRadar)") == 0
    assert harness.lua.eval("cover(SkynetIADSSamSite)") == 0


def test_an_awacs_covers_by_range_alone() -> None:
    harness = _cover()
    harness.lua.execute("DcsHarness.losBlocked = true")
    assert harness.lua.eval("cover(SkynetIADSAWACSRadar)") == 2
    assert harness.lua.eval("#lineOfSight") == 0
