"""Intercept (QRA): the detection-prefix escape (upstream PR #782 drift).

Runs the real ``resources/plugins/intercept/intercept-config.lua`` against the
harness with a recording fake of the MOOSE surface it touches (the bundled
Moose.lua models real DCS AI and cannot run headless). Pins the FilterPrefixes
gotcha the Lua syntax gate cannot:

* Moose ``SET_GROUP:FilterPrefixes`` matches names with Lua-pattern semantics
  (``string.find``, only ``-`` pre-escaped), so a raw parenthesized Retribution
  group name ("0041 | LION (EWR)") reads as a pattern capture and never matches
  its own group — QRA detection was empty and no base ever scrambled;
* every detection prefix is escaped before it reaches ``FilterPrefixes``;
* nothing is spawned onto the airfield: the per-base backstop EWR is gone
  (2026-08-06), so ``mist.dynAdd`` must never be called;
* the task-type reaction filter: QRA reacts only to air-to-ground taskings
  parsed from the namegen group name (Strike/BAI/OCA-Runway/OCA-Aircraft/
  Anti-ship/Armed Recon — no DEAD, no Air Assault), a cluster reacts as soon
  as one member is a react type (escorted strikes still trigger), and the
  per-instance ``EvaluateGCI``/``EvaluateENGAGE`` wrap skips react-free
  clusters without touching Moose's originals.

What the fake cannot model: Moose's real detection cycle and the scramble
itself — that is the in-game pass (checklist A5).
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.lua.harness import REPO_ROOT, DcsPluginHarness

PLUGIN = "resources/plugins/intercept/intercept-config.lua"

BUILD_DELAY_S = 5  # intercept-config.lua BUILD_DELAY; the dispatcher builds then

#: Real Retribution IADS group-name shapes: every one carries "(" / ")".
PAREN_NAMES = [
    "0041 | LION (EWR)",
    "0035 | ELEPHANT (Naval Two Ship)",
    "0114 | LORIKEET (S-300)",
    "0178 | OPOSSUM (Patriot)",
]

# A recording fake of the MOOSE classes intercept-config.lua touches at load
# and during the deferred dispatcher build. SET_GROUP records the prefixes it
# was given; AI_A2A_DISPATCHER records tuning calls and keeps live
# EvaluateGCI/EvaluateENGAGE originals so the plugin's per-instance wrap (the
# react-task filter) can be exercised. mist.dynAdd registers the backstop EWR
# as a real harness group so the build's existence check passes.
MOOSE_FAKE = """
InterceptTest = { filterPrefixes = nil, dispatchers = {} }

DETECTION_MANAGER = {}
function DETECTION_MANAGER:MessageToPlayers(Squadron, Message, DefenderGroup) end

BASE = {}
function BASE:CreateEventTakeoff(EventTime, Initiator) end

ZONE_RADIUS = {}
function ZONE_RADIUS:New(name, vec2, radius, doNotRegister)
    return { name = name, radius = radius }
end

SET_GROUP = {}
function SET_GROUP:New()
    local obj = {}
    function obj:FilterCoalitions(c)
        self.coalitions = c
        return self
    end
    function obj:FilterPrefixes(prefixes)
        InterceptTest.filterPrefixes = prefixes
        return self
    end
    function obj:FilterStart()
        return self
    end
    return obj
end

DETECTION_AREAS = {}
function DETECTION_AREAS:New(set, radius)
    return { set = set, radius = radius }
end

AI_A2A_DISPATCHER = {}
function AI_A2A_DISPATCHER:New(detection)
    local obj = { detection = detection, DefenderSquadrons = {}, gciCalls = {}, engageCalls = {} }
    function obj:SetDefaultTakeoffInAir() end
    function obj:SetDefaultTakeoffInAirAltitude(alt) end
    function obj:SetDefaultLandingAtEngineShutdown() end
    function obj:SetIntercept(delay) end
    function obj:SetEngageRadius(radius) end
    function obj:SetTacticalDisplay(onoff) end
    function obj:SetGciRadius(radius) end
    function obj:SetBorderZone(zones) end
    function obj:SetDisengageRadius(radius) end
    function obj:SetDefaultFuelThreshold(threshold, time) end
    function obj:SetSendMessages(onoff) end
    function obj:SetSquadron(name, base, templates, count)
        local spawn = { alts = {} }
        function spawn:InitSpeedKnots(kt) end
        function spawn:SpawnAtAirbase(airbase, takeoff, alt)
            table.insert(self.alts, alt)
        end
        self.DefenderSquadrons[name] = {
            Spawn = { spawn }, ResourceCount = count, Captured = false,
        }
    end
    function obj:SetSquadronGci(name, minSpeed, maxSpeed)
        self.DefenderSquadrons[name].Gci = { EngageMinSpeed = minSpeed }
    end
    function obj:SetSquadronTakeoffInAirAltitude(name, alt) end
    function obj:SetSquadronGrouping(name, n) end
    function obj:SetSquadronLanguage(name, lang) end
    function obj:EvaluateGCI(item)
        -- Moose: one defender per attacker, less those already engaged.
        table.insert(self.gciCalls, item)
        return item.Set:Count() - (item.engaged or 0), "friendlies"
    end
    function obj:EvaluateENGAGE(item)
        table.insert(self.engageCalls, item)
        return "friendlies"
    end
    obj.gciPicks = {}
    function obj:onafterGCI(From, Event, To, AttackerDetection, DefendersMissing)
        -- Moose's own pick loops over every squadron that has a Gci table.
        -- Record which ones it could see, sorted.
        local seen = {}
        for name, squadron in pairs(self.DefenderSquadrons) do
            if squadron.Gci then
                table.insert(seen, name)
            end
        end
        table.sort(seen)
        table.insert(self.gciPicks, table.concat(seen, ";"))
        if AttackerDetection == "boom" then
            error("moose failed")
        end
    end
    obj.shutdownCalls = 0
    function obj:OnEventEngineShutdown(EventData)
        -- Moose's own handler: a single-ship defender goes back to the pool.
        self.shutdownCalls = self.shutdownCalls + 1
    end
    table.insert(InterceptTest.dispatchers, obj)
    return obj
end

mist = {}
function mist.scheduleFunction(fn, vars, t)
    return timer.scheduleFunction(function()
        return fn(unpack(vars or {}))
    end, {}, t)
end
InterceptTest.dynAdds = {}
function mist.dynAdd(spec)
    -- Records only. The plugin must never spawn anything: the backstop EWR it
    -- used to place at the airbase reference point stood on the taxiways.
    table.insert(InterceptTest.dynAdds, spec)
end

-- Moose SET_GROUP:FilterPrefixes matcher (Moose.lua): string.find with the
-- prefix as a Lua PATTERN, only "-" pre-escaped. What an escaped prefix must
-- survive to land its group in the detection set.
function InterceptTest.mooseMatches(name, prefix)
    return string.find(name, (prefix:gsub("%-", "%%-")), 1) ~= nil
end

-- A detected cluster the shape qra_cluster_has_react walks: a Set of units,
-- each carrying its group name.
function InterceptTest.fakeItem(groupNames)
    local units = {}
    for _, n in ipairs(groupNames) do
        local group = { GetName = function() return n end }
        units[#units + 1] = { GetGroup = function() return group end }
    end
    return {
        Set = {
            Count = function() return #units end,
            ForEachUnit = function(_, fn)
                for _, u in ipairs(units) do
                    fn(u)
                end
            end,
        },
    }
end
"""


def _intercept_record(airbase: str, squadron_id: str) -> dict[str, str]:
    """One dcsRetribution.Intercept record (add_key_value emits all strings)."""
    return {
        "squadronId": squadron_id,
        "squadronName": "Test Squadron",
        "airbaseName": airbase,
        "templatePrefix": f"Intercept|{airbase}|{squadron_id}",
        "coalition": "BLUE",
        "resourceCount": "2",
        "grouping": "2",
        "engagementRangeNm": "38",
        "gciMaxRadiusNm": "60",
        "ambushPosture": "false",
        "disengageRadiusNm": "0",
    }


def _load(
    harness: DcsPluginHarness,
    ewr_names: list[str],
    awacs: list[dict[str, str]] | None = None,
    records: list[dict[str, str]] | None = None,
) -> Any:
    """Load the real plugin with one BLUE alert base and the given EWR net."""
    harness.add_airbase({"name": "Test AFB", "x": 0.0, "z": 0.0, "elev": 100.0})
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
    config.Intercept = harness.to_lua(
        {"BLUE": records or [_intercept_record("Test AFB", "sq-1")]}
    )
    config.IADS = harness.to_lua(
        {"BLUE": {"Ewr": [{"dcsGroupName": name} for name in ewr_names]}}
    )
    if awacs is not None:
        config.AWACs = harness.to_lua(awacs)
    harness.lua.execute(MOOSE_FAKE)
    script = (REPO_ROOT / PLUGIN).read_text(encoding="utf-8")
    # The chunk's return value is the plugin's test hook (inert in DCS, which
    # discards it); harness.load_plugin_script would throw it away.
    return harness.lua.execute(script)


def test_escaped_prefix_matches_where_raw_fails() -> None:
    """A parenthesized group name survives the escape and matches itself."""
    harness = DcsPluginHarness()
    module = _load(harness, ewr_names=list(PAREN_NAMES))
    matches = harness.lua.globals().InterceptTest.mooseMatches
    for name in PAREN_NAMES:
        # Raw prefix: "(" / ")" read as pattern captures -> never matches.
        assert not matches(name, name), f"raw prefix unexpectedly matched: {name}"
        # Escaped prefix: matches its literal group name.
        assert matches(name, module.pattern_escape(name)), f"no match: {name}"


def test_the_detection_list_is_the_escaped_iads_network() -> None:
    """With no AWACS up, FilterPrefixes receives the escaped IADS EWR network."""
    harness = DcsPluginHarness()
    _load(harness, ewr_names=["0041 | LION (EWR)", "0114 | LORIKEET (S-300)"])
    harness.advance_to(BUILD_DELAY_S + 1)
    harness.assert_no_lua_errors()

    prefixes = harness.to_python(harness.lua.globals().InterceptTest.filterPrefixes)
    assert prefixes == [
        "0041 | LION %(EWR%)",
        "0114 | LORIKEET %(S-300%)",  # "-" stays raw for Moose's own gsub
    ]


def test_nothing_is_spawned_onto_the_airfield() -> None:
    """The backstop EWR is gone and must not come back.

    It was a real vehicle placed at the airbase reference point + 300 m NE. DCS
    has no non-colliding ground unit -- mist's ``hidden`` only drops the F10
    symbol and ``SetCommandInvisible`` only blinds AI sensors -- so a 55G6 mast
    stood in the taxiway network and AI taxi routing had no way past it (flown
    Red Tide at Sperenberg; upstream PR #782 removed it for the same reason).
    """
    harness = DcsPluginHarness()
    _load(harness, ewr_names=list(PAREN_NAMES))
    harness.advance_to(BUILD_DELAY_S + 1)
    harness.assert_no_lua_errors()

    # An empty Lua table converts to {}, so test emptiness rather than equality.
    spawns = harness.to_python(harness.lua.globals().InterceptTest.dynAdds)
    assert not spawns, f"the plugin spawned something onto the field: {spawns}"


def test_a_wiped_out_radar_network_simply_stops_scrambling() -> None:
    """No EWR net and no AWACS => no detection source => no dispatcher, no crash.

    This is the deliberate consequence of dropping the backstop: QRA sees what
    its radars see.
    """
    harness = DcsPluginHarness()
    _load(harness, ewr_names=[])
    harness.advance_to(BUILD_DELAY_S + 1)
    harness.assert_no_lua_errors()

    dispatchers = harness.to_python(harness.lua.globals().InterceptTest.dispatchers)
    assert not dispatchers


def test_a_side_with_an_awacs_and_no_ground_radar_still_scrambles() -> None:
    """Test 55: blue had two E-2Cs, no EWR, and eight alert jets that never could
    launch. The side's own AWACS is a detection source; the enemy's is not.
    """
    harness = DcsPluginHarness()
    _load(
        harness,
        ewr_names=[],
        awacs=[
            {"dcsGroupName": "Vaziani AEW&C|3|E-2C|", "coalition": "blue"},
            {"dcsGroupName": "Anapa AEW&C|25|A-50|", "coalition": "red"},
        ],
    )
    harness.advance_to(BUILD_DELAY_S + 1)
    harness.assert_no_lua_errors()

    prefixes = harness.to_python(harness.lua.globals().InterceptTest.filterPrefixes)
    assert prefixes == ["Vaziani AEW&C|3|E-2C|"]
    matches = harness.lua.globals().InterceptTest.mooseMatches
    assert matches("Vaziani AEW&C|3|E-2C|", prefixes[0])
    dispatchers = harness.to_python(harness.lua.globals().InterceptTest.dispatchers)
    assert len(dispatchers) == 1


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
    harness.advance_to(BUILD_DELAY_S + 1)
    harness.assert_no_lua_errors()

    prefixes = harness.to_python(harness.lua.globals().InterceptTest.filterPrefixes)
    assert prefixes == ["0041 | LION %(EWR%)", "Magic"]


def test_escape_leaves_dash_for_moose() -> None:
    """ "-" must stay raw: Moose's own FilterPrefixes gsub escapes it (escaping
    here would double-escape and break the match)."""
    harness = DcsPluginHarness()
    module = _load(harness, ewr_names=list(PAREN_NAMES))
    assert (
        module.pattern_escape("0114 | LORIKEET (S-300)") == "0114 | LORIKEET %(S-300%)"
    )


def test_group_reacts_only_to_air_to_ground_taskings() -> None:
    """React list: Strike/BAI/OCA-Runway/OCA-Aircraft/Anti-ship/Armed Recon.

    NO DEAD, NO Air Assault (upstream f0bd1b63's final list); CAP/sweep/escort
    and non-ATO names never react."""
    harness = DcsPluginHarness()
    module = _load(harness, ewr_names=list(PAREN_NAMES))
    reacts = module.group_reacts

    assert reacts("PKG Strike|USA|1|F-16C_50|")
    assert reacts("Al Dhafra BAI|21|2|F-15E|")
    assert reacts("Incirlik OCA/Runway|2|3|B-1B|")
    assert reacts("Incirlik OCA/Aircraft|2|4|F-16C_50|")
    assert reacts("CVN-71 Anti-ship|1|5|Su-24M|")
    assert reacts("Haina Armed Recon|1|6|A-10C|")
    # The 2026-10 short format: no country id, DCS type id as the airframe.
    assert reacts("MANTIS Strike|31|FA-18C_hornet|")
    assert not reacts("MANTIS DEAD|31|FA-18C_hornet|")

    assert not reacts("PKG BARCAP|USA|7|F-14B|")
    assert not reacts("PKG DEAD|USA|8|F-16C_50|")
    assert not reacts("LZ Air Assault|21|9|Mi-8MT|")
    assert not reacts("PKG Fighter sweep|USA|10|F-15C|")
    assert not reacts("PKG Escort|USA|11|F-16C_50|")
    # Non-ATO group (no namegen "|" fields) is unclassifiable -> never reacts,
    # even when coincidentally named like a task.
    assert not reacts("Eagle Strike")
    assert not reacts(None)


def test_cluster_reacts_when_any_member_is_react_type() -> None:
    """An escorted strike still triggers; a pure fighter cluster never does."""
    harness = DcsPluginHarness()
    module = _load(harness, ewr_names=list(PAREN_NAMES))
    fake_item = harness.lua.globals().InterceptTest.fakeItem

    escorted_strike = fake_item(
        harness.to_lua(["PKG Escort|USA|1|F-16C_50|", "PKG Strike|USA|2|F-15E|"])
    )
    pure_fighters = fake_item(
        harness.to_lua(["PKG Fighter sweep|USA|3|F-15C|", "PKG BARCAP|USA|4|F-14B|"])
    )
    assert module.cluster_has_react(escorted_strike)
    assert not module.cluster_has_react(pure_fighters)
    assert not module.cluster_has_react(harness.to_lua({}))


def test_dispatcher_evaluation_skips_react_free_clusters() -> None:
    """The per-instance EvaluateGCI/EvaluateENGAGE wrap: a cluster with no
    react-type group returns nil (no scramble) without touching Moose's
    original; a react cluster delegates."""
    harness = DcsPluginHarness()
    _load(harness, ewr_names=["0041 | LION (EWR)"])
    harness.advance_to(BUILD_DELAY_S + 1)
    harness.assert_no_lua_errors()

    test_globals = harness.lua.globals().InterceptTest
    dispatcher = test_globals.dispatchers[1]
    fake_item = test_globals.fakeItem

    # lupa surfaces Lua multi-returns as tuples: "nil, nil" -> (None, None).
    sweep = fake_item(harness.to_lua(["PKG Fighter sweep|USA|1|F-15C|"]))
    assert dispatcher.EvaluateGCI(dispatcher, sweep) == (None, None)
    assert dispatcher.EvaluateENGAGE(dispatcher, sweep) is None
    assert len(dispatcher.gciCalls) == 0
    assert len(dispatcher.engageCalls) == 0

    strike = fake_item(harness.to_lua(["PKG Strike|USA|2|F-15E|"]))
    assert dispatcher.EvaluateGCI(dispatcher, strike) == (1, "friendlies")
    assert dispatcher.EvaluateENGAGE(dispatcher, strike) == "friendlies"
    assert len(dispatcher.gciCalls) == 1
    assert len(dispatcher.engageCalls) == 1


def test_one_raid_draws_at_most_four_defenders() -> None:
    """Test 62: Moose sends one defender per attacker and, with spent squadrons
    hidden, reaches every base inside the 200 NM GCI radius. Red launched 32 jets
    from 10 squadrons in 15 minutes. A raid now draws at most 4."""
    harness = DcsPluginHarness()
    _load(harness, ewr_names=["0041 | LION (EWR)"])
    harness.advance_to(BUILD_DELAY_S + 1)
    harness.assert_no_lua_errors()

    test_globals = harness.lua.globals().InterceptTest
    dispatcher = test_globals.dispatchers[1]
    names = ["PKG Strike|USA|2|F-15E|"] * 2 + ["PKG Escort|USA|1|F-16C_50|"] * 10
    raid = test_globals.fakeItem(harness.to_lua(names))

    assert dispatcher.EvaluateGCI(dispatcher, raid) == (4, "friendlies")
    raid.engaged = 3
    assert dispatcher.EvaluateGCI(dispatcher, raid) == (1, "friendlies")
    raid.engaged = 4
    assert dispatcher.EvaluateGCI(dispatcher, raid)[0] <= 0

    pair = test_globals.fakeItem(harness.to_lua(["PKG Strike|USA|2|F-15E|"] * 2))
    assert dispatcher.EvaluateGCI(dispatcher, pair) == (2, "friendlies")


def test_a_jet_shot_down_is_not_handed_back_to_the_pool() -> None:
    """Test 56: DCS raised engine-shutdown for four JF-17s as they fell, their
    Unit already gone. Moose's handler tests ``not DefenderUnit:InAir()``, and
    InAir() is nil for a dead unit, so each was booked as landed and relaunched:
    8 jets from a reserve of 4. Only a jet DCS says is on the ground has landed."""
    harness = DcsPluginHarness()
    _load(harness, ewr_names=["0041 | LION (EWR)"])
    harness.advance_to(BUILD_DELAY_S + 1)
    harness.assert_no_lua_errors()

    lua = harness.lua
    dispatcher = lua.globals().InterceptTest.dispatchers[1]
    event = lua.eval("""
        function(in_air)
            return { IniUnit = { InAir = function() return in_air end } }
        end
    """)

    dispatcher.OnEventEngineShutdown(dispatcher, event(None))  # dead, falling
    dispatcher.OnEventEngineShutdown(dispatcher, event(True))  # still flying
    dispatcher.OnEventEngineShutdown(dispatcher, lua.eval("{}"))  # no unit at all
    assert dispatcher.shutdownCalls == 0

    dispatcher.OnEventEngineShutdown(dispatcher, event(False))  # parked
    assert dispatcher.shutdownCalls == 1


def _two_squadrons_at_one_base() -> tuple[DcsPluginHarness, Any, list[str]]:
    harness = DcsPluginHarness()
    _load(
        harness,
        ewr_names=["0041 | LION (EWR)"],
        records=[
            _intercept_record("Test AFB", "aaaaaaaa-jf17"),
            _intercept_record("Test AFB", "bbbbbbbb-mig29"),
        ],
    )
    harness.advance_to(BUILD_DELAY_S + 1)
    harness.assert_no_lua_errors()
    dispatcher = harness.lua.globals().InterceptTest.dispatchers[1]
    names = sorted(dispatcher.DefenderSquadrons.keys())
    assert len(names) == 2
    return harness, dispatcher, names


def test_a_spent_squadron_is_hidden_so_the_other_one_at_the_base_launches() -> None:
    """Test 56: Kirkuk held a JF-17 and a MiG-29 alert squadron. Moose picks the
    nearest squadron without checking it has a jet left, the two tie on distance,
    and when the pick is empty it stops. The MiG-29s never launched."""
    _harness, dispatcher, names = _two_squadrons_at_one_base()
    first, second = names

    dispatcher.onafterGCI(dispatcher, "s", "GCI", "s", "raid", 2)
    assert dispatcher.gciPicks[1] == f"{first};{second}"

    dispatcher.DefenderSquadrons[first].ResourceCount = 0
    dispatcher.onafterGCI(dispatcher, "s", "GCI", "s", "raid", 2)
    assert dispatcher.gciPicks[2] == second
    # Hidden only for the length of the pick.
    assert dispatcher.DefenderSquadrons[first].Gci is not None

    dispatcher.DefenderSquadrons[second].Captured = True
    dispatcher.onafterGCI(dispatcher, "s", "GCI", "s", "raid", 2)
    assert dispatcher.gciPicks[3] == ""
    assert dispatcher.DefenderSquadrons[second].Gci is not None


def test_a_failed_pick_still_puts_the_hidden_squadron_back() -> None:
    _harness, dispatcher, names = _two_squadrons_at_one_base()
    first = names[0]
    dispatcher.DefenderSquadrons[first].ResourceCount = 0

    with pytest.raises(Exception, match="moose failed"):
        dispatcher.onafterGCI(dispatcher, "s", "GCI", "s", "boom", 2)
    assert dispatcher.DefenderSquadrons[first].Gci is not None


def test_simultaneous_scrambles_air_start_on_separate_levels() -> None:
    """Moose air-starts every group on one point over the field; two scrambles
    in the same second collided unit for unit (test 48, Kerman F-14 wingmen).
    Each scramble inside the window goes ~500 ft higher; a quiet base resets."""
    harness = DcsPluginHarness()
    _load(harness, ewr_names=["0041 | LION (EWR)"])
    harness.advance_to(BUILD_DELAY_S + 1)
    harness.assert_no_lua_errors()

    dispatcher = harness.lua.globals().InterceptTest.dispatchers[1]
    squadron = next(iter(dispatcher.DefenderSquadrons.values()))
    spawn = squadron.Spawn[1]
    spawn.SpawnAtAirbase(spawn, "Test AFB", "air", 860.0)
    spawn.SpawnAtAirbase(spawn, "Test AFB", "air", 860.0)
    harness.advance_to(BUILD_DELAY_S + 120)
    spawn.SpawnAtAirbase(spawn, "Test AFB", "air", 860.0)

    assert harness.to_python(spawn.alts) == [860.0, 1010.0, 860.0]
