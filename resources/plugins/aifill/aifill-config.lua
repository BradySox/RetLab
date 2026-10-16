---------------------------------------------------------------------------------------------------
-- AI fills an empty player flight (§113). docs/dev/design/retlab-ai-fill-notes.md
--
-- Reads dcsRetribution.aiFill (emitted only when a flight carries an AI twin; inert otherwise):
--   checkDelay = "<s>", announce = "true" | "",
--   pairs = { { client, twin, coalition = "blue" | "red", activateAfter = "<s>", message }, ... }
--
-- At checkDelay the plugin looks for a player in each client group. If nobody is in any seat, it
-- announces the takeover and launches the twin (a late-activated AI air start of those seats) at
-- activateAfter, the planned takeoff, or at once if that has passed. A player who slots in after
-- the check is not stopped: a mission script cannot block a slot.
---------------------------------------------------------------------------------------------------

if not (dcsRetribution and dcsRetribution.aiFill) then
    return
end

local data = dcsRetribution.aiFill
local CHECK_DELAY = tonumber(data.checkDelay) or 300
local ANNOUNCE = data.announce == "true"
local ANNOUNCE_SECONDS = 20

local SIDES = { blue = coalition.side.BLUE, red = coalition.side.RED }

local function occupied(side, groupName)
    for _, unit in ipairs(coalition.getPlayers(side) or {}) do
        local group = unit:getGroup()
        if group and group:getName() == groupName then
            return true
        end
    end
    return false
end

local function launch(pair)
    local group = Group.getByName(pair.twin)
    if not group then
        env.warning("AI fill: twin group " .. tostring(pair.twin) .. " not found")
        return
    end
    group:activate()
    env.info("AI fill: " .. tostring(pair.twin) .. " launched for " .. tostring(pair.client))
end

local function check(pair, time)
    local side = SIDES[pair.coalition]
    if side == nil or occupied(side, pair.client) then
        return
    end
    if ANNOUNCE and pair.message then
        trigger.action.outTextForCoalition(side, pair.message, ANNOUNCE_SECONDS)
    end
    local at = tonumber(pair.activateAfter) or 0
    if at > time then
        timer.scheduleFunction(function()
            local ok, err = pcall(launch, pair)
            if not ok then
                env.error("AI fill: " .. tostring(err))
            end
            return nil
        end, nil, at)
    else
        launch(pair)
    end
end

for _, pair in ipairs(data.pairs or {}) do
    timer.scheduleFunction(function(p, time)
        local ok, err = pcall(check, p, time)
        if not ok then
            env.error("AI fill: " .. tostring(err))
        end
        return nil
    end, pair, timer.getTime() + CHECK_DELAY)
end
