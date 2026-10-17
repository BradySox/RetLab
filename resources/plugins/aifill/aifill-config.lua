---------------------------------------------------------------------------------------------------
-- AI fills an empty player flight (§113). docs/dev/design/retlab-ai-fill-notes.md
--
-- Reads dcsRetribution.aiFill (emitted only when a flight carries an AI twin; inert otherwise):
--   checkDelay = "<s>", announce = "true" | "",
--   pairs = { { client, twin, coalition = "blue" | "red", activateAfter = "<s>",
--               clientActivation = "<s>", message, escorts = { { group, engagementDistMax,
--               targetTypes = {...}, x, y, z, splitFlag }, ... } }, ... }
--
-- checkDelay after the client group appears (clientActivation; a late-activated one has no seat
-- to take before then) the plugin looks for a player in it. If nobody is in any seat, it
-- announces the takeover and launches the twin (a late-activated AI air start of those seats) at
-- activateAfter, the planned takeoff, or at once if that has passed. A player who slots in after
-- the check is not stopped: a mission script cannot block a slot.
--
-- The package's escorts were tasked on the client group's id, so each gets a fresh Escort task on
-- the twin once airborne (pushed: its route resumes when the task ends), and the base plugin's
-- escort leash is pointed at the twin.
---------------------------------------------------------------------------------------------------

if not (dcsRetribution and dcsRetribution.aiFill) then
    return
end

local data = dcsRetribution.aiFill
local CHECK_DELAY = tonumber(data.checkDelay) or 300
local ANNOUNCE = data.announce == "true"
local ANNOUNCE_SECONDS = 20
-- An escort still on the ground is retried, not tasked: a pushed task replaces its taxi.
local ESCORT_RETRY_SECONDS = 30
local ESCORT_GIVE_UP_SECONDS = 3600

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

local function escortTask(escort, twinId)
    local targets = {}
    for i, target in ipairs(escort.targetTypes or {}) do
        targets[i] = target
    end
    local task = {
        id = "ControlledTask",
        params = {
            task = {
                id = "Escort",
                params = {
                    groupId = twinId,
                    engagementDistMax = tonumber(escort.engagementDistMax) or 60000,
                    targetTypes = targets,
                    pos = {
                        x = tonumber(escort.x) or 0,
                        y = tonumber(escort.y) or 0,
                        z = tonumber(escort.z) or 0,
                    },
                    lastWptIndexFlag = false,
                    lastWptIndexFlagChangedManually = false,
                },
            },
        },
    }
    if escort.splitFlag then
        task.params.stopCondition = { userFlag = escort.splitFlag, userFlagValue = true }
    end
    return task
end

local function airborne(group)
    if not (group and group:isExist()) then
        return false
    end
    local lead = group:getUnits()[1]
    return lead ~= nil and lead:inAir()
end

local function pushEscort(escort, twinId, giveUpAt)
    local group = Group.getByName(escort.group)
    if airborne(group) then
        group:getController():pushTask(escortTask(escort, twinId))
        env.info("AI fill: " .. tostring(escort.group) .. " escorts the twin")
        return
    end
    if timer.getTime() >= giveUpAt then
        env.info("AI fill: " .. tostring(escort.group) .. " never airborne; not retasked")
        return
    end
    timer.scheduleFunction(function()
        local ok, err = pcall(pushEscort, escort, twinId, giveUpAt)
        if not ok then
            env.error("AI fill: " .. tostring(err))
        end
        return nil
    end, nil, timer.getTime() + ESCORT_RETRY_SECONDS)
end

local function repointLeash(pair, twinId)
    if type(dcsRetribution.Escorts) ~= "table" then
        return
    end
    for _, leash in pairs(dcsRetribution.Escorts) do
        if leash.escortedGroupName == pair.client then
            leash.escortedGroupName = pair.twin
            leash.escortedGroupId = tostring(twinId)
        end
    end
end

local function launch(pair)
    local group = Group.getByName(pair.twin)
    if not group then
        env.warning("AI fill: twin group " .. tostring(pair.twin) .. " not found")
        return
    end
    group:activate()
    env.info("AI fill: " .. tostring(pair.twin) .. " launched for " .. tostring(pair.client))
    local twinId = group:getID()
    repointLeash(pair, twinId)
    local giveUpAt = timer.getTime() + ESCORT_GIVE_UP_SECONDS
    for _, escort in ipairs(pair.escorts or {}) do
        pushEscort(escort, twinId, giveUpAt)
    end
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
    end, pair, timer.getTime() + (tonumber(pair.clientActivation) or 0) + CHECK_DELAY)
end
