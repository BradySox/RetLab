env.info("-----DCSRetribution|MOOSE ATIS plugin - start -----")

-- Reads no plugin options; the frequency pair is used by the mission generator.
-- "Debug Mode" (never used) and "Announce Field Name" (needs ATIS:SetReportName,
-- absent from the bundled Moose.lua) were removed 2026-09-22.

if not (dcsRetribution and dcsRetribution.Atis) then
    env.info("-----dcsRetribution.Atis NOT FOUND -- no ATIS stations created")
    return
end

for _, entry in pairs(dcsRetribution.Atis) do
    local ok, err = pcall(function()
        local atis = ATIS:New(entry.name, entry.freq, entry.modulation or 0)
        -- pydcs stores bundled resources flat by basename under l10n/DEFAULT,
        -- so point all three MOOSE soundfile sub-paths there. DCS resolves
        -- transmission files relative to the .miz root; a bare basename (empty
        -- path) does not resolve and the ATIS plays silently.
        local soundPath = "l10n/DEFAULT/"
        atis:SetSoundfilesPath(soundPath, soundPath, soundPath)
        atis:Start()
        env.info(string.format(
            "DCSRetribution|MOOSE ATIS: started %s on %.3f MHz", entry.name, entry.freq
        ))
    end)
    if not ok then
        env.info("DCSRetribution|MOOSE ATIS: failed to start a station: " .. tostring(err))
    end
end
