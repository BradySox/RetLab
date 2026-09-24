-- luacheck configuration for RetLab DCS Lua plugins.
--
-- Target runtime is DCS World's Lua 5.1 (LuaJIT) server sandbox. This config
-- powers the *advisory* luacheck job in .github/workflows/lint.yml, run over all
-- of resources/plugins. The BLOCKING gate beside it is `luac5.1 -p` (pure
-- syntax) over every plugin file. luacheck adds typo / undefined-global
-- detection on top. Files we did not write are excluded below, so a new RetLab
-- plugin is covered without touching this file.

std = "lua51"
max_line_length = false
codes = true

-- Upstream's and third parties' scripts: not ours to restyle, and fixing them
-- here would conflict with every sync.
exclude_files = {
    "resources/plugins/base/Moose.lua",
    "resources/plugins/base/mist_*.lua",
    "resources/plugins/base/json.lua",
    "resources/plugins/base/dcs_retribution.lua",
    "resources/plugins/base/land_relocate.lua",
    "resources/plugins/base/water_relocate.lua",
    "resources/plugins/airboss/*",
    "resources/plugins/bigeye/*",
    "resources/plugins/ctld/*",
    "resources/plugins/lotatc/*",
    "resources/plugins/MooseMarkerOps/*",
    "resources/plugins/MooseSoundhandler/*",
    "resources/plugins/skynetiads/*",
    "resources/plugins/splashdamage3/*",
    "resources/plugins/tic/TIC_v1.1.lua",
}

-- DCS plugin scripts assign module-level globals freely and read a large host
-- API; don't flag every top-level definition as an accidental global.
allow_defined = true
allow_defined_top = true

-- Quiet the high-noise, low-signal warnings so that the things we actually
-- care about (syntax slips, undefined/typo'd calls) stand out.
ignore = {
    "211", -- unused local variable
    "212", -- unused argument
    "213", -- unused loop variable
    "311", -- value assigned to a local is never used (overwritten)
    "542", -- empty if branch
    "631", -- line too long (belt-and-suspenders with max_line_length=false)
}

read_globals = {
    -- DCS World scripting API (server-side sandbox; no os/io/lfs)
    "env", "timer", "trigger", "coalition", "country", "world", "land",
    "atmosphere", "coord", "missionCommands", "radio", "net", "Controller",
    "Unit", "Group", "StaticObject", "Object", "Airbase", "Weapon", "Spot",
    "AI", "Warehouse", "VoiceChat", "SceneryObject", "CoalitionObject",

    -- Retribution generator bridge table (emitted into the .miz by the planner)
    "dcsRetribution",

    -- MOOSE framework surface (bundled base/Moose.lua)
    "BASE", "GROUP", "UNIT", "STATIC", "AIRBASE", "COORDINATE", "POINT_VEC2",
    "POINT_VEC3", "ZONE", "ZONE_RADIUS", "ZONE_POLYGON", "SET_GROUP",
    "SET_UNIT", "SET_STATIC", "SET_CLIENT", "SPAWN", "SCHEDULER", "MESSAGE",
    "MENU_MISSION", "MENU_MISSION_COMMAND", "MENU_COALITION",
    "MENU_COALITION_COMMAND", "MENU_GROUP", "MENU_GROUP_COMMAND", "CLIENT",
    "DETECTION_AREAS", "AI_A2A_DISPATCHER", "SETTINGS", "Ops", "UTILS",
    "routines", "mist",

    -- Plugin-defined globals RetLab init scripts probe before using
    "GLSCO", "GLSCO_COMBATANT", "GLSCO_BATTLEFIELD",
}
