---------------------------------------------------------------------------------------------------
-- Voice ATC (§119). docs/dev/retlab-features.md §119
--
-- Reads dcsRetribution.voiceAtc (emitted only with the Voice ATC setting on and a player flight
-- at an airfield): linkHost, linkPort, declination,
-- and dcsRetribution.radioDiscipline (strict|relaxed|casual, §121),
--   fields = { { name, airbase, runway, runways ('10R,28L,...' in pairs), altimeter, ground,
--     tower, groundVoice, towerVoice } },
--   flights = { { group, callsign, departure, arrival, divert } }
--
-- Ground and Tower for player flights, through SkyEye's mission link: SkyEye hears the calls on
-- the field frequencies and this script decides every reply, in military calls: the altimeter
-- with taxi, wind and a frequency change with takeoff, report initial (or a straight-in) when
-- inbound, cleared to land at base or final with the gear down. Under Strict radio discipline a
-- rule bust (moving before taxi, taking off or landing without clearance) gets a scolding call and
-- nothing more: ATC never blocks a player (user call, 2026-10-20). An F10 ATC menu makes the same
-- requests. Replies are voice only; without LuaSocket the menu is the only way in and replies are
-- on-screen text. AI traffic is left to DCS's own ATC.
---------------------------------------------------------------------------------------------------

if not (dcsRetribution and dcsRetribution.voiceAtc) then
    return
end

local data = dcsRetribution.voiceAtc
-- Radio discipline (§116-§119, user call 2026-10-20). Strict: readbacks checked, busts scolded.
-- Relaxed: any acknowledgement counts, only a wrong number is corrected, no scolding, a
-- misheard callsign is matched. Casual: answer only when called, never expect a call, accept
-- a loose call.
local DISCIPLINE = dcsRetribution.radioDiscipline or "strict"
local STRICT = DISCIPLINE == "strict"
local CASUAL = DISCIPLINE == "casual"
local LINK_POLL_SECONDS = 1
local ANNOUNCE_SECONDS = 30
local WATCH_SECONDS = 2
local TEXT_SECONDS = 15
local NM = 1852
-- A "gear down" call farther out than this is misheard: Tower answers it as an inbound call.
local LANDING_RANGE_NM = 10
-- Faster than this on the ground is taxiing, about 6 kt.
local TAXI_MPS = 3
local KNOTS = 1.94384
local CALM_KT = 3
-- Strict asks for a readback that has not come in this long after the clearance.
local READBACK_PROMPT_SECONDS = 20

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
    -- Ship -> field it is inbound to or in the pattern at, until it lands.
    flight.pattern = {}
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

local function callsignPart(callsign, formation)
    if formation then
        return { callsign .. " flight", spokenCallsign(callsign) .. " flight" }
    end
    return { callsign, spokenCallsign(callsign) }
end

-- A whole word in the heard call: "flight" in "viper 1 1 flight of 2".
local function heardWord(text, word)
    return (" " .. tostring(text or ""):lower() .. " "):find("[^%a]" .. word .. "[^%a]") ~= nil
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
    -- SkyEye only puts these in its speech recognizer's prompt.
    local callsigns, seen = {}, {}
    for _, flight in ipairs(flights) do
        if not seen[flight.key] then
            seen[flight.key] = true
            table.insert(callsigns, tostring(flight.callsign))
        end
    end
    send({ { "type", "atc" }, { "fields", list }, { "discipline", DISCIPLINE }, { "callsigns", callsigns } })
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

-- The unit's seat in its group, which does not shift when another ship dies or, in
-- multiplayer, when an empty client slot has no unit: live index 1 can be ship 2.
local function shipNumber(u, index)
    local ok, number = pcall(function()
        return u:getNumber()
    end)
    return ok and tonumber(number) or index
end

local function playerUnits(flight)
    local out = {}
    for index, u in ipairs(liveUnits(flight.group)) do
        local ok, name = pcall(function()
            return u:getPlayerName()
        end)
        if ok and name and name ~= "" then
            table.insert(out, { unit = u, member = shipNumber(u, index) })
        end
    end
    return out
end

-- The flight and ship number a heard callsign is: "viper 1 1" is the lead, "viper 1 2" ship 2.
-- The flight callsign alone, "viper 1", is the lead: the AWACS and ABCCC cards teach it.
-- Whole callsigns, then a flight alone, then a ship: "flight 123" is Flight 123-1, never
-- ship 3 of Flight 12, as pkgcontrol's findCaller reads them.
local function findFlight(callsign)
    local key = normalize(callsign or "")
    if key == "" then
        return nil, nil
    end
    for _, flight in ipairs(flights) do
        if key == flight.key then
            return flight, 1
        end
    end
    for _, flight in ipairs(flights) do
        if key == flight.prefix then
            return flight, 1
        end
    end
    local member = tonumber(key:sub(-1))
    for _, flight in ipairs(flights) do
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
            return shipNumber(u, index)
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

-- Speaks a call on a field position and keeps it for "say again". Text only without LuaSocket.
local function say(field, position, flight, call)
    local frequency = field[position]
    if not frequency or frequency == "" then
        return
    end
    if flight then
        flight.lastCall[field.name .. position] = call
        local g = Group.getByName(flight.group)
        if not link and g and g:isExist() then
            trigger.action.outTextForGroup(g:getID(), stationLabel(field, position) .. ": " .. call.text, TEXT_SECONDS)
        end
    end
    send({
        { "type", "say" },
        { "frequency", frequency },
        { "text", call.text },
        { "speech", call.speech },
        { "voice", field[position .. "Voice"] or "" },
        { "speaker", stationLabel(field, position) },
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
        return { "wind calm" }, {}
    end
    local towards = math.deg(math.atan2(wind.z, wind.x))
    local from = (towards + 180 - declination()) % 360
    local tens = math.floor(from / 10 + 0.5) * 10
    if tens == 0 then
        tens = 360
    end
    return { "wind ", digits(string.format("%03d", tens)), " at ", { tostring(knots), tostring(knots) } }, { tens, knots }
end

-- Adds the wind to a call and returns its numbers, which a readback may say.
local function withWind(parts, field)
    local wind, values = windParts(field)
    if wind then
        for _, part in ipairs(wind) do
            table.insert(parts, part)
        end
        table.insert(parts, ", ")
    end
    return values or {}
end

-- What a readback must hold: each item is a number (the runway). The optional numbers (wind,
-- altimeter, frequency) were in the call too, so reading one back is never a wrong number.
local function pend(flight, member, field, position, items, optional)
    flight.pending[member] = {
        field = field,
        position = position,
        items = items,
        optional = optional or {},
        at = timer.getTime(),
        state = flight.state,
    }
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

-- A number in the readback that is none of the cleared items: "hold short 52" for 25.
local function wrongNumber(pending, numbers)
    for n in tostring(numbers):gmatch("%S+") do
        local known = false
        for _, item in ipairs(pending.items) do
            if heardNumber(n, item.value) then
                known = true
            end
        end
        for _, value in ipairs(pending.optional or {}) do
            if heardNumber(n, value) then
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
    pending.at = timer.getTime()
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
local function altimeterPart(field)
    local inches = field.altimeter or ""
    if inches == "" then
        return nil
    end
    return { inches, spokenDigits((inches:gsub("%.", ""))) }
end

-- The lead calling for the whole formation: it said "flight", or (going out) it has wingmen.
local function isFormation(flight, member, text, outbound)
    if member ~= 1 then
        return false
    end
    return heardWord(text, "flight") or (outbound and #liveUnits(flight.group) > 1)
end

-- "Have the numbers": the pilot has the runway, wind and altimeter, so they are left out.
local function hasNumbers(detail, text)
    return detail == "numbers" or heardWord(text, "numbers")
end

local function taxi(field, flight, member, on, detail, text)
    if flight.state == "parked" then
        flight.state = "taxi"
    end
    if hasNumbers(detail, text) then
        flight.numbers = true
    end
    local runway = field.runway
    local tower = frequencyLabel(field.tower)
    local formation = isFormation(flight, member, text, true)
    local parts = { callsignPart(memberCallsign(flight, member), formation), ", runway ", digits(runway), ", " }
    local optional = { tower }
    local altimeter = altimeterPart(field)
    if altimeter and not flight.numbers then
        table.insert(parts, "altimeter ")
        table.insert(parts, altimeter)
        table.insert(parts, ", ")
        -- "Two niner niner two" is heard as 2992.
        table.insert(optional, field.altimeter)
        table.insert(optional, (field.altimeter:gsub("%.", "")))
    end
    for _, part in ipairs({ "taxi, hold short runway ", digits(runway), ", contact Tower ", digits(tower), "." }) do
        table.insert(parts, part)
    end
    pend(flight, member, field, on or "ground", {
        { kind = "number", value = runway, say = phrase({ "hold short runway ", digits(runway) }) },
    }, optional)
    say(field, on or "ground", flight, line(parts))
end

-- The frequency change is approved with the clearance, so no airborne call is needed.
local function takeoff(field, flight, member, on, detail, text)
    local formation = isFormation(flight, member, text, true)
    local parts = { callsignPart(memberCallsign(flight, member), formation), ", runway ", digits(field.runway), ", " }
    local optional = {}
    if not (flight.numbers or hasNumbers(detail, text)) then
        optional = withWind(parts, field)
    end
    table.insert(parts, "cleared for takeoff, frequency change approved.")
    flight.state = "cleared"
    pend(flight, member, field, on or "tower", {
        { kind = "number", value = field.runway, say = phrase({ "cleared for takeoff runway ", digits(field.runway) }) },
    }, optional)
    say(field, on or "tower", flight, line(parts))
end

-- Another player flight inbound to this field or cleared to land there, not down yet.
local function trafficInPattern(field, flight)
    for _, other in ipairs(flights) do
        if other ~= flight then
            for _, name in pairs(other.pattern) do
                if name == field.name then
                    return true
                end
            end
            for _, name in pairs(other.landing) do
                if name == field.name then
                    return true
                end
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
    for index, u in ipairs(liveUnits(flight.group)) do
        if shipNumber(u, index) == member then
            return u
        end
    end
    return nil
end

-- The landing clearance, at base or final with the gear down: each ship, or the formation.
local function landing(field, flight, member, on, text)
    local formation = isFormation(flight, member, text, false)
    local parts = { callsignPart(memberCallsign(flight, member), formation), ", runway ", digits(field.runway), ", " }
    local optional = withWind(parts, field)
    table.insert(parts, "cleared to land.")
    flight.landing[member] = field.name
    if formation then
        for _, seat in ipairs(playerUnits(flight)) do
            flight.landing[seat.member] = field.name
        end
    end
    pend(flight, member, field, on, {
        { kind = "number", value = field.runway, say = phrase({ "cleared to land runway ", digits(field.runway) }) },
    }, optional)
    say(field, on, flight, line(parts))
end

-- Inbound gets the runway, the wind and the overhead (report initial), or a straight-in when it
-- asks for one. Initial and the break are acknowledged; the landing call comes at base or final.
local function inbound(field, flight, member, detail, on, text)
    on = on or "tower"
    local callsign = memberCallsign(flight, member)
    local unit = memberUnit(flight, member)
    if detail == "geardown" and not (unit and distanceNm(unit, field) > LANDING_RANGE_NM) then
        flight.pattern[member] = nil
        return landing(field, flight, member, on, text)
    end
    local formation = isFormation(flight, member, text, false)
    flight.pattern[member] = field.name
    if detail == "initial" or detail == "break" then
        local reply = ", roger."
        if detail == "initial" and trafficInPattern(field, flight) then
            reply = ", report break."
        end
        return say(field, on, flight, line({ callsignPart(callsign, formation), reply }))
    end
    local parts = { callsignPart(callsign, formation), ", runway ", digits(field.runway), ", " }
    withWind(parts, field)
    if detail == "straightin" then
        table.insert(parts, "make straight-in, report ")
        table.insert(parts, { "3", "three" })
        table.insert(parts, "-mile final.")
    else
        table.insert(parts, "report initial.")
    end
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

-- "Runway in use": the runway and the wind, from whoever was called.
local function runwayInUse(field, position, flight, member)
    local parts = { callsignPart(memberCallsign(flight, member)), ", runway ", digits(field.runway) }
    local wind = windParts(field)
    if wind then
        table.insert(parts, ", ")
        for _, part in ipairs(wind) do
            table.insert(parts, part)
        end
    end
    table.insert(parts, ".")
    say(field, position, flight, line(parts))
end

local function sayAgain(field, position, flight, member)
    local last = flight.lastCall[field.name .. position]
    if last then
        return say(field, position, flight, last)
    end
    say(field, position, flight, line({ callsignPart(memberCallsign(flight, member)), ", say again." }))
end

-- A call to one position: the reply, or the right frequency when it is the other position's job.
local function handleCall(field, position, flight, member, kind, detail, text)
    if kind == "radiocheck" then
        return radioCheck(field, position, flight, member)
    elseif kind == "sayagain" then
        return sayAgain(field, position, flight, member)
    elseif kind == "emergency" then
        return emergency(field, position, flight, member)
    elseif kind == "runway" then
        return runwayInUse(field, position, flight, member)
    elseif kind == "startup" or kind == "airborne" then
        -- A short answer from whoever was called, never "say again": start needs no
        -- clearance (taxi is the first call), and the takeoff clearance already approved the
        -- frequency change, so an airborne call is answered but never needed.
        local reply = kind == "startup" and ", start at your discretion. Call ready to taxi." or ", frequency change approved."
        return say(field, position, flight, line({ callsignPart(memberCallsign(flight, member)), reply }))
    end
    local ground = kind == "taxi"
    local tower = kind == "ready" or kind == "inbound" or kind == "clear"
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
        taxi(field, flight, member, on, detail, text)
    elseif kind == "ready" then
        takeoff(field, flight, member, on, detail, text)
    elseif kind == "inbound" then
        inbound(field, flight, member, detail, on, text)
    elseif kind == "clear" then
        flight.landing[member] = nil
        say(field, on or "tower", flight, line({ callsignPart(memberCallsign(flight, member)), ", taxi to parking." }))
    else
        say(field, position, flight, line({ callsignPart(memberCallsign(flight, member)), ", say again." }))
    end
end

-- Relaxed and Casual: a misheard or missing callsign is the flight with the same numbers at
-- this field, the only one there with the heard flight name ("Enfield 2" for Enfield 4-1,
-- Test 65), or the only player flight using it.
local function guessFlight(field, callsign)
    local heard = normalize(callsign or "")
    local wanted = heard:gsub("%a", "")
    local name = heard:gsub("%d", "")
    local here = {}
    for _, flight in ipairs(flights) do
        if flight.departure == field.name or flight.arrival == field.name then
            table.insert(here, flight)
        end
    end
    if wanted ~= "" then
        for _, flight in ipairs(here) do
            local numbers = flight.key:gsub("%a", "")
            if wanted == numbers or wanted == numbers:sub(1, -2) then
                return flight, 1
            end
            if #wanted == #numbers and wanted:sub(1, -2) == numbers:sub(1, -2) then
                return flight, tonumber(wanted:sub(-1)) or 1
            end
        end
    end
    if name ~= "" then
        local named = {}
        for _, flight in ipairs(here) do
            if flight.key:gsub("%d", "") == name then
                table.insert(named, flight)
            end
        end
        if #named == 1 then
            return named[1], 1
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
    if not flight and not STRICT then
        flight, member = guessFlight(field, request.callsign)
    end
    if not flight then
        return say(field, position, nil, line({ "Station calling ", stationLabel(field, position), ", say again your callsign." }))
    end
    if request.kind == "readback" then
        return checkReadback(flight, member, request)
    end
    handleCall(field, position, flight, member, request.kind, request.detail, request.text)
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

-- Strict: a clearance with no usable readback gets one "read back" prompt, while it is still the
-- flight's current clearance. Otherwise an unheard readback is silence (user call, 2026-10-21).
local function promptReadbacks(flight, now)
    if not STRICT then
        return
    end
    for member, pending in pairs(flight.pending) do
        if not pending.prompted and pending.state == flight.state and now - pending.at >= READBACK_PROMPT_SECONDS then
            pending.prompted = true
            say(pending.field, pending.position, flight, line({ callsignPart(memberCallsign(flight, member)), ", read back." }))
        end
    end
end

-- A player rolling before a taxi clearance.
local function watch(_, now)
    for _, flight in ipairs(flights) do
        promptReadbacks(flight, now)
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

-- A group menu cannot tell who pressed it: the top items speak for the one player aboard,
-- else the lead, and a "Ship N" submenu speaks for that seat.
local function menuMember(flight, ship)
    if ship then
        return ship
    end
    local seats = playerUnits(flight)
    if #seats == 1 then
        return seats[1].member
    end
    return 1
end

-- Outbound calls go to the departure field, inbound calls to the arrival field.
local function menuCall(arg)
    local flight, kind, detail = arg.flight, arg.kind, arg.detail
    local member = menuMember(flight, arg.ship)
    local outbound = kind == "taxi" or kind == "ready"
    local field = fieldsByName[outbound and flight.departure or flight.arrival]
        or fieldsByName[flight.departure]
        or fieldsByName[flight.arrival]
    if not field then
        return
    end
    if kind == "readback" then
        -- A readback by menu is complete: the strict check is for spoken readbacks.
        flight.pending[member] = nil
        return
    end
    local position = kind == "taxi" and "ground" or "tower"
    handleCall(field, position, flight, member, kind, detail)
end

local MENU = {
    { "Ground: request taxi", "taxi" },
    { "Tower: holding short, ready", "ready" },
    { "Tower: 10 miles, full stop", "inbound" },
    { "Tower: base, gear down", "inbound", "geardown" },
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
    local function addItems(parent, ship)
        for _, item in ipairs(MENU) do
            missionCommands.addCommandForGroup(g:getID(), item[1], parent, menuCall, {
                flight = flight,
                kind = item[2],
                detail = item[3],
                ship = ship,
            })
        end
    end
    local root = missionCommands.addSubMenuForGroup(g:getID(), "ATC")
    addItems(root, nil)
    -- The slots, not the units: a client slot nobody has taken has no unit yet.
    local ok, size = pcall(function()
        return g:getInitialSize()
    end)
    size = ok and tonumber(size) or g:getSize()
    -- 7 calls and 3 submenus fill F1-F10 for a 4-ship.
    for ship = 2, math.min(size or 1, 4) do
        addItems(missionCommands.addSubMenuForGroup(g:getID(), "Ship " .. ship, root), ship)
    end
end

-- A respawn in the same slot is a new sortie: no clearance, no pending readback, no
-- scolding spent. The flight's own state resets only when no other player is in it.
local function newSortie(flight, unit)
    local member = memberOf(flight, unit)
    flight.pending[member] = nil
    flight.landing[member] = nil
    flight.pattern[member] = nil
    flight.scolded["land" .. member] = nil
    local name = unit:getName()
    for _, seat in ipairs(playerUnits(flight)) do
        if seat.unit:getName() ~= name then
            return
        end
    end
    flight.state = "parked"
    flight.pending = {}
    flight.landing = {}
    flight.pattern = {}
    flight.scolded = {}
    flight.lastCall = {}
    flight.numbers = nil
end

---------------------------------------------------------------------------------------------------
-- Runway in use
---------------------------------------------------------------------------------------------------

-- DCS's AI does not always take the into-wind runway the briefing picks (flown 2026-10-21:
-- Tower cleared 28L, the AI used 10L at Hatzerim), so the first AI takeoff at a field sets
-- the runway Ground and Tower give from then on.
local LEARN_NM = 5
local RUNWAY_MATCH_DEG = 35

local function runwayNumber(name)
    return tonumber(tostring(name):match("^(%d+)"))
end

local function angleOff(a, b)
    local d = math.abs(a - b) % 360
    return d > 180 and 360 - d or d
end

local function nearestField(unit)
    local field, best = nil, nil
    for _, f in ipairs(fields) do
        if airbasePoint(f) then
            local d = distanceNm(unit, f)
            if d <= LEARN_NM and (best == nil or d < best) then
                field, best = f, d
            end
        end
    end
    return field
end

local function learnRunway(unit)
    local field = nearestField(unit)
    if not field or field.learned then
        return
    end
    local ok, pos = pcall(function()
        return unit:getPosition()
    end)
    if not (ok and pos and pos.x) then
        return
    end
    local heading = (math.deg(math.atan2(pos.x.z, pos.x.x)) - declination()) % 360
    local ends, pairOf = {}, {}
    for name in tostring(field.runways or ""):gmatch("[^,]+") do
        table.insert(ends, name)
        if #ends % 2 == 0 then
            pairOf[ends[#ends - 1]], pairOf[name] = name, ends[#ends - 1]
        end
    end
    -- The briefed runway's own strip first, so 28L turns into 10R rather than 10L.
    local choice = nil
    for _, name in ipairs(ends) do
        local number = runwayNumber(name)
        if number and angleOff(number * 10, heading) <= RUNWAY_MATCH_DEG then
            if choice == nil or name == field.runway or pairOf[name] == field.runway then
                choice = name
            end
        end
    end
    if choice then
        field.learned = true
        if choice ~= field.runway then
            env.info(string.format("voiceatc: %s AI took off on %s; runway %s -> %s", field.name, choice, field.runway, choice))
            field.runway = choice
        end
    end
end

local function isAirplane(unit)
    local ok, desc = pcall(function()
        return unit:getDesc()
    end)
    return not (ok and desc and desc.category ~= nil and desc.category ~= 0)
end

local handler = {}
function handler:onEvent(event)
    if event.id == S_EVENT_BIRTH and event.initiator then
        local flight = flightOfUnit(event.initiator)
        if flight then
            addMenu(flight)
            local ok, player = pcall(function()
                return event.initiator:getPlayerName()
            end)
            if ok and player and player ~= "" then
                newSortie(flight, event.initiator)
            end
        end
        return
    end
    if not event.initiator or (event.id ~= S_EVENT_TAKEOFF and event.id ~= S_EVENT_LAND) then
        return
    end
    if event.id == S_EVENT_TAKEOFF then
        local ok, name = pcall(function()
            return event.initiator:getPlayerName()
        end)
        if not (ok and name and name ~= "") and isAirplane(event.initiator) then
            learnRunway(event.initiator)
        end
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
    flight.pattern[member] = nil
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
