-- The MIST functions Skynet IADS calls, on the plain DCS API, for when MIST is not loaded.
-- RetLab is removing MIST (docs/dev/design/retlab-mist-removal-notes.md); Skynet stays
-- byte-for-byte as vendored, so it gets this instead.
--
--  * Inert while the real MIST is loaded: `mist` already exists and is left alone.
--  * Only what skynet-iads-compiled.lua calls. A Skynet update that calls another mist.*
--    function needs it added here; tests/lua/test_skynet_mist_compat.py checks the list.
--  * No 100 Hz loop and no copy of the mission: scheduled functions are DCS timers, and
--    the DBs hold names only, built once.
--  * Ports keep MIST's own behavior (groupToRandomZone's route shape, getRandPointInCircle's
--    inner radius): Skynet's shoot-and-scoot was tuned against it.

if mist ~= nil then
    return
end

mist = { utils = {}, ground = {}, DBs = {} }

-- Numbers and units ------------------------------------------------------------------------

function mist.utils.round(num, idp)
    local mult = 10 ^ (idp or 0)
    return math.floor(num * mult + 0.5) / mult
end

function mist.utils.toDegree(angle)
    return angle * 180 / math.pi
end

function mist.utils.metersToNM(meters)
    return meters / 1852
end

function mist.utils.metersToFeet(meters)
    return meters / 0.3048
end

function mist.utils.kmphToMps(kmph)
    return kmph / 3.6
end

-- An integer in [low, high] (MIST's form: one argument means [1, n]).
function mist.random(low, high)
    if not high then
        low, high = 1, low
    end
    return math.random(low, high)
end

-- Points (a Vec2's y is a Vec3's z) --------------------------------------------------------

function mist.utils.makeVec2(vec)
    if vec.z then
        return { x = vec.x, y = vec.z }
    end
    return { x = vec.x, y = vec.y }
end

function mist.utils.makeVec3(vec, y)
    if vec.z then
        return { x = vec.x, y = vec.y, z = vec.z }
    end
    return { x = vec.x, y = y or vec.alt or 0, z = vec.y }
end

function mist.utils.get2DDist(point1, point2)
    local p1, p2 = mist.utils.makeVec3(point1), mist.utils.makeVec3(point2)
    return math.sqrt((p1.x - p2.x) ^ 2 + (p1.z - p2.z) ^ 2)
end

function mist.utils.get3DDist(point1, point2)
    return math.sqrt((point1.x - point2.x) ^ 2 + (point1.y - point2.y) ^ 2 + (point1.z - point2.z) ^ 2)
end

local function northCorrection(point)
    local p = mist.utils.makeVec3(point)
    local lat, lon = coord.LOtoLL(p)
    local north = coord.LLtoLO(lat + 1, lon)
    return math.atan2(north.z - p.z, north.x - p.x)
end

local function wrap2Pi(angle)
    if angle < 0 then
        return angle + 2 * math.pi
    end
    return angle
end

function mist.getHeading(unit, rawHeading)
    local pos = unit:getPosition()
    if pos then
        local heading = math.atan2(pos.x.z, pos.x.x)
        if not rawHeading then
            heading = heading + northCorrection(pos.p)
        end
        return wrap2Pi(heading)
    end
end

function mist.utils.getHeadingPoints(point1, point2, north)
    local p1, p2 = mist.utils.makeVec3(point1), mist.utils.makeVec3(point2)
    local dir = math.atan2(p2.z - p1.z, p2.x - p1.x)
    if north then
        dir = dir + northCorrection(p1)
    end
    return wrap2Pi(dir)
end

-- The first living unit's position.
function mist.getLeadPos(group)
    if type(group) == "string" then
        group = Group.getByName(group)
    end
    if not group then
        return nil
    end
    for _, unit in ipairs(group:getUnits() or {}) do
        if unit:isExist() then
            return unit:getPoint()
        end
    end
end

-- A random point in the ring innerRadius..r around p, uniform over its area. Vec2 out.
function mist.getRandPointInCircle(p, r, innerRadius)
    local point = mist.utils.makeVec3(p)
    local radius = r or 1000
    local minR = innerRadius or 0
    if radius <= 0 then
        return { x = point.x, y = point.z }
    end
    if minR > radius then
        minR = 0
    end
    local theta = 2 * math.pi * math.random()
    local dist = math.sqrt(minR ^ 2 + (radius ^ 2 - minR ^ 2) * math.random())
    return { x = point.x + math.cos(theta) * dist, y = point.z + math.sin(theta) * dist }
end

-- Highest minus lowest ground within searchSize of a point.
function mist.terrainHeightDiff(point, searchSize)
    local radius = searchSize or 5
    local c = mist.utils.makeVec2(point)
    local high = land.getHeight(c)
    local low = high
    for deg = 0, 360, 30 do
        local s, co = math.sin(math.rad(deg)), math.cos(math.rad(deg))
        local rings = radius >= 20 and { radius, radius / 2 } or { radius }
        for _, ring in ipairs(rings) do
            local h = land.getHeight({ x = c.x + s * ring, y = c.y + co * ring })
            high = math.max(high, h)
            low = math.min(low, h)
        end
    end
    return mist.utils.round(high - low, 2)
end

-- Scheduling --------------------------------------------------------------------------------

local tasks = {} -- our id -> DCS timer id
local lastTaskId = 0

-- f(unpack(vars)) at model time t, then every rep seconds if rep is set, until stopTime.
-- Errors are logged and the repeat carries on, as in MIST.
function mist.scheduleFunction(f, vars, t, rep, stopTime)
    vars = vars or {}
    lastTaskId = lastTaskId + 1
    local id = lastTaskId
    tasks[id] = timer.scheduleFunction(function(_, now)
        if stopTime and now >= stopTime then
            tasks[id] = nil
            return nil
        end
        local ok, err = pcall(f, unpack(vars, 1, table.maxn(vars)))
        if not ok then
            env.error("Skynet mist compat: scheduled function error: " .. tostring(err))
        end
        if rep and tasks[id] then
            return now + rep
        end
        tasks[id] = nil
        return nil
    end, nil, t)
    return id
end

function mist.removeFunction(id)
    local timerId = tasks[id]
    if not timerId then
        return false
    end
    tasks[id] = nil
    pcall(timer.removeFunction, timerId)
    return true
end

-- Ground moves (MIST's route shape) --------------------------------------------------------

local FORMATIONS = {
    ["off road"] = "Off Road", off_road = "Off Road",
    ["on road"] = "On Road", on_road = "On Road",
    rank = "Rank", ["line abrest"] = "Rank", line_abrest = "Rank", lineabrest = "Rank",
    cone = "Cone", diamond = "Diamond", vee = "Vee",
    ["echelon left"] = "EchelonL", echelonl = "EchelonL",
    ["echelon right"] = "EchelonR", echelonr = "EchelonR",
}

function mist.ground.buildWP(point, form, speed)
    return {
        x = point.x,
        y = point.z or point.y,
        speed = speed or mist.utils.kmphToMps(20),
        action = FORMATIONS[string.lower(form or "cone")] or "Cone",
        type = "Turning Point",
        ETA = 0,
        ETA_locked = false,
        speed_locked = true,
    }
end

local function goRoute(group, path)
    local controller = group and group:getController()
    if controller then
        controller:setTask({ id = "Mission", params = { route = { points = path } } })
    end
end

-- Drive a group to a random point in zone {point = Vec3, radius}. Speed in km/h.
function mist.groupToRandomZone(group, zone, form, heading, speed, disableRoads)
    if type(group) == "string" then
        group = Group.getByName(group)
    end
    if type(zone) == "string" then
        zone = mist.DBs.zonesByName[zone]
    elseif type(zone) == "table" and not zone.radius then
        zone = mist.DBs.zonesByName[zone[math.random(1, #zone)]]
    end
    if not (group and zone) then
        return
    end
    local mps = speed and mist.utils.kmphToMps(speed) or mist.utils.kmphToMps(20)
    local center = mist.utils.makeVec3(zone.point)
    local radius = zone.radius or 0
    form = form or "Cone"
    heading = heading and math.rad(heading) or math.random() * 2 * math.pi

    local dest = mist.getRandPointInCircle(center, radius)
    local offset = {
        x = mist.utils.round(math.sin(heading - math.pi / 2) * 50 + dest.x, 3),
        z = mist.utils.round(math.cos(heading + math.pi / 2) * 50 + dest.y, 3),
    }
    local path = {}
    local start = mist.getLeadPos(group)
    if start then
        path[#path + 1] = mist.ground.buildWP(start, form, mps)
        local far = math.sqrt((center.x - start.x) ^ 2 + (center.z - start.z) ^ 2) > radius * 1.3
        if not disableRoads and far then
            path[#path + 1] = mist.ground.buildWP({ x = start.x + 11, z = start.z + 11 }, "off_road", mps)
            path[#path + 1] = mist.ground.buildWP(start, "on_road", mps)
            path[#path + 1] = mist.ground.buildWP(offset, "on_road", mps)
        else
            path[#path + 1] = mist.ground.buildWP({ x = start.x + 25, z = start.z + 25 }, form, mps)
        end
    end
    path[#path + 1] = mist.ground.buildWP(offset, form, mps)
    path[#path + 1] = mist.ground.buildWP(dest, form, mps)
    goRoute(group, path)
end

-- Name lookups (Skynet's *ByPrefix and scoot-zone paths). Names only, from env.mission. ----

do
    local units, groups, zones = {}, {}, {}
    for _, side in pairs(env.mission.coalition or {}) do
        for _, country in pairs(side.country or {}) do
            for _, category in ipairs({ "plane", "helicopter", "vehicle", "ship", "static" }) do
                for _, group in pairs(country[category] and country[category].group or {}) do
                    groups[env.getValueDictByKey(group.name)] = true
                    for _, unit in pairs(group.units or {}) do
                        units[env.getValueDictByKey(unit.name)] = true
                    end
                end
            end
        end
    end
    for _, zone in pairs(env.mission.triggers and env.mission.triggers.zones or {}) do
        zones[zone.name] = {
            point = { x = zone.x, y = land.getHeight({ x = zone.x, y = zone.y }), z = zone.y },
            radius = zone.radius,
        }
    end
    mist.DBs.unitsByName, mist.DBs.groupsByName, mist.DBs.zonesByName = units, groups, zones
end
