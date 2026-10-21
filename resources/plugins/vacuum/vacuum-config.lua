---------------------------------------------------------------------------------------------------
-- Vacuum ELINT (§118). docs/dev/retlab-features.md §118
--
-- Reads dcsRetribution.vacuum (emitted only when a blue Vacuum flies): callsign, frequency,
--   strike (when an ABCCC runs STRIKE), voice, linkHost, linkPort, rangeMeters, groups = {...},
--   emitters = { { label, units = {...}, strike } }
--
-- While a Vacuum is alive AND airborne, each red radar within range is called once each time it
-- comes on: "Vacuum, new emitter, SA-6, bullseye 090, 25." A radar must stay off a full minute
-- before it counts as a new on-cycle, so a site blinking under Skynet is one call. Every call goes
-- on Vacuum's own frequency; it goes on STRIKE too only for a radar whose threat ring covers a
-- player package's route or target. SkyEye speaks the calls and works out the magnetic bullseye
-- from its own picture. Nothing is said with no Vacuum airborne. It never jams or lases.
---------------------------------------------------------------------------------------------------

if not (dcsRetribution and dcsRetribution.vacuum) then
    return
end

local data = dcsRetribution.vacuum
local POLL_SECONDS = 10
local SEND_SECONDS = 8
local TUNE_SECONDS = 60
local OFF_RESET_SECONDS = 60
local RANGE = tonumber(data.rangeMeters) or (250 * 1852)
local emitters = data.emitters or {}
-- Casual radio discipline (§121): only the radars that threaten a player package.
if dcsRetribution.radioDiscipline == "casual" then
    local threats = {}
    for _, e in ipairs(emitters) do
        if e.strike == "true" then
            table.insert(threats, e)
        end
    end
    emitters = threats
end

local function airborneVacuum()
    for _, name in ipairs(data.groups or {}) do
        local g = Group.getByName(name)
        if g and g:isExist() then
            for _, u in ipairs(g:getUnits() or {}) do
                if u and u:isExist() and u:getLife() > 0 and u:inAir() then
                    return u
                end
            end
        end
    end
    return nil
end

local function distance2d(a, b)
    local dx, dz = a.x - b.x, a.z - b.z
    return math.sqrt(dx * dx + dz * dz)
end

-- The first unit of an emitter that is radiating within range of Vacuum, or nil.
local function radiating(emitter, vacuum)
    local from = vacuum:getPoint()
    for _, name in ipairs(emitter.units or {}) do
        local u = Unit.getByName(name)
        if u and u:isExist() and u:getLife() > 0 then
            local ok, on = pcall(function()
                return u:getRadar()
            end)
            if ok and on and distance2d(u:getPoint(), from) <= RANGE then
                return u
            end
        end
    end
    return nil
end

---------------------------------------------------------------------------------------------------
-- SkyEye link
---------------------------------------------------------------------------------------------------

local function jsonValue(value)
    if type(value) == "number" then
        return string.format("%.6f", value)
    elseif type(value) == "table" then
        local items = {}
        for _, item in ipairs(value) do
            table.insert(items, jsonValue(item))
        end
        return "[" .. table.concat(items, ",") .. "]"
    end
    local escaped = tostring(value):gsub('[%c"\\]', function(c)
        if c == '"' then
            return '\\"'
        elseif c == "\\" then
            return "\\\\"
        end
        return string.format("\\u%04x", string.byte(c))
    end)
    return '"' .. escaped .. '"'
end

local function jsonObject(fields)
    local parts = {}
    for _, kv in ipairs(fields) do
        table.insert(parts, jsonValue(kv[1]) .. ":" .. jsonValue(kv[2]))
    end
    return "{" .. table.concat(parts, ",") .. "}"
end

local function openLink()
    if not (package and require) then
        return nil
    end
    local ok, socket = pcall(function()
        package.path = package.path .. ";.\\LuaSocket\\?.lua;"
        package.cpath = package.cpath .. ";.\\LuaSocket\\?.dll;"
        return require("socket")
    end)
    if not ok or not socket then
        env.warning("vacuum: LuaSocket unavailable, Vacuum stays silent: " .. tostring(socket))
        return nil
    end
    local udp = socket.udp()
    udp:settimeout(0)
    udp:setsockname("127.0.0.1", 0)
    return udp
end

local link = openLink()

local function send(fields)
    if link then
        link:sendto(jsonObject(fields), data.linkHost or "127.0.0.1", tonumber(data.linkPort) or 42690)
    end
end

local function frequencies(emitter)
    local list = { data.frequency }
    if emitter == nil or emitter.strike == "true" then
        if data.strike and data.strike ~= "" then
            table.insert(list, data.strike)
        end
    end
    return list
end

---------------------------------------------------------------------------------------------------
-- The watch
---------------------------------------------------------------------------------------------------

local queue = {}
local lastTune = nil

local function reset()
    for _, e in ipairs(emitters) do
        e.on = false
        e.offSince = nil
    end
    queue = {}
end

local function watch(vacuum, now)
    for _, e in ipairs(emitters) do
        local unit = radiating(e, vacuum)
        if unit then
            e.offSince = nil
            if not e.on then
                e.on = true
                table.insert(queue, e)
            end
        elseif e.on then
            e.offSince = e.offSince or now
            if now - e.offSince >= OFF_RESET_SECONDS then
                e.on = false
                e.offSince = nil
            end
        end
    end
end

local function speakNext(vacuum)
    while #queue > 0 do
        local e = table.remove(queue, 1)
        local unit = radiating(e, vacuum)
        if unit then
            local lat, lon = coord.LOtoLL(unit:getPoint())
            send({
                { "type", "emitter" },
                { "frequencies", frequencies(e) },
                { "callsign", data.callsign or "Vacuum" },
                { "voice", data.voice or "" },
                { "label", e.label },
                { "lat", lat },
                { "lon", lon },
            })
            return
        end
    end
end

local function tick(_, now)
    local vacuum = airborneVacuum()
    if not vacuum then
        reset()
        lastTune = nil
        return now + POLL_SECONDS
    end
    if lastTune == nil or now - lastTune >= TUNE_SECONDS then
        send({ { "type", "tune" }, { "frequencies", frequencies(nil) } })
        lastTune = now
    end
    watch(vacuum, now)
    return now + POLL_SECONDS
end

local function speaker(_, now)
    local vacuum = airborneVacuum()
    if vacuum then
        speakNext(vacuum)
    end
    return now + SEND_SECONDS
end

timer.scheduleFunction(tick, nil, timer.getTime() + POLL_SECONDS)
timer.scheduleFunction(speaker, nil, timer.getTime() + POLL_SECONDS + 1)
