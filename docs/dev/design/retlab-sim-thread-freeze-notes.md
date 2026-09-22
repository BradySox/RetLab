# Sim-thread freezes on a big turn — evidence ledger and the profiler runbook

Opened 2026-09-20. Long Road to H3 (Syria; turn 3 on 09-20, turn 1 of a new game for test 37),
an 870-unit turn, the DM in an F-16C at Incirlik: a ~1 s lock-up every 15–30 s for the whole flight. Three flights and one
regenerate later, two hypotheses are dead and the cause is still unmeasured. This note
records what is known so the next session does not guess a fourth time, and carries the
runbook for the `profiler` plugin that measures it.

Read this before touching any of: TIC's stuck-unit retry, `sortie_recorder.lua`'s
sample cadence, §94's re-assert sweep, or the 15 s `state.json` write. Each was accused
here and each has a checkable reason it is not the answer.

**Second look, 2026-09-22.** Four findings in the first write-up did not survive a re-check:
the campaign was misnamed (it was Long Road to H3, not Anatolian Reach); the 09-20 phase test
was run on wall-clock times, which smear whenever the sim runs behind, so it could not clear
anything — test 37's model-time stall log redoes it properly below; the stall log itself was
blind to freezes DCS catches up from (fixed); and the test-37 "the stutter is the battle"
reading does not hold — the slow phase tracks the human being in the jet. Each is corrected in
place.

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
`TIC:unit|81|33|BMP-2|-18#001`, retried 11 times, and about half of the ten `CREATING PATH
MAKES TOO LONG!!!!!` lines in run 2 had an `ANTIFREEZE` within 3–5 s (the rest had none
within 30 s). But run 3 froze with TIC off, and a path
warning fired there too — the pathfinder serves upstream's convoys and FLOT groups as
well. TIC was a contributor in run 2, not the cause. The retry ceiling the TIC note
pre-registered is still owed; it is not this fix.

**The 15 s `state.json` write / the 30 s sortie sample.** Three reasons:
- the track is emitted only on the final write by design (`sortie_recorder.lua`
  header); the periodic payload is the light one;
- the stalls are not phase-locked to 15, 30 or 60 s. **This is from test 37, in model
  time** (Rayleigh test on the 41 sub-2 s stall times: 15 s p=0.77, 30 s p=0.28, 60 s
  p=0.47). The 09-20 version of this test used wall-clock log times; the scheduler runs on
  model time, and the two drift apart whenever the sim runs behind, so that test proved
  nothing and is withdrawn. The same result clears §94's 60 s re-assert and the 30 s
  intercept and redscramble sweeps.

The DM's instinct about size was not wrong, though: by the end of test 37 the periodic
payload (no tracks) was **203 KB**, not the 74 KB a 73-second run showed. Half of it is
`kill_events` and `unit_lost_events` — 3,905 and 4,068 entries, almost all numeric map-object
ids (trees and buildings the mission destroyed), written by upstream's base script. It is
re-encoded every write and grows all mission. It is not the freeze (no 15 s lock), but it is
real work that grows without bound on a long mission.

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

`resources/plugins/profiler/` — default off, listed on the Lua Plugins page as *Lua profiler
(diagnostic)*. One script, `profiler-config.lua`, two instruments:

- **MOOSE PROFILER.** `debug.sethook` on every Lua call for a window (default: start at
  t+60 s, run 300 s). Needs `os`, `io`, `lfs`, which Retribution's `MissionScripting.lua`
  leaves open. Writes `Saved Games\DCS\Logs\MooseProfiler.txt` and `.csv` when the
  window ends (or at mission end), plus a summary to `dcs.log`. The mission runs
  noticeably slower inside the window — this is a measurement flight, not a mission.
- **Stall log.** A probe scheduled every 0.25 s of model time measures the wall-clock gap
  between consecutive runs. Anything over the tick plus the threshold (default 250 ms) is one
  `PROFILER| stall NNNN ms at t=…  model +X.XX s  heap=… KB` line in `dcs.log`. `model +` near
  the stall length means DCS caught model time up (a hitch); near 0.25 means it lagged. The
  first version (test 37) measured only the lag, so a freeze DCS caught up from was invisible —
  its stall counts are a lower bound;
  a heartbeat every 30 s carries the running count and the worst gap. Runs the whole
  mission; costs nothing measurable. Independent of the profiler window, so it gives a
  clean baseline before t+60 and after the window closes.

### Runbook

1. Settings → Lua Plugins → tick *Lua profiler*. Leave the three numbers alone unless
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
- **Stall times clustering at one phase of a period** → a scheduled job. Test the model-time
  `t=` values (Rayleigh, and a shuffle on the 0.25 s probe grid), never the log's wall clock.
- **Heartbeat spacing** (wall seconds between `alive` lines, 30 s of model time apart) is the
  sim rate. Above 30 s the sim is behind; below 30 s is time acceleration.
- **Stalls only before t+60 and after the window** → the profiler's own overhead hid
  them; rerun with a longer delay.

A profiled flight is slower than an unprofiled one; compare *shares* between functions,
never absolute seconds against a normal flight.

## Test 37 — the first profiled flight (2026-09-21)

Long Road to H3 turn 1 of a new game with the plugin on (build `5a11efa13`, TIC off), 65 min
in an F-16C,
`Tacview-20260921-194148`. Profiler window t+60 s for 300 s; stall log the whole flight.
Output files kept beside the flight in `Desktop\New test\37`.

**Lua function time, quiet phase:** 37.4 s of 300 s = 12.5 %, hook-inflated. Per source:
MOOSE 16.6 s, unattributed builtins 11.7 s, MIST 3.1 s, Skynet 2.2 s, json 1.5 s,
sortie_recorder 0.75 s, Splash Damage 0.58 s, neutralborder 0.46 s, everything else of
ours under 0.25 s. No function above 33 ms/call; the slowest repeating one is Ops.CSAR's
`_AddMedevacMenuItem`, 33 ms every 10 s. **Lua is not the sink in the quiet phase.**

**Heap:** a sawtooth from ~430 MB to ~950 MB every ~150 s for the whole flight — the
collector fires when the heap doubles (Lua's default pause of 200). Churn ~3.3 MB/s. The
profiler does not measure allocation, so what allocates it is **unknown** (the first write-up
named MOOSE `DeepCopy` from call counts alone; that was an inference, withdrawn). 17 of the 41
sub-2 s stalls show a visible collection drop against the previous reading (a lower bound —
the readings are 0.25–30 s apart). The 430 MB floor is live data; MOOSE and MIST each hold a
copy of the mission's group tables, the likely bulk.

**Stall timing, in model time:** phase-locked to a **5 s cycle** (Rayleigh p=0.0016; a
shuffle on the probe's 0.25 s grid gives p=0.0018) and to the whole second, clustering at
t ≡ 0–1.25 (mod 5). Not locked to 15, 30 or 60 s. Jobs on a 5 s cycle in this mission:
Skynet's contact evaluation (first run t=1, every 5 s), CTLD's transport, smoke and beacon
refreshes, and Ops.CSAR's poll. None costs more than a few ms per call in the profiled
window, so the likeliest reading is the collector's atomic step finishing inside one of those
allocation bursts. Not proven; the next profiled flight should cover the stalls directly.

**Sim rate, from the heartbeats (wall seconds per 30 s of model time):** 30.0 from t=60 to
t=930 (the human airborne from t=779); 33–37 from t=960; **45–54 from t=1230 to t=1770 and
39–45 to t=2610**; back to 30.0 on the first heartbeat after the DM left the jet for spectator
(00:40:16 UTC, t≈2601), and 30.0 for the next 11 minutes; 24–26 later, which is time
acceleration. 755 `ANTIFREEZE` over the flight, 25–40 per minute inside the slow stretch.

**The slow stretch tracks the human in the jet, not the battle.** The first write-up said
"the stutter is the battle". Test that: shots and kills per minute were 4, 4, 3 in the three
minutes before the DM left (sim at 0.75×) and 4, 2, 9, 3, 4, 2, 2 in the seven after (sim at
1.0×). Same fighting, different sim rate; what changed is that a human cockpit was no longer
being simulated or rendered. Candidates: the F-16C's own sensors and datalink working through
~300 aircraft, or the 3-D scene around the camera. The two separate on one flight: when the sim
is slow, switch to the F10 map for a minute (sensors keep running, the 3-D scene does not),
then back, and read the heartbeats. The profiler window had closed 11 minutes before the slow
stretch began, so Lua's share in it is unmeasured.

**Not stalls:** the 8–155 s gaps at 00:03, 00:06, 00:14, 00:15, 00:20 and 00:48 UTC carry
DCS's `SAME MODEL TIME` — pauses or menus. Radio storage filled/trimmed three times, one
stall each. No `CREATING PATH MAKES TOO LONG` this flight (TIC off).

**What this settles:** Lua function time is small in the quiet phase; the sub-second
stalls are on a 5 s cycle, and many coincide with a collection. **What it does not settle:**
whether the DM's 1 s freezes were in this flight at all — the first stall log could not see a
freeze DCS caught up from — and what the in-cockpit slowdown is. Next flight: the fixed stall
log, profiler delay ~900 s and duration 600 s so it covers the slow stretch, and one F10-map
minute during it.

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
