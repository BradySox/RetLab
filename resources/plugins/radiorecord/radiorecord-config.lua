---------------------------------------------------------------------------------------------------
-- Record radios for Tacview (§127). docs/dev/retlab-features.md §127
--
-- Reads dcsRetribution.radioRecord (emitted only with the setting on): linkHost, linkPort,
--   frequencies = { { frequency ('251.000AM'), label, recordOnly ('true' or '') } }
--
-- Sends SkyEye a record message over its mission link, and again every minute so a SkyEye
-- started after the mission still records. SkyEye writes one WAV per frequency next to the
-- Tacview recordings. A player flight's own frequency is record-only: SkyEye never answers there.
---------------------------------------------------------------------------------------------------

if not (dcsRetribution and dcsRetribution.radioRecord) then
    return
end

local data = dcsRetribution.radioRecord
local RESEND_SECONDS = 60

local function jsonString(s)
    local escaped = tostring(s):gsub('[%c"\]', function(c)
        if c == '"' then
            return '\\"'
        elseif c == "\\" then
            return "\\\\"
        end
        return string.format("\u%04x", string.byte(c))
    end)
    return '"' .. escaped .. '"'
end

local function jsonValue(value)
    if type(value) == "boolean" then
        return value and "true" or "false"
    end
    return jsonString(value)
end

local function message()
    local items = {}
    for _, f in ipairs(data.frequencies or {}) do
        table.insert(items, "{" .. table.concat({
            jsonString("frequency") .. ":" .. jsonValue(f.frequency),
            jsonString("label") .. ":" .. jsonValue(f.label or ""),
            jsonString("recordOnly") .. ":" .. jsonValue(f.recordOnly == "true"),
        }, ",") .. "}")
    end
    return '{"type":"record","frequencies":[' .. table.concat(items, ",") .. "]}"
end

local function openLink()
    if not (package and require) then
        return nil
    end
    local ok, socket = pcall(function()
        package.path = package.path .. ";.\LuaSocket\?.lua;"
        package.cpath = package.cpath .. ";.\LuaSocket\?.dll;"
        return require("socket")
    end)
    if not ok or not socket then
        env.warning("radiorecord: LuaSocket unavailable, nothing is recorded: " .. tostring(socket))
        return nil
    end
    local udp = socket.udp()
    udp:settimeout(0)
    udp:setsockname("127.0.0.1", 0)
    return udp
end

local link = openLink()
local text = message()

local function send(_, now)
    if link then
        link:sendto(text, data.linkHost or "127.0.0.1", tonumber(data.linkPort) or 42690)
    end
    return now + RESEND_SECONDS
end

if link then
    env.info("radiorecord: asking SkyEye to record " .. #(data.frequencies or {}) .. " frequencies")
    timer.scheduleFunction(send, nil, timer.getTime() + 5)
end
