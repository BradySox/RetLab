# Removing MIST

**Date:** 2026-11-12 (DM call)
**Status:** step 1 of 4 in progress.
**Checklist:** B326 (step 1).

## 1. The decision

The DM chose to drop `mist_4_5_126.lua` from every mission, so the mission runs one
scripting framework (MOOSE) instead of two. Picks, all his:

- Full removal.
- **Skynet stays** and gets a small compatibility file with only the MIST functions it
  calls. Going back to MANTIS was compared and rejected (the 2026-09-12 reasons stand:
  `retlab-skynet-return-notes.md`).
- **CTLD moves to MOOSE's `Ops.CTLD`**, keeping all five jobs: helicopter Air Assault and
  Airlift, fixed-wing paradrops, logistics units and zone smoke, sling loading, and the JTAC
  lasing. The JTAC lasing moves to MOOSE `AUTOLASE`.
- Order: our own scripts, then Skynet's compatibility file, then CTLD, then MIST stops
  loading.

## 2. What to expect from it

Test 37's profiler (`retlab-sim-thread-freeze-notes.md`) had MIST at 3.1 s of 37.4 s of Lua
time in a 300 s window; MOOSE was 16.6 s. Lua was not the stutter sink. MIST's real costs
are `mist.main`, which reschedules itself every 0.01 s, and its own copy of every group in
`mist.DBs`, which adds to the heap floor the collector sweeps. Expect a smaller heap, not a
cure for stutters.

## 3. Who called MIST (audit, 2026-11-12)

No campaign `.miz` calls `mist.` (85 checked).

| Caller | Calls | Replaced by | Step |
|---|---|---|---|
| `base/dcs_retribution.lua` | Logger, message.add, scheduleFunction, getHeading, addEventHandler, DBs.groupsById | env logger, `trigger.action.outText`, `timer.scheduleFunction` + pcall, inline true heading, `world.addEventHandler`, a group-id map from `env.mission` | 1 |
| `base/sortie_recorder.lua` | scheduleFunction | `timer.scheduleFunction` | 1 |
| `base/water_relocate.lua`, `base/land_relocate.lua` | getGroupData, dynAdd | MOOSE `GROUP:GetTemplate()`, `_DATABASE:Spawn()` | 1 |
| `intercept/intercept-config.lua` | scheduleFunction | a local pcall'd `schedule_once` | 1 |
| `coin/coin-config.lua` | goRoute, ground.buildWP, getRandPointInCircle, utils.kmphToMps | a local off-road waypoint, `Controller:setTask`, a local random point | 1 |
| `skynetiads/skynet-iads-compiled.lua` | 48 calls, ~17 functions | compatibility file | 2 |
| `ctld/CTLD.lua`, `ctld/ctld-config.lua` | 85 calls | `Ops.CTLD` + `AUTOLASE` | 3 |

`base/dcs_retribution.lua` and `sortie_recorder.lua` load before `Moose.lua`, so they use
the plain DCS API. The relocation scripts load after it.

## 4. History

The same removal ran 2026-06-25 to 2026-09-12 through `mist_moose_shim.lua` (44 symbols,
plain DCS calls, flown on GermanyCW) and was dropped with the Skynet return. Recover it with
`git show ae35a13e7^:resources/plugins/base/mist_moose_shim.lua`; its note is
`git show ae35a13e7^:docs/dev/design/414th-mist-moose-shim-notes.md`. Its first go-live
crashed on `dynAdd` taking a string category from one caller and a number from another:
check every caller's argument shapes against a replacement before merging. The shelved
`Ops.CTLD` scope (template groups the mission must carry) is
`git show 0dcaf73e2^:docs/dev/design/retlab-ctld-mantis-style-port-scope.md`.

## 5. Rules while MIST is half gone

- Upstream Lua merged during this work: grep it for `mist.` and route each call to the
  replacement for its step.
- Do not add a new `mist.` call anywhere.
