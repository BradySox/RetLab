"""Headless check of the three RetLab additions to the Skynet config bridge.

The bridge (skynetiads-config.lua) is upstream's, plus:

* DeadC2 -- a C2 node the campaign already knows is destroyed is registered as
  a dead stand-in. Skynet reads a SAM with no comms/power object as fully
  connected, so a node dropped from the graph silently restored the SAMs behind
  it on the next turn (juanjux/dcs-retribution#97).
* AWACS fold -- a ground-starting AWACS is not a spawned group when the bridge
  runs; it is added once it exists instead of being skipped for the mission.
* Point defence -- a PD is paired only if Skynet rates it HARM-capable, because
  Skynet keeps the parent live on its PDs' ammo without asking (test 37).

Also pinned: "Exclude SA-15", which upstream's copy shadows into a no-op.

Skynet itself is faked: the real engine needs a live DCS world. The fake records
what the bridge hands it, which is the whole contract under test.
"""

from __future__ import annotations

from typing import Any

from tests.lua.harness import DcsPluginHarness

PLUGIN = "resources/plugins/skynetiads/skynetiads-config.lua"

FAKE_SKYNET = """
SkynetIADS = {}
SkynetIADS.__index = SkynetIADS
SkynetRecords = { sams = {}, ewrs = {}, commandCenters = {}, nodes = {}, power = {}, pds = {}, actMobile = {} }
-- Group name -> true where Skynet's type database rates the site HARM-capable (Tor, Patriot...).
SkynetHarmCapable = {}

local function element(iads, name)
    local e = { name = name }
    function e:setEngagementZone() end
    function e:setCanEngageHARM() end
    function e:getCanEngageHARM() return SkynetHarmCapable[name] == true end
    function e:setHARMDetectionChance() end
    function e:setCanEngageAirWeapons() end
    function e:setGoLiveRangeInPercent() end
    function e:setAutonomousBehaviour() end
    function e:setActAsEW() end
    function e:setActMobile(enable)
        table.insert(SkynetRecords.actMobile, { nato = name, enable = enable })
    end
    function e:addPointDefence(pd)
        table.insert(SkynetRecords.pds, { sam = name, pd = pd.name })
    end
    function e:addConnectionNode(obj)
        table.insert(SkynetRecords.nodes, { sam = name, node = obj:getName(), exists = obj:isExist() })
    end
    function e:addPowerSource(obj)
        table.insert(SkynetRecords.power, { sam = name, node = obj:getName(), exists = obj:isExist() })
    end
    return e
end

function SkynetIADS:create(name)
    return setmetatable({ name = name }, SkynetIADS)
end
function SkynetIADS:getDebugSettings() return {} end
function SkynetIADS:addSAMSite(groupName)
    table.insert(SkynetRecords.sams, groupName)
    return element(self, groupName)
end
function SkynetIADS:addEarlyWarningRadar(unitName)
    table.insert(SkynetRecords.ewrs, unitName)
    return element(self, unitName)
end
function SkynetIADS:addCommandCenter(obj)
    table.insert(SkynetRecords.commandCenters, { name = obj:getName(), exists = obj:isExist(), coalition = obj:getCoalition() })
    return element(self, obj:getName())
end
function SkynetIADS:getSAMSitesByNatoName(nato) return element(self, nato) end
function SkynetIADS:addRadioMenu() end
function SkynetIADS:activate() end
"""


def _awacs_group(name: str) -> dict[str, Any]:
    return {
        "name": name,
        "side": 1,  # RED
        "category": 0,  # AIRPLANE
        "units": [
            {
                "name": name + "-1",
                "type": "A-50",
                "x": 0.0,
                "z": 0.0,
                "alt": 8000,
                "airborne": True,
            }
        ],
    }


def _sam_group(name: str) -> dict[str, Any]:
    return {
        "name": name,
        "side": 1,
        "category": 2,  # GROUND
        "units": [{"name": name + "-1", "type": "Kub 1S91 str", "x": 0.0, "z": 0.0}],
    }


def _list(h: DcsPluginHarness, value: Any) -> list[Any]:
    # An empty Lua table converts to {}; the recorders are lists.
    converted = h.to_python(value)
    return [] if converted == {} else converted


def _bridge(
    *, dead_c2: list[str], awacs: list[dict[str, Any]]
) -> tuple[DcsPluginHarness, Any]:
    h = DcsPluginHarness()
    h.lua.execute(FAKE_SKYNET)
    h.add_group(_sam_group("SAM-1"))
    h.add_static({"name": "power-alive object", "exists": True})
    config = {
        "plugins": {
            "skynetiads": {
                "createRedIADS": True,
                "createBlueIADS": False,
                "includeRedInRadio": False,
                "includeBlueInRadio": False,
                "debugRED": False,
                "debugBLUE": False,
                "actMobile": False,
                "actMobile_merad": False,
                "adjustGoLiveRange": False,
            }
        },
        "AWACs": awacs,
        "IADS": {
            "BLUE": {},
            "RED": {
                "Sam": [
                    {
                        "dcsGroupName": "SAM-1",
                        "ConnectionNode": ["comms-dead"],
                        "PowerSource": ["power-alive", "power-dead"],
                    }
                ],
                "CommandCenter": [{"dcsGroupName": "cc-dead"}],
                "DeadC2": dead_c2,
            },
        },
    }
    h.lua.globals().dcsRetribution = h.to_lua(config)
    h.load_plugin_script(PLUGIN)
    h.assert_no_lua_errors()
    return h, h.lua.globals().SkynetRecords


def test_dead_c2_nodes_are_registered_as_dead_stand_ins() -> None:
    h, rec = _bridge(dead_c2=["comms-dead", "power-dead", "cc-dead"], awacs=[])
    nodes = _list(h, rec.nodes)
    power = _list(h, rec.power)
    ccs = _list(h, rec.commandCenters)
    # The scenery comms node has no DCS object; without the stand-in Skynet would
    # see a SAM with no connection node and call it connected.
    assert nodes == [{"sam": "SAM-1", "node": "comms-dead", "exists": False}]
    # The live static is passed through untouched (pydcs names it "<unit> object");
    # the dead one is a stand-in under the campaign's own name.
    assert {p["node"]: p["exists"] for p in power} == {
        "power-alive object": True,
        "power-dead": False,
    }
    # A destroyed command centre still counts: an empty list reads as "usable".
    assert ccs == [{"name": "cc-dead", "exists": False, "coalition": 1}]


def test_unknown_missing_node_is_still_skipped() -> None:
    # Not in DeadC2 and no object: culled or never spawned. Upstream behaviour.
    h, rec = _bridge(dead_c2=[], awacs=[])
    assert _list(h, rec.nodes) == []
    assert [p["node"] for p in _list(h, rec.power)] == ["power-alive object"]
    assert _list(h, rec.commandCenters) == []


def test_ground_start_awacs_is_added_once_it_spawns() -> None:
    awacs = [{"dcsGroupName": "Overlord", "callsign": "Overlord", "coalition": "red"}]
    h, rec = _bridge(dead_c2=[], awacs=awacs)
    assert _list(h, rec.ewrs) == []
    assert h.pending_scheduled() == 1
    h.advance_to(120)
    assert _list(h, rec.ewrs) == []  # still on the ramp
    h.add_group(_awacs_group("Overlord"))
    h.advance_to(200)
    h.assert_no_lua_errors()
    assert _list(h, rec.ewrs) == ["Overlord-1"]
    assert h.pending_scheduled() == 0  # nothing left to poll for


def test_air_start_awacs_is_added_immediately() -> None:
    h = DcsPluginHarness()
    h.lua.execute(FAKE_SKYNET)
    h.add_group(_awacs_group("Overlord"))
    h.lua.globals().dcsRetribution = h.to_lua(
        {
            "plugins": {"skynetiads": {"createRedIADS": True}},
            "AWACs": [{"dcsGroupName": "Overlord", "coalition": "red"}],
            "IADS": {"BLUE": {}, "RED": {}},
        }
    )
    h.load_plugin_script(PLUGIN)
    h.assert_no_lua_errors()
    assert _list(h, h.lua.globals().SkynetRecords.ewrs) == ["Overlord-1"]
    assert h.pending_scheduled() == 0


def test_only_a_harm_capable_point_defence_is_paired() -> None:
    """Skynet's shallIgnoreHARMShutdown keeps the parent SAM emitting while its
    PDs have missiles and launchers, and never checks that a PD can engage a
    HARM. Test 37's SA-11 was paired with two Strela-1s and two ZU-23s, so it
    could hold the Buk live into the shot. Only a PD Skynet itself rates
    HARM-capable is paired; the other is still registered as a SAM site."""
    h = DcsPluginHarness()
    h.lua.execute(FAKE_SKYNET)
    h.lua.execute('SkynetHarmCapable["PD-tor"] = true')
    h.lua.globals().dcsRetribution = h.to_lua(
        {
            "plugins": {"skynetiads": {"createRedIADS": True}},
            "IADS": {
                "BLUE": {},
                "RED": {
                    "Sam": [{"dcsGroupName": "SA-11", "PD": ["PD-tor", "PD-strela"]}]
                },
            },
        }
    )
    h.load_plugin_script(PLUGIN)
    h.assert_no_lua_errors()
    rec = h.lua.globals().SkynetRecords
    assert _list(h, rec.pds) == [{"sam": "SA-11", "pd": "PD-tor"}]
    assert set(_list(h, rec.sams)) >= {"SA-11", "PD-tor", "PD-strela"}


def test_other_coalitions_awacs_is_not_polled_for() -> None:
    awacs = [{"dcsGroupName": "Magic", "coalition": "blue"}]
    h, rec = _bridge(dead_c2=[], awacs=awacs)
    assert h.pending_scheduled() == 0
    assert _list(h, rec.ewrs) == []


def _mobile_shorad(exclude_sa15: bool) -> list[str]:
    h = DcsPluginHarness()
    h.lua.execute(FAKE_SKYNET)
    h.lua.globals().dcsRetribution = h.to_lua(
        {
            "plugins": {
                "skynetiads": {
                    "createRedIADS": True,
                    "actMobile": True,
                    "actMobileMaxEmissionTime": 30,
                    "actMobileMinimumScootDistance": 300,
                    "actMobileMaximumScootDistance": 500,
                    "actMobile_exclude_SA15": exclude_sa15,
                }
            },
            "IADS": {"BLUE": {}, "RED": {}},
        }
    )
    h.load_plugin_script(PLUGIN)
    h.assert_no_lua_errors()
    return [r["nato"] for r in _list(h, h.lua.globals().SkynetRecords.actMobile)]


def test_mobile_shorad_includes_sa15_by_default() -> None:
    assert _mobile_shorad(exclude_sa15=False) == [
        "SA-8",
        "SA-9",
        "SA-13",
        "SA-15",
        "SA-19",
    ]


def test_exclude_sa15_leaves_the_tor_static() -> None:
    # Upstream declares the shorter list with an inner `local`, which shadows the
    # one the loop reads, so the option never excluded anything.
    assert _mobile_shorad(exclude_sa15=True) == ["SA-8", "SA-9", "SA-13", "SA-19"]
