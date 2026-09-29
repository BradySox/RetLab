-- dcs_terrain_height_probe.lua -- samples land.getHeight on a grid for the DTC.
-- Built into a probe mission by scripts/dcs_terrain_heights.py (generate), which
-- prepends RETLAB_HEIGHT_GRID = {terrain, x0, y0, step, nx, ny}. Writes one text
-- row per x step to Saved Games\DCS\Logs; `apply` turns that into the .npz.
-- Needs io and lfs, i.e. Retribution's de-sanitized MissionScripting.lua.
-- Not in plugin.json: it only ever runs in the probe mission.

local cfg = RETLAB_HEIGHT_GRID
local ROWS_PER_TICK = 10

local function say(msg)
  env.info("[HEIGHTS] " .. msg)
  trigger.action.outText("[HEIGHTS] " .. msg, 30)
end

if not (io and lfs) then
  say("io/lfs are sanitized: install Retribution's MissionScripting.lua and rerun")
  return
end

local path = lfs.writedir() .. "Logs\\retlab_terrain_heights_" .. cfg.terrain .. ".txt"
local out = io.open(path, "w")
if not out then
  say("cannot write " .. path)
  return
end

out:write(string.format("RETLAB-HEIGHTS 1 %s %.1f %.1f %.1f %d %d\n",
  cfg.terrain, cfg.x0, cfg.y0, cfg.step, cfg.nx, cfg.ny))
say(string.format("sampling %d x %d points into %s", cfg.nx, cfg.ny, path))

local row = 0
local function sample(_, now)
  local last = math.min(row + ROWS_PER_TICK, cfg.nx)
  while row < last do
    local x = cfg.x0 + row * cfg.step
    local values = {}
    for j = 0, cfg.ny - 1 do
      local h = land.getHeight({ x = x, y = cfg.y0 + j * cfg.step })
      values[j + 1] = string.format("%d", math.floor(h + 0.5))
    end
    out:write(table.concat(values, " "), "\n")
    row = row + 1
  end
  if row < cfg.nx then
    if row % 100 < ROWS_PER_TICK then
      say(string.format("row %d of %d", row, cfg.nx))
    end
    return now + 0.01
  end
  out:write("END\n")
  out:close()
  say("done: " .. path)
  return nil
end

timer.scheduleFunction(sample, nil, timer.getTime() + 1)
