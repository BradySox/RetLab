---------------------------------------------------------------------------------------------------
-- Vacuum ELINT (§118). docs/dev/retlab-features.md §118
--
-- Reads dcsRetribution.vacuum (emitted only when a blue Vacuum flies): callsign, frequency,
--   strike (when an ABCCC runs STRIKE), voice, linkHost, linkPort, rangeMeters, groups = {...},
--   emitters = { { label, units = {...}, sam, strike, reach, known, knownError } },
--   flights = { { group, callsign, targetX, targetY } } (the player flights that may call it)
--
-- While a Vacuum is alive AND airborne, each red radar within range is called once each time it
-- comes on: "Vacuum, SA-6 awake, bullseye 304, 60, loose." A radar must stay off a full minute
-- before it counts as a new on-cycle, so a site blinking under Skynet is one call. Vacuum remembers
-- every radar it has located: off now, it is "asleep". Each fix is "loose" until Vacuum has heard
-- the radar long enough, added up across blinks, to call it "tight" (within about 1 NM); a loose
-- radar that goes tight while on is called once more. Every radar Vacuum hears is written to
-- vacuum_fixes for the debrief, which reveals it on the map after the turn. Every call goes
-- on Vacuum's own frequency; it goes on STRIKE too only for a radar whose threat ring covers a
-- player package's route or target. SkyEye speaks the calls and works out the magnetic bullseye
-- from its own picture. Nothing is said with no Vacuum airborne. It never jams or lases.
--
-- Players call it through SkyEye ("Vacuum, Ford 9, say emitters"): check in, emitters, target
-- status, mud <bearing>, say again. SkyEye sends each as an elintRequest and the answer is a say
-- line on the frequency the call came in on. Answers name awake and asleep radars; mud names only
-- awake ones. An older SkyEye never sends a request, so these answers simply never happen.
--
-- Vacuum speaks of SAMs only (sam = "true"): an early warning or search radar is heard and its fix
-- written to vacuum_fixes, so the site is still revealed, but no call or answer ever names it.
---------------------------------------------------------------------------------------------------

if not (dcsRetribution and dcsRetribution.vacuum) then
    return
end

local data = dcsRetribution.vacuum
local POLL_SECONDS = 10
local SEND_SECONDS = 8
local TUNE_SECONDS = 60
local OFF_RESET_SECONDS = 60
local LINK_POLL_SECONDS = 1
local NM = 1852
local RANGE = tonumber(data.rangeMeters) or (250 * NM)
-- A target-area radar: inside its own threat ring of the target, or this close to it.
local TARGET_AREA_METERS = 15 * NM
-- A mud bearing matches a radar this many degrees either side.
local MUD_DEGREES = 15
local MAX_ANSWERED = 3
-- Answers use every radar; only the unprompted calls are thinned under Casual.
local allEmitters = data.emitters or {}
local emitters = allEmitters
-- Casual radio discipline (§121): only the radars that threaten a player package.
if dcsRetribution.radioDiscipline == "casual" then
    local threats = {}
    for _, e in ipairs(allEmitters) do
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
                -- A late-activated air start exists and reads inAir before it activates (Test 63).
                local ok, active = pcall(function()
                    return u:isActive()
                end)
                if u and u:isExist() and ok and active and u:getLife() > 0 and u:inAir() then
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
-- Fixes
---------------------------------------------------------------------------------------------------

-- A first fix is off by about 1 NM plus 1 NM per 10 NM from Vacuum, 15 at most, and closes to
-- the radar's spot after 20 s heard in total up close, 90 s at 150 NM or more (Brady's call,
-- 2026-10-22: Skynet keeps radars dark, so the listening adds up across blinks). The error is
-- real and always the same way for a site, so repeat calls agree. Asleep, a fix stays put.
local TIGHT_METERS = 1 * NM
local KNOWN_LOOSE_METERS = 10 * NM

local function firstFix(distance)
    return math.min(NM + distance / 10, 15 * NM)
end

local function secondsToTight(distance)
    return 20 + 70 * math.min(distance / (150 * NM), 1)
end

local function errorOf(e)
    return (e.startError or 0) * (1 - (e.progress or 0))
end

local function fixWord(e)
    return errorOf(e) <= TIGHT_METERS and "tight" or "loose"
end

-- The direction a site's fix is off, from its name: the same every call and every mission.
local function errorAngle(e)
    local sum = 0
    for i = 1, #tostring(e.label) do
        sum = sum + string.byte(e.label, i) * i
    end
    for _, name in ipairs(e.units or {}) do
        for i = 1, #name do
            sum = sum + string.byte(name, i) * i
        end
    end
    return (sum % 360) * math.pi / 180
end

local function liveUnit(e)
    for _, name in ipairs(e.units or {}) do
        local u = Unit.getByName(name)
        if u and u:isExist() and u:getLife() > 0 then
            return u
        end
    end
    return nil
end

local function locate(e, point)
    e.fixed = true
    e.point = { x = point.x, y = point.y, z = point.z }
    e.angle = e.angle or errorAngle(e)
end

-- Sites blue already knows start asleep: a fixed SAM tight, the rest loose, each at the fix an
-- earlier Vacuum left (knownError) when there is one.
for _, e in ipairs(allEmitters) do
    local u = (e.known == "tight" or e.known == "loose") and liveUnit(e)
    if u then
        locate(e, u:getPoint())
        local default = e.known == "tight" and 0 or KNOWN_LOOSE_METERS
        e.startError = tonumber(e.knownError) or default
        e.progress = 0
    end
end

-- Read by the base plugin's state writer: { unit, error } per radar heard this mission.
vacuum_fixes = vacuum_fixes or {}

local function record(e)
    local err = math.floor(errorOf(e) + 0.5)
    if not e.record then
        e.record = { unit = (e.units or {})[1] or "", error = err }
        table.insert(vacuum_fixes, e.record)
        dirty_state = true
    elseif math.floor(err / NM) < math.floor(e.record.error / NM) then
        e.record.error = err
        dirty_state = true
    else
        e.record.error = err
    end
end

-- Vacuum heard this radar for `seconds` from `vacuum`.
local function hear(e, unit, vacuum, seconds)
    local distance = distance2d(unit:getPoint(), vacuum:getPoint())
    local first = firstFix(distance)
    if not e.fixed or errorOf(e) > first then
        e.startError = first
        e.progress = 0
    end
    locate(e, unit:getPoint())
    e.progress = math.min(1, (e.progress or 0) + seconds / secondsToTight(distance))
    record(e)
end

-- Where Vacuum puts the radar: its spot, off by the fix error.
local function calledPoint(e)
    local err = errorOf(e)
    return { x = e.point.x + math.cos(e.angle) * err, y = e.point.y, z = e.point.z + math.sin(e.angle) * err }
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
-- Answers to players
---------------------------------------------------------------------------------------------------

local NUMBER_WORDS = { "one", "two", "three", "four", "five", "six", "seven", "eight", "nine" }

local function normalize(callsign)
    return (tostring(callsign):lower():gsub("[^%w]", ""))
end

local callers = {}
for _, f in ipairs(data.flights or {}) do
    f.key = normalize(f.callsign)
    -- "ford91" -> "ford9": the flight; "ford92" is its ship 2.
    f.prefix = f.key:sub(1, -2)
    table.insert(callers, f)
end

-- The flight and ship a heard callsign is, as voiceatc's findFlight reads it: the whole seat,
-- then the flight alone ("ford 9" is Ford 9-1), then a ship ("ford 9 2").
local function findCaller(callsign)
    local key = normalize(callsign or "")
    if key == "" then
        return nil, nil
    end
    for _, f in ipairs(callers) do
        if key == f.key then
            return f, tonumber(key:sub(-1)) or 1
        end
    end
    for _, f in ipairs(callers) do
        if key == f.prefix then
            return f, 1
        end
    end
    local ship = tonumber(key:sub(-1))
    for _, f in ipairs(callers) do
        if ship and key:sub(1, -2) == f.prefix then
            return f, ship
        end
    end
    return nil, nil
end

-- The caller's jet: its own seat if alive, else any live jet of the flight.
local function callerUnit(flight, ship)
    local g = Group.getByName(flight.group)
    if not (g and g:isExist()) then
        return nil
    end
    local first = nil
    for index, u in ipairs(g:getUnits() or {}) do
        if u and u:isExist() and u:getLife() > 0 then
            local ok, number = pcall(function()
                return u:getNumber()
            end)
            if (ok and tonumber(number) or index) == ship then
                return u
            end
            first = first or u
        end
    end
    return first
end

-- "ford 9" -> Ford 9, "viper 1 1" -> Viper 1-1 (spoken "Viper 1 1"): the caller as heard.
local function callerPart(heard)
    local words, digits = {}, {}
    for w in tostring(heard):gmatch("%S+") do
        if w:match("^%d+$") then
            table.insert(digits, w)
        else
            table.insert(words, w:sub(1, 1):upper() .. w:sub(2))
        end
    end
    local name = table.concat(words, " ")
    if #digits == 0 then
        return { name, name }
    end
    return { name .. " " .. table.concat(digits, "-"), name .. " " .. table.concat(digits, " ") }
end

local function declination()
    local ok, value = pcall(function()
        return UTILS.GetMagneticDeclination()
    end)
    if ok and tonumber(value) then
        return tonumber(value)
    end
    return tonumber(data.declination) or 0
end

-- True bearing by great circle from lat/lon. The map grid is not aligned to true north: on
-- GermanyCW at 9E it is about 9 degrees off, and grid bearings read 9 high (Test 65).
local function trueBearing(from, to)
    local ok, lat1, lon1, lat2, lon2 = pcall(function()
        local a1, o1 = coord.LOtoLL(from)
        local a2, o2 = coord.LOtoLL(to)
        return a1, o1, a2, o2
    end)
    if not (ok and tonumber(lat1) and tonumber(lat2)) then
        return math.deg(math.atan2(to.z - from.z, to.x - from.x))
    end
    local p1, p2 = math.rad(lat1), math.rad(lat2)
    local dl = math.rad(lon2 - lon1)
    local y = math.sin(dl) * math.cos(p2)
    local x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return math.deg(math.atan2(y, x))
end

-- Magnetic bearing (whole degrees, 1-360) and range in whole NM from one point to another.
local function bearingRange(from, to)
    local dx, dz = to.x - from.x, to.z - from.z
    local bearing = math.floor((trueBearing(from, to) - declination()) % 360 + 0.5)
    if bearing == 0 then
        bearing = 360
    end
    return bearing, math.floor(math.sqrt(dx * dx + dz * dz) / NM + 0.5)
end

local function angleOff(a, b)
    local d = math.abs(a - b) % 360
    return d > 180 and 360 - d or d
end

local function three(n)
    return string.format("%03d", n % 360 == 0 and 360 or n % 360)
end

-- Digit by digit, as SkyEye says a bearing: 270 -> "2 7 0".
local function spokenBearing(n)
    return (three(n):gsub("(%d)", "%1 "):gsub(" $", ""))
end

-- "SA-6" -> "S-A-6", which Piper reads letter by letter, as SkyEye's own calls do.
local function spokenLabel(label)
    return (tostring(label):gsub("(%u%u%u?)%-(%d+)", function(letters, number)
        return letters:gsub("(%u)", "%1-") .. number
    end))
end

-- A reply in two forms, as voiceatc builds them: each part is text, or { text, speech }.
local function line(parts)
    local text, speech = {}, {}
    for _, part in ipairs(parts) do
        if type(part) == "table" then
            table.insert(text, part[1])
            table.insert(speech, part[2])
        else
            table.insert(text, part)
            table.insert(speech, part)
        end
    end
    return { text = table.concat(text), speech = table.concat(speech) }
end

local function labelPart(label)
    return { label, spokenLabel(label) }
end

local function bullseyePart(point)
    local ok, bull = pcall(function()
        return coalition.getMainRefPoint(coalition.side.BLUE)
    end)
    if not (ok and type(bull) == "table" and bull.x) then
        return nil
    end
    local bearing, range = bearingRange(bull, point)
    if range <= 5 then
        return "at bullseye"
    end
    return { "bullseye " .. three(bearing) .. "/" .. range, "bullseye " .. spokenBearing(bearing) .. ", " .. range }
end

local function withBullseye(parts, point)
    local bull = bullseyePart(point)
    if bull then
        table.insert(parts, ", ")
        table.insert(parts, bull)
    end
end

-- Every SAM radar Vacuum has located and that still stands, awake ones first, each nearest a point
-- first. A radar on that has not been heard yet is located now.
local function locatedNear(vacuum, point)
    local out = {}
    for _, e in ipairs(allEmitters) do
        local unit = radiating(e, vacuum)
        if unit and not e.fixed then
            hear(e, unit, vacuum, 0)
        end
        if e.sam == "true" and e.fixed and liveUnit(e) then
            local p = calledPoint(e)
            table.insert(out, {
                label = e.label,
                point = p,
                reach = tonumber(e.reach) or 0,
                distance = distance2d(p, point),
                awake = unit ~= nil,
                fix = fixWord(e),
            })
        end
    end
    table.sort(out, function(a, b)
        if a.awake ~= b.awake then
            return a.awake
        end
        return a.distance < b.distance
    end)
    return out
end

local function awakeOnly(radars)
    local out = {}
    for _, r in ipairs(radars) do
        if r.awake then
            table.insert(out, r)
        end
    end
    return out
end

local function statusPart(radar)
    return radar.awake and " awake" or " asleep"
end

local function countWord(n)
    return n == 0 and "none" or (NUMBER_WORDS[n] or tostring(n))
end

local function checkInReply(me, from, vacuum)
    local radars = locatedNear(vacuum, from)
    if #radars == 0 then
        return line({ me, ", blank." })
    end
    local awake = #awakeOnly(radars)
    local parts = { me, ", " .. countWord(awake) .. " awake" }
    if #radars > awake then
        table.insert(parts, ", " .. countWord(#radars - awake) .. " asleep")
    end
    table.insert(parts, ", nearest ")
    table.insert(parts, labelPart(radars[1].label))
    table.insert(parts, statusPart(radars[1]))
    withBullseye(parts, radars[1].point)
    table.insert(parts, ", " .. radars[1].fix .. ".")
    return line(parts)
end

local function emittersReply(me, from, vacuum)
    local radars = locatedNear(vacuum, from)
    if #radars == 0 then
        return line({ me, ", blank." })
    end
    local parts = { me }
    for i = 1, math.min(MAX_ANSWERED, #radars) do
        local bearing, range = bearingRange(from, radars[i].point)
        table.insert(parts, i == 1 and ", " or "; ")
        table.insert(parts, labelPart(radars[i].label))
        table.insert(parts, statusPart(radars[i]))
        table.insert(parts, { " " .. three(bearing) .. ", " .. range, " " .. spokenBearing(bearing) .. ", " .. range })
        table.insert(parts, ", " .. radars[i].fix)
    end
    table.insert(parts, ".")
    return line(parts)
end

local function targetReply(me, flight, vacuum)
    local tx, ty = tonumber(flight.targetX), tonumber(flight.targetY)
    if not (tx and ty) then
        return line({ me, ", no target for you." })
    end
    local near = {}
    for _, r in ipairs(locatedNear(vacuum, { x = tx, y = 0, z = ty })) do
        if r.distance <= math.max(r.reach, TARGET_AREA_METERS) then
            table.insert(near, r)
        end
    end
    if #near == 0 then
        return line({ me, ", target area blank." })
    end
    local parts = { me, ", target area" }
    for i = 1, math.min(MAX_ANSWERED, #near) do
        table.insert(parts, i == 1 and ", " or "; ")
        table.insert(parts, labelPart(near[i].label))
        table.insert(parts, statusPart(near[i]))
        withBullseye(parts, near[i].point)
        table.insert(parts, ", " .. near[i].fix)
    end
    table.insert(parts, ".")
    return line(parts)
end

local function mudReply(me, from, vacuum, bearing)
    local wanted = tonumber(bearing)
    if not wanted then
        return line({ me, ", say mud bearing." })
    end
    local spoken = { three(wanted), spokenBearing(wanted) }
    local best, bestOff = nil, nil
    -- A spike on the RWR is a radar transmitting, so only awake ones.
    for _, r in ipairs(awakeOnly(locatedNear(vacuum, from))) do
        local off = angleOff((bearingRange(from, r.point)), wanted)
        if off <= MUD_DEGREES and (bestOff == nil or off < bestOff) then
            best, bestOff = r, off
        end
    end
    if not best then
        return line({ me, ", no emitter ", spoken, "." })
    end
    local parts = { me, ", mud ", spoken, " is ", labelPart(best.label), " awake" }
    withBullseye(parts, best.point)
    table.insert(parts, ", " .. best.fix .. ".")
    return line(parts)
end

local lastReply = {} -- caller seat -> line
local lastOnFrequency = {} -- frequency -> line

-- Vacuum answers on STRIKE when called there, else on its own frequency.
local function answerFrequency(heard)
    if data.strike and data.strike ~= "" and heard == data.strike then
        return heard
    end
    return data.frequency
end

-- No on-screen text: a request only arrives over the LuaSocket link, so every answer is spoken.
local function sayLine(frequency, call)
    lastOnFrequency[frequency] = call
    send({
        { "type", "say" },
        { "frequency", frequency },
        { "text", call.text },
        { "speech", call.speech },
        { "voice", data.voice or "" },
        { "speaker", data.callsign or "Vacuum" },
    })
end

local function handleRequest(request, vacuum)
    local frequency = answerFrequency(request.frequency)
    local speaker = data.callsign or "Vacuum"
    local flight, ship = findCaller(request.callsign)
    if not flight then
        return sayLine(frequency, line({ "Station calling ", speaker, ", say again your callsign." }))
    end
    local caller = callerPart(request.callsign)
    local me = { caller[1] .. ", " .. speaker, caller[2] .. ", " .. speaker }
    local seat = flight.key .. ship
    if request.kind == "sayagain" then
        local last = lastReply[seat] or lastOnFrequency[frequency]
        return sayLine(frequency, last or line({ me, ", nothing to say again." }))
    end
    local unit = callerUnit(flight, ship)
    if not unit then
        return
    end
    local from = unit:getPoint()
    local call
    if request.kind == "checkin" then
        call = checkInReply(me, from, vacuum)
    elseif request.kind == "emitters" then
        call = emittersReply(me, from, vacuum)
    elseif request.kind == "target" then
        call = targetReply(me, flight, vacuum)
    elseif request.kind == "mud" then
        call = mudReply(me, from, vacuum, request.bearing)
    else
        call = line({ me, ", say again." })
    end
    lastReply[seat] = call
    sayLine(frequency, call)
end

-- Reads the flat string fields of a SkyEye request.
local function jsonFields(text)
    local out = {}
    for key, value in tostring(text):gmatch('"([%w_]+)"%s*:%s*"([^"]*)"') do
        out[key] = value
    end
    return out
end

local function pollLink(_, now)
    if not (link and link.receivefrom) then
        return nil
    end
    while true do
        local datagram = link:receivefrom()
        if not datagram then
            break
        end
        local message = jsonFields(datagram)
        local vacuum = airborneVacuum()
        if message.type == "elintRequest" and vacuum then
            local ok, err = pcall(handleRequest, message, vacuum)
            if not ok then
                env.warning("vacuum: request failed: " .. tostring(err))
            end
        end
    end
    return now + LINK_POLL_SECONDS
end

---------------------------------------------------------------------------------------------------
-- The watch
---------------------------------------------------------------------------------------------------

local queue = {}
local lastTune = nil

for _, e in ipairs(emitters) do
    e.callable = e.sam == "true"
end

-- Fixes are kept: Vacuum remembers what it located even when it lands.
local function reset()
    for _, e in ipairs(allEmitters) do
        e.on = false
        e.offSince = nil
        e.queued = false
    end
    queue = {}
end

local function enqueue(e)
    if e.callable and not e.queued then
        e.queued = true
        table.insert(queue, e)
    end
end

local function watch(vacuum, now)
    for _, e in ipairs(allEmitters) do
        local unit = radiating(e, vacuum)
        if unit then
            hear(e, unit, vacuum, POLL_SECONDS)
            e.offSince = nil
            if not e.on then
                e.on = true
                enqueue(e)
            elseif fixWord(e) == "tight" and not e.toldTight then
                enqueue(e)
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

-- A queued radar is called while it is on or still in its on-cycle; one off longer stays queued
-- until it comes on again. Dropping it lost its tight call for good (Test 65, an SA-6).
local function speakNext(vacuum)
    local i = 1
    while i <= #queue do
        local e = queue[i]
        if not liveUnit(e) then
            table.remove(queue, i)
            e.queued = false
        elseif not (e.on or radiating(e, vacuum)) then
            i = i + 1
        else
            table.remove(queue, i)
            e.queued = false
            local fix = fixWord(e)
            if fix == "tight" then
                e.toldTight = true
            end
            local point = calledPoint(e)
            local lat, lon = coord.LOtoLL(point)
            -- Kept for "say again": SkyEye words the call itself from the same position.
            local call = { data.callsign or "Vacuum", ", ", labelPart(e.label), " awake" }
            withBullseye(call, point)
            table.insert(call, ", " .. fix .. ".")
            for _, f in ipairs(frequencies(e)) do
                lastOnFrequency[f] = line(call)
            end
            send({
                { "type", "emitter" },
                { "frequencies", frequencies(e) },
                { "callsign", data.callsign or "Vacuum" },
                { "voice", data.voice or "" },
                { "label", e.label },
                { "status", "awake" },
                { "fix", fix },
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
        -- callsign and frequency make SkyEye pass calls to Vacuum back here; an older one ignores them.
        send({
            { "type", "tune" },
            { "frequencies", frequencies(nil) },
            { "callsign", data.callsign or "Vacuum" },
            { "frequency", data.frequency },
        })
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
timer.scheduleFunction(pollLink, nil, timer.getTime() + LINK_POLL_SECONDS)
