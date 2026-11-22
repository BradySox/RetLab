-- Silence AI ATC (features doc §132): every land airfield and FARP starts the
-- mission with its DCS tower in silent mode. Carriers are left alone; their
-- tower runs the recovery pattern.

local function retlabSilenceAtc()
    if not world or not world.getAirbases or not Airbase or not Airbase.Category then
        return 0
    end
    local silenced = 0
    for _, airbase in pairs(world.getAirbases() or {}) do
        local ok, desc = pcall(airbase.getDesc, airbase)
        if ok and desc and desc.category ~= Airbase.Category.SHIP
            and airbase.setRadioSilentMode then
            if pcall(airbase.setRadioSilentMode, airbase, true) then
                silenced = silenced + 1
            end
        end
    end
    return silenced
end

env.info("RetLab silent ATC: " .. tostring(retlabSilenceAtc()) .. " towers silenced")
