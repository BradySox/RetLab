-- Intercept (QRA) -- one MOOSE EASYGCICAP per coalition from
-- dcsRetribution.Intercept. Rationale, the flown-test history and the tuning
-- record are in docs/dev/retlab-features.md §1. The load-bearing parts:
--
--  * MOOSE develop deleted AI_A2A_DISPATCHER (2026-02-06), so QRA runs on the
--    Ops EASYGCICAP since 2026-11-14. Each airwing anchors on a static named
--    after its airbase; the generator places it clear of the runway and stands.
--  * Never restore the per-base backstop EWR. DCS has no non-colliding ground
--    unit, so the mast blocked AI taxi routing (flown Red Tide 2026-08-06).
--    Detection is the IADS radars plus the side's own AWACS (DM call
--    2026-10-11, test 55); a side with neither has no GCI, by design.
--  * Jets air-start. Every ground spawn failed on saturated ramps; the air
--    spawn is patched for altitude, speed and stacking below (Ops' own spawns
--    at 1-2 km MSL, 0 kt, every jet on one point).
--  * No alert-5, no standing CAP: Retribution's BARCAP is the patrol (DM call
--    2026-11-14).

env.info("DCSRetribution|Intercept: configuring QRA")

intercept_survivors = intercept_survivors or {}

-- Run fn once at model time t. pcall'd so one bad tick logs instead of breaking a
-- self-rescheduling chain.
local function schedule_once(fn, t)
    timer.scheduleFunction(function()
        local ok, err = pcall(fn)
        if not ok then
            env.error("DCSRetribution|Intercept: " .. tostring(err))
        end
    end, nil, t)
end

-- squadronId -> { gci, airbaseName, squadronName }. Filled by the deferred build,
-- read by the survivor refresh.
local intercept_registry = {}

-- The generator carries the QRA radii on every record of a side; build_gcicap
-- reads them from records[1]. add_key_value serializes everything as a string.
local NM = 1852  -- metres per nautical mile
local BUILD_DELAY = 5  -- seconds; let the mission's groups register before SET_GROUP
-- One defender per attacker, at most this many jets on one raid: one raid drew
-- 32 red jets from 10 squadrons (test 62).
local MAX_DEFENDERS_PER_RAID = 4

-- Air-spawn profile (2026-06-21, test 48). Spawned at ~0 kt, a Su-27 dived 4,600 ft
-- clawing back airspeed; one MSL altitude for every base spawns into terrain at a
-- high field. Two scrambles in the same second overlapped unit for unit (two F-14s
-- collided at Kerman), so each scramble inside the window goes one level higher.
local SCRAMBLE_SPEED_KT = 300
local SCRAMBLE_AGL_M = 760      -- ~2,500 ft above the launching field
local STACK_STEP_M = 150        -- ~500 ft between scrambles launched together
local STACK_LEVELS = 4
local STACK_WINDOW_S = 60

local scramble_stack = {}

local function scramble_stack_offset(base_name)
    local now = timer.getTime()
    local s = scramble_stack[base_name]
    if s == nil or now - s.t > STACK_WINDOW_S then
        s = { level = 0 }
    else
        s.level = (s.level + 1) % STACK_LEVELS
    end
    s.t = now
    scramble_stack[base_name] = s
    return s.level * STACK_STEP_M
end

-- GCI-ambush hit-and-run (Vietnam W5): the generator marks a side ambushPosture.
local AMBUSH_DISENGAGE_NM = 50
local AMBUSH_FUEL_PERCENT = 35  -- RTB at 35% fuel: one slash, then home
local LEASH_INTERVAL = 15       -- seconds between leash checks

local function field_elevation(base_name)
    local base = AIRBASE:FindByName(base_name)
    if not base then return nil end
    local ok, elev = pcall(function()
        return base:GetCoordinate():GetLandHeight()
    end)
    if ok then return elev end
    return nil
end

-- Rewrite an Ops air-start template before it reaches DCS: terrain-relative
-- altitude, a real airspeed, and the stack level. Ground spawns pass untouched.
local function shape_air_start(template, base_name)
    local points = template.route and template.route.points
    local first = points and points[1]
    if not first or first.type ~= "Turning Point" then
        return
    end
    local elev = field_elevation(base_name)
    if not elev then return end
    local alt = elev + SCRAMBLE_AGL_M + scramble_stack_offset(base_name)
    local speed = SCRAMBLE_SPEED_KT * 0.514444
    first.alt = alt
    first.alt_type = "BARO"
    first.speed = speed
    for _, unit in ipairs(template.units or {}) do
        unit.alt = alt
        unit.alt_type = "BARO"
        unit.speed = speed
    end
end

local function patch_air_spawn(wing, base_name)
    local orig = wing._SpawnAssetAircraft
    function wing:_SpawnAssetAircraft(...)
        local db = _DATABASE
        local orig_spawn = db.Spawn
        db.Spawn = function(dbself, template)
            local ok, err = pcall(shape_air_start, template, base_name)
            if not ok then
                env.error("DCSRetribution|Intercept: air-start shape failed: " .. tostring(err))
            end
            return orig_spawn(dbself, template)
        end
        local ok, result = pcall(orig, self, ...)
        db.Spawn = orig_spawn
        if not ok then
            error(result, 0)
        end
        return result
    end
end

-- This side's defended airspace: circles around its bases and fronts, plus §98
-- aligned-nation borders as polygons. Empty when the generator emitted none, in
-- which case the side engages wherever its radars see.
--
-- DoNotRegisterZone=true: internal filter zones must not fire MOOSE's new-zone
-- event for every control point on the map.
local function defense_zones_for(coalition_name)
    local zones = {}
    local all = dcsRetribution.Intercept and dcsRetribution.Intercept.ZONES
    local records = all and all[coalition_name]
    if records then
        for _, rec in pairs(records) do
            local x = tonumber(rec.x)
            local y = tonumber(rec.y)
            local radius = tonumber(rec.radiusM)
            if x and y and radius and radius > 0 then
                zones[#zones + 1] = ZONE_RADIUS:New(rec.name, { x = x, y = y }, radius, true)
            end
        end
    end
    local polys = dcsRetribution.Intercept and dcsRetribution.Intercept.POLYGONS
    local poly_records = polys and polys[coalition_name]
    if poly_records then
        for _, rec in pairs(poly_records) do
            local pts = {}
            for _, p in ipairs(rec.points or {}) do
                local x, y = tonumber(p.x), tonumber(p.y)
                if x and y then
                    pts[#pts + 1] = { x = x, y = y }
                end
            end
            if #pts >= 3 then
                local ok, zone = pcall(function()
                    return ZONE_POLYGON:NewFromPointsArray(rec.name, pts)
                end)
                if ok and zone then
                    zones[#zones + 1] = zone
                else
                    env.error("INTERCEPT|: bad airspace polygon " .. tostring(rec.name))
                end
            end
        end
    end
    return zones
end

-- MOOSE SET_GROUP:FilterPrefixes matches with Lua-pattern semantics and gsubs "-"
-- itself. Retribution IADS names carry "(" and ")" ("0041 | LION (EWR)"), which
-- would never match unescaped; escape everything except "-".
local function lua_pattern_escape(s)
    return (s:gsub("([%(%)%.%%%+%*%?%[%]%^%$])", "%%%1"))
end

-- The EWR / SAM-as-EWR group names the IADS generator published for a side, plus
-- its AWACS. Standalone Ewr entries carry the UNIT name (Skynet convention), so
-- they resolve to the parent group (test 55: two E-2Cs and no ground radar left
-- blue's QRA blind).
local function ewr_group_names(coalition_name)
    local names = {}
    local seen = {}
    local iads = dcsRetribution.IADS and dcsRetribution.IADS[coalition_name]
    if iads then
        for _, role in ipairs({ "Ewr", "SamAsEwr" }) do
            local list = iads[role]
            if list then
                for _, node in pairs(list) do
                    if node.dcsGroupName then
                        local group_name = node.dcsGroupName
                        local grp = GROUP:FindByName(group_name)
                        if not grp then
                            local unit = UNIT:FindByName(group_name)
                            if unit then
                                local parent = unit:GetGroup()
                                if parent then
                                    group_name = parent:GetName()
                                end
                            end
                        end
                        if not seen[group_name] then
                            seen[group_name] = true
                            names[#names + 1] = group_name
                        end
                    end
                end
            end
        end
    end
    for _, awacs in pairs(dcsRetribution.AWACs or {}) do
        local group_name = awacs.dcsGroupName
        if group_name and string.upper(tostring(awacs.coalition)) == coalition_name
            and not seen[group_name]
        then
            seen[group_name] = true
            names[#names + 1] = group_name
        end
    end
    return names
end

-- ---------------------------------------------------------------------------
-- Task-type reaction filter (upstream PR #782): QRA only answers air-to-ground
-- raids. namegen embeds the task as "{target} {flight_type}|{n}|{type}|"
-- (game/naming.py); a name with no "|" is not an ATO flight and never reacts.
-- ---------------------------------------------------------------------------
local QRA_REACT_TASKS = {
    ["Strike"] = true,
    ["BAI"] = true,
    ["OCA/Runway"] = true,
    ["OCA/Aircraft"] = true,
    ["Anti-ship"] = true,
    ["Armed Recon"] = true,
}

local function ends_with(str, suffix)
    return str:sub(-#suffix) == suffix
end

-- The leading space keeps a target name that merely ends in a task word from
-- matching; multi-word target names still work.
local function qra_group_reacts(group_name)
    if type(group_name) ~= "string" then return false end
    local field = group_name:match("^([^|]+)|")
    if not field then return false end
    for task, _ in pairs(QRA_REACT_TASKS) do
        if ends_with(field, " " .. task) then
            return true
        end
    end
    return false
end

-- An INTEL cluster reacts as soon as one contact is a react-type group, so an
-- escorted strike still triggers.
local function qra_cluster_has_react(cluster)
    for _, contact in pairs((cluster and cluster.Contacts) or {}) do
        if qra_group_reacts(contact.groupname) then
            return true
        end
    end
    return false
end

-- Jets a raid draws: one per attacker, capped, and never more than the best
-- stocked base holds (EASYGCICAP skips a base that cannot field the whole ask, so
-- an uncapped ask leaves a 2-jet base silent against a 4-ship).
local function defenders_for_raid(attackers, best_stock)
    local n = math.min(attackers or 1, MAX_DEFENDERS_PER_RAID, best_stock or 0)
    if n < 1 then return 0 end
    return n
end

local function best_stock(gci)
    local best = 0
    for _, data in pairs(gci.wings or {}) do
        local ok, n = pcall(function() return data[1]:CountAssets(true) end)
        if ok and n and n > best then best = n end
    end
    return best
end

-- Template skill and modex carry over: Ops would stamp AVERAGE and 402 on every
-- clone, and the reserve wears its squadron's numbers (§62, test 62).
local function template_identity(template_name)
    local ok, template = pcall(function()
        return _DATABASE:GetGroupTemplate(template_name)
    end)
    local unit = ok and template and template.units and template.units[1]
    if not unit then return nil, nil end
    return unit.skill, tonumber(unit.onboard_num)
end

local function install_overrides(gci, leash_nm)
    -- Single-jet assets, intercept only, air start. MOOSE's own _AddSquadron adds
    -- CAP capabilities and keeps the template's 2-ship grouping.
    -- Skill and modex come from the template, not EASYGCICAP's AVERAGE/402 defaults.
    function gci:_AddSquadron(TemplateName, SquadName, AirbaseName, AirFrames)
        local wing = self.wings[AirbaseName] and self.wings[AirbaseName][1]
        if not wing then
            env.info("DCSRetribution|Intercept: no airwing at " .. tostring(AirbaseName)
                     .. " for " .. tostring(SquadName))
            return self
        end
        local skill, modex = template_identity(TemplateName)
        local squadron = SQUADRON:New(TemplateName, AirFrames, SquadName)
        squadron:SetGrouping(1)
        squadron:AddMissionCapability({ AUFTRAG.Type.INTERCEPT })
        squadron:SetTakeoffAir()
        squadron:SetFuelLowThreshold(0.3)
        squadron:SetTurnoverTime(self.maintenancetime, self.repairtime)
        squadron:SetMissionRange(self.missionrange)
        if skill then squadron:SetSkill(skill) end
        if modex then squadron:SetModex(modex) end
        wing:AddSquadron(squadron)
        wing:NewPayload(TemplateName, -1, { AUFTRAG.Type.INTERCEPT }, 100)
        return self
    end

    local orig_add_airwing = gci._AddAirwing
    function gci:_AddAirwing(Airbasename, Alias)
        local result = orig_add_airwing(self, Airbasename, Alias)
        local entry = self.wings[Airbasename]
        if entry and entry[1] then
            patch_air_spawn(entry[1], Airbasename)
        end
        return result
    end

    local orig_assign = gci._AssignIntercept
    function gci:_AssignIntercept(Cluster)
        if not qra_cluster_has_react(Cluster) then
            return
        end
        local attackers = self.Intel and self.Intel:ClusterCountUnits(Cluster) or 1
        local n = defenders_for_raid(attackers, best_stock(self))
        if n < 1 then
            return
        end
        -- EASYGCICAP asks for overhead * (attackers + 1), capped at maxinterceptsize.
        self.overhead = 1
        self.maxinterceptsize = n
        return orig_assign(self, Cluster)
    end

    if leash_nm and leash_nm > 0 then
        local leash_m = leash_nm * NM
        local function check_leash()
            for base_name, data in pairs(gci.wings or {}) do
                local wing = data[1]
                local base = AIRBASE:FindByName(base_name)
                local home = base and base:GetCoordinate()
                if wing and home then
                    for _, mission in pairs(wing.missionqueue or {}) do
                        if mission.type == AUFTRAG.Type.INTERCEPT and not mission:IsOver() then
                            for _, og in pairs(mission:GetOpsGroups() or {}) do
                                local coord = og:IsAlive() and og:GetCoordinate()
                                if coord and coord:Get2DDistance(home) > leash_m then
                                    mission:Cancel()
                                    break
                                end
                            end
                        end
                    end
                end
            end
            schedule_once(check_leash, timer.getTime() + LEASH_INTERVAL)
        end
        schedule_once(check_leash, timer.getTime() + BUILD_DELAY + LEASH_INTERVAL)
    end
end

local function build_gcicap(coalition_name, records)
    if #records == 0 then return end

    local scramble_radius_nm = tonumber(records[1].gciMaxRadiusNm) or 60
    local engagement_range_nm = tonumber(records[1].engagementRangeNm) or 38
    -- Home-base leash in NM (forward defense). 0 leaves the Ops mission range alone.
    local disengage_radius_nm = tonumber(records[1].disengageRadiusNm) or 0
    local ambush_posture = records[1].ambushPosture == "true"

    schedule_once(function()
        local detection = ewr_group_names(coalition_name)
        if #detection == 0 then
            env.info("DCSRetribution|Intercept: no detection sources for "
                     .. coalition_name .. "; QRA will not scramble.")
            return
        end
        local patterns = {}
        for i, name in ipairs(detection) do
            patterns[i] = lua_pattern_escape(name)
        end

        -- A base without its anchor static cannot host an airwing.
        local bases, anchored, seen = {}, {}, {}
        for _, rec in ipairs(records) do
            local name = rec.airbaseName
            if not seen[name] then
                seen[name] = true
                if STATIC:FindByName(name, false) then
                    anchored[name] = true
                    bases[#bases + 1] = name
                else
                    env.info("DCSRetribution|Intercept: no anchor static at " .. tostring(name)
                             .. "; that base fields no QRA.")
                end
            end
        end
        if #bases == 0 then return end

        local gci = EASYGCICAP:New("QRA " .. coalition_name, bases[1],
                                   string.lower(coalition_name), patterns)
        for i = 2, #bases do
            gci:AddAirwing(bases[i], "QRA " .. bases[i])
        end
        gci:SetDefaultTakeOffType("air")
        gci:SetDefaultNumberAlert5Standby(0)
        gci:SetDefaultEngageRange(engagement_range_nm)
        gci:SetDefaultMissionRange(scramble_radius_nm)

        local leash_nm = nil
        if ambush_posture then
            gci:SetFuelLow(AMBUSH_FUEL_PERCENT)
            leash_nm = AMBUSH_DISENGAGE_NM
        elseif disengage_radius_nm > 0 then
            leash_nm = disengage_radius_nm
        end

        local zones = defense_zones_for(coalition_name)
        for _, zone in ipairs(zones) do
            gci:AddAcceptZone(zone)
        end
        if #zones > 0 then
            env.info("DCSRetribution|Intercept: " .. coalition_name .. " defends "
                     .. #zones .. " zone(s); scramble radius "
                     .. scramble_radius_nm .. " NM")
        end

        install_overrides(gci, leash_nm)

        for _, rec in ipairs(records) do
            if anchored[rec.airbaseName] then
                -- Squadron display names repeat across bases (dr-wz6p); a slice of
                -- the unique id keeps one base's QRA from overwriting another's.
                local sq = rec.squadronName .. " #" .. string.sub(tostring(rec.squadronId), 1, 8)
                gci:AddSquadron(rec.templatePrefix, sq, rec.airbaseName,
                                tonumber(rec.resourceCount))
                intercept_survivors[rec.squadronId] = tonumber(rec.resourceCount)
                intercept_registry[rec.squadronId] = {
                    gci = gci,
                    airbaseName = rec.airbaseName,
                    squadronName = sq,
                }
            end
        end
    end, timer.getTime() + BUILD_DELAY)
end

-- ---------------------------------------------------------------------------
-- Survivor refresh: every jet still in the squadron, parked or airborne. Ops drops
-- a dead asset from its squadron, and assets are single jets, so the count is the
-- squadron's asset count. Before the wings start (6-12 s in) the last value stands.
-- ---------------------------------------------------------------------------
local REFRESH_INTERVAL = 30

local function refresh_survivors()
    for squadron_id, entry in pairs(intercept_registry) do
        local ok, err = pcall(function()
            local wing_entry = entry.gci.wings and entry.gci.wings[entry.airbaseName]
            local wing = wing_entry and wing_entry[1]
            local squadron = wing and wing:GetSquadron(entry.squadronName)
            if squadron then
                intercept_survivors[squadron_id] = math.max(0, squadron:CountAssets())
            end
        end)
        if not ok then
            env.info("DCSRetribution|Intercept: survivor refresh error for squadron "
                     .. tostring(squadron_id) .. ": " .. tostring(err))
        end
    end
    schedule_once(refresh_survivors, timer.getTime() + REFRESH_INTERVAL)
end

-- ---------------------------------------------------------------------------
-- Player-manned QRA scramble cue (§1 player-manning). Calls the player to scramble
-- a lead margin beyond the AI scramble radius so a cold start has spool-up and taxi
-- time. It never launches anything.
-- ---------------------------------------------------------------------------
local PLAYER_SCRAMBLE_LEAD_NM = 30
local PLAYER_ALERT_INTERVAL = 20
local PLAYER_ALERT_REPEAT = 120
local PLAYER_ALERT_DURATION = 25

local COALITION_SIDE = { BLUE = coalition.side.BLUE, RED = coalition.side.RED }

-- base_vec2: MOOSE Vec2 {x=north, y=east}; p: DCS Vec3 {x=north, y=alt, z=east}.
local function alert_bearing_range(base_vec2, p)
    local north_delta = p.x - base_vec2.x
    local east_delta = p.z - base_vec2.y
    local brg = math.deg(math.atan2(east_delta, north_delta))
    if brg < 0 then brg = brg + 360 end
    local rng_nm = math.sqrt(north_delta * north_delta + east_delta * east_delta) / NM
    local angels = math.floor(((p.y or 0) * 3.28084) / 1000 + 0.5)
    return brg, rng_nm, angels
end

-- Deliberately task-blind: the cue informs, the human judges.
local function nearest_hostile(base_vec2, enemy_side, max_dist_m)
    local best_p, best_d
    for _, category in ipairs({ Group.Category.AIRPLANE, Group.Category.HELICOPTER }) do
        local ok, groups = pcall(coalition.getGroups, enemy_side, category)
        if ok and groups then
            for _, grp in ipairs(groups) do
                local units = grp:getUnits()
                if units then
                    for _, u in ipairs(units) do
                        if u:isExist() and u:getLife() > 0 then
                            local p = u:getPoint()
                            local dx = p.x - base_vec2.x
                            local dz = p.z - base_vec2.y
                            local d = math.sqrt(dx * dx + dz * dz)
                            if d <= max_dist_m and (not best_d or d < best_d) then
                                best_p, best_d = p, d
                            end
                        end
                    end
                end
            end
        end
    end
    return best_p
end

local function setup_player_alerts(records)
    if not records or #records == 0 then return end

    local bases = {}
    for _, rec in ipairs(records) do
        local airbase = AIRBASE:FindByName(rec.airbaseName)
        local own_side = COALITION_SIDE[rec.coalition]
        if airbase and own_side then
            local enemy_side = (own_side == coalition.side.BLUE)
                and coalition.side.RED or coalition.side.BLUE
            local scramble_nm = tonumber(rec.scrambleRadiusNm) or 60
            bases[#bases + 1] = {
                name = rec.airbaseName,
                vec2 = airbase:GetVec2(),
                own_side = own_side,
                enemy_side = enemy_side,
                cue_radius_m = (scramble_nm + PLAYER_SCRAMBLE_LEAD_NM) * NM,
            }
        end
    end
    if #bases == 0 then return end

    local last_alert = {}

    local function scan()
        local now = timer.getTime()
        for _, b in ipairs(bases) do
            local hostile = nearest_hostile(b.vec2, b.enemy_side, b.cue_radius_m)
            if hostile then
                local last = last_alert[b.name] or -1e9
                if now - last >= PLAYER_ALERT_REPEAT then
                    last_alert[b.name] = now
                    local brg, rng, angels = alert_bearing_range(b.vec2, hostile)
                    local msg = string.format(
                        "QRA SCRAMBLE -- %s: bandits %03d for %d nm, angels %d. Launch when ready.",
                        b.name, math.floor(brg + 0.5), math.floor(rng + 0.5), angels)
                    trigger.action.outTextForCoalition(b.own_side, msg, PLAYER_ALERT_DURATION)
                end
            end
        end
        schedule_once(scan, timer.getTime() + PLAYER_ALERT_INTERVAL)
    end

    schedule_once(scan, timer.getTime() + BUILD_DELAY + 2)
end

if dcsRetribution.Intercept then
    local blue = dcsRetribution.Intercept.BLUE or {}
    local red = dcsRetribution.Intercept.RED or {}
    build_gcicap("BLUE", blue)
    build_gcicap("RED", red)

    setup_player_alerts(dcsRetribution.Intercept.PLAYER_ALERT or {})

    if #blue > 0 or #red > 0 then
        schedule_once(refresh_survivors, timer.getTime() + 15)
    end
end

-- Test hook for tests/lua/test_intercept_filter.py. The DCS plugin loader discards
-- a chunk's return value, so this is inert in-mission.
return {
    pattern_escape = lua_pattern_escape,
    group_reacts = qra_group_reacts,
    cluster_has_react = qra_cluster_has_react,
    scramble_stack_offset = scramble_stack_offset,
    defenders_for_raid = defenders_for_raid,
    shape_air_start = shape_air_start,
}
