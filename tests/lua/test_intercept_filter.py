"""Intercept (QRA) on MOOSE's EASYGCICAP.

Runs the real ``resources/plugins/intercept/intercept-config.lua`` against the
harness with a recording fake of the EASYGCICAP / AIRWING / SQUADRON surface it
touches (the bundled Moose.lua models real DCS AI and cannot run headless).
``test_moose_classes.py`` separately checks that every MOOSE class the plugins
use is still in the bundle: the fake below cannot catch a bundle that lost
EASYGCICAP, the way #1501 lost AI_A2A_DISPATCHER.

Pinned here:

* the detection prefixes are escaped (Retribution IADS names carry "(" ")");
* the side's AWACS is a detection source; no radar and no AWACS = no GCI;
* a base without its anchor static fields no QRA and breaks no other base;
* QRA reacts only to air-to-ground raids, one jet per attacker, at most 4;
* squadrons are single-jet, intercept-only, air-start, with the template's
  skill and modex;
* the air start is reshaped: field elevation + 2,500 ft, 300 kt, stacked;
* the ambush and forward-defense leash cancels an intercept that strays;
* the survivor count is the squadron's asset count.

What the fake cannot model: INTEL's detection cycle, the Ops flight itself and
the warehouse. That is the in-game pass (checklist A5).
"""

from __future__ import annotations

from typing import Any

from tests.lua.harness import REPO_ROOT, DcsPluginHarness

PLUGIN = "resources/plugins/intercept/intercept-config.lua"

BUILD_DELAY_S = 5  # intercept-config.lua BUILD_DELAY; EASYGCICAP is built then

#: Real Retribution IADS group-name shapes: every one carries "(" / ")".
PAREN_NAMES = [
    "0041 | LION (EWR)",
    "0035 | ELEPHANT (Naval Two Ship)",
    "0114 | LORIKEET (S-300)",
    "0178 | OPOSSUM (Patriot)",
]

# A recording fake of the Ops classes intercept-config.lua touches. EASYGCICAP
# records its settings and keeps "originals" of _AddAirwing and _AssignIntercept
# so the plugin's per-instance overrides can be exercised. InterceptTest.start
# plays EASYGCICAP:onafterStart: build each wing, then each squadron.
MOOSE_FAKE = """
InterceptTest = { gcis = {}, statics = {}, templates = {}, spawned = {} }

STATIC = {}
function STATIC.FindByName(_, name, raise)
    if InterceptTest.statics[name] then
        return { name = name }
    end
    return nil
end

ZONE_RADIUS = {}
function ZONE_RADIUS:New(name, vec2, radius, doNotRegister)
    return { name = name, radius = radius }
end

AUFTRAG = { Type = { INTERCEPT = "Intercept", ALERT5 = "Alert5" } }

_DATABASE = {}
function _DATABASE:GetGroupTemplate(name)
    return InterceptTest.templates[name]
end
function _DATABASE:Spawn(template)
    table.insert(InterceptTest.spawned, template)
    return { name = template.name }
end
InterceptTest.realSpawn = _DATABASE.Spawn

SQUADRON = {}
function SQUADRON:New(template, n, name)
    local sq = { template = template, n = n, name = name, caps = {} }
    function sq:SetGrouping(g) self.grouping = g; return self end
    function sq:AddMissionCapability(c) self.caps = c; return self end
    function sq:SetTakeoffAir() self.takeoff = "air"; return self end
    function sq:SetFuelLowThreshold(f) return self end
    function sq:SetTurnoverTime(a, b) return self end
    function sq:SetMissionRange(r) self.range = r; return self end
    function sq:SetSkill(s) self.skill = s; return self end
    function sq:SetModex(m) self.modex = m; return self end
    function sq:CountAssets() return self.n end
    return sq
end

local function new_wing(name)
    local wing = { name = name, squadrons = {}, missionqueue = {}, stock = 4 }
    function wing:AddSquadron(sq) self.squadrons[sq.name] = sq end
    function wing:NewPayload(template, n, types, perf) self.payload = template end
    function wing:CountAssets(inStock) return self.stock end
    function wing:GetSquadron(name) return self.squadrons[name] end
    function wing:_SpawnAssetAircraft(alias, asset, request, parking, uncontrolled, late)
        return _DATABASE:Spawn(asset.template)
    end
    return wing
end

EASYGCICAP = {}
function EASYGCICAP:New(alias, airbase, coalition, ewr)
    local gci = {
        alias = alias, coalitionname = coalition, EWRName = ewr,
        wings = {}, bases = { airbase }, squads = {}, accept = {},
        overhead = 0.75, maxinterceptsize = 2, missionrange = 100,
        maintenancetime = 5, repairtime = 10, assignCalls = {},
        Intel = {},
    }
    function gci.Intel:ClusterCountUnits(cluster) return cluster.units end
    function gci:AddAirwing(name, alias) table.insert(self.bases, name) end
    function gci:SetDefaultTakeOffType(t) self.takeoff = t end
    function gci:SetDefaultNumberAlert5Standby(n) self.alert5 = n end
    function gci:SetDefaultEngageRange(r) self.engagerange = r end
    function gci:SetDefaultMissionRange(r) self.missionrange = r end
    function gci:SetFuelLow(p) self.fuellow = p end
    function gci:AddAcceptZone(z) table.insert(self.accept, z) end
    function gci:AddSquadron(template, name, base, n, skill, modex)
        table.insert(self.squads, { template, name, base, n, skill, modex })
    end
    function gci:_AddAirwing(name, alias)
        self.wings[name] = { new_wing(name), {}, name }
        return self
    end
    function gci:_AddSquadron() error("MOOSE's own _AddSquadron must be replaced") end
    function gci:_AssignIntercept(cluster)
        table.insert(self.assignCalls, {
            overhead = self.overhead, size = self.maxinterceptsize,
        })
    end
    table.insert(InterceptTest.gcis, gci)
    return gci
end

function InterceptTest.start(gci)
    for _, name in ipairs(gci.bases) do
        gci:_AddAirwing(name, "QRA " .. name)
    end
    for _, s in ipairs(gci.squads) do
        gci:_AddSquadron(s[1], s[2], s[3], s[4], s[5], s[6])
    end
end

-- Moose SET_GROUP:FilterPrefixes matcher: string.find with the prefix as a Lua
-- PATTERN, only "-" pre-escaped.
function InterceptTest.mooseMatches(name, prefix)
    return string.find(name, (prefix:gsub("%-", "%%-")), 1) ~= nil
end

-- An INTEL cluster: Contacts carry the group name.
function InterceptTest.cluster(groupNames, units)
    local contacts = {}
    for _, n in ipairs(groupNames) do
        contacts[#contacts + 1] = { groupname = n }
    end
    return { Contacts = contacts, units = units or #groupNames }
end

-- An intercept mission with one flight group at the given distance from home.
function InterceptTest.mission(distance)
    local m = { type = AUFTRAG.Type.INTERCEPT, cancelled = false }
    function m:IsOver() return self.cancelled end
    function m:Cancel() self.cancelled = true end
    function m:GetOpsGroups()
        local og = {}
        function og:IsAlive() return true end
        function og:GetCoordinate()
            return { Get2DDistance = function(_, home) return distance end }
        end
        return { og }
    end
    return m
end

function InterceptTest.airStart(kind)
    return { template = { name = "QRA",
        route = { points = { { type = kind, alt = 1500, speed = 0 } } },
        units = { { alt = 1500, speed = 0 } } } }
end
"""


def _intercept_record(
    airbase: str, squadron_id: str, **overrides: str
) -> dict[str, str]:
    """One dcsRetribution.Intercept record (add_key_value emits all strings)."""
    record = {
        "squadronId": squadron_id,
        "squadronName": "Test Squadron",
        "airbaseName": airbase,
        "templatePrefix": f"Intercept|{airbase}|{squadron_id}",
        "coalition": "BLUE",
        "resourceCount": "3",
        "grouping": "2",
        "engagementRangeNm": "38",
        "gciMaxRadiusNm": "60",
        "ambushPosture": "false",
        "disengageRadiusNm": "0",
    }
    record.update(overrides)
    return record


def _load(
    harness: DcsPluginHarness,
    ewr_names: list[str],
    awacs: list[dict[str, str]] | None = None,
    records: list[dict[str, str]] | None = None,
    anchored: tuple[str, ...] = ("Test AFB",),
) -> Any:
    """Load the real plugin with BLUE alert bases and the given EWR net."""
    records = records or [_intercept_record("Test AFB", "sq-1")]
    for base in sorted({r["airbaseName"] for r in records}):
        harness.add_airbase({"name": base, "x": 0.0, "z": 0.0, "elev": 100.0})
    for name in ewr_names:
        harness.add_group(
            {
                "name": name,
                "side": harness.side.BLUE,
                "category": harness.category.GROUND,
                "units": [{"name": f"{name} radar", "type": "FPS-117"}],
            }
        )
    harness.set_retribution_config(plugin_options={})
    config = harness.lua.globals().dcsRetribution
    config.Intercept = harness.to_lua({"BLUE": records})
    config.IADS = harness.to_lua(
        {"BLUE": {"Ewr": [{"dcsGroupName": name} for name in ewr_names]}}
    )
    if awacs is not None:
        config.AWACs = harness.to_lua(awacs)
    harness.lua.execute(MOOSE_FAKE)
    test_globals = harness.lua.globals().InterceptTest
    for base in anchored:
        test_globals.statics[base] = True
    for record in records:
        test_globals.templates[record["templatePrefix"]] = harness.to_lua(
            {"units": [{"skill": "Excellent", "onboard_num": "051"}]}
        )
    script = (REPO_ROOT / PLUGIN).read_text(encoding="utf-8")
    # The chunk's return value is the plugin's test hook (inert in DCS, which
    # discards it); harness.load_plugin_script would throw it away.
    return harness.lua.execute(script)


def _built(harness: DcsPluginHarness) -> Any:
    harness.advance_to(BUILD_DELAY_S + 1)
    harness.assert_no_lua_errors()
    test_globals = harness.lua.globals().InterceptTest
    gci = test_globals.gcis[1]
    test_globals.start(gci)
    harness.assert_no_lua_errors()
    return gci


def test_escaped_prefix_matches_where_raw_fails() -> None:
    harness = DcsPluginHarness()
    module = _load(harness, ewr_names=list(PAREN_NAMES))
    matches = harness.lua.globals().InterceptTest.mooseMatches
    for name in PAREN_NAMES:
        assert not matches(name, name), f"raw prefix unexpectedly matched: {name}"
        assert matches(name, module.pattern_escape(name)), f"no match: {name}"


def test_escape_leaves_dash_for_moose() -> None:
    harness = DcsPluginHarness()
    module = _load(harness, ewr_names=list(PAREN_NAMES))
    assert (
        module.pattern_escape("0114 | LORIKEET (S-300)") == "0114 | LORIKEET %(S-300%)"
    )


def test_the_detection_list_is_the_escaped_iads_network() -> None:
    harness = DcsPluginHarness()
    _load(harness, ewr_names=["0041 | LION (EWR)", "0114 | LORIKEET (S-300)"])
    gci = _built(harness)
    assert harness.to_python(gci.EWRName) == [
        "0041 | LION %(EWR%)",
        "0114 | LORIKEET %(S-300%)",
    ]
    assert gci.coalitionname == "blue"


def test_a_wiped_out_radar_network_simply_stops_scrambling() -> None:
    harness = DcsPluginHarness()
    _load(harness, ewr_names=[])
    harness.advance_to(BUILD_DELAY_S + 1)
    harness.assert_no_lua_errors()
    assert not harness.to_python(harness.lua.globals().InterceptTest.gcis)


def test_a_side_with_an_awacs_and_no_ground_radar_still_scrambles() -> None:
    """Test 55: two E-2Cs, no EWR, eight alert jets that never launched."""
    harness = DcsPluginHarness()
    _load(
        harness,
        ewr_names=[],
        awacs=[
            {"dcsGroupName": "Vaziani AEW&C|3|E-2C|", "coalition": "blue"},
            {"dcsGroupName": "Anapa AEW&C|25|A-50|", "coalition": "red"},
        ],
    )
    gci = _built(harness)
    assert harness.to_python(gci.EWRName) == ["Vaziani AEW&C|3|E-2C|"]


def test_the_awacs_joins_the_ground_radars_once() -> None:
    harness = DcsPluginHarness()
    _load(
        harness,
        ewr_names=["0041 | LION (EWR)"],
        awacs=[
            {"dcsGroupName": "Magic", "coalition": "blue"},
            {"dcsGroupName": "Magic", "coalition": "blue"},
        ],
    )
    gci = _built(harness)
    assert harness.to_python(gci.EWRName) == ["0041 | LION %(EWR%)", "Magic"]


def test_a_base_without_its_anchor_fields_no_qra_and_breaks_nothing() -> None:
    harness = DcsPluginHarness()
    _load(
        harness,
        ewr_names=["0041 | LION (EWR)"],
        records=[
            _intercept_record("Lost AFB", "sq-lost"),
            _intercept_record("Test AFB", "sq-1"),
        ],
        anchored=("Test AFB",),
    )
    gci = _built(harness)
    assert harness.to_python(gci.bases) == ["Test AFB"]
    assert [s[2] for s in harness.to_python(gci.squads)] == ["Test AFB"]
    infos = harness.records("infos")
    assert any("no anchor static at Lost AFB" in line for line in infos)


def test_alert_only_air_start_with_the_generator_radii() -> None:
    harness = DcsPluginHarness()
    _load(
        harness,
        ewr_names=["0041 | LION (EWR)"],
        records=[_intercept_record("Test AFB", "sq-1", gciMaxRadiusNm="200")],
    )
    gci = _built(harness)
    assert gci.takeoff == "air"
    assert gci.alert5 == 0
    assert gci.engagerange == 38
    assert gci.missionrange == 200
    assert gci.fuellow is None


def test_squadrons_are_single_jet_intercept_only_with_template_identity() -> None:
    """Ops stamps AVERAGE and modex 402 by default; the reserve keeps its own
    skill and squadron numbers (§62, test 62)."""
    harness = DcsPluginHarness()
    _load(harness, ewr_names=["0041 | LION (EWR)"])
    gci = _built(harness)
    wing = gci.wings["Test AFB"][1]
    squadrons = list(harness.to_python(wing.squadrons).values())
    assert len(squadrons) == 1
    squadron = squadrons[0]
    assert squadron["grouping"] == 1
    assert squadron["n"] == 3
    assert squadron["takeoff"] == "air"
    assert squadron["caps"] == ["Intercept"]
    assert squadron["skill"] == "Excellent"
    assert squadron["modex"] == 51
    assert squadron["range"] == 60
    assert wing.payload == "Intercept|Test AFB|sq-1"


def test_group_reacts_only_to_air_to_ground_taskings() -> None:
    harness = DcsPluginHarness()
    module = _load(harness, ewr_names=list(PAREN_NAMES))
    reacts = module.group_reacts

    assert reacts("PKG Strike|USA|1|F-16C_50|")
    assert reacts("Al Dhafra BAI|21|2|F-15E|")
    assert reacts("Incirlik OCA/Runway|2|3|B-1B|")
    assert reacts("Incirlik OCA/Aircraft|2|4|F-16C_50|")
    assert reacts("CVN-71 Anti-ship|1|5|Su-24M|")
    assert reacts("Haina Armed Recon|1|6|A-10C|")
    assert reacts("MANTIS Strike|31|FA-18C_hornet|")
    assert not reacts("MANTIS DEAD|31|FA-18C_hornet|")
    assert not reacts("PKG BARCAP|USA|7|F-14B|")
    assert not reacts("LZ Air Assault|21|9|Mi-8MT|")
    assert not reacts("PKG Fighter sweep|USA|10|F-15C|")
    assert not reacts("PKG Escort|USA|11|F-16C_50|")
    assert not reacts("Eagle Strike")
    assert not reacts(None)


def test_cluster_reacts_when_any_contact_is_react_type() -> None:
    harness = DcsPluginHarness()
    module = _load(harness, ewr_names=list(PAREN_NAMES))
    cluster = harness.lua.globals().InterceptTest.cluster

    escorted = cluster(
        harness.to_lua(["PKG Escort|USA|1|F-16C_50|", "PKG Strike|USA|2|F-15E|"])
    )
    fighters = cluster(
        harness.to_lua(["PKG Fighter sweep|USA|3|F-15C|", "PKG BARCAP|USA|4|F-14B|"])
    )
    assert module.cluster_has_react(escorted)
    assert not module.cluster_has_react(fighters)
    assert not module.cluster_has_react(harness.to_lua({}))


def test_a_raid_draws_one_jet_per_attacker_at_most_four() -> None:
    """Test 62: one raid drew 32 red jets from 10 squadrons."""
    harness = DcsPluginHarness()
    _load(harness, ewr_names=["0041 | LION (EWR)"])
    gci = _built(harness)
    cluster = harness.lua.globals().InterceptTest.cluster

    sweep = cluster(harness.to_lua(["PKG Fighter sweep|USA|1|F-15C|"]), 4)
    gci._AssignIntercept(gci, sweep)
    assert not harness.to_python(gci.assignCalls)

    strike = harness.to_lua(["PKG Strike|USA|2|F-15E|"])
    gci._AssignIntercept(gci, cluster(strike, 12))
    gci._AssignIntercept(gci, cluster(strike, 2))
    calls = harness.to_python(gci.assignCalls)
    assert calls == [{"overhead": 1, "size": 4}, {"overhead": 1, "size": 2}]


def test_the_ask_never_exceeds_the_best_stocked_base() -> None:
    """EASYGCICAP skips a base that cannot field the whole ask."""
    harness = DcsPluginHarness()
    _load(harness, ewr_names=["0041 | LION (EWR)"])
    gci = _built(harness)
    cluster = harness.lua.globals().InterceptTest.cluster
    strike = cluster(harness.to_lua(["PKG Strike|USA|2|F-15E|"]), 4)

    gci.wings["Test AFB"][1].stock = 1
    gci._AssignIntercept(gci, strike)
    gci.wings["Test AFB"][1].stock = 0
    gci._AssignIntercept(gci, strike)
    assert harness.to_python(gci.assignCalls) == [{"overhead": 1, "size": 1}]


def test_the_air_start_is_low_fast_and_stacked() -> None:
    """Ops air-starts at 1-2 km MSL, 0 kt, on one point. Kerman sits ~5,700 ft
    up; two F-14s spawning together collided (test 48)."""
    harness = DcsPluginHarness()
    _load(harness, ewr_names=["0041 | LION (EWR)"])
    harness.harness.terrainHeight = 1750.0
    gci = _built(harness)
    wing = gci.wings["Test AFB"][1]
    test_globals = harness.lua.globals().InterceptTest
    air_start = test_globals.airStart

    wing._SpawnAssetAircraft(wing, "a", air_start("Turning Point"), {}, None, False)
    wing._SpawnAssetAircraft(wing, "b", air_start("Turning Point"), {}, None, False)
    wing._SpawnAssetAircraft(wing, "c", air_start("TakeOffParking"), {}, None, False)
    harness.assert_no_lua_errors()

    first, second, ground = harness.to_python(test_globals.spawned)
    assert first["units"][0]["alt"] == 1750.0 + 760
    assert second["units"][0]["alt"] == 1750.0 + 760 + 150
    assert round(first["units"][0]["speed"], 1) == 154.3
    assert first["route"]["points"][0]["speed"] == first["units"][0]["speed"]
    assert ground["units"][0] == {"alt": 1500, "speed": 0}
    # The spawn hook is put back after each call.
    assert harness.lua.eval("_DATABASE.Spawn == InterceptTest.realSpawn")


def test_the_ambush_leash_cancels_a_straying_intercept() -> None:
    """Vietnam W5: a MiG slashes once near home and recovers."""
    harness = DcsPluginHarness()
    _load(
        harness,
        ewr_names=["0041 | LION (EWR)"],
        records=[_intercept_record("Test AFB", "sq-1", ambushPosture="true")],
    )
    gci = _built(harness)
    assert gci.fuellow == 35
    test_globals = harness.lua.globals().InterceptTest
    near = test_globals.mission(40 * 1852)
    far = test_globals.mission(60 * 1852)
    queue = gci.wings["Test AFB"][1].missionqueue
    queue[1] = near
    queue[2] = far

    harness.advance_to(BUILD_DELAY_S + 40)
    harness.assert_no_lua_errors()
    assert not near.cancelled
    assert far.cancelled


def test_no_leash_without_ambush_or_forward_defense() -> None:
    harness = DcsPluginHarness()
    _load(harness, ewr_names=["0041 | LION (EWR)"])
    gci = _built(harness)
    far = harness.lua.globals().InterceptTest.mission(500 * 1852)
    gci.wings["Test AFB"][1].missionqueue[1] = far
    harness.advance_to(BUILD_DELAY_S + 60)
    assert not far.cancelled


def test_survivors_are_the_squadron_asset_count() -> None:
    harness = DcsPluginHarness()
    _load(harness, ewr_names=["0041 | LION (EWR)"])
    gci = _built(harness)
    survivors = harness.lua.globals().intercept_survivors
    assert survivors["sq-1"] == 3

    squadron = next(iter(gci.wings["Test AFB"][1].squadrons.values()))
    squadron.n = 1
    harness.advance_to(BUILD_DELAY_S + 60)
    harness.assert_no_lua_errors()
    assert survivors["sq-1"] == 1


def test_simultaneous_scrambles_stack_and_a_quiet_base_resets() -> None:
    harness = DcsPluginHarness()
    module = _load(harness, ewr_names=["0041 | LION (EWR)"])
    offset = module.scramble_stack_offset
    assert offset("Kerman") == 0
    assert offset("Kerman") == 150
    assert offset("Shiraz") == 0
    harness.advance_to(120)
    assert offset("Kerman") == 0


def test_defenders_for_raid() -> None:
    harness = DcsPluginHarness()
    module = _load(harness, ewr_names=["0041 | LION (EWR)"])
    assert module.defenders_for_raid(1, 4) == 1
    assert module.defenders_for_raid(12, 4) == 4
    assert module.defenders_for_raid(3, 2) == 2
    assert module.defenders_for_raid(3, 0) == 0
