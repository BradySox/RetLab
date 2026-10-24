-- Train losses (features doc §123). DCS sees a whole train as one unit and fires no
-- dead event when it is destroyed (2026-10-24 probe: health 5 -> -745, speed 0, no
-- event), so this polls each train's health and reports its cargo once.
-- retlab_trains (train unit name -> cargo names) is written by the mission generator.

local TRAIN_POLL_SECONDS = 5
local train_reported = {}

local function train_is_dead(name)
    local unit = Unit.getByName(name)
    if unit == nil or not unit:isExist() then
        return true
    end
    return unit:getLife() < 1
end

local function poll_trains()
    if retlab_trains == nil then
        return nil
    end
    local pending = false
    for name, cargo in pairs(retlab_trains) do
        if not train_reported[name] then
            local ok, dead = pcall(train_is_dead, name)
            if ok and dead then
                train_reported[name] = true
                for _, cargo_name in ipairs(cargo) do
                    dead_events[#dead_events + 1] = cargo_name
                end
                dirty_state = true
                logger:info(string.format("Train destroyed: '%s' (%d cargo units)", name, #cargo))
            else
                pending = true
            end
        end
    end
    if not pending then
        return nil
    end
    return timer.getTime() + TRAIN_POLL_SECONDS
end

timer.scheduleFunction(poll_trains, nil, timer.getTime() + TRAIN_POLL_SECONDS)
