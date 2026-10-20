---------------------------------------------------------------------------------------------------
-- Airborne package control (§117). docs/dev/retlab-features.md §117
--
-- Reads dcsRetribution.packageControl (emitted only when a blue ABCCC C-130 and a player
-- package fly): startSeconds, linkHost, linkPort, strikeFreq, strikeModulation, awacsVoice,
--   controllerVoice, controllers = { { group, callsign } },
--   packages = { { name, totAfter, targetName, targetX, targetY,
--   targetUnits = {...}, flights = { { group, callsign, role = strike|sead|escort, client,
--   pushAfter, holdX, holdY, holdAngels, holdIndex, home } } } }
--
-- While a ABCCC C-130 is alive AND airborne it runs every package on STRIKE (common):
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
local MAX_SLIPS = 2
local NM = 1852
local EGRESS_NM = 10
-- A striker must have come this close to the target before it can egress.
local REACHED_NM = 30
local EGRESS_GIVE_UP_SECONDS = 3600
local TEXT_SECONDS = 15

local START_SECONDS = tonumber(data.startSeconds) or 0
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

local function airborneUnit(groupName)
    for _, u in ipairs(liveUnits(groupName)) do
        if u:inAir() then
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

local function spokenCallsign(callsign)
    return (tostring(callsign):gsub("%-", " "))
end

local function clock(missionSeconds)
    local t = math.floor(START_SECONDS + missionSeconds) % 86400
    return string.format("%02d %02d", math.floor(t / 3600), math.floor(t / 60) % 60)
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
    })
end

---------------------------------------------------------------------------------------------------
-- Calls
---------------------------------------------------------------------------------------------------

local function say(pkg, text)
    local c = controller()
    if not c then
        return false
    end
    local line = text:gsub("{controller}", c.callsign)
    for _, f in ipairs(pkg.flights or {}) do
        if f.client == "true" then
            local g = Group.getByName(f.group)
            if g and g:isExist() then
                trigger.action.outTextForGroup(g:getID(), line, TEXT_SECONDS)
            end
        end
    end
    send({ { "type", "say" }, { "frequency", STRIKE }, { "text", line }, { "voice", data.controllerVoice or "" } })
    return true
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
    say(pkg, string.format("Package %s, {controller}, abort, abort, abort. %s. RTB.", pkg.name, reason))
end

local function push(pkg)
    pkg.state = "pushed"
    pkg.pushedAt = timer.getTime()
    say(pkg, string.format("Package %s, {controller}, push, push.", pkg.name))
end

local function notReady(pkg)
    local missing = {}
    for _, role in ipairs({ "sead", "escort" }) do
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

local function decidePush(pkg)
    if targetDestroyed(pkg) then
        return abort(pkg, "Target " .. tostring(pkg.targetName) .. " destroyed")
    end
    if seadLost(pkg) then
        return abort(pkg, "SEAD lost")
    end
    local missing = notReady(pkg)
    if #missing == 0 then
        return push(pkg)
    end
    if pkg.slips < MAX_SLIPS then
        pkg.slips = pkg.slips + 1
        pkg.pushAt = pkg.pushAt + HOLD_SLIP_SECONDS
        holdAI(pkg)
        return say(
            pkg,
            string.format(
                "Package %s, {controller}, hold, hold. %s not airborne. New push time %s.",
                pkg.name,
                table.concat(missing, " and "),
                clock(pkg.pushAt)
            )
        )
    end
    if #flightsWithRole(pkg, "sead") == 0 or anySeadAirborne(pkg) then
        return push(pkg)
    end
    return abort(pkg, "No SEAD")
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
        elseif pkg.state == "pushed" then
            if strikersEgressed(pkg) then
                pkg.state = "done"
                say(pkg, string.format("Package %s, {controller}, all strikers egressed. RTB.", pkg.name))
            elseif now - pkg.pushedAt > EGRESS_GIVE_UP_SECONDS then
                pkg.state = "done"
            end
        end
    end
    return now + POLL_SECONDS
end

local function checkIn(arg)
    local pkg, flight = arg.pkg, arg.flight
    local callsign = spokenCallsign(flight.callsign)
    local text
    if pkg.state == "waiting" and pkg.pushAt then
        local hold = flight.holdAngels and string.format(" Cleared direct hold, angels %s.", flight.holdAngels) or ""
        text = string.format("%s, {controller}, radar contact.%s Push time %s.", callsign, hold, clock(pkg.pushAt))
    elseif pkg.state == "pushed" then
        text = string.format("%s, {controller}, radar contact. Package %s has pushed, continue.", callsign, pkg.name)
    else
        text = string.format("%s, {controller}, radar contact. Continue as fragged.", callsign)
    end
    say(pkg, text)
end

local function readyToPush(pkg, flight)
    local callsign = spokenCallsign(flight.callsign)
    if pkg.state ~= "waiting" then
        return say(pkg, string.format("%s, {controller}, package %s has pushed.", callsign, pkg.name))
    end
    local missing = notReady(pkg)
    if #missing == 0 then
        releaseAI(pkg)
        return push(pkg)
    end
    say(
        pkg,
        string.format(
            "%s, {controller}, negative, %s not airborne. Push time %s.",
            callsign,
            table.concat(missing, " and "),
            clock(pkg.pushAt or timer.getTime())
        )
    )
end

local function sayPushTime(pkg, flight)
    local callsign = spokenCallsign(flight.callsign)
    if pkg.state == "waiting" and pkg.pushAt then
        return say(pkg, string.format("%s, {controller}, push time %s.", callsign, clock(pkg.pushAt)))
    end
    say(pkg, string.format("%s, {controller}, package %s has pushed.", callsign, pkg.name))
end

-- The package and flight a SkyEye request is from, by the caller's callsign.
local function findCaller(request)
    local wanted = normalize(request.callsign or "")
    for _, pkg in ipairs(packages) do
        for _, f in ipairs(pkg.flights or {}) do
            if wanted ~= "" and normalize(f.callsign) == wanted then
                return pkg, f
            end
        end
    end
    return nil, nil
end

local function handleRequest(request)
    if not controller() then
        return
    end
    local pkg, flight = findCaller(request)
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
