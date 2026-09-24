# Observer-gated frontline artillery — scoping note (2026-09-23)

Status: **scoping only, nothing built.** Concept from FinCenturion's fire-support work (his
Discord post 2026-09-18; see §11 of
[retlab-fincenturion-dist-notes.md](retlab-fincenturion-dist-notes.md)). His code is not
read or copied; licence unasked.

## 1. The idea

A frontline artillery battery fires when a friendly unit in front of it sees an enemy, at
that enemy. Real units, real shells, visible from the air.

## 2. What frontline artillery does today

`_plan_artillery_action` (`game/missiongenerator/flotgenerator.py:556`):

- One `FireAtPoint(target, size × 10, 100)`, pushed by a `TimeAfter` trigger at a random
  1–45 min.
- The target is the **spawn point** of a random enemy group within range, chosen at
  generation (`:1160`). By the time it fires, the enemy may have moved.
- Retreats when any unit is damaged (`:600`). Only with `perf_artillery` on (`:981`).
- Placement (`:1182`): `threat_range − 7.5 km` if over 18 km gives 16–18 km back;
  under that, the **tank band, 2.2–3.2 km** — short-range tubes sit at the front.
- TIC does not manage it: `_tic_managed_role` is TANK/IFV/APC/ATGM only (`:407`).

So it fires once, blind, at a stale point.

**The group names already reach Lua**, unused: `luagenerator.py:359` emits
`dcsRetribution.artilleryGroups.groundArtillery[].groupName`. That list also carries
theater-object artillery and has no coalition field, so it needs filtering to frontline
groups.

## 3. Mechanism

Per battery, every ~25 s:

1. Observers: TIC combatants on the same side — `GLSCO.battle.formations[]:GetCombatants()`,
   walked the way `tic_retlab_init.lua:31` does.
2. Targets: TIC already computes each unit's 10 nearest visible enemies in
   `GLSCO_TRACKER:broadcast` (`TIC_v1.1.lua:4173`, `IsLOS` at `:4253`). **Reuse that result;
   do not run a second observers × enemies sight loop.**
3. Pick the target cluster with the most units inside the battery's range.
4. `TaskFireAtPoint` + `PushTask` on the real group, cooldown per battery.

Pairing is **automatic** — any battery supports whichever observer sees something in its
range. FinCenturion's FSCM dialog (hand-assigned batteries, priorities, time windows) is
platoon-level command: admission rule 3, not taken.

## 4. Rules it must keep

- **Real units only** — compliant: `TaskFireAtPoint` on a real group, no
  `trigger.action.explosion`.
- **Never on an airfield.** Real shells are not scripted explosions, but whether they put a
  field into DCS's under-attack hold is **unverified**. Exclude aimpoints inside any field's
  area anyway. The §36 player-field walk survives at `coinluadata.py:273`
  (`_client_spawn_control_points`) and is tested.
- **Not on a 5 s multiple.** The sim-thread freeze note found stalls phase-locked to a 5 s
  cycle; 25 s is one. Use a jittered ~23–29 s. Keep per-tick allocation low.
- **A plugin toggle is a second gate** — any campaign that wants it preseeds both.

## 5. Where it hooks in

- A third TIC late-init file, or a block after the pcall init in `tic_retlab_init.lua:119`,
  gated by a new `plugin.json` option like `ambientFireEnabled()`. It then only runs with
  TIC on, which is where the observers are.
- `game/plugins/tests/test_late_init.py:70` pins TIC's file list; update it if a file is added.
- The generator's timed `FireAtPoint` stays as the TIC-off path, or is dropped for TIC groups.
  **Decide which before building** — two fire sources on one battery is the thing to avoid.

## 6. Test coverage

- TIC itself is not in the Lua harness (`tests/lua/`): the stubs lack MOOSE `SCHEDULER`,
  `TIMER`, `COORDINATE:IsLOS`. The harness does record `TaskFireAtPoint`/`PushTask` into
  `records("firedTasks")` (used by `test_cruisemissiles_runtime.py`).
- Cheapest test path: write the module against raw DCS + MOOSE `GROUP`, feed it a faked
  observer→target table, assert the fired task, the cooldown, and the airfield exclusion.

## 7. In-game pass (a checklist row when built)

- Pass: a battery fires within ~1 min of a friendly unit engaging, at that engagement;
  none in any airfield's area; the profiler plugin shows the tick under a few ms.
- Fail: tubes silent with contact on; shells on a field; a new stall cadence at the tick.

## 8. Found while scoping

The Vietnam Ops naval gunfire comment (`vietnamops-config.lua:401`) and features doc §34
said NGFS uses "the TIC artillery path". There is no such path: TIC's `TaskFireAtPoint` is
direct-fire tracer shooting by combatants (`TIC_v1.1.lua:1957`). Both corrected 2026-09-23.
