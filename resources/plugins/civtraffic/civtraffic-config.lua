---------------------------------------------------------------------------------------------------
-- Civil air traffic: a steady stream. docs/dev/design/retlab-civil-traffic-notes.md
--
-- Reads dcsRetribution.civilTraffic (emitted only when the setting is not Off; inert otherwise):
--   targets = { airway = "<n>", hop = "<n>" },
--   flights = { { group, layer = "airway" | "hop", queued = "true" | "", maxAge = "<s>",
--                 exitX, exitZ (leaves at the map edge), field (departure field) }, ... }
--
-- Every 30 s: a flight that landed, reached its map-edge exit, never got airborne, or outlived
-- maxAge is removed; then queued flights are switched on (Group:activate) until each layer is
-- back at its target. Two take-offs from one field are spaced. Planned in Python; this script
-- only switches groups on and removes them, never spawns one.
---------------------------------------------------------------------------------------------------

if not (dcsRetribution and dcsRetribution.civilTraffic) then
    return
end

local data = dcsRetribution.civilTraffic
local TICK_S = 30
local EXIT_RADIUS_M = 15000
local LANDED_LINGER_S = 90
local STUCK_S = 900
local FIELD_SPACING_S = 180
local MAX_ACTIVATIONS_PER_TICK = 2

local targets = {}
local queues = {}
for layer, value in pairs(data.targets or {}) do
    targets[layer] = tonumber(value) or 0
    queues[layer] = {}
end

local active = {}
local lastDeparture = {}

for _, flight in ipairs(data.flights or {}) do
    local layer = flight.layer
    if queues[layer] == nil then
        queues[layer] = {}
        targets[layer] = 0
    end
    if flight.queued == "true" then
        table.insert(queues[layer], flight)
    else
        table.insert(active, { flight = flight, since = 0 })
    end
end

local function remove(entry, why)
    local group = Group.getByName(entry.flight.group)
    if why ~= "gone" and group and group:isExist() then
        group:destroy()
    end
    env.info("Civil traffic: " .. tostring(entry.flight.group) .. " removed, " .. why)
end

-- Returns a reason when the flight is done, nil while it is still flying its route.
local function finished(entry, time)
    local flight = entry.flight
    local group = Group.getByName(flight.group)
    if not (group and group:isExist()) then
        return "gone"
    end
    local lead = group:getUnits()[1]
    if lead == nil then
        return "gone"
    end
    if time - entry.since >= (tonumber(flight.maxAge) or 14400) then
        return "out of time"
    end
    local airborne = lead:inAir()
    if airborne then
        entry.wasAirborne = true
        entry.landedAt = nil
        local exitX, exitZ = tonumber(flight.exitX), tonumber(flight.exitZ)
        if exitX and exitZ then
            local p = lead:getPoint()
            local dx, dz = p.x - exitX, p.z - exitZ
            if dx * dx + dz * dz <= EXIT_RADIUS_M * EXIT_RADIUS_M then
                return "left the map"
            end
        end
        return nil
    end
    if entry.wasAirborne then
        entry.landedAt = entry.landedAt or time
        if time - entry.landedAt >= LANDED_LINGER_S then
            return "landed"
        end
        return nil
    end
    if time - entry.since >= STUCK_S then
        return "never took off"
    end
    return nil
end

local function canDepart(flight, time)
    local field = flight.field
    if field == nil or field == "" then
        return true
    end
    local last = lastDeparture[field]
    return last == nil or time - last >= FIELD_SPACING_S
end

local function activateNext(layer, time)
    local queue = queues[layer]
    for i, flight in ipairs(queue) do
        if canDepart(flight, time) then
            table.remove(queue, i)
            local group = Group.getByName(flight.group)
            if group == nil then
                env.warning("Civil traffic: group " .. tostring(flight.group) .. " not found")
                return true
            end
            group:activate()
            if flight.field and flight.field ~= "" then
                lastDeparture[flight.field] = time
            end
            table.insert(active, { flight = flight, since = time })
            return true
        end
    end
    return false
end

local function tick(time)
    local counts = {}
    for i = #active, 1, -1 do
        local entry = active[i]
        local why = finished(entry, time)
        if why then
            remove(entry, why)
            table.remove(active, i)
        else
            local layer = entry.flight.layer
            counts[layer] = (counts[layer] or 0) + 1
        end
    end
    local launched = 0
    for layer, target in pairs(targets) do
        local count = counts[layer] or 0
        while count < target and launched < MAX_ACTIVATIONS_PER_TICK do
            if not activateNext(layer, time) then
                break
            end
            count = count + 1
            launched = launched + 1
        end
    end
end

timer.scheduleFunction(function(_, time)
    local ok, err = pcall(tick, time)
    if not ok then
        env.error("Civil traffic: " .. tostring(err))
    end
    return time + TICK_S
end, nil, timer.getTime() + TICK_S)

env.info("Civil traffic: " .. tostring(#active) .. " flying at start")
