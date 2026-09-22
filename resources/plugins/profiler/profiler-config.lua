---------------------------------------------------------------------------------------------------
-- Lua profiler + sim-thread stall log. Diagnostic only, default off.
-- docs/dev/design/retlab-sim-thread-freeze-notes.md carries the runbook and how to read the output.
--
-- Two instruments, because they answer different questions:
--   * MOOSE's PROFILER (debug.sethook on every call) says WHICH Lua function ate the time. It
--     needs os/io/lfs, which Retribution's MissionScripting.lua leaves open. It slows the
--     mission, so it runs for a window, not the whole flight.
--   * The stall log says WHEN the sim thread stopped, whatever stopped it: a wall-clock gap
--     between probe runs longer than the tick plus the threshold. Measured on wall time alone,
--     because DCS catches model time up after a short freeze -- a model-lag measure (the first
--     version, test 37) never sees those. Each line carries the model advance too, so a
--     caught-up hitch (model ~ wall) reads apart from a lag (model << wall). Runs all mission.
-- If the profiler's function total is a small share of the window while the stall log is full,
-- the stall is native DCS (pathfinding, radio storage, model loads), not Lua.
---------------------------------------------------------------------------------------------------

local opts = (dcsRetribution and dcsRetribution.plugins and dcsRetribution.plugins.profiler) or {}
local DELAY_S = tonumber(opts.delaySeconds) or 60
local DURATION_S = tonumber(opts.durationSeconds) or 300
local HITCH_S = (tonumber(opts.hitchThresholdMs) or 250) / 1000

local TICK_S = 0.25          -- model-time spacing of the stall probe
local HEARTBEAT_S = 30       -- proves the probe is alive in a mission with no stalls

local function log(msg)
    env.info("PROFILER| " .. msg)
end

local function heapKB()
    return collectgarbage("count")
end

-- os.clock on DCS's CRT is wall time since process start (MOOSE labels it "Runtime Real").
local haveClock = (os ~= nil and os.clock ~= nil)

if haveClock then
    local lastWall = os.clock()
    local lastModel = timer.getTime()
    local nextBeat = lastModel + HEARTBEAT_S
    local stalls, worst = 0, 0

    local function probe(_, now)
        local wall = os.clock()
        local gap = (wall - lastWall) - TICK_S
        if gap > HITCH_S then
            stalls = stalls + 1
            if gap > worst then
                worst = gap
            end
            log(string.format("stall %4.0f ms at t=%.2f  model +%.2f s  heap=%.0f KB",
                gap * 1000, now, now - lastModel, heapKB()))
        end
        if now >= nextBeat then
            nextBeat = now + HEARTBEAT_S
            log(string.format("alive t=%.0f  stalls=%d  worst=%.0f ms  heap=%.0f KB",
                now, stalls, worst * 1000, heapKB()))
        end
        lastWall, lastModel = wall, now
        return now + TICK_S
    end

    timer.scheduleFunction(probe, nil, timer.getTime() + TICK_S)
    log(string.format("stall log armed: threshold %d ms, probe every %.2f s", HITCH_S * 1000, TICK_S))
else
    log("os.clock unavailable: MissionScripting.lua sanitizes os, so no stall log and no profiler")
end

if PROFILER == nil then
    log("MOOSE PROFILER not loaded (Moose.lua missing or older), function profiling skipped")
elseif haveClock and io ~= nil and lfs ~= nil then
    -- PROFILER.Start with a delay schedules itself through MOOSE; Duration schedules the Stop,
    -- which writes MooseProfiler.txt/.csv to Saved Games\DCS\Logs and a summary to dcs.log.
    -- Mission end stops it early via PROFILER's own S_EVENT_MISSION_END handler.
    PROFILER.Start(DELAY_S, DURATION_S)
    log(string.format("function profiler starts at t+%d s for %d s -> Logs\\MooseProfiler.txt",
        DELAY_S, DURATION_S))
else
    log("io or lfs unavailable: function profiling needs both (MissionScripting.lua)")
end
