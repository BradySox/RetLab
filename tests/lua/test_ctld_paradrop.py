"""Headless runtime check for the CTLD plugin on MOOSE (resources/plugins/ctld/ctld-config.lua).

The CTLD script was replaced by MOOSE's Ops.CTLD and AUTOLASE in the MIST removal
(docs/dev/design/retlab-mist-removal-notes.md). MOOSE itself is faked here to the surface
the config touches; what runs for real is the config: per-side setup, the AI helicopter
loader, the fixed-wing paradrop with its descent, the zone smoke and the JTAC lasing.
Real DCS behavior (AI landing, MOOSE's menus) still needs an in-game pass.
"""

from __future__ import annotations

from typing import Any

from tests.lua.harness import DcsPluginHarness

CONFIG = "resources/plugins/ctld/ctld-config.lua"

# Constants mirrored from ctld-config.lua.
SINK_MPS = 6.5
MAX_DESCENT_S = 90
EXIT_THROW_S = 2
AI_POLL_S = 5

_MOOSE_FAKES = """
local zones = {}
trigger.misc = trigger.misc or {}
trigger.misc.getZone = function(name) return zones[name] end
function AddTestZone(name, x, z, radius)
    zones[name] = { point = { x = x, y = 0, z = z }, radius = radius }
end
ZONE = {}
function ZONE:FindByName(name) return zones[name] and { name = name } or nil end

SMOKECOLOR = { Green = 0, Red = 1, White = 2, Orange = 3, Blue = 4 }
CTLD_CARGO = { Enum = { TROOPS = "Troops", ENGINEERS = "Engineers", VEHICLE = "Vehicle" } }

local Cargo = {}
Cargo.__index = Cargo
function Cargo:GetType() return self.kind end
function Cargo:WasDropped() return self.dropped end
function Cargo:SetWasDropped(v) self.dropped = v end
function Cargo:GetTemplates() return self.templates end

CTLD = { CargoZoneType = { LOAD = "load", DROP = "drop", MOVE = "move", SHIP = "ship" },
    FixedWingTypes = { "Hercules" } }
CTLD.__index = CTLD
ctlds = {}
function CTLD:New(side, prefixes, alias)
    local c = setmetatable({ side = side, prefixes = prefixes, alias = alias,
        Loaded_Cargo = {}, UnitTypeCapabilities = {}, caps = {}, troops = {}, crates = {},
        zones = {}, started = false, log = {} }, CTLD)
    table.insert(ctlds, c)
    return c
end
function CTLD:SetUnitCapabilities(t, crates, troops, crateLimit, troopLimit, length, mass)
    self.caps[t] = { crates = crates, troops = troops, cratelimit = crateLimit,
        trooplimit = troopLimit, mass = mass }
end
function CTLD:AddTroopsCargo(label, templates, kind, size)
    self.troops[label] = { templates = templates, size = size }
end
function CTLD:AddCratesCargo(label, templates, kind, crates)
    self.crates[label] = { templates = templates, crates = crates }
end
function CTLD:AddCTLDZone(name, kind)
    table.insert(self.zones, { name = name, kind = kind })
end
function CTLD:__Start() self.started = true end
function CTLD:PreloadTroops(unit, label)
    local troop = self.troops[label]
    table.insert(self.log, "preload " .. unit:GetName() .. " " .. label)
    if troop then
        self.Loaded_Cargo[unit:GetName()] = { Troopsloaded = troop.size, Cratesloaded = 0,
            Cargo = { setmetatable({ kind = "Troops", dropped = false,
                templates = troop.templates }, Cargo) } }
    end
end
function CTLD:IsUnitInAir(unit) return unit.unit:inAir() end
function CTLD:IsUnitInZone(unit, kind)
    local p = unit:GetVec3()
    for _, z in ipairs(self.zones) do
        local zone = zones[z.name]
        if z.kind == kind and zone then
            local d = math.sqrt((p.x - zone.point.x) ^ 2 + (p.z - zone.point.z) ^ 2)
            if d <= zone.radius then return true end
        end
    end
    return false
end
function CTLD:_UnloadTroops(group, unit)
    table.insert(self.log, "stock unload " .. unit:GetName())
    self.Loaded_Cargo[unit:GetName()] = nil
end
function CTLD:IsCorrectFlightParameters(unit)
    local p, v = unit:GetVec3(), unit:GetVelocityVec3()
    local speed = math.sqrt(v.x ^ 2 + v.y ^ 2 + v.z ^ 2)
    return p.y >= 165 and p.y <= 914 and speed <= 77
end
function CTLD:_SendMessage(text) table.insert(self.log, "msg " .. text) end
function CTLD:_UpdateUnitCargoMass() end
function CTLD:__TroopsDeployed() table.insert(self.log, "deployed") end
function CTLD:_FindCratesCargoObject(name) return self.crates[name] and { name = name } end
function CTLD:InjectStatics(zone, cargo)
    table.insert(self.log, "crate " .. cargo.name .. " at " .. zone.name)
end

lases = {}
SET_GROUP = {}
function SET_GROUP:New()
    local s = {}
    function s:FilterCoalitions(c) self.coalitions = c return self end
    function s:FilterPrefixes(p) self.prefixes = p return self end
    function s:FilterStart() return self end
    return s
end
AUTOLASE = {}
function AUTOLASE:New(set, side, alias)
    local a = { side = side, prefixes = set.prefixes, codes = {}, blacklist = {}, smoke = false }
    function a:SetLasingParameters(d, t) self.distance = d return self end
    function a:SetLaserCoolDown(on) self.cooldown = on return self end
    function a:AddBlackListAttributes(list) self.blacklist = list return self end
    function a:SetSmokeTargets(on) self.smoke = on return self end
    function a:SetRecceLaserCode(name, code) self.codes[name] = code return self end
    table.insert(lases, a)
    return a
end
"""

_OPTIONS = {
    "debug": False,
    "slingload": False,
    "smoke": False,
    "tailorctld": True,
    "logisticunit": False,
    "autolase": False,
    "airliftcrates": False,
}

_TEMPLATES = {
    "troops": [
        {
            "side": "blue",
            "label": "Retribution Troops (24)",
            "group": "CTLD blue Retribution Troops (24)",
            "size": "24",
            "jtac": "true",
            "stock": "false",
        },
        {
            "side": "blue",
            "label": "Retribution Troops (8)",
            "group": "CTLD blue Retribution Troops (8)",
            "size": "8",
            "jtac": "false",
            "stock": "false",
        },
    ],
    "crates": [
        {
            "side": "blue",
            "label": "M1043 HMMWV Armament",
            "unit": "M1043 HMMWV Armament",
            "group": "CTLD blue crate M1043 HMMWV Armament",
            "crates": "1",
            "stock": "false",
        }
    ],
}


def _transport(aircraft_type: str, cabin: int, paradrop: bool) -> dict[str, Any]:
    return {
        "aircraft_type": aircraft_type,
        "cabin_size": str(cabin),
        "troops": "true" if cabin > 0 else "false",
        "crates": "false" if paradrop else "true",
        "paradrop": "true" if paradrop else "false",
    }


def _flight(
    pilots: list[str],
    aircraft_type: str,
    group: str,
    target_zone: str = "",
    pickup_zone: str = "",
    drop_off_zone: str = "",
    preload: bool = True,
) -> dict[str, Any]:
    return {
        "pilot_names": pilots,
        "group_name": group,
        "side": "2",
        "aircraft_type": aircraft_type,
        "preload": "true" if preload else "false",
        "pickup_zone": pickup_zone,
        "drop_off_zone": drop_off_zone,
        "target_zone": target_zone,
        "logistic_unit": "",
    }


def _load(
    h: DcsPluginHarness,
    flights: list[dict[str, Any]],
    transports: list[dict[str, Any]],
    zones: list[tuple[str, float, float, float]] | None = None,
    crates: list[dict[str, Any]] | None = None,
    **options: Any,
) -> None:
    h.lua.execute(_MOOSE_FAKES)
    for name, x, z, radius in zones or []:
        h.lua.globals().AddTestZone(name, x, z, radius)
    h.lua.globals().dcsRetribution = h.to_lua(
        {
            "plugins": {"ctld": {**_OPTIONS, **options}},
            "Logistics": {
                "flights": flights,
                "transports": transports,
                "crates": crates or [],
                "spawnable_crates": [],
                "templates": _TEMPLATES,
            },
            "JTACs": [],
        }
    )
    h.load_plugin_script(CONFIG)


def _aircraft(
    h: DcsPluginHarness,
    name: str,
    aircraft_type: str,
    x: float = 50_000.0,
    z: float = 10_000.0,
    alt: float = 300.0,
    airborne: bool = True,
    player: str | None = None,
) -> None:
    h.add_group(
        {
            "name": name,
            "side": 2,
            "category": 0,
            "units": [
                {
                    "name": name,
                    "type": aircraft_type,
                    "x": x,
                    "z": z,
                    "alt": alt,
                    "airborne": airborne,
                    "playerName": player,
                    "velocity": {"x": 60.0, "y": 0.0, "z": -30.0},
                }
            ],
        }
    )


def _ctld(h: DcsPluginHarness) -> Any:
    return h.lua.eval("ctlds[1]")


def _log(h: DcsPluginHarness) -> list[str]:
    return h.to_python(_ctld(h).log) or []


def _ground_spawns(h: DcsPluginHarness) -> list[dict[str, Any]]:
    return [s for s in h.records("spawns") if s.get("base") == "ground"]


def _texts(h: DcsPluginHarness) -> list[str]:
    return [t["text"] for t in h.records("texts")]


def _herc_mission(h: DcsPluginHarness, preload: bool = False) -> None:
    _load(
        h,
        flights=[
            _flight(
                ["Herc 1-1"],
                "C-130J-30",
                "Herc 1",
                target_zone="Herc 1 TARGET_ZONE",
                preload=preload,
            )
        ],
        transports=[_transport("C-130J-30", 24, paradrop=True)],
        zones=[("Herc 1 TARGET_ZONE", 50_000.0, 10_000.0, 2_000.0)],
    )


_PRELOAD_AND_UNLOAD = (
    "local u = UNIT:FindByName('Herc 1-1')"
    " ctlds[1]:PreloadTroops(u, 'Retribution Troops (24)')"
    " ctlds[1]:_UnloadTroops(u:GetGroup(), u)"
)


def test_one_ctld_per_side_with_its_cargo_and_zones() -> None:
    h = DcsPluginHarness()
    _load(
        h,
        flights=[
            _flight(
                ["Huey 1-1"],
                "UH-1H",
                "Huey 1",
                pickup_zone="Huey 1PICKUP_ZONE",
                drop_off_zone="Huey 1DROPOFF_ZONE",
                target_zone="Huey 1 TARGET_ZONE",
            )
        ],
        transports=[_transport("UH-1H", 8, paradrop=False)],
        zones=[
            ("Huey 1PICKUP_ZONE", 0.0, 0.0, 300.0),
            ("Huey 1DROPOFF_ZONE", 10_000.0, 0.0, 300.0),
            ("Huey 1 TARGET_ZONE", 12_000.0, 0.0, 1_000.0),
        ],
    )
    assert h.lua.eval("#ctlds") == 1
    c = h.to_python(_ctld(h))
    assert c["side"] == "blue" and c["prefixes"] == ["Huey 1"] and c["started"]
    assert c["caps"]["UH-1H"]["trooplimit"] == 8
    assert set(c["troops"]) == {"Retribution Troops (24)", "Retribution Troops (8)"}
    assert set(c["crates"]) == {"M1043 HMMWV Armament"}
    assert [(z["name"], z["kind"]) for z in c["zones"]] == [
        ("Huey 1PICKUP_ZONE", "load"),
        ("Huey 1DROPOFF_ZONE", "drop"),
        ("Huey 1 TARGET_ZONE", "move"),
    ]
    h.assert_no_lua_errors()


def test_preload_retries_until_a_late_activated_transport_spawns() -> None:
    h = DcsPluginHarness()
    _herc_mission(h, preload=True)
    h.advance_to(40)
    assert not any(e.startswith("preload") for e in _log(h))
    _aircraft(h, "Herc 1-1", "C-130J-30", airborne=False, alt=0.0)
    h.advance_to(80)
    assert "preload Herc 1-1 Retribution Troops (24)" in _log(h)
    h.assert_no_lua_errors()


def test_player_airborne_unload_paradrops_after_descent() -> None:
    h = DcsPluginHarness()
    _herc_mission(h)
    _aircraft(h, "Herc 1-1", "C-130J-30", alt=300.0, player="Brady")
    h.lua.execute(_PRELOAD_AND_UNLOAD)
    assert any("paradropped troops" in t for t in _texts(h))
    assert _ground_spawns(h) == []
    h.advance_to(300 / SINK_MPS + 1)
    spawns = _ground_spawns(h)
    assert len(spawns) == 1
    assert spawns[0]["template"] == "CTLD blue Retribution Troops (24)"
    assert spawns[0]["x"] == 50_000.0 + 60.0 * EXIT_THROW_S
    assert spawns[0]["z"] == 10_000.0 - 30.0 * EXIT_THROW_S
    assert "deployed" in _log(h)
    h.assert_no_lua_errors()


def test_player_outside_the_jump_window_keeps_the_troops() -> None:
    h = DcsPluginHarness()
    _herc_mission(h)
    _aircraft(h, "Herc 1-1", "C-130J-30", alt=2_000.0, player="Brady")
    h.lua.execute(_PRELOAD_AND_UNLOAD)
    assert any("540 to 3000 ft" in e for e in _log(h))
    h.advance_to(200)
    assert _ground_spawns(h) == []
    assert h.lua.eval("ctlds[1].Loaded_Cargo['Herc 1-1'].Troopsloaded") == 24
    h.assert_no_lua_errors()


def test_grounded_fixed_wing_unload_is_moose_stock() -> None:
    h = DcsPluginHarness()
    _herc_mission(h)
    _aircraft(h, "Herc 1-1", "C-130J-30", alt=0.0, airborne=False, player="Brady")
    h.lua.execute(_PRELOAD_AND_UNLOAD)
    assert "stock unload Herc 1-1" in _log(h)
    h.assert_no_lua_errors()


def test_ai_drops_once_when_crossing_its_own_target_zone() -> None:
    h = DcsPluginHarness()
    _herc_mission(h, preload=True)
    _aircraft(h, "Herc 1-1", "C-130J-30", x=40_000.0, alt=2_000.0)
    h.advance_to(6)
    assert "preload Herc 1-1 Retribution Troops (24)" in _log(h)
    h.advance_to(30)
    assert _ground_spawns(h) == []
    # Over the zone, well above the player window: AI still jumps.
    h.update_unit("Herc 1-1", {"x": 50_500.0, "z": 10_000.0})
    h.advance_to(30 + AI_POLL_S + MAX_DESCENT_S + 1)
    assert len(_ground_spawns(h)) == 1
    h.advance_to(400)
    assert len(_ground_spawns(h)) == 1
    h.assert_no_lua_errors()


def test_ai_helicopter_loads_and_unloads_in_its_zones() -> None:
    h = DcsPluginHarness()
    _load(
        h,
        flights=[
            _flight(
                ["Huey 1-1"],
                "UH-1H",
                "Huey 1",
                pickup_zone="Huey 1PICKUP_ZONE",
                drop_off_zone="Huey 1DROPOFF_ZONE",
                preload=False,
            )
        ],
        transports=[_transport("UH-1H", 8, paradrop=False)],
        zones=[
            ("Huey 1PICKUP_ZONE", 0.0, 0.0, 300.0),
            ("Huey 1DROPOFF_ZONE", 10_000.0, 0.0, 300.0),
        ],
    )
    _aircraft(h, "Huey 1-1", "UH-1H", x=0.0, z=0.0, alt=0.0, airborne=False)
    h.advance_to(3)
    assert "preload Huey 1-1 Retribution Troops (8)" in _log(h)
    h.update_unit("Huey 1-1", {"x": 10_000.0, "z": 0.0})
    h.advance_to(5)
    assert "stock unload Huey 1-1" in _log(h)
    h.assert_no_lua_errors()


def test_zone_smoke_burns_all_mission_with_the_option() -> None:
    h = DcsPluginHarness()
    _load(
        h,
        flights=[
            _flight(
                ["Huey 1-1"],
                "UH-1H",
                "Huey 1",
                pickup_zone="Huey 1PICKUP_ZONE",
                drop_off_zone="Huey 1DROPOFF_ZONE",
            )
        ],
        transports=[_transport("UH-1H", 8, paradrop=False)],
        zones=[
            ("Huey 1PICKUP_ZONE", 0.0, 0.0, 300.0),
            ("Huey 1DROPOFF_ZONE", 10_000.0, 0.0, 300.0),
        ],
        smoke=True,
    )
    h.advance_to(3)
    assert len(h.records("smokes")) == 2
    h.advance_to(310)
    assert len(h.records("smokes")) == 4
    h.assert_no_lua_errors()


def test_no_zone_smoke_without_the_option() -> None:
    h = DcsPluginHarness()
    _herc_mission(h)
    h.advance_to(400)
    assert h.records("smokes") == []


def test_airlift_crates_are_placed_with_the_option() -> None:
    h = DcsPluginHarness()
    _load(
        h,
        flights=[_flight(["Huey 1-1"], "UH-1H", "Huey 1")],
        transports=[_transport("UH-1H", 8, paradrop=False)],
        zones=[("Huey 1crate_spawn", 0.0, 0.0, 50.0)],
        crates=[
            {
                "weight": "200",
                "unit": "M1043 HMMWV Armament",
                "coalition": "blue",
                "zone": "Huey 1crate_spawn",
            }
        ],
        airliftcrates=True,
    )
    h.advance_to(4)
    assert "crate M1043 HMMWV Armament at Huey 1crate_spawn" in _log(h)
    h.assert_no_lua_errors()


def _load_with_jtac(h: DcsPluginHarness, **options: Any) -> None:
    _herc_mission(h)
    config = h.lua.globals().dcsRetribution
    config.JTACs = h.to_lua(
        [
            {
                "dcsGroupName": "JTAC Reaper",
                "dcsUnit": "JTAC Reaper-1",
                "laserCode": "1688",
            }
        ]
    )
    for key, value in options.items():
        config.plugins.ctld[key] = value
    h.lua.execute("lases = {}")
    h.load_plugin_script(CONFIG)


def test_jtac_lases_through_autolase_for_both_sides() -> None:
    h = DcsPluginHarness()
    _load_with_jtac(h, autolase=True, jtacsmoke=False, fc3LaserCode=False)
    lases = h.to_python(h.lua.eval("lases"))
    assert [a["side"] for a in lases] == ["blue", "red"]
    for a in lases:
        # The drone, and any dropped squad cloned from the JTAC-carrying template.
        assert a["prefixes"] == ["JTAC Reaper", "CTLD blue Retribution Troops (24)"]
        assert a["codes"] == {"JTAC Reaper-1": 1688}
        assert a["distance"] == 10000
        assert a["cooldown"] is False
        assert a["blacklist"] == ["Infantry"]
        assert a["smoke"] is False
    h.assert_no_lua_errors()


def test_jtac_fc3_code_and_smoke_options() -> None:
    h = DcsPluginHarness()
    _load_with_jtac(h, autolase=True, jtacsmoke=True, fc3LaserCode=True)
    for a in h.to_python(h.lua.eval("lases")):
        assert a["codes"] == {"JTAC Reaper-1": 1113}
        assert a["smoke"] is True
    h.assert_no_lua_errors()


def test_no_autolase_without_the_option() -> None:
    h = DcsPluginHarness()
    _load_with_jtac(h, autolase=False)
    assert h.to_python(h.lua.eval("lases")) in ([], {}, None)
    h.assert_no_lua_errors()
