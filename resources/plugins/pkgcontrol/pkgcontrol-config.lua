---------------------------------------------------------------------------------------------------
-- Airborne package control (§117). docs/dev/retlab-features.md §117
--
-- Reads dcsRetribution.packageControl (emitted only when a blue ABCCC C-130 and a player
-- package fly): startSeconds, linkHost, linkPort, strikeFreq, strikeModulation, awacsVoice,
--   controllerVoice, controllers = { { group, callsign } },
--   packages = { { name, totAfter, targetName, targetX, targetY,
--   targetUnits = {...}, flights = { { group, callsign, role = strike|sead|escort, client,
--   pushAfter, holdX, holdY, holdAngels, holdIndex, home } } } },
--   players = { { group, callsign } } (every blue player flight, for the AWACS to find by name)
--
-- While an ABCCC C-130 is alive AND airborne it runs every package on STRIKE (common):
-- check-in (F10 or spoken), ready to push, say push time, the push call, up to two 3-minute holds
-- while a SEAD or escort flight is not airborne, an abort for a dead target or a lost SEAD, and
-- the egress call. AI flights in the package obey: a hold adds a 3-minute orbit at their HOLD
-- point, an early push releases them from it, an abort sends them home. With no controller
-- airborne nothing is said and the push waits: the AWACS never stands in (user call,
-- 2026-10-20). SkyEye speaks the calls over local UDP (its mission-link-address) in the opposite
-- voice to the AWACS, which works STRIKE trimmed. Every call is also text.
---------------------------------------------------------------------------------------------------

if not (dcsRetribution and dcsRetribution.packageControl) then
    return
end

local data = dcsRetribution.packageControl
local POLL_SECONDS = 10
local LINK_POLL_SECONDS = 1
local ANNOUNCE_SECONDS = 30
local HOLD_SLIP_SECONDS = 180
-- The roll call goes out this long before the push (user call, 2026-10-20).
local ROLL_CALL_LEAD_SECONDS = 180
local MAX_SLIPS = 2
local NM = 1852
local EGRESS_NM = 10
-- A striker must have come this close to the target before it can egress.
local REACHED_NM = 30
local EGRESS_GIVE_UP_SECONDS = 3600
local TEXT_SECONDS = 15

local START_SECONDS = tonumber(data.startSeconds) or 0
-- Radio discipline (§121): strict (by the book), relaxed or casual (user call, 2026-10-20).
local DISCIPLINE = (dcsRetribution.radioDiscipline or "strict")
local STRICT = DISCIPLINE == "strict"
local CASUAL = DISCIPLINE == "casual"
local packages = data.packages or {}

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

-- A late-activated unit not yet activated reads isExist and inAir true (Test 63), so it must
-- also be active.
local function isActive(u)
    local ok, active = pcall(function()
        return u:isActive()
    end)
    return not ok or active ~= false
end

local function airborneUnit(groupName)
    for _, u in ipairs(liveUnits(groupName)) do
        if u:inAir() and isActive(u) then
            return u
        end
    end
    return nil
end

-- The controller on station: the first ABCCC C-130 that is alive and airborne.
local function controller()
    for _, c in ipairs(data.controllers or {}) do
        if airborneUnit(c.group) then
            return c
        end
    end
    return nil
end

local function normalize(callsign)
    return (tostring(callsign):lower():gsub("[^%w]", ""))
end

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

-- "0510" -> "zero five one zero": Piper reads "05 10" as "oh five ten".
local function spokenDigits(s)
    local words = {}
    for c in tostring(s):gmatch("%d") do
        table.insert(words, DIGIT_WORDS[c])
    end
    return table.concat(words, " ")
end

-- "Ford 9-1" -> "Ford niner one", as voiceatc says it.
local function spokenCallsign(callsign)
    local name, digits = tostring(callsign):match("^(.-)%s*([%d%-%s]+)$")
    if not name or name == "" then
        return tostring(callsign)
    end
    return name .. " " .. spokenDigits(digits)
end

-- A line in two forms, as voiceatc sends them: the text shown, and the words SkyEye speaks. Each
-- part is plain text, or { text, speech }.
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

local function phrase(parts)
    local l = line(parts)
    return { l.text, l.speech }
end

local function callsignPart(callsign)
    return { tostring(callsign), spokenCallsign(callsign) }
end

local function digitsPart(s)
    return { tostring(s), spokenDigits(s) }
end

-- A push time: text "1410", speech "one four one zero".
local function clock(missionSeconds)
    local t = math.floor(START_SECONDS + missionSeconds) % 86400
    return digitsPart(string.format("%02d%02d", math.floor(t / 3600), math.floor(t / 60) % 60))
end

-- "Ford package", or "Ford and Colt packages" for a roll call to several.
local function packagePart(list)
    local names = {}
    for _, pkg in ipairs(list) do
        table.insert(names, pkg.name)
    end
    local label = table.concat(names, " and ") .. (#names > 1 and " packages" or " package")
    return { label, label }
end

-- No strikeFreq: no ABCCC flies, and the link only tells SkyEye its AWACS name and voice.
local STRIKE = data.strikeFreq
        and string.format("%.3f%s", tonumber(data.strikeFreq) or 0, data.strikeModulation == "FM" and "FM" or "AM")
    or ""


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

local function jsonObject(fields)
    local parts = {}
    for _, kv in ipairs(fields) do
        local key, value = kv[1], kv[2]
        local encoded
        if type(value) == "boolean" then
            encoded = value and "true" or "false"
        elseif type(value) == "table" then
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
    local fields = {}
    for key, value in tostring(text):gmatch('"([%w_]+)"%s*:%s*"([^"]*)"') do
        fields[key] = value
    end
    return fields
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
        env.warning("pkgcontrol: LuaSocket unavailable, package calls are text only: " .. tostring(socket))
        return nil
    end
    local udp = socket.udp()
    udp:settimeout(0)
    udp:setsockname("127.0.0.1", 0)
    return udp
end

local function send(fields)
    if link then
        link:sendto(jsonObject(fields), data.linkHost or "127.0.0.1", tonumber(data.linkPort) or 42690)
    end
end

-- Each player in a blue player flight by the seat they fly, and the flight alone as its lead, so
-- the AWACS finds "Ford 9-1" when the DCS name is "Flash" (flown 2026-10-21).
local function pilots()
    local out = {}
    for _, p in ipairs(data.players or {}) do
        local flightName = (tostring(p.callsign):gsub("%-%d$", ""))
        local lead = nil
        for index, u in ipairs(liveUnits(p.group)) do
            local ok, name = pcall(function()
                return u:getPlayerName()
            end)
            if ok and name and name ~= "" then
                local okNumber, number = pcall(function()
                    return u:getNumber()
                end)
                local ship = okNumber and tonumber(number) or index
                local seat = (tostring(p.callsign):gsub("%d$", tostring(ship)))
                table.insert(out, { { "name", name }, { "callsign", seat } })
                if ship == 1 or not lead then
                    lead = name
                end
            end
        end
        if lead and flightName ~= p.callsign then
            table.insert(out, { { "name", lead }, { "callsign", flightName } })
        end
    end
    return out
end

local function announcePackages()
    local controllers = {}
    for _, c in ipairs(data.controllers or {}) do
        table.insert(controllers, c.callsign)
    end
    local list = {}
    for _, pkg in ipairs(packages) do
        table.insert(list, { { "name", pkg.name }, { "frequency", STRIKE } })
    end
    send({
        { "type", "packages" },
        { "controllers", controllers },
        { "packages", list },
        { "strike", STRIKE },
        { "gciVoice", data.awacsVoice or "" },
        { "gciCallsign", data.awacsCallsign or "" },
        { "looseCalls", not STRICT },
        { "strikeThreatsOnly", CASUAL },
        { "pilots", pilots() },
    })
end

---------------------------------------------------------------------------------------------------
-- Calls
---------------------------------------------------------------------------------------------------

-- Speaks a call on STRIKE and texts it to the player flights of each package in the list.
local function sayTo(list, call)
    local c = controller()
    if not c then
        return false
    end
    local text = (call.text:gsub("{controller}", c.callsign))
    local speech = (call.speech:gsub("{controller}", c.callsign))
    for _, pkg in ipairs(list) do
        for _, f in ipairs(pkg.flights or {}) do
            if f.client == "true" then
                local g = Group.getByName(f.group)
                if g and g:isExist() then
                    trigger.action.outTextForGroup(g:getID(), text, TEXT_SECONDS)
                end
            end
        end
    end
    send({
        { "type", "say" },
        { "frequency", STRIKE },
        { "text", text },
        { "speech", speech },
        { "voice", data.controllerVoice or "" },
    })
    return true
end

local function say(pkg, parts)
    return sayTo(pkg and { pkg } or {}, line(parts))
end

local function flightsWithRole(pkg, role)
    local out = {}
    for _, f in ipairs(pkg.flights or {}) do
        if f.role == role then
            table.insert(out, f)
        end
    end
    return out
end

local function airborne(flight)
    return airborneUnit(flight.group) ~= nil
end

-- Dead only once seen alive: a late-activated flight has no units before it appears.
local function lost(flight)
    if #liveUnits(flight.group) > 0 then
        flight.seen = true
        return false
    end
    return flight.seen == true
end

local function targetDestroyed(pkg)
    local names = pkg.targetUnits or {}
    if #names == 0 then
        return false
    end
    for _, name in ipairs(names) do
        local u = Unit.getByName(name)
        if u and u:isExist() and u:getLife() > 0 then
            return false
        end
        local s = StaticObject and StaticObject.getByName(name)
        if s and s:isExist() and s:getLife() > 0 then
            return false
        end
    end
    return true
end

local function pushTime(pkg)
    local earliest = nil
    for _, f in ipairs(pkg.flights or {}) do
        local t = tonumber(f.pushAfter)
        if t and f.role == "strike" and (earliest == nil or t < earliest) then
            earliest = t
        end
    end
    if earliest == nil then
        for _, f in ipairs(pkg.flights or {}) do
            local t = tonumber(f.pushAfter)
            if t and (earliest == nil or t < earliest) then
                earliest = t
            end
        end
    end
    return earliest
end

local FEET = 0.3048
local AI_SPEED_MPS = 200 * 0.514444

-- Airborne AI flights only: a task pushed on a parked flight would replace its takeoff.
local function aiFlights(pkg)
    local out = {}
    for _, f in ipairs(pkg.flights or {}) do
        local g = f.client ~= "true" and airborneUnit(f.group) and Group.getByName(f.group)
        if g and g:isExist() then
            table.insert(out, { flight = f, controller = g:getController() })
        end
    end
    return out
end

-- A hold: each AI flight orbits its HOLD point for the slip, then resumes its route.
local function holdAI(pkg)
    for _, ai in ipairs(aiFlights(pkg)) do
        local f = ai.flight
        if f.holdX and f.holdY then
            ai.controller:pushTask({
                id = "ControlledTask",
                params = {
                    task = {
                        id = "Orbit",
                        params = {
                            pattern = "Circle",
                            point = { x = tonumber(f.holdX), y = tonumber(f.holdY) },
                            altitude = (tonumber(f.holdAngels) or 20) * 1000 * FEET,
                            speed = AI_SPEED_MPS,
                        },
                    },
                    stopCondition = { duration = HOLD_SLIP_SECONDS },
                },
            })
        end
    end
end

-- An early push: each AI flight leaves its HOLD orbit for the next waypoint.
local function releaseAI(pkg)
    for _, ai in ipairs(aiFlights(pkg)) do
        local index = tonumber(ai.flight.holdIndex)
        if index then
            ai.controller:setCommand({
                id = "SwitchWaypoint",
                params = { fromWaypointIndex = index, goToWaypointIndex = index + 1 },
            })
        end
    end
end

-- An abort: each AI flight drops its route and lands at home.
local function sendAIHome(pkg)
    for _, ai in ipairs(aiFlights(pkg)) do
        local base = ai.flight.home and Airbase and Airbase.getByName and Airbase.getByName(ai.flight.home)
        local lead = liveUnits(ai.flight.group)[1]
        if base and lead then
            local here, home = lead:getPoint(), base:getPoint()
            ai.controller:setTask({
                id = "Mission",
                params = {
                    route = {
                        points = {
                            {
                                type = "Turning Point",
                                action = "Turning Point",
                                x = here.x,
                                y = here.z,
                                alt = here.y,
                                alt_type = "BARO",
                                speed = AI_SPEED_MPS,
                            },
                            {
                                type = "Land",
                                action = "Landing",
                                x = home.x,
                                y = home.z,
                                alt = home.y,
                                alt_type = "BARO",
                                speed = AI_SPEED_MPS,
                                airdromeId = base:getID(),
                            },
                        },
                    },
                },
            })
        end
    end
end

local function abort(pkg, reason)
    pkg.state = "done"
    sendAIHome(pkg)
    say(pkg, { packagePart({ pkg }), ", {controller}, abort, abort, abort. ", reason, ". RTB." })
end

local function push(pkg)
    pkg.state = "pushed"
    pkg.pushedAt = timer.getTime()
    say(pkg, { packagePart({ pkg }), ", {controller}, push." })
end

local function notReady(pkg)
    local missing = {}
    for _, role in ipairs(CASUAL and { "sead" } or { "sead", "escort" }) do
        for _, f in ipairs(flightsWithRole(pkg, role)) do
            if not lost(f) and not airborne(f) then
                table.insert(missing, role == "sead" and "SEAD" or "escort")
                break
            end
        end
    end
    return missing
end

local function anySeadAirborne(pkg)
    for _, f in ipairs(flightsWithRole(pkg, "sead")) do
        if airborne(f) then
            return true
        end
    end
    return false
end

local function seadLost(pkg)
    local seads = flightsWithRole(pkg, "sead")
    if #seads == 0 then
        return false
    end
    for _, f in ipairs(seads) do
        if not lost(f) then
            return false
        end
    end
    return true
end

-- A player flight counts only with someone in a seat: an empty slot is not waited for.
local function seated(flight)
    if flight.client ~= "true" then
        return false
    end
    for _, u in ipairs(liveUnits(flight.group)) do
        local ok, name = pcall(function()
            return u:getPlayerName()
        end)
        if ok and name and name ~= "" then
            return true
        end
    end
    return false
end

local function silentPlayers(pkg, role)
    local out = {}
    if not STRICT then
        -- Relaxed and casual never wait on a player who stays quiet.
        return out
    end
    for _, f in ipairs(flightsWithRole(pkg, role)) do
        if seated(f) and not f.ready then
            table.insert(out, f)
        end
    end
    return out
end

local function callsigns(flights)
    local parts = {}
    for i, f in ipairs(flights) do
        if i > 1 then
            table.insert(parts, " and ")
        end
        table.insert(parts, callsignPart(f.callsign))
    end
    return phrase(parts)
end

-- A striker other than the silent ones is set to go: a ready player or an airborne AI flight.
local function anotherStrikerReady(pkg)
    for _, f in ipairs(flightsWithRole(pkg, "strike")) do
        if f.client == "true" then
            if f.ready and seated(f) then
                return true
            end
        elseif airborne(f) then
            return true
        end
    end
    return false
end

local function slip(pkg, reason)
    pkg.slips = pkg.slips + 1
    pkg.pushAt = pkg.pushAt + HOLD_SLIP_SECONDS
    holdAI(pkg)
    return say(pkg, {
        packagePart({ pkg }),
        ", {controller}, hold, hold. ",
        reason,
        ". New push time ",
        clock(pkg.pushAt),
        ".",
    })
end

-- The roll call, one call for every package due this tick: players answer; AI flights are read
-- out by what they are doing.
local function rollCall(list)
    for _, pkg in ipairs(list) do
        pkg.rollCalled = true
    end
    local minutes = tostring(math.floor(ROLL_CALL_LEAD_SECONDS / 60))
    sayTo(list, line({
        packagePart(list),
        ", {controller}, check in. Push in ",
        { minutes, minutes == "3" and "three" or minutes },
        " minutes.",
    }))
    for _, pkg in ipairs(list) do
        local up, down = {}, {}
        for _, f in ipairs(pkg.flights or {}) do
            if f.client ~= "true" and not lost(f) then
                table.insert(airborne(f) and up or down, f)
            end
        end
        if #up + #down > 0 then
            local parts = { packagePart({ pkg }), ", {controller}, " }
            if #up > 0 then
                table.insert(parts, callsigns(up))
                table.insert(parts, " airborne")
            end
            if #down > 0 then
                table.insert(parts, #up > 0 and ". " or "")
                table.insert(parts, callsigns(down))
                table.insert(parts, " not airborne")
            end
            table.insert(parts, ".")
            say(pkg, parts)
        end
    end
end

local function decidePush(pkg)
    if targetDestroyed(pkg) then
        -- The text names the target; the voice does not read a Retribution object name.
        return abort(pkg, { "Target " .. tostring(pkg.targetName) .. " destroyed", "Target destroyed" })
    end
    if seadLost(pkg) then
        return abort(pkg, "SEAD lost")
    end
    -- Silent players, by role (user call, 2026-10-20): SEAD holds like a SEAD on the
    -- ground, an escort gets one hold, a striker is left behind unless they are the strike.
    local silentSead = pkg.rollCalled and silentPlayers(pkg, "sead") or {}
    local silentEscort = pkg.rollCalled and silentPlayers(pkg, "escort") or {}
    local silentStrike = pkg.rollCalled and silentPlayers(pkg, "strike") or {}
    local missing = notReady(pkg)
    if #missing > 0 or #silentSead > 0 then
        if pkg.slips < MAX_SLIPS then
            local reasons = {}
            if #missing > 0 then
                table.insert(reasons, table.concat(missing, " and ") .. " not airborne")
            end
            if #silentSead > 0 then
                table.insert(reasons, #missing > 0 and ". " or "")
                table.insert(reasons, callsigns(silentSead))
                table.insert(reasons, " not checked in")
            end
            return slip(pkg, phrase(reasons))
        end
        if #silentSead > 0 then
            return abort(pkg, phrase({ callsigns(silentSead), " not checked in" }))
        end
        if not (#flightsWithRole(pkg, "sead") == 0 or anySeadAirborne(pkg)) then
            return abort(pkg, "No SEAD")
        end
    end
    if #silentEscort > 0 and not pkg.escortHoldUsed then
        pkg.escortHoldUsed = true
        return slip(pkg, phrase({ callsigns(silentEscort), " not checked in" }))
    end
    if #silentStrike > 0 and not anotherStrikerReady(pkg) then
        if not pkg.strikeHoldUsed then
            pkg.strikeHoldUsed = true
            return slip(pkg, phrase({ callsigns(silentStrike), " not checked in" }))
        end
        return abort(pkg, "No strikers checked in")
    end
    if #silentStrike > 0 then
        say(pkg, { callsigns(silentStrike), ", {controller}, not checked in. Package pushing without you." })
    end
    return push(pkg)
end

local function distanceNm(unit, x, y)
    local p = unit:getPoint()
    local dx, dz = p.x - x, p.z - y
    return math.sqrt(dx * dx + dz * dz) / NM
end

-- Every striker still alive has come within REACHED_NM and is now EGRESS_NM out, opening.
local function strikersEgressed(pkg)
    local tx, ty = tonumber(pkg.targetX), tonumber(pkg.targetY)
    if not (tx and ty) then
        return false
    end
    local anyAlive = false
    for _, f in ipairs(flightsWithRole(pkg, "strike")) do
        local lead = liveUnits(f.group)[1]
        if lead then
            anyAlive = true
            local d = distanceNm(lead, tx, ty)
            f.closest = math.min(f.closest or math.huge, d)
            local opening = f.lastDistance ~= nil and d > f.lastDistance
            f.lastDistance = d
            if f.closest > REACHED_NM or d < EGRESS_NM or not opening then
                return false
            end
        end
    end
    return anyAlive
end

local function tick(_, now)
    local onStation = controller() ~= nil
    local dueRollCall = {}
    for _, pkg in ipairs(packages) do
        for _, f in ipairs(pkg.flights or {}) do
            lost(f)
        end
        if not onStation then
            -- No controller, no package control: the push waits for one to get airborne.
            if pkg.state == "waiting" and pkg.pushAt and now >= pkg.pushAt then
                pkg.pushAt = now + POLL_SECONDS
            end
        elseif pkg.state == "waiting" and pkg.pushAt and now >= pkg.pushAt then
            decidePush(pkg)
        elseif pkg.state == "waiting" and pkg.pushAt and not pkg.rollCalled and not CASUAL
            and now >= pkg.pushAt - ROLL_CALL_LEAD_SECONDS then
            table.insert(dueRollCall, pkg)
        elseif pkg.state == "pushed" then
            if strikersEgressed(pkg) then
                pkg.state = "done"
                if not CASUAL then
                    say(pkg, { packagePart({ pkg }), ", {controller}, all strikers egressed. RTB." })
                end
            elseif now - pkg.pushedAt > EGRESS_GIVE_UP_SECONDS then
                pkg.state = "done"
            end
        end
    end
    if #dueRollCall > 0 then
        rollCall(dueRollCall)
    end
    return now + POLL_SECONDS
end

local function checkIn(arg)
    local pkg, flight = arg.pkg, arg.flight
    local callsign = callsignPart(flight.callsign)
    if pkg.state == "waiting" and pkg.rollCalled then
        flight.ready = true
        say(pkg, { callsign, ", {controller}, copy ready. Push time ", clock(pkg.pushAt), "." })
    elseif pkg.state == "waiting" and pkg.pushAt then
        local parts = { callsign, ", {controller}, radar contact." }
        if flight.holdAngels then
            table.insert(parts, " Cleared direct hold, angels ")
            table.insert(parts, digitsPart(flight.holdAngels))
            table.insert(parts, ".")
        end
        table.insert(parts, " Push time ")
        table.insert(parts, clock(pkg.pushAt))
        table.insert(parts, ".")
        say(pkg, parts)
    elseif pkg.state == "pushed" then
        say(pkg, { callsign, ", {controller}, radar contact. ", packagePart({ pkg }), " has pushed, continue." })
    else
        say(pkg, { callsign, ", {controller}, radar contact. Continue as fragged." })
    end
end

local function readyToPush(pkg, flight)
    local callsign = callsignPart(flight.callsign)
    if pkg.state ~= "waiting" then
        return say(pkg, { callsign, ", {controller}, ", packagePart({ pkg }), " has pushed." })
    end
    if pkg.rollCalled and not flight.ready then
        -- "Ready to push" in answer to the roll call is a check-in, never an early push.
        return checkIn({ pkg = pkg, flight = flight })
    end
    local reasons = {}
    local missing = notReady(pkg)
    if #missing > 0 then
        table.insert(reasons, table.concat(missing, " and ") .. " not airborne")
    end
    local silent = {}
    for _, role in ipairs({ "sead", "escort", "strike" }) do
        for _, f in ipairs(silentPlayers(pkg, role)) do
            table.insert(silent, f)
        end
    end
    if #silent > 0 then
        table.insert(reasons, #missing > 0 and ". " or "")
        table.insert(reasons, callsigns(silent))
        table.insert(reasons, " not checked in")
    end
    if #reasons == 0 then
        releaseAI(pkg)
        return push(pkg)
    end
    say(pkg, {
        callsign,
        ", {controller}, negative, ",
        phrase(reasons),
        ". Push time ",
        clock(pkg.pushAt or timer.getTime()),
        ".",
    })
end

local function sayPushTime(pkg, flight)
    local callsign = callsignPart(flight.callsign)
    if pkg.state == "waiting" and pkg.pushAt then
        return say(pkg, { callsign, ", {controller}, push time ", clock(pkg.pushAt), "." })
    end
    say(pkg, { callsign, ", {controller}, ", packagePart({ pkg }), " has pushed." })
end

-- A call SkyEye heard but could not read: the controller asks again in its own voice, by the
-- callsign it heard (user call, 2026-10-21).
local function sayAgain(pkg, flight, heard)
    if flight then
        return say(pkg, { callsignPart(flight.callsign), ", {controller}, say again." })
    end
    if heard and heard ~= "" then
        local name = heard:gsub("(%a)(%a*)", function(first, rest)
            return first:upper() .. rest
        end)
        return say(nil, { callsignPart(name), ", {controller}, say again." })
    end
    say(nil, { "Station calling {controller}, say again your callsign." })
end

local function callsignWord(callsign)
    return (tostring(callsign):lower():gsub("[^%a]", ""))
end

-- The package and flight a SkyEye request is from, by the caller's callsign. A player flight
-- is its lead's seat ("Ford 5-1"); "ford 5" is the flight and "ford 5 2" its ship 2, as
-- voiceatc hears them. Off Strict, a close-enough callsign ("Colt" for "Colt 1-1") finds
-- the one player flight it names.
local function findCaller(request)
    local wanted = normalize(request.callsign or "")
    if wanted == "" then
        return nil, nil
    end
    for _, pkg in ipairs(packages) do
        for _, f in ipairs(pkg.flights or {}) do
            if normalize(f.callsign) == wanted then
                return pkg, f
            end
        end
    end
    -- The flight alone before a ship number, so "ford 12" is Ford 12-1, not Ford 1-2.
    for pass = 1, 2 do
        for _, pkg in ipairs(packages) do
            for _, f in ipairs(pkg.flights or {}) do
                local prefix = normalize(f.callsign):sub(1, -2)
                if f.client == "true" and prefix ~= "" then
                    if pass == 1 and wanted == prefix then
                        return pkg, f
                    elseif pass == 2 and tonumber(wanted:sub(-1)) and wanted:sub(1, -2) == prefix then
                        return pkg, f
                    end
                end
            end
        end
    end
    if STRICT then
        return nil, nil
    end
    local word, foundPkg, found = callsignWord(request.callsign), nil, nil
    for _, pkg in ipairs(packages) do
        for _, f in ipairs(pkg.flights or {}) do
            if f.client == "true" and word ~= "" and callsignWord(f.callsign) == word then
                if found then
                    return nil, nil
                end
                foundPkg, found = pkg, f
            end
        end
    end
    return foundPkg, found
end

local function handleRequest(request)
    if not controller() then
        return
    end
    local pkg, flight = findCaller(request)
    if request.kind == "unknown" then
        return sayAgain(pkg, flight, request.callsign)
    end
    if not pkg then
        return
    end
    if request.kind == "checkin" then
        checkIn({ pkg = pkg, flight = flight })
    elseif request.kind == "ready" then
        readyToPush(pkg, flight)
    elseif request.kind == "pushtime" then
        sayPushTime(pkg, flight)
    end
end

local function pollLink(_, now)
    while link do
        local datagram = link:receivefrom()
        if not datagram then
            break
        end
        local fields = jsonFields(datagram)
        if fields.type == "request" then
            local ok, err = pcall(handleRequest, fields)
            if not ok then
                env.warning("pkgcontrol: request failed: " .. tostring(err))
            end
        end
    end
    return now + LINK_POLL_SECONDS
end

local function announce(_, now)
    announcePackages()
    return now + ANNOUNCE_SECONDS
end

---------------------------------------------------------------------------------------------------
-- Setup
---------------------------------------------------------------------------------------------------

local menus = {}

local function addMenu(groupName)
    for _, pkg in ipairs(packages) do
        for _, flight in ipairs(pkg.flights or {}) do
            if flight.group == groupName and flight.client == "true" then
                local g = Group.getByName(groupName)
                if g and not menus[g:getID()] then
                    menus[g:getID()] = true
                    local root = missionCommands.addSubMenuForGroup(g:getID(), "Package control")
                    missionCommands.addCommandForGroup(g:getID(), "Check in", root, checkIn, {
                        pkg = pkg,
                        flight = flight,
                    })
                end
                return
            end
        end
    end
end

for _, pkg in ipairs(packages) do
    pkg.state = "waiting"
    pkg.slips = 0
    pkg.pushAt = pushTime(pkg)
    pkg.name = pkg.name or "package"
end

local handler = {}
function handler:onEvent(event)
    if event.id ~= world.event.S_EVENT_BIRTH or not event.initiator then
        return
    end
    local ok, group = pcall(function()
        return event.initiator:getGroup()
    end)
    if ok and group then
        addMenu(group:getName())
    end
end
world.addEventHandler(handler)

for _, pkg in ipairs(packages) do
    for _, flight in ipairs(pkg.flights or {}) do
        if flight.client == "true" then
            addMenu(flight.group)
        end
    end
end

link = openLink()
timer.scheduleFunction(tick, nil, timer.getTime() + POLL_SECONDS)
if link then
    timer.scheduleFunction(announce, nil, timer.getTime() + 1)
    timer.scheduleFunction(pollLink, nil, timer.getTime() + LINK_POLL_SECONDS)
end
env.info(string.format("pkgcontrol: %d player package(s) under airborne package control", #packages))
