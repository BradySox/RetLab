-- dcs_placement_probe.lua -- reads the ground under candidate unit spots.
-- Built into a check mission by tools/campaign_placement.py (check), which prepends
-- RETLAB_PLACEMENT = {name, points = {{id, x, y}, ...}}. Writes one row per point
-- to Saved Games\DCS\Logs; `report` scores the rows and draws the review map.
-- Slope is read over a launcher's footprint: an erecting SAM launcher never raises
-- past about 5 degrees of tilt (docs/dev/design/retlab-campaign-placement-notes.md).
-- Needs io and lfs, i.e. Retribution's de-sanitized MissionScripting.lua.
-- Not in plugin.json: it only ever runs in the check mission.

local cfg = RETLAB_PLACEMENT
local POINTS_PER_TICK = 40
local SLOPE_RADII = { 10, 25 }
local SURFACE_RADIUS = 15
local BUILDING_RADIUS = 60

local function say(msg)
  env.info("[PLACEMENT] " .. msg)
  trigger.action.outText("[PLACEMENT] " .. msg, 30)
end

if not (io and lfs) then
  say("io/lfs are sanitized: install Retribution's MissionScripting.lua and rerun")
  return
end

local path = lfs.writedir() .. "Logs\\retlab_placement_" .. cfg.name .. ".txt"
local out = io.open(path, "w")
if not out then
  say("cannot write " .. path)
  return
end

local function height(x, y)
  return land.getHeight({ x = x, y = y })
end

-- Steepest rise across the spot, in degrees, over each footprint radius.
local function slope_at(x, y)
  local worst = 0
  for _, r in ipairs(SLOPE_RADII) do
    for i = 0, 3 do
      local a = i * math.pi / 4
      local dx, dy = r * math.cos(a), r * math.sin(a)
      local rise = math.abs(height(x + dx, y + dy) - height(x - dx, y - dy))
      local deg = math.deg(math.atan(rise / (2 * r)))
      if deg > worst then
        worst = deg
      end
    end
  end
  return worst
end

-- The worst surface on and around the spot: water beats runway beats road beats land.
local RANK = { [1] = 0, [4] = 1, [5] = 2, [2] = 3, [3] = 4 }
local function surface_at(x, y)
  local worst = land.getSurfaceType({ x = x, y = y })
  for i = 0, 7 do
    local a = i * math.pi / 4
    local s = land.getSurfaceType({
      x = x + SURFACE_RADIUS * math.cos(a),
      y = y + SURFACE_RADIUS * math.sin(a),
    })
    if (RANK[s] or 0) > (RANK[worst] or 0) then
      worst = s
    end
  end
  return worst
end

local function buildings_at(x, y, h)
  local count, nearest, kind = 0, -1, "-"
  local volume = {
    id = world.VolumeType.SPHERE,
    params = { point = { x = x, y = h, z = y }, radius = BUILDING_RADIUS },
  }
  world.searchObjects(Object.Category.SCENERY, volume, function(obj)
    local p = obj:getPoint()
    local d = math.sqrt((p.x - x) ^ 2 + (p.z - y) ^ 2)
    count = count + 1
    if nearest < 0 or d < nearest then
      nearest = d
      kind = string.gsub(obj:getTypeName() or "-", "%s", "_")
    end
    return true
  end)
  return count, nearest, kind
end

out:write(string.format("RETLAB-PLACEMENT 1 %s %d\n", cfg.name, #cfg.points))
say(string.format("checking %d spots into %s", #cfg.points, path))

local index = 0
local function sample(_, now)
  local last = math.min(index + POINTS_PER_TICK, #cfg.points)
  while index < last do
    index = index + 1
    local p = cfg.points[index]
    local h = height(p.x, p.y)
    local count, nearest, kind = buildings_at(p.x, p.y, h)
    out:write(string.format("%s %.1f %.1f %d %d %.0f %s\n",
      p.id, h, slope_at(p.x, p.y), surface_at(p.x, p.y), count, nearest, kind))
  end
  if index < #cfg.points then
    return now + 0.01
  end
  out:write("END\n")
  out:close()
  say("done: " .. path .. " -- you can quit now")
  return nil
end

timer.scheduleFunction(sample, nil, timer.getTime() + 1)
