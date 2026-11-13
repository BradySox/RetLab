# Removing MIST

**Date:** 2026-11-12 (DM call)
**Status:** done 2026-11-12; MIST no longer loads. Every step awaits its in-game pass.
**Checklist:** B326 (step 1), B328 (step 3a), B329 (step 3b), B330 (step 4).

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
| `skynetiads/skynet-iads-compiled.lua` | 48 calls, 18 functions | `skynetiads/skynet-mist-compat.lua` | 2 |
| `ctld/ctld-config.lua` JTAC lasing (`ctld.JTACAutoLase`) | via CTLD | MOOSE `AUTOLASE`, one per coalition | 3a |
| `ctld/CTLD.lua`, `ctld/ctld-config.lua` cargo | 85 calls | `Ops.CTLD` + our own AI loader | 3b |

`base/dcs_retribution.lua` and `sortie_recorder.lua` load before `Moose.lua`, so they use
the plain DCS API. The relocation scripts load after it.

## 4. Skynet's compatibility file

`skynetiads/skynet-mist-compat.lua` loads just before the compiled Skynet and defines a
`mist` table with only the 18 functions Skynet calls. It does nothing while the real MIST is
loaded, so it takes over in step 4. Scheduled functions are DCS timers; the name tables are
built once from `env.mission` and hold names only. `groupToRandomZone` and
`getRandPointInCircle` keep MIST's route shape and inner radius, because shoot-and-scoot was
tuned against them. `tests/lua/test_skynet_mist_compat.py` fails when a Skynet update calls
a `mist.` function the file lacks.

## 5. JTAC lasing (step 3a)

`ctld-config.lua` builds one `AUTOLASE` per coalition over a `SET_GROUP` of the emitted JTAC
group names. Kept from CTLD's JTAC: 10 km reach (`SetLasingParameters(10000, 1800)`),
vehicles only (`Infantry` blacklisted), no cooldown gap between lasings, the emitted code per
JTAC unit (1113 with the FC3 option), smoke with the smoke option. Reports are text only
(DM pick, no SRS). CTLD's F10 JTAC menu is replaced by AUTOLASE's own status menu. A 24-man
stick's JTAC joins the same AUTOLASE from step 3b (below).

## 6. CTLD cargo on Ops.CTLD (step 3b)

`ctld/CTLD.lua` and `CTLD-i18n.lua` are deleted; `ctld-config.lua` builds one `Ops.CTLD`
per side that has logistics flights. DM picks, 2026-11-12:

| Behavior | Kept as |
|---|---|
| AI Air Assault / Airlift | our own loop: helicopters load landed in their pickup zone, unload landed in their drop zone; fixed-wing jumps over its target zone. Not MOOSE's AI cargo dispatcher, which would override Retribution's routes |
| Paradrop | our own, with the 6.5 m/s descent (max 90 s); players inside MOOSE's window (540-3000 ft AGL, under 150 kt), AI at any height |
| Zone smoke | kept burning: a 300 s refresh, blue at pickup, green at drop-off |
| Logistics trucks | scenery; crates come from anywhere in the 300 m pickup zone |
| "Use only Retribution's crates and troops" off | a small stock list: four squads and four crates per side, from the old CTLD catalog (`ctldtemplates.py`) |

**Templates.** Ops.CTLD clones late-activated groups. `game/missiongenerator/ctldtemplates.py`
writes, per side with logistics: one squad per size 2/4/6/10/12/24 and per transport cabin
size (the old CTLD infantry mix; the 24 carries a JTAC), one crate vehicle per airlift
cargo type, and the stock list when the option is off. All hidden, never activated. A
cargo type not in pydcs's `vehicle_map` gets no template and is logged.

**Unchanged on purpose:** sling-load setting maps to `enableslingload`; carriers are SHIP
load zones; the CH-47 "reads airborne on the ground" fix is not needed (Ops.CTLD judges
airborne by AGL). The F10 menu is MOOSE's (CTLD > Manage Troops > Drop Troops).

## 7. History

The same removal ran 2026-06-25 to 2026-09-12 through `mist_moose_shim.lua` (44 symbols,
plain DCS calls, flown on GermanyCW) and was dropped with the Skynet return. Recover it with
`git show ae35a13e7^:resources/plugins/base/mist_moose_shim.lua`; its note is
`git show ae35a13e7^:docs/dev/design/414th-mist-moose-shim-notes.md`. Its first go-live
crashed on `dynAdd` taking a string category from one caller and a number from another:
check every caller's argument shapes against a replacement before merging. The shelved
`Ops.CTLD` scope (template groups the mission must carry) is
`git show 0dcaf73e2^:docs/dev/design/retlab-ctld-mantis-style-port-scope.md`.

## 8. Step 4: MIST stops loading

`base/plugin.json` drops the `mist` work order and `mist_4_5_126.lua` is deleted. Skynet's
compatibility file now defines `mist`. The stale-docs audit flags a published page that
still says MIST loads.

**Measuring the gain (B330).** Compare against test 37's numbers in
`retlab-sim-thread-freeze-notes.md`: the heap floor (~430 MB) and the collector's period
(~150 s). Expect the floor to drop; a stutter that remains is not MIST's.

## 9. Rules from here

- Upstream Lua merged from now on: grep it for `mist.`; port each call to MOOSE or the
  DCS API before it lands. Never restore MIST for one caller.
- A Skynet update: run `tests/lua/test_skynet_mist_compat.py`; it fails on a `mist.`
  function the compatibility file lacks.
- Do not add a new `mist.` call anywhere.
