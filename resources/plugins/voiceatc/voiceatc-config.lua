---------------------------------------------------------------------------------------------------
-- Voice ATC (§119). docs/dev/retlab-features.md §119
--
-- Reads dcsRetribution.voiceAtc (emitted only with the Voice ATC setting on and a player flight
-- at an airfield): linkHost, linkPort, declination,
-- and dcsRetribution.radioDiscipline (strict|relaxed|casual, §121),
--   fields = { { name, airbase, runway, altimeter, ground, tower, groundVoice, towerVoice } },
--   flights = { { group, callsign, squawk, departure, arrival, divert } }
--
-- Ground and Tower for player flights, through SkyEye's mission link: SkyEye hears the calls on
-- the field frequencies and this script decides every reply. Taxi with a squawk,
-- takeoff with wind and altimeter, landing, clear of the runway. Under Strict radio discipline a
-- rule bust (moving before taxi, taking off or landing without clearance) gets a scolding call and
-- nothing more: ATC never blocks a player (user call, 2026-10-20). An F10 ATC menu makes the same requests; without
-- LuaSocket it is the only way in and replies are text. AI traffic is left to DCS's own ATC.
---------------------------------------------------------------------------------------------------

if not (dcsRetribution and dcsRetribution.voiceAtc) then
    return
end

local data = dcsRetribution.voiceAtc
-- Radio discipline (§116-§119, user call 2026-10-20). Strict: readbacks checked, busts scolded.
-- Relaxed: any acknowledgement counts, only a wrong number is corrected, no scolding. Casual:
-- answer only when called, never expect a call, accept a loose call or a misheard callsign.
local DISCIPLINE = dcsRetribution.radioDiscipline or "strict"
local STRICT = DISCIPLINE == "strict"
local CASUAL = DISCIPLINE == "casual"
local LINK_POLL_SECONDS = 1
local ANNOUNCE_SECONDS = 30
local WATCH_SECONDS = 2
local TEXT_SECONDS = 15
local NM = 1852
-- Tower takes the landing call this close in; farther out it asks for a call at 5 NM.
local TOWER_RANGE_NM = 15
-- Faster than this on the ground is taxiing, about 6 kt.
local TAXI_MPS = 3
local KNOTS = 1.94384
local CALM_KT = 3

local S_EVENT_TAKEOFF = world.event.S_EVENT_TAKEOFF or 3
local S_EVENT_LAND = world.event.S_EVENT_LAND or 4
local S_EVENT_BIRTH = world.event.S_EVENT_BIRTH or 15

local fields = {}
local fieldsByName = {}
local stations = {} -- frequency string -> { field, position }
for _, f in ipairs(data.fields or {}) do
    table.insert(fields, f)
    fieldsByName[f.name] = f
    for _, position in ipairs({ "ground", "tower" }) do
        if f[position] and f[position] ~= "" then
            stations[f[position]] = { field = f, position = position }
        end
    end
end

local function normalize(callsign)
    return (tostring(callsign):lower():gsub("[^%w]", ""))
end

local flights = {}
for _, flight in ipairs(data.flights or {}) do
    flight.key = normalize(flight.callsign)
    -- "viper11" -> "viper1": a wingman is the same name and flight number, another ship.
    flight.prefix = flight.key:sub(1, -2)
    flight.state = "parked"
    flight.pending = {}
    flight.lastCall = {}
    flight.scolded = {}
    flight.landing = {}
    table.insert(flights, flight)
end

---------------------------------------------------------------------------------------------------
-- Words
---------------------------------------------------------------------------------------------------

local DIGIT_WORDS = {
    ["0"] = "zero",
    ["1"] = "one",
    ["2"] = "two",
    ["3"] = "three",
    ["4"] = "four",
    ["5"] = "five",
    ["6"] = "six",
    ["7"] = "seven",
    ["8"] = "eight",
    ["9"] = "niner",
}

-- "262.0" -> "two six two decimal zero"; "25L" -> "two five left".
local function spokenDigits(s)
    local words = {}
    for c in tostring(s):gmatch(".") do
        if DIGIT_WORDS[c] then
            table.insert(words, DIGIT_WORDS[c])
        elseif c == "." then
            table.insert(words, "decimal")
        elseif c == "L" then
            table.insert(words, "left")
        elseif c == "R" then
            table.insert(words, "right")
        elseif c == "C" then
            table.insert(words, "center")
        end
    end
    return table.concat(words, " ")
end

-- "Viper 1-1" -> "Viper one one".
local function spokenCallsign(callsign)
    local name, digits = tostring(callsign):match("^(.-)%s*([%d%-]+)$")
    if not name then
        return tostring(callsign)
    end
    return name .. " " .. spokenDigits((digits:gsub("%-", "")))
end

-- A frequency as a controller writes it: "262.000AM" -> "262.0", "270.450AM" -> "270.45".
local function frequencyLabel(frequency)
    local mhz = tonumber(tostring(frequency):match("^[%d%.]+"))
    if not mhz then
        return tostring(frequency)
    end
    local label = string.format("%.3f", mhz):gsub("0+$", "")
    if label:sub(-1) == "." then
        label = label .. "0"
    end
    return label
end

-- A line in two forms: the text shown to the flight, and the words SkyEye speaks. Each part is
-- plain text, or { text, speech } for a number Piper would read as an amount.
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

-- A line as one { text, speech } part, to put inside another line.
local function phrase(parts)
    local l = line(parts)
    return { l.text, l.speech }
end

local function digits(s)
    return { tostring(s), spokenDigits(s) }
end

local function callsignPart(callsign)
    return { callsign, spokenCallsign(callsign) }
end

---------------------------------------------------------------------------------------------------
-- SkyEye link
---------------------------------------------------------------------------------------------------

local function jsonString(s)
    local escaped = tostring(s):gsub('[%c"\\]', function(c)
        if c == '"' then
            return '\\"'
        elseif c == "\\" then
            return "\\\\"
        end
        return string.format("\\u%04x", string.byte(c))
    end)
    return '"' .. escaped .. '"'
end

local function jsonObject(pairsList)
    local parts = {}
    for _, kv in ipairs(pairsList) do
        local key, value = kv[1], kv[2]
        local encoded
        if type(value) == "table" then
            local items = {}
            for _, item in ipairs(value) do
                if type(item) == "table" then
                    table.insert(items, jsonObject(item))
                else
                    table.insert(items, jsonString(item))
                end
            end
            encoded = "[" .. table.concat(items, ",") .. "]"
        else
            encoded = jsonString(value)
        end
        table.insert(parts, jsonString(key) .. ":" .. encoded)
    end
    return "{" .. table.concat(parts, ",") .. "}"
end

-- Reads the flat string fields of a SkyEye request.
local function jsonFields(text)
    local out = {}
    for key, value in tostring(text):gmatch('"([%w_]+)"%s*:%s*"([^"]*)"') do
        out[key] = value
    end
    return out
end

local link = nil

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
        env.warning("voiceatc: LuaSocket unavailable, ATC answers the F10 menu in text only: " .. tostring(socket))
        return nil
    end
    local udp = socket.udp()
    udp:settimeout(0)
    udp:setsockname("127.0.0.1", 0)
    return udp
end

local function send(message)
    if link then
        link:sendto(jsonObject(message), data.linkHost or "127.0.0.1", tonumber(data.linkPort) or 42690)
    end
end

local function announce(_, now)
    local list = {}
    for _, f in ipairs(fields) do
        local positions = {}
        for _, position in ipairs({ "ground", "tower" }) do
            if f[position] and f[position] ~= "" then
                table.insert(positions, { { "position", position }, { "frequency", f[position] } })
            end
        end
        table.insert(list, { { "name", f.name }, { "positions", positions } })
    end
    send({ { "type", "atc" }, { "fields", list }, { "discipline", DISCIPLINE } })
    return now + ANNOUNCE_SECONDS
end

---------------------------------------------------------------------------------------------------
-- Flights
---------------------------------------------------------------------------------------------------

local function liveUnits(groupName)
    local g = Group.getByName(groupName)
    if not (g and g:isExist()) then
        return {}
    end
    local alive = {}
    for _, u in ipairs(g:getUnits() or {}) do
        if u and u:isExist() and u:getLife() > 0 then
            table.insert(alive, u)
        end
    end
    return alive
end

local function playerUnits(flight)
    local out = {}
    for index, u in ipairs(liveUnits(flight.group)) do
        local ok, name = pcall(function()
            return u:getPlayerName()
        end)
        if ok and name and name ~= "" then
            table.insert(out, { unit = u, member = index })
        end
    end
    return out
end

-- The flight and ship number a heard callsign is: "viper 1 1" is the lead, "viper 1 2" ship 2.
-- The flight callsign alone, "viper 1", is the lead: the AWACS and ABCCC cards teach it.
local function findFlight(callsign)
    local key = normalize(callsign or "")
    if key == "" then
        return nil, nil
    end
    for _, flight in ipairs(flights) do
        if key == flight.key or key == flight.prefix then
            return flight, 1
        end
        local member = tonumber(key:sub(-1))
        if member and key:sub(1, -2) == flight.prefix then
            return flight, member
        end
    end
    return nil, nil
end

local function memberCallsign(flight, member)
    if member == 1 then
        return flight.callsign
    end
    return (tostring(flight.callsign):gsub("%d$", tostring(member)))
end

local function memberOf(flight, unit)
    local name = unit:getName()
    for index, u in ipairs(liveUnits(flight.group)) do
        if u:getName() == name then
            return index
        end
    end
    return 1
end

local function flightOfUnit(unit)
    local ok, group = pcall(function()
        return unit:getGroup()
    end)
    if not (ok and group) then
        return nil
    end
    local name = group:getName()
    for _, flight in ipairs(flights) do
        if flight.group == name then
            return flight
        end
    end
    return nil
end

---------------------------------------------------------------------------------------------------
-- Calls
---------------------------------------------------------------------------------------------------

local function stationLabel(field, position)
    return field.name .. " " .. (position == "ground" and "Ground" or "Tower")
end

-- Speaks a call on a field position, shows it to the flight, and keeps it for "say again".
local function say(field, position, flight, call)
    local frequency = field[position]
    if not frequency or frequency == "" then
        return
    end
    if flight then
        flight.lastCall[field.name .. position] = call
        local g = Group.getByName(flight.group)
        if g and g:isExist() then
            trigger.action.outTextForGroup(g:getID(), stationLabel(field, position) .. ": " .. call.text, TEXT_SECONDS)
        end
    end
    send({
        { "type", "say" },
        { "frequency", frequency },
        { "text", call.text },
        { "speech", call.speech },
        { "voice", field[position .. "Voice"] or "" },
    })
end

local function airbasePoint(field)
    local base = Airbase and Airbase.getByName and Airbase.getByName(field.airbase or field.name)
    if base then
        return base:getPoint()
    end
    return nil
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

-- The surface wind as a tower gives it: magnetic direction it blows from, to 10 degrees, in knots.
local function windParts(field)
    local p = airbasePoint(field)
    if not (p and atmosphere and atmosphere.getWind) then
        return nil
    end
    local ok, wind = pcall(function()
        return atmosphere.getWind({ x = p.x, y = p.y + 10, z = p.z })
    end)
    if not (ok and wind) then
        return nil
    end
    local knots = math.floor(math.sqrt(wind.x * wind.x + wind.z * wind.z) * KNOTS + 0.5)
    if knots < CALM_KT then
        return { "wind calm" }
    end
    local towards = math.deg(math.atan2(wind.z, wind.x))
    local from = (towards + 180 - declination()) % 360
    local tens = math.floor(from / 10 + 0.5) * 10
    if tens == 0 then
        tens = 360
    end
    return { "wind ", digits(string.format("%03d", tens)), " at ", { tostring(knots), tostring(knots) } }
end

local function withWind(parts, field)
    local wind = windParts(field)
    if wind then
        for _, part in ipairs(wind) do
            table.insert(parts, part)
        end
        table.insert(parts, ", ")
    end
    return parts
end

-- What a readback must hold: each item is a number (a runway, a squawk or a frequency).
local function pend(flight, member, field, position, items)
    flight.pending[member] = { field = field, position = position, items = items }
end

local function heardNumber(numbers, wanted)
    local w = tonumber((tostring(wanted):gsub("[^%d%.]", "")))
    for n in tostring(numbers):gmatch("%S+") do
        local v = tonumber(n)
        if v and w and math.abs(v - w) < 0.005 then
            return true
        end
    end
    return false
end

-- A number in the readback that is none of the cleared items: "squawk 4110" for 4101.
local function wrongNumber(pending, numbers)
    for n in tostring(numbers):gmatch("%S+") do
        local known = false
        for _, item in ipairs(pending.items) do
            if heardNumber(n, item.value) then
                known = true
            end
        end
        if not known then
            return true
        end
    end
    return false
end

local function checkReadback(flight, member, request)
    local pending = flight.pending[member]
    if not pending then
        return
    end
    flight.pending[member] = nil
    if CASUAL then
        return
    end
    local missing = {}
    for _, item in ipairs(pending.items) do
        if not heardNumber(request.numbers, item.value) then
            table.insert(missing, item.say)
        end
    end
    if #missing == 0 then
        return
    end
    local opening = ", readback incomplete"
    if not STRICT then
        -- Relaxed: a readback that leaves an item out is fine; one with a wrong number is not.
        if not wrongNumber(pending, request.numbers) then
            return
        end
        opening = ", negative"
    end
    local parts = { callsignPart(memberCallsign(flight, member)), opening }
    for _, part in ipairs(missing) do
        table.insert(parts, ", ")
        table.insert(parts, part)
    end
    table.insert(parts, ".")
    flight.pending[member] = pending
    say(pending.field, pending.position, flight, line(parts))
end

local function contact(field, position, flight, member, other)
    local label = frequencyLabel(field[other])
    say(field, position, flight, line({
        callsignPart(memberCallsign(flight, member)),
        ", contact ",
        other == "ground" and "Ground " or "Tower ",
        digits(label),
        ".",
    }))
end

-- No taxiway names: DCS gives scripts none, so every field taxis "to runway 25" (user call,
-- 2026-10-20). Taxi is the first call: there is no engine-start request, since SRS radios
-- are dead until the jet is powered (user call, 2026-10-21).
local function taxi(field, flight, member, on)
    if flight.state == "parked" then
        flight.state = "taxi"
    end
    local runway = field.runway
    pend(flight, member, field, on or "ground", {
        { kind = "number", value = flight.squawk, say = phrase({ "squawk ", digits(flight.squawk) }) },
        { kind = "number", value = runway, say = phrase({ "hold short runway ", digits(runway) }) },
    })
    say(field, on or "ground", flight, line({
        callsignPart(memberCallsign(flight, member)),
        ", squawk ",
        digits(flight.squawk),
        ", taxi to runway ",
        digits(runway),
        ", hold short, contact Tower ",
        digits(frequencyLabel(field.tower)),
        ".",
    }))
end

local function altimeterPart(field)
    local inches = field.altimeter or ""
    if inches == "" then
        return nil
    end
    return { inches, spokenDigits((inches:gsub("%.", ""))) }
end

local function takeoff(field, flight, member, on)
    local parts = { callsignPart(memberCallsign(flight, member)), ", runway ", digits(field.runway), ", " }
    withWind(parts, field)
    local altimeter = altimeterPart(field)
    if altimeter then
        table.insert(parts, "altimeter ")
        table.insert(parts, altimeter)
        table.insert(parts, ", ")
    end
    table.insert(parts, "cleared for takeoff.")
    flight.state = "cleared"
    pend(flight, member, field, on or "tower", {
        { kind = "number", value = field.runway, say = phrase({ "cleared for takeoff runway ", digits(field.runway) }) },
    })
    say(field, on or "tower", flight, line(parts))
end

-- Another player ship cleared to land and not down yet: the runway is busy.
local function runwayBusy(field, flight, member)
    for _, other in ipairs(flights) do
        for m, landing in pairs(other.landing) do
            if landing == field.name and not (other == flight and (m == member or member ~= 1 and m == 1)) then
                return true
            end
        end
    end
    return false
end

local function distanceNm(unit, field)
    local p, base = unit:getPoint(), airbasePoint(field)
    if not base then
        return 0
    end
    local dx, dz = p.x - base.x, p.z - base.z
    return math.sqrt(dx * dx + dz * dz) / NM
end

local function memberUnit(flight, member)
    return liveUnits(flight.group)[member]
end

local function inbound(field, flight, member, detail, on)
    on = on or "tower"
    local callsign = memberCallsign(flight, member)
    local unit = memberUnit(flight, member)
    if unit and distanceNm(unit, field) > TOWER_RANGE_NM then
        return say(field, on, flight, line({ callsignPart(callsign), ", report ", { "5", "five" }, " miles." }))
    end
    if runwayBusy(field, flight, member) then
        return say(field, on, flight, line({
            callsignPart(callsign),
            ", enter the pattern at ",
            { "3,000", "three thousand" },
            ", report downwind.",
        }))
    end
    local parts = { callsignPart(callsign), ", " }
    if detail == "overhead" then
        table.insert(parts, "overhead approved, ")
    end
    table.insert(parts, "runway ")
    table.insert(parts, digits(field.runway))
    table.insert(parts, ", ")
    withWind(parts, field)
    table.insert(parts, "cleared to land.")
    flight.landing[member] = field.name
    pend(flight, member, field, on, {
        { kind = "number", value = field.runway, say = phrase({ "cleared to land runway ", digits(field.runway) }) },
    })
    say(field, on, flight, line(parts))
end

local function emergency(field, position, flight, member)
    flight.landing[member] = field.name
    say(field, position, flight, line({ callsignPart(memberCallsign(flight, member)), ", cleared to land any runway." }))
end

local function radioCheck(field, position, flight, member)
    say(field, position, flight, line({
        callsignPart(memberCallsign(flight, member)),
        ", ",
        stationLabel(field, position),
        ", read you ",
        { "5", "five" },
        " by ",
        { "5", "five" },
        ".",
    }))
end

local function sayAgain(field, position, flight, member)
    local last = flight.lastCall[field.name .. position]
    if last then
        return say(field, position, flight, last)
    end
    say(field, position, flight, line({ callsignPart(memberCallsign(flight, member)), ", say again." }))
end

-- A call to one position: the reply, or the right frequency when it is the other position's job.
local function handleCall(field, position, flight, member, kind, detail)
    if kind == "radiocheck" then
        return radioCheck(field, position, flight, member)
    elseif kind == "sayagain" then
        return sayAgain(field, position, flight, member)
    elseif kind == "emergency" then
        return emergency(field, position, flight, member)
    end
    local ground = kind == "taxi"
    local tower = kind == "ready" or kind == "inbound" or kind == "clear" or kind == "airborne"
    -- Casual answers whoever was called; the others send the pilot to the right position.
    local on = nil
    if CASUAL then
        on = position
    elseif position == "ground" and tower then
        return contact(field, position, flight, member, "tower")
    elseif position == "tower" and ground then
        return contact(field, position, flight, member, "ground")
    end
    if kind == "taxi" then
        taxi(field, flight, member, on)
    elseif kind == "ready" then
        takeoff(field, flight, member, on)
    elseif kind == "inbound" then
        inbound(field, flight, member, detail, on)
    elseif kind == "clear" then
        flight.landing[member] = nil
        say(field, on or "tower", flight, line({ callsignPart(memberCallsign(flight, member)), ", taxi to parking." }))
    else
        say(field, position, flight, line({ callsignPart(memberCallsign(flight, member)), ", say again." }))
    end
end

-- Casual: a misheard or missing callsign is the flight with the same numbers at this field, or
-- the only player flight using it.
local function guessFlight(field, callsign)
    local wanted = normalize(callsign or ""):gsub("%a", "")
    local here = {}
    for _, flight in ipairs(flights) do
        if flight.departure == field.name or flight.arrival == field.name then
            table.insert(here, flight)
        end
    end
    if wanted ~= "" then
        for _, flight in ipairs(here) do
            local numbers = flight.key:gsub("%a", "")
            if wanted == numbers then
                return flight, 1
            end
            if #wanted == #numbers and wanted:sub(1, -2) == numbers:sub(1, -2) then
                return flight, tonumber(wanted:sub(-1)) or 1
            end
        end
    end
    if #here == 1 then
        return here[1], 1
    end
    return nil, nil
end

local function handleRequest(request)
    local station = stations[request.frequency or ""]
    if not station then
        return
    end
    local field, position = station.field, station.position
    local flight, member = findFlight(request.callsign)
    if not flight and CASUAL then
        flight, member = guessFlight(field, request.callsign)
    end
    if not flight then
        return say(field, position, nil, line({ "Station calling ", stationLabel(field, position), ", say again your callsign." }))
    end
    if request.kind == "readback" then
        return checkReadback(flight, member, request)
    end
    handleCall(field, position, flight, member, request.kind, request.detail)
end

local function pollLink(_, now)
    while link do
        local datagram = link:receivefrom()
        if not datagram then
            break
        end
        local message = jsonFields(datagram)
        if message.type == "atcRequest" then
            local ok, err = pcall(handleRequest, message)
            if not ok then
                env.warning("voiceatc: request failed: " .. tostring(err))
            end
        end
    end
    return now + LINK_POLL_SECONDS
end

---------------------------------------------------------------------------------------------------
-- Rule busts
---------------------------------------------------------------------------------------------------

local function scold(flight, key, field, position, member, text)
    if not STRICT or flight.scolded[key] then
        return
    end
    flight.scolded[key] = true
    say(field, position, flight, line({ callsignPart(memberCallsign(flight, member)), text }))
end

local function speed(unit)
    local v = unit:getVelocity() or { x = 0, y = 0, z = 0 }
    return math.sqrt(v.x * v.x + v.z * v.z)
end

-- A player rolling before a taxi clearance.
local function watch(_, now)
    for _, flight in ipairs(flights) do
        local field = fieldsByName[flight.departure]
        for _, seat in ipairs(playerUnits(flight)) do
            local u = seat.unit
            if u:inAir() then
                if flight.state == "parked" or flight.state == "taxi" then
                    -- An air start, or a takeoff the event missed.
                    flight.state = "airborne"
                end
            elseif field and flight.state == "parked" and speed(u) > TAXI_MPS then
                scold(flight, "taxi", field, "ground", seat.member, ", not cleared for taxi.")
            end
        end
    end
    return now + WATCH_SECONDS
end

---------------------------------------------------------------------------------------------------
-- F10 menu: the same requests, for when SkyEye mishears (user call, 2026-10-20)
---------------------------------------------------------------------------------------------------

local menus = {}

-- Outbound calls go to the departure field, inbound calls to the arrival field.
local function menuCall(arg)
    local flight, kind, detail = arg.flight, arg.kind, arg.detail
    local outbound = kind == "taxi" or kind == "ready"
    local field = fieldsByName[outbound and flight.departure or flight.arrival]
        or fieldsByName[flight.departure]
        or fieldsByName[flight.arrival]
    if not field then
        return
    end
    if kind == "readback" then
        -- A readback by menu is complete: the strict check is for spoken readbacks.
        flight.pending[1] = nil
        return
    end
    local position = kind == "taxi" and "ground" or "tower"
    handleCall(field, position, flight, 1, kind, detail)
end

local MENU = {
    { "Ground: request taxi", "taxi" },
    { "Tower: holding short, ready", "ready" },
    { "Tower: 5 miles, full stop", "inbound" },
    { "Tower: 5 miles, request the overhead", "inbound", "overhead" },
    { "Tower: clear of the runway", "clear" },
    { "Read back", "readback" },
    { "Mayday", "emergency" },
}

local function addMenu(flight)
    local g = Group.getByName(flight.group)
    if not (g and g:isExist()) or menus[g:getID()] then
        return
    end
    menus[g:getID()] = true
    local root = missionCommands.addSubMenuForGroup(g:getID(), "ATC")
    for _, item in ipairs(MENU) do
        missionCommands.addCommandForGroup(g:getID(), item[1], root, menuCall, {
            flight = flight,
            kind = item[2],
            detail = item[3],
        })
    end
end

local handler = {}
function handler:onEvent(event)
    if event.id == S_EVENT_BIRTH and event.initiator then
        local flight = flightOfUnit(event.initiator)
        if flight then
            addMenu(flight)
        end
        return
    end
    if not event.initiator or (event.id ~= S_EVENT_TAKEOFF and event.id ~= S_EVENT_LAND) then
        return
    end
    local flight = flightOfUnit(event.initiator)
    if not flight then
        return
    end
    local ok, player = pcall(function()
        return event.initiator:getPlayerName()
    end)
    if not (ok and player and player ~= "") then
        return
    end
    local member = memberOf(flight, event.initiator)
    if event.id == S_EVENT_TAKEOFF then
        local field = fieldsByName[flight.departure]
        if field and flight.state ~= "cleared" then
            scold(flight, "takeoff", field, "tower", member, ", you were not cleared for takeoff.")
        end
        flight.state = "airborne"
        return
    end
    -- The field it landed at: the nearest of the arrival, the divert and the departure.
    local field, best = nil, nil
    for _, name in ipairs({ flight.arrival, flight.divert, flight.departure }) do
        local candidate = fieldsByName[name or ""]
        if candidate then
            local d = distanceNm(event.initiator, candidate)
            if best == nil or d < best then
                field, best = candidate, d
            end
        end
    end
    if not field then
        return
    end
    local cleared = flight.landing[member] or flight.landing[1]
    if not cleared then
        scold(flight, "land" .. member, field, "tower", member, ", you landed without clearance.")
    end
    flight.landing[member] = nil
    flight.state = "landed"
    if not CASUAL then
        say(field, "tower", flight, line({ callsignPart(memberCallsign(flight, member)), ", clear the runway, taxi to parking." }))
    end
end

---------------------------------------------------------------------------------------------------
-- Setup
---------------------------------------------------------------------------------------------------

link = openLink()
world.addEventHandler(handler)
for _, flight in ipairs(flights) do
    addMenu(flight)
end
timer.scheduleFunction(watch, nil, timer.getTime() + WATCH_SECONDS)
if link then
    timer.scheduleFunction(announce, nil, timer.getTime() + 1)
    timer.scheduleFunction(pollLink, nil, timer.getTime() + LINK_POLL_SECONDS)
end
env.info(string.format("voiceatc: ATC at %d field(s) for %d player flight(s)", #fields, #flights))
