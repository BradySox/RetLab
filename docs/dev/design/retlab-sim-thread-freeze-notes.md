# Sim-thread freezes on a big turn — evidence ledger and the profiler runbook

Opened 2026-09-20. Anatolian Reach (Syria), an 870-unit turn, the DM in an F-16C at
Incirlik: a ~1 s lock-up every 15–30 s for the whole flight. Three flights and one
regenerate later, two hypotheses are dead and the cause is still unmeasured. This note
records what is known so the next session does not guess a fourth time, and carries the
runbook for the `profiler` plugin that measures it.

Read this before touching any of: TIC's stuck-unit retry, `sortie_recorder.lua`'s
sample cadence, §94's re-assert sweep, or the 15 s `state.json` write. Each was accused
here and each has a checkable reason it is not the answer.

## The flights

All from one `dcs.log` (UTC), DCS 2.9.29.27468, i7-14700K, 128 GB, 4K + DLSS.

| Run | Window | Length | TIC | ANTIFREEZE | Path warnings | Notes |
|---|---|---|---|---|---|---|
| 1 | 14:05:12–14:11:39 | 6.5 min | on | 10 | 0 | all 10 in the first 4:45; the last 1:43 clean |
| 2 | 14:20:07–14:29:28 | 9.3 min | on | 25 | 10 | never settled; one TIC unit wedged (11 retries) |
| 3 | 14:33:15–14:34:28 | 73 s | **off** | 11 | 1 | 5 freezes after spawn-in, no log line before any of them |

`ModelTimeQuantizer: ANTIFREEZE ENABLED` is DCS clamping model time because the sim
thread fell behind. Run 2's 25 in 9.3 min is one per ~22 s, which is the DM's "every
15–30 s" — so ANTIFREEZE timestamps are the freeze timestamps for this investigation.

The mission: 870 units / 387 groups — 285 planes, 52 helicopters, 457 vehicles, 16 ships,
61 statics; 102 late-activated groups; 58 vehicle groups with a multi-point route (37
upstream convoys, the FLOT groups). Scripts loaded: MOOSE, MIST, CTLD, Skynet (both
sides), Splash Damage, AIRBOSS ×2, RESCUEHELO ×2, Ops.CSAR ×2, and 14 RetLab plugin
scripts. Exports: Tacview, WinWing, SRS, an OH-6 gunner export.

## Falsified

**TIC's stuck-unit retry (the first accusation).** Real, and it did cost run 2: one unit,
`TIC:unit|81|33|BMP-2|-18#001`, retried 11 times, and every `CREATING PATH MAKES TOO
LONG!!!!!` in run 2 had a freeze within 3–5 s. But run 3 froze with TIC off, and a path
warning fired there too — the pathfinder serves upstream's convoys and FLOT groups as
well. TIC was a contributor in run 2, not the cause. The retry ceiling the TIC note
pre-registered is still owed; it is not this fix.

**The 15 s `state.json` write / the 30 s sortie sample.** Three reasons:
- the track is emitted only on the final write by design (`sortie_recorder.lua`
  header); the periodic payload is the light one;
- `state.json` was 74 KB after run 3;
- the freeze times are not phase-locked to any timer. Run 2's freezes, seconds since
  script start, mod 15: 0.4, 0.9, 2.2, 3.5, 4.3, 5.1, 5.2, 7.0, 7.1, 7.4, 9.7, 9.8, 10.1,
  11.3, 11.6, 12.0, 12.3, 12.5 — uniform. A write on a 15 s timer stacks at one phase.
  Uniform mod 30 and mod 10 as well, which also clears §94's 10 s sweep, the 30 s
  intercept and redscramble sweeps, and the 60 s §94 re-assert.

**`collectgarbage()`.** MOOSE calls it twice, both inside the MISSION/TASK tasking
framework, which nothing in a Retribution mission instantiates.

**Cloud sync.** Desktop and Documents are plain `%USERPROFILE%` paths; OneDrive's
known-folder move is not engaged. Tacview records to Documents, `state.json` sits on
Desktop; neither is synced.

## Confirmed, but partial

Two stock-DCS stalls are pinned by timestamp:

- **Ground pathfinding.** `WARNING TRANSPORT: CREATING PATH MAKES TOO LONG!!!!!` is the
  pathfinder giving up a search on the sim thread. Ten in run 2, one in run 3 with TIC
  off. Each is followed by a freeze.
- **Radio storage.** `WRADIO: Radio storage is filled with more than 300 radio pairs`
  then `Radio storage size reduced` at 14:09:01.496 — a freeze at 14:09:01.084. Once per
  run so far. Driven by the number of radios, which is the number of aircraft.

Together they explain roughly a third of run 2's freezes. The rest have no log line
within 3 s before them.

## What is not settled

Whether the remaining stalls are our Lua or DCS choking on the size. The mission size
is ours either way — the planner built a 337-aircraft ATO — but the fix differs: a Lua
sink is a code change, a native sink is a smaller turn. DCS logs no frame time and every
script that works is silent, so the log cannot separate them. The profiler can.

Two things every future test flight needs:

1. **Fly at least five minutes.** Every run hitches through spawn-in; run 1 settled to
   ~1/min after 14:09:56. Run 3's 73 s sat entirely inside the window that hitches
   anyway, which is why it could neither clear nor convict TIC.
2. **Read the freeze count off ANTIFREEZE per minute**, or off the profiler's stall log
   below, not off feel.

## The `profiler` plugin

`resources/plugins/profiler/` — default off, shown in Plugin Options as *Lua profiler
(diagnostic)*. One script, `profiler-config.lua`, two instruments:

- **MOOSE PROFILER.** `debug.sethook` on every Lua call for a window (default: start at
  t+60 s, run 300 s). Needs `os`, `io`, `lfs`, which Retribution's `MissionScripting.lua`
  leaves open. Writes `Saved Games\DCS\Logs\MooseProfiler.txt` and `.csv` when the
  window ends (or at mission end), plus a summary to `dcs.log`. The mission runs
  noticeably slower inside the window — this is a measurement flight, not a mission.
- **Stall log.** A probe scheduled every 0.25 s of model time compares the wall-clock
  gap between consecutive ticks against the model-time gap. Anything over the threshold
  (default 250 ms) is one `PROFILER| stall NNNN ms at t=… heap=… KB` line in `dcs.log`;
  a heartbeat every 30 s carries the running count and the worst gap. Runs the whole
  mission; costs nothing measurable. Independent of the profiler window, so it gives a
  clean baseline before t+60 and after the window closes.

### Runbook

1. Settings → Plugin Options → tick *Lua profiler*. Leave the three numbers alone unless
   the mission is short.
2. Regenerate the turn (a plugin toggle only reaches the next generated `.miz`).
3. Fly ≥ 6 minutes past spawn-in. Do not pause: a pause is a stall to the probe. Note
   the mission time of any freeze you feel.
4. Collect `Saved Games\DCS\Logs\MooseProfiler.txt` and `dcs.log`. The `.txt` is written
   at the end of the window; if it is missing, `grep "Profiler" dcs.log` says why.
5. Untick the plugin.

### Reading it

`MooseProfiler.txt` opens with `Runtime Game`, `Runtime Real` and `Function time … (N %
of runtime game)`, then three tables sorted by total time, time per call, and calls.

- **Function time is a large share** (tens of percent) and one family of functions
  dominates the total-time table → that script is the sink. The source column names the
  file: `skynet-iads-compiled.lua`, `Moose.lua` (read the function name for the class),
  `TIC_v1.1.lua`, or one of ours.
- **Function time is small** but the stall log is full → the stalls are native. Match
  each `stall` line's `t=` against `dcs.log` for a path warning or a radio-storage line
  in the preceding seconds; what is left is unlogged native work (model loads, AI task
  replanning) and the lever is the size of the turn.
- **`heap=` climbing across heartbeats** without coming back down → a Lua leak; a sawtooth
  whose drops line up with stall lines → garbage-collection pauses on a big heap, and
  the lever is allocation, not any one function.
- **Stalls only before t+60 and after the window** → the profiler's own overhead hid
  them; rerun with a longer delay.

A profiled flight is slower than an unprofiled one; compare *shares* between functions,
never absolute seconds against a normal flight.

## Found on the way

- `ai_reaction.lua` was a `scriptsWorkOrders` file reading
  `dcsRetribution.plugins.ai_reaction.DEBUG` at file scope, before its configuration
  trigger existed, so DEBUG was always false. Moved to `configurationWorkOrders` in the
  same change; `tests/test_plugin_script_pass.py` fails any early-pass script that reads
  its own config table at file scope.
- Not fixed: `escort_leash_update` (`dcs_retribution.lua`) re-issues `setOption(ROE)` on every
  escort every 10 s whether or not the state changed; ~40 of the `group change option`
  events per 10 s in run 3's debrief are that. Cheap, but it is churn the §94 header
  explicitly says to avoid.
