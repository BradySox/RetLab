---------------------------------------------------------------------------------------------------
-- AWACS package controller (§117). docs/dev/retlab-features.md §117
--
-- Reads dcsRetribution.packageControl (emitted only when the setting is on and a blue AWACS and
-- a player package fly): startSeconds, srsPath, port, gender, culture,
--   awacs = { { group, callsign } }, packages = { { name, freq, modulation, totAfter,
--   targetName, targetX, targetY, targetUnits = {...},
--   flights = { { group, callsign, role = strike|sead|escort, client, pushAfter,
--                 holdX, holdY, holdAngels } } } }
--
-- The first live blue AWACS talks on each package's frequency: a check-in reply from the F10
-- menu, the push call at the package push time, up to two 3-minute holds while a SEAD or escort
-- flight is not airborne, an abort when the target is already dead or the SEAD is lost, and the
-- egress call. Speech goes through MOOSE MSRS (SRS External Audio); every call is also shown as
-- text to the package's player groups. With no AWACS alive nothing is said.
---------------------------------------------------------------------------------------------------

if not (dcsRetribution and dcsRetribution.packageControl) then
    return
end

local data = dcsRetribution.packageControl
local POLL_SECONDS = 10
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

local function speaker()
    for _, a in ipairs(data.awacs or {}) do
        if #liveUnits(a.group) > 0 then
            return a
        end
    end
    return nil
end

local function spokenCallsign(callsign)
    return (tostring(callsign):gsub("%-", " "))
end

local function clock(missionSeconds)
    local t = math.floor(START_SECONDS + missionSeconds) % 86400
    return string.format("%02d %02d", math.floor(t / 3600), math.floor(t / 60) % 60)
end

local function srsFor(pkg, label)
    if not (MSRS and os and io) then
        return nil
    end
    if pkg.srs == nil then
        local ok, srs = pcall(function()
            local modulation = pkg.modulation == "FM" and radio.modulation.FM or radio.modulation.AM
            local s = MSRS:New(data.srsPath, tonumber(pkg.freq), modulation)
            s:SetCoalition(coalition.side.BLUE)
            s:SetPort(tonumber(data.port) or 5002)
            s:SetGender(data.gender or "male")
            s:SetCulture(data.culture or "en-US")
            s:SetLabel((tostring(label):gsub("%s", "")))
            return s
        end)
        pkg.srs = ok and srs or false
        if not ok then
            env.warning("pkgcontrol: SRS setup failed: " .. tostring(srs))
        end
    end
    return pkg.srs or nil
end

local function say(pkg, text)
    local awacs = speaker()
    if not awacs then
        return false
    end
    local line = text:gsub("{awacs}", awacs.callsign)
    for _, f in ipairs(pkg.flights or {}) do
        if f.client == "true" then
            local g = Group.getByName(f.group)
            if g and g:isExist() then
                trigger.action.outTextForGroup(g:getID(), line, TEXT_SECONDS)
            end
        end
    end
    local srs = srsFor(pkg, awacs.callsign)
    if srs then
        local ok, err = pcall(function()
            srs:PlayText(line)
        end)
        if not ok then
            env.warning("pkgcontrol: SRS call failed: " .. tostring(err))
        end
    end
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
    for _, u in ipairs(liveUnits(flight.group)) do
        if u:inAir() then
            return true
        end
    end
    return false
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

local function abort(pkg, reason)
    pkg.state = "done"
    say(pkg, string.format("Package %s, {awacs}, abort, abort, abort. %s. RTB.", pkg.name, reason))
end

local function push(pkg)
    pkg.state = "pushed"
    pkg.pushedAt = timer.getTime()
    say(pkg, string.format("Package %s, {awacs}, push, push.", pkg.name))
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
        return say(
            pkg,
            string.format(
                "Package %s, {awacs}, hold, hold. %s not airborne. New push time %s.",
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
    for _, pkg in ipairs(packages) do
        for _, f in ipairs(pkg.flights or {}) do
            lost(f)
        end
        if pkg.state == "waiting" and pkg.pushAt and now >= pkg.pushAt then
            decidePush(pkg)
        elseif pkg.state == "pushed" then
            if strikersEgressed(pkg) then
                pkg.state = "done"
                say(pkg, string.format("Package %s, {awacs}, all strikers egressed. RTB.", pkg.name))
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
        text = string.format("%s, {awacs}, radar contact.%s Push time %s.", callsign, hold, clock(pkg.pushAt))
    elseif pkg.state == "pushed" then
        text = string.format("%s, {awacs}, radar contact. Package %s has pushed, continue.", callsign, pkg.name)
    else
        text = string.format("%s, {awacs}, radar contact. Continue as fragged.", callsign)
    end
    say(pkg, text)
end

local menus = {}

local function addMenu(groupName)
    for _, pkg in ipairs(packages) do
        for _, flight in ipairs(pkg.flights or {}) do
            if flight.group == groupName and flight.client == "true" then
                local g = Group.getByName(groupName)
                if g and not menus[g:getID()] then
                    menus[g:getID()] = true
                    local root = missionCommands.addSubMenuForGroup(g:getID(), "AWACS")
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

timer.scheduleFunction(tick, nil, timer.getTime() + POLL_SECONDS)
env.info(string.format("pkgcontrol: %d player package(s) under AWACS control", #packages))
