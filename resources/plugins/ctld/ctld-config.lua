---------------------------------------------------------------------------------------------------
-- CTLD for a DCS Retribution mission, on MOOSE: Ops.CTLD carries the cargo, AUTOLASE lases for
-- the JTACs. Replaced the CTLD script in the MIST removal; picks and rationale are in
-- docs/dev/design/retlab-mist-removal-notes.md. The load-bearing parts:
--
--  * Ops.CTLD only serves players. AI Air Assault and Airlift flights load, unload and
--    paradrop through the AI loops below, against the flight's own zones.
--  * Troops and crate vehicles are cloned from hidden templates the generator writes
--    (game/missiongenerator/ctldtemplates.py); a missing template group means no cargo.
--  * Fixed-wing paradrops keep a real descent: the stick spawns on the ground 6.5 m/s
--    below the jump, at most 90 s later, so a transport shot down after the jump still
--    delivers. Players jump inside MOOSE's window (540-3000 ft AGL, under 150 kt); AI
--    jumps at any height, so a terrain-forced high crossing still delivers.
--  * A paradrop transport loads once, at preload: the helicopter loop never reloads one.
--  * Pickup and drop zone smoke is kept burning, as the CTLD script did.
---------------------------------------------------------------------------------------------------

local PARADROP_SINK_MPS = 6.5
local PARADROP_MAX_DESCENT_S = 90
local PARADROP_EXIT_THROW_S = 2 -- stick thrown forward along track
local PARADROP_AI_RANGE_M = 1200 -- AI release: distance to target zone centre
local PARADROP_AI_POLL_S = 5
local AI_LOAD_POLL_S = 2
local SMOKE_REFRESH_S = 300 -- a DCS smoke marker burns about 5 minutes
local PRELOAD_RETRY_S = 30
local PRELOAD_MAX_TRIES = 240 -- about 2 h of mission time

local function toboolean(value)
    return value == true or value == "true"
end

-- The emitter writes an absent zone as "".
local function present(value)
    return value ~= nil and value ~= ""
end

local function log(text)
    env.info("DCSRetribution|CTLD - " .. text)
end

local function sideName(side)
    if side == "2" or side == 2 then
        return "blue"
    end
    return "red"
end

-- The generator writes one Retribution squad per cabin size.
local function troopLabelFor(cabin)
    return string.format("Retribution Troops (%d)", cabin)
end

-- Fixed-wing paradrop ------------------------------------------------------------------------

-- Spawn one stick on the ground after its descent. The aircraft may be dead by then.
local function landStick(ctld, args)
    local ok, err = pcall(function()
        local alias = string.format("%s-%d", args.template, math.random(1, 100000))
        local troops = SPAWN:NewWithAlias(args.template, alias):InitDelayOff():SpawnFromVec2(args.point)
        if troops then
            ctld:__TroopsDeployed(1, nil, nil, troops, CTLD_CARGO.Enum.TROOPS)
        end
        trigger.action.outTextForCoalition(args.side,
            string.format("%s: paratroopers from %s are on the ground", args.pilot, args.typeName), 10)
    end)
    if not ok then
        env.error("DCSRetribution|CTLD paradrop - landing failed: " .. tostring(err))
    end
end

-- Jump every troop cargo aboard. Returns true when a stick left the aircraft.
local function paradrop(ctld, unit, isPlayer)
    local name = unit:GetName()
    local loaded = ctld.Loaded_Cargo[name]
    if not loaded or (loaded.Troopsloaded or 0) <= 0 then
        return false
    end
    if isPlayer and not ctld:IsCorrectFlightParameters(unit) then
        ctld:_SendMessage("Paradrop from 540 to 3000 ft AGL, under 150 kt.", 10, false, unit:GetGroup())
        return false
    end
    local point = unit:GetVec3()
    local vel = unit:GetVelocityVec3()
    local agl = point.y - land.getHeight({ x = point.x, y = point.z })
    local descent = math.min(math.max(agl, 0) / PARADROP_SINK_MPS, PARADROP_MAX_DESCENT_S)
    local drop = {
        x = point.x + vel.x * PARADROP_EXIT_THROW_S,
        y = point.z + vel.z * PARADROP_EXIT_THROW_S,
    }
    local side = unit:GetCoalition()
    local pilot = unit:GetPlayerName() or unit:GetTypeName()
    local kept = {}
    local jumped = false
    for _, cargo in pairs(loaded.Cargo or {}) do
        local kind = cargo:GetType()
        if (kind == CTLD_CARGO.Enum.TROOPS or kind == CTLD_CARGO.Enum.ENGINEERS) and not cargo:WasDropped() then
            cargo:SetWasDropped(true)
            jumped = true
            for _, template in pairs(cargo:GetTemplates() or {}) do
                local args = { template = template, point = drop, side = side, pilot = pilot,
                    typeName = unit:GetTypeName() }
                timer.scheduleFunction(function()
                    landStick(ctld, args)
                end, nil, timer.getTime() + descent)
            end
        elseif not cargo:WasDropped() then
            kept[#kept + 1] = cargo
        end
    end
    if not jumped then
        return false
    end
    ctld.Loaded_Cargo[name] = { Troopsloaded = 0, Cratesloaded = #kept, Cargo = kept }
    ctld:_UpdateUnitCargoMass(unit)
    trigger.action.outTextForCoalition(side, string.format("%s paradropped troops from %s", pilot, unit:GetTypeName()), 10)
    return true
end

-- One coalition's CTLD --------------------------------------------------------------------

local function buildSide(side, flights, transports, templates, options)
    local prefixes, paradropTypes = {}, {}
    for _, flight in ipairs(flights) do
        prefixes[#prefixes + 1] = flight.group_name
    end
    local ctld = CTLD:New(side, prefixes, side == "blue" and "Blue CTLD" or "Red CTLD")
    ctld.useprefix = true
    ctld.enableslingload = toboolean(options.slingload)
    ctld.enableFixedWing = true
    ctld.FixedMinAngels = 165 -- 540 ft
    ctld.FixedMaxAngels = 914 -- 3000 ft
    ctld.FixedMaxSpeed = 77 -- 150 kt
    ctld.movetroopstowpzone = true
    if toboolean(options.debug) then
        ctld.verbose = 2
    end

    for _, transport in pairs(transports) do
        local cabin = tonumber(transport.cabin_size) or 0
        local crates = toboolean(transport.crates)
        local known = ctld.UnitTypeCapabilities[transport.aircraft_type] or {}
        local crateLimit = crates and math.max(known.cratelimit or 0, 1) or 0
        local maxMass = math.max(known.cargoweightlimit or 500, cabin * 100)
        ctld:SetUnitCapabilities(transport.aircraft_type, crates, toboolean(transport.troops),
            crateLimit, cabin, known.length, maxMass)
        if toboolean(transport.troops) and toboolean(transport.paradrop) then
            paradropTypes[transport.aircraft_type] = true
            table.insert(ctld.FixedWingTypes, transport.aircraft_type)
        end
    end

    for _, troop in pairs(templates.troops or {}) do
        if troop.side == side then
            ctld:AddTroopsCargo(troop.label, { troop.group }, CTLD_CARGO.Enum.TROOPS, tonumber(troop.size))
        end
    end
    for _, crate in pairs(templates.crates or {}) do
        if crate.side == side then
            ctld:AddCratesCargo(crate.label, { crate.group }, CTLD_CARGO.Enum.VEHICLE, tonumber(crate.crates))
        end
    end

    local smokeZones = {}
    for _, flight in ipairs(flights) do
        if present(flight.pickup_zone) then
            ctld:AddCTLDZone(flight.pickup_zone, CTLD.CargoZoneType.LOAD, SMOKECOLOR.Blue, true, false)
            smokeZones[#smokeZones + 1] = { flight.pickup_zone, trigger.smokeColor.Blue }
        end
        if present(flight.drop_off_zone) then
            ctld:AddCTLDZone(flight.drop_off_zone, CTLD.CargoZoneType.DROP, SMOKECOLOR.Green, true, false)
            smokeZones[#smokeZones + 1] = { flight.drop_off_zone, trigger.smokeColor.Green }
        end
        if present(flight.target_zone) then
            ctld:AddCTLDZone(flight.target_zone, CTLD.CargoZoneType.MOVE, SMOKECOLOR.Red, true, false)
        end
    end
    for _, carrier in pairs(dcsRetribution.Carriers or {}) do
        local unit = Unit.getByName(carrier.unit_name)
        if unit and sideName(unit:getCoalition()) == side then
            ctld:AddCTLDZone(carrier.unit_name, CTLD.CargoZoneType.SHIP, SMOKECOLOR.Blue, true, false, 300, 70)
        end
    end

    -- A fixed-wing transport's airborne unload is a jump; everything else is MOOSE's own.
    local stockUnload = ctld._UnloadTroops
    function ctld:_UnloadTroops(Group, Unit)
        if paradropTypes[Unit:GetTypeName()] and self:IsUnitInAir(Unit) then
            return paradrop(self, Unit, Unit:GetPlayerName() ~= nil)
        end
        return stockUnload(self, Group, Unit)
    end

    ctld:__Start(1)
    if not toboolean(options.smoke) then
        smokeZones = {}
    end
    return ctld, paradropTypes, smokeZones
end

-- AI cargo work -----------------------------------------------------------------------------

local function aiUnit(name)
    local unit = UNIT:FindByName(name)
    if unit and unit:IsAlive() and unit:GetPlayerName() == nil then
        return unit
    end
    return nil
end

local function troopsAboard(ctld, unit)
    local loaded = ctld.Loaded_Cargo[unit:GetName()]
    return loaded ~= nil and (loaded.Troopsloaded or 0) > 0
end

-- AI helicopters: load when landed in their pickup zone, unload when landed in their drop zone.
local function aiHelicopterTick(ctld, flights, paradropTypes, cabinOf)
    for _, flight in ipairs(flights) do
        if not paradropTypes[flight.aircraft_type] then
            for _, pilot in pairs(flight.pilot_names) do
                local ok, err = pcall(function()
                    local unit = aiUnit(pilot)
                    if not unit or ctld:IsUnitInAir(unit) then
                        return
                    end
                    local aboard = troopsAboard(ctld, unit)
                    if not aboard and ctld:IsUnitInZone(unit, CTLD.CargoZoneType.LOAD) then
                        ctld:PreloadTroops(unit, troopLabelFor(cabinOf[flight.aircraft_type] or 0))
                    elseif aboard and ctld:IsUnitInZone(unit, CTLD.CargoZoneType.DROP) then
                        ctld:_UnloadTroops(unit:GetGroup(), unit)
                    end
                end)
                if not ok then
                    env.error("DCSRetribution|CTLD - AI helicopter check failed: " .. tostring(err))
                end
            end
        end
    end
end

-- AI fixed-wing: jump once, crossing its own target zone.
local function aiParadropTick(ctld, plan)
    for pilot, zoneName in pairs(plan) do
        local ok, err = pcall(function()
            local unit = aiUnit(pilot)
            if not unit or not ctld:IsUnitInAir(unit) or not troopsAboard(ctld, unit) then
                return
            end
            local zone = trigger.misc.getZone(zoneName)
            if not zone then
                return
            end
            local p = unit:GetVec3()
            local dist = math.sqrt((p.x - zone.point.x) ^ 2 + (p.z - zone.point.z) ^ 2)
            if dist <= math.min(zone.radius or PARADROP_AI_RANGE_M, PARADROP_AI_RANGE_M)
                and paradrop(ctld, unit, false) then
                log(string.format("%s released at %.0f m", pilot, dist))
                plan[pilot] = nil
            end
        end)
        if not ok then
            env.error("DCSRetribution|CTLD paradrop - AI check failed: " .. tostring(err))
        end
    end
end

-- Preload a transport once it exists (TOT-delayed flights late-activate).
local function preload(ctld, pilot, label, tries)
    local unit = UNIT:FindByName(pilot)
    if not (unit and unit:IsAlive()) then
        if tries < PRELOAD_MAX_TRIES then
            timer.scheduleFunction(function()
                preload(ctld, pilot, label, tries + 1)
            end, nil, timer.getTime() + PRELOAD_RETRY_S)
        else
            log("giving up preload for " .. pilot .. " (never spawned)")
        end
        return
    end
    log("preloading " .. label .. " into " .. pilot)
    ctld:PreloadTroops(unit, label)
end

local function refreshSmoke(zones)
    for _, entry in ipairs(zones) do
        local zone = trigger.misc.getZone(entry[1])
        if zone then
            trigger.action.smoke(zone.point, entry[2])
        end
    end
    timer.scheduleFunction(function()
        refreshSmoke(zones)
    end, nil, timer.getTime() + SMOKE_REFRESH_S)
end

local function startSide(side, logistics, options)
    local flights = {}
    for _, flight in pairs(logistics.flights or {}) do
        if sideName(flight.side) == side then
            flights[#flights + 1] = flight
        end
    end
    if #flights == 0 then
        return
    end
    local transports = logistics.transports or {}
    local cabinOf = {}
    for _, transport in pairs(transports) do
        cabinOf[transport.aircraft_type] = tonumber(transport.cabin_size) or 0
    end
    local ctld, paradropTypes, smokeZones = buildSide(side, flights, transports, logistics.templates or {}, options)

    local plan = {}
    for _, flight in ipairs(flights) do
        local label = troopLabelFor(cabinOf[flight.aircraft_type] or 0)
        for _, pilot in pairs(flight.pilot_names) do
            if toboolean(flight.preload) then
                timer.scheduleFunction(function()
                    preload(ctld, pilot, label, 0)
                end, nil, timer.getTime() + 5)
            end
            if present(flight.target_zone) and paradropTypes[flight.aircraft_type] then
                plan[pilot] = flight.target_zone
                log(string.format("AI paradrop plan: %s -> %s", pilot, flight.target_zone))
            end
        end
    end

    timer.scheduleFunction(function()
        aiHelicopterTick(ctld, flights, paradropTypes, cabinOf)
        return timer.getTime() + AI_LOAD_POLL_S
    end, nil, timer.getTime() + AI_LOAD_POLL_S)
    timer.scheduleFunction(function()
        aiParadropTick(ctld, plan)
        return timer.getTime() + PARADROP_AI_POLL_S
    end, nil, timer.getTime() + PARADROP_AI_POLL_S)

    if #smokeZones > 0 then
        timer.scheduleFunction(function()
            refreshSmoke(smokeZones)
        end, nil, timer.getTime() + 2)
    end

    if toboolean(options.airliftcrates) then
        timer.scheduleFunction(function()
            for _, crate in pairs(logistics.crates or {}) do
                if crate.coalition == side then
                    local zone = ZONE:FindByName(crate.zone)
                    local cargo = ctld:_FindCratesCargoObject(crate.unit)
                    if zone and cargo then
                        ctld:InjectStatics(zone, cargo, true)
                    end
                end
            end
        end, nil, timer.getTime() + 3)
    end
    log(string.format("%s running: %d flights", side, #flights))
end

-- JTAC lasing (MOOSE AUTOLASE) --------------------------------------------------------------

local function startJtacs(options, templates)
    local smoke = toboolean(options.jtacsmoke)
    local fc3LaserCode = toboolean(options.fc3LaserCode)
    -- The JTAC drones, plus every dropped squad that carries a JTAC (a clone keeps its
    -- template's name as a prefix).
    local names = {}
    for _, jtac in pairs(dcsRetribution.JTACs or {}) do
        names[#names + 1] = jtac.dcsGroupName
    end
    for _, troop in pairs(templates.troops or {}) do
        if toboolean(troop.jtac) then
            names[#names + 1] = troop.group
        end
    end
    if #names == 0 then
        return
    end
    for _, side in ipairs({ "blue", "red" }) do
        local ok, err = pcall(function()
            local recce = SET_GROUP:New():FilterCoalitions(side):FilterPrefixes(names):FilterStart()
            local lase = AUTOLASE:New(recce, side, "JTAC")
            -- Kept from CTLD's JTAC: 10 km reach, vehicles only, steady lasing, text reports.
            lase:SetLasingParameters(10000, 1800)
            lase:SetLaserCoolDown(false)
            lase:AddBlackListAttributes({ "Infantry" })
            if smoke then
                lase:SetSmokeTargets(true)
            end
            for _, jtac in pairs(dcsRetribution.JTACs or {}) do
                -- 1113 lets the Su-25 and A-10A (FC3) use the spot.
                local code = fc3LaserCode and 1113 or tonumber(jtac.laserCode)
                lase:SetRecceLaserCode(jtac.dcsUnit, code)
                log(string.format("JTAC %s lases on %d (%s)", jtac.dcsGroupName, code, side))
            end
        end)
        if not ok then
            env.error("DCSRetribution|JTAC - AUTOLASE setup failed: " .. tostring(err))
        end
    end
end

-- Entry -------------------------------------------------------------------------------------

if dcsRetribution and dcsRetribution.plugins and dcsRetribution.plugins.ctld then
    local options = dcsRetribution.plugins.ctld
    local logistics = dcsRetribution.Logistics or {}
    for _, side in ipairs({ "blue", "red" }) do
        local ok, err = pcall(startSide, side, logistics, options)
        if not ok then
            env.error("DCSRetribution|CTLD - " .. side .. " setup failed: " .. tostring(err))
        end
    end
    if toboolean(options.autolase) then
        startJtacs(options, logistics.templates or {})
    end
end
