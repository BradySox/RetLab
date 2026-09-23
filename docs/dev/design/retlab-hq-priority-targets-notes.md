# HQ priority targets — design note (2026-09-23)

Status: **§103, BUILT 2026-09-23, not flown** (checklist B140). Built: §7 steps 1–2, with the
measure below replacing a single cross-kind score (§8). Not built: difficulty, the top-few list.
The objective half of juanjux's High Command
(`juanjux/dcs-escalation` `game/highcommand/`, his #421–#429), without the prizes. Read
alongside the High Command entry in
[retlab-juanjux-fork-watch-notes.md](retlab-juanjux-fork-watch-notes.md), which records the
DM's 2026-09-23 "watch, decide later" on the whole system.

## 1. The idea

Rate every enemy target the player can see on two axes, with a one-line reason:

- **Importance** — what losing it costs red.
- **Difficulty** — what reaching it costs blue.

Show the top few as "HQ priorities". Achieving one pays nothing: the reward is what already
happens when the site dies.

## 2. What his version does

Read from his `importance.py`, `approach.py`, `objectives.py`, 2026-09-23. **Reimplemented
from our APIs if built, never copied** (his licence has not been checked against LGPL-3).

**Importance** is a sum of reasons, each in $M with a line of text; the highest one's line
is the reason shown.

| Reason | His source |
|---|---|
| Rebuild cost | unit prices + building `repair_cost()`; fixed values for warships by class |
| Income | `REWARDS` × live statics × 4 turns |
| Front | front-line units lost with an ammo depot, `cp.deployable_front_line_units_with()` |
| Aircraft / runway | 0.5 × aircraft value + $25M per squadron; `RUNWAY_REPAIR_COST` + squadrons |
| Reserve / garrison | motorpool units; armour price, raised near its base and at a front |
| Threat | 0.25 × blue value inside its `max_threat_range()` |
| Cover / network | share of what its SAM ring covers; an `IadsStateMap` what-if of who goes dark |

**Difficulty** is effort points:

- Route: shortest path on a 5 NM grid from every blue base; each mile inside a ring costs
  `RING_WEIGHT` (long 4, medium 2.5, short 1); the weapon's own leg at 0.5; ÷ 60.
- Fighters: enemy fighters based within 150 NM, ÷ 12, capped at 2.
- Size: (units − 4) ÷ 12, capped at 1.

Both are binned into fifths of the table (1–5). His "comical" line for the least important
fifth is dropped here.

**Missing here:** `repair_cost()`, `IadsStateMap`/`IadsState`, `game.mfd.Band`,
`motorpool_rendered_units`, his `Campaign` class. The cover and network reasons are each a
port of their own.

## 3. Our numbers to reuse (admission rule 4: no invented costs)

| What losing it costs red | Where it already lives |
|---|---|
| Command post | `game/retlab/c2_decapitation.py` — `c2_health`, `offensive_package_cap` (§52) |
| Ammo depot | `ControlPoint.deployable_front_line_units_with` (`controlpoint.py:1319`) |
| Motorpool | `reserve_armor_for` (`ai_ground_planner.py:274`) (§56) |
| Supply | `supply_status`, `SupplyStatus` (`game/theater/supply.py`) (§90 rung A) |
| Runway, income | `RUNWAY_REPAIR_COST`, `REWARDS` (`game/config.py`) |
| Air defence | `air_defense_band` on the target, `max_threat_range()` |

## 4. Where it plugs in

Admission rule 1 needs two readers, or it is a private ledger. The two:

1. **The §4 Target Intel panel.** A "Why it matters" row in
   `QGroundObjectMenu.target_intel_rows()` (`qt_ui/windows/groundobject/QGroundObjectMenu.py:357`),
   hidden when `known_for(viewer)` is false like the other rows. The web client has no
   target-intel component; the nearest is the base tooltip.
2. **A planner weight.** The blue offensive sort key is range × §93 factor,
   `objectivefinder.py:102` and `:161`. Importance becomes a third factor there. It runs
   **before** §17's shuffle (`targetorder.py`), so the two compose.

Reporting: an achieved priority is a SITREP line (`game/sitrep.py`, pattern:
`red_c2_status`, `supply_lines`) and a pre-turn brief item (`pre_turn_briefing.py:128`).

## 5. Rules it must keep

- **Weight, never fence** (pillar 3.5). A factor on distance, like §93. Never a filter.
- **Blue only.** The sort keys are shared with red; gate the factor the way
  `region_priorities.py:142` does. Pillar 3.4: zero change to red's decisions.
- **Fog.** The player-facing list filters with `fogofwar.hidden_from(Player.BLUE, tgo)`.
  Naming a hidden site hands the player a find (§3).
- **No prize, no ticket, no currency.** The reason §53, awards and his prize loop are out.

## 6. Open questions

1. `objectivefinder.py` never calls `hidden_from`, so the blue auto-planner already ranks
   targets hidden on the player's map. CLAUDE.md says anything that picks targets for blue
   must gate on the fog, and lists raids, the carrier strike and fire missions. Whether the
   auto-planner belongs on that list is **unasked**. It decides whether the weight may see
   hidden sites.
2. Difficulty needs a route cost. His grid search is new code. Our threat zones
   (`ThreatZones`) may answer "miles inside a ring" more cheaply. Measure before porting.
3. Does the planner weight earn its place, or is the panel line enough? If only the panel
   reads it, rule 1 fails and the feature is a label.

## 7. Build order, if picked up

1. Importance from §3's numbers only (no cover/network), the panel row, tests.
2. The blue-only planner factor behind a setting, default off; a checklist row that reads
   the ATO before and after.
3. Difficulty and the top-few list, if 1–2 are kept.

## 8. As built (2026-09-23)

- **No cross-kind score.** Each target is measured in its own kind's unit (enemy income a turn,
  front-line vehicles, offensive packages, equipment price) and ranked only within its §93 family.
  Mixing kinds needs an exchange rate — his 4-turn income horizon is one — and rule 4 forbids
  inventing it. Within a strike list, a top factory and a top command post both rank closer.
- **Unmeasured is neutral.** Power, comms and bunkers have no measure yet; they are not ranked
  and not weighted, so a power plant is never pushed down for lacking a price.
- **Factors 0.75 / 1.25** for the top and bottom third, gentler than §93's 0.5 / 2.0.
- **Open question 1 answered by construction:** hidden sites are neither ranked nor weighted, so
  the weight never names one; the auto-planner's existing behaviour toward them is unchanged.
- The panel line shows whatever the setting, so the measure has a reader even with the planner
  weight off.
