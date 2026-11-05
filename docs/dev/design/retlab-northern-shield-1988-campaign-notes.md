# Germany — Northern Shield 1988

**Status: BUILT 2026-11-05; headless-verified (a fresh turn 0 plans 10 blue and 9 red
packages and generates a mission). In-game pass is checklist row B310. New game required.**

Owner: this note. CI lock: `tests/retlab/test_northern_shield_1988.py`.

| | |
|---|---|
| Files | `resources/campaigns/northern_shield_1988.yaml` + `.miz` |
| `.miz` | **The DM's Mission Editor save (2026-11-05)** with the template SAM sites swapped in. First built from `red_tide.miz` by `tools/build_northern_shield_miz.py`, deleted; it is in the first two commits of PR #1447. Edit the `.miz` in the Mission Editor from now on |
| Routes | 4 M-113 roads and 1 Train rail line from real town and station lat/lon; 4 HandyWind sea lanes |
| Factions | Red Tide's: `Blufor Late Cold War (80s)`, `Russia 1980 (Red Tide)` (stock DCS) |
| Squadrons | 26 squadrons, existing presets only: 89 blue and 79 red aircraft |
| Checklist row | B310 |

## Why it exists

The DM asked for a campaign on the northernmost fields of the Germany Cold War map, which no
campaign used, shaped like Red Tide but with blue in the north pushing south.

## The DM's calls (2026-11-05)

- **1988, Red Tide's factions.** The same war: Hamburg fell, Copenhagen never did.
- **Blue in the north, separated by water.** No land front until the first red base is
  taken.
- **Long legs, few bases.** Smaller is better, like Fulda Gap 1985: 3 blue, 4 red.
- **Heavy air defense, the SA-5 in the rear, not on the coast.**
- **The SAMs are Carsten's Cold War Germany Framework sites**, as many as the sector holds
  ("AS MUCH AS we can from that sam template"). The template has no SA-10, so the campaign
  has none: "only 5s". The Berlin ring north and the Polish coast sites come in; the
  Rostock and Wismar group does not, and neither does the coastal SA-5 at Rostock.
- **Neubrandenburg's ammo depot moved 400 m south**, off the runway line past the west
  threshold (DM call); New Game flagged it on the runway strip.
- **The SA-5 moved south** from Badingen to the template's Magdeburg site (DM call,
  2026-11-05).
- **F-4s added**: JG 74 (BARCAP) and the 480th TFS (SEAD) at Kastrup (DM call, 2026-11-05).
- **His laydown stands** for everything but the SAMs: he moved the bases' defenses, depots
  and IADS nodes in the Mission Editor before the SAM call.

## The laydown

| Side | Base | Squadrons |
|---|---|---|
| NATO | Kastrup (Copenhagen) | F-15C 525th TFS, F-4E JG 74 and 480th TFS, F-16 23rd FS, F-15E 414th TFS, A-10C 81st TFS, Tornado JBG 31, AH-64D, E-3A, KC-135, C-130J |
| NATO | Sturup (Sweden) | AJS-37 Viggen 71. Attackflygdivisionen, F/A-18C VMFA-251 |
| NATO | Bornholm | CH-47F and UH-1H, Air Assault |
| Pact | Barth | Mi-24P |
| Pact | Peenemunde | MiG-23MLD, MiG-21bis JG-1 (GDR), Su-24M naval, An-26 |
| Pact | Neubrandenburg | MiG-29A, Su-25, Mi-8, A-50 |
| Pact | Templin | Su-27, Su-24M |

Red has no tanker and no Backfires: no red field but Neubrandenburg has a stand for a heavy,
and it has one, which the A-50 takes.

Red base legs: Barth to Neubrandenburg 50 NM, Neubrandenburg to Templin 35 NM, Peenemunde to
Neubrandenburg 37 NM. Copenhagen to Templin is 158 NM, so `max_mission_range_planes` is 200.

## How the first base falls

A control point is captured when the attacker has ground units within 3 km of it and the
defender has none (`capture_zone_taken`, `dcs_retribution.lua`). With no road between the
water and the coast, only an Air Assault (or a C-130J paradrop) can put blue troops there.

- **Barth is the door.** Its garrison armor stands inside the capture zone, so it has to
  be destroyed before troops can take it.
- **The NATO fields hold their own.** Kastrup, Sturup and Bornholm each keep an armor
  garrison inside the zone. Without it the red HTN planned a Mi-8 air assault on an empty
  blue field on turn 0 (one fresh game in two).
- Anything else the DM puts inside a zone also has to die before a capture: Sturup's Hawk
  and two of Neubrandenburg's guns stand inside theirs in his laydown.
- **The blue AI waits for the air defense.** `PlanAirAssault` needs the target area clear of
  IADS threats, so the planner flies DEAD first.
- **Supply after the capture** comes by sea: lanes Kastrup to Barth and Bornholm to
  Peenemunde. Kastrup has the blue factory, so ground units bought for a captured coastal
  field ship from there.
- **No land front on turn 0.** Every blue control point has no road, and the HTN planner
  lists them as isolated.

## Air defense

The fixed sites are FIXED groups (features doc §122) copied unit by unit from Carsten's
framework. The mobile ones are generated and pinned in the yaml's `ground_forces`.

| Belt | Sites |
|---|---|
| Coast | SA-3 Dranske, SA-3 Barhoft, SA-2 Franzburg (Barth); SA-2 Ueckermunde, SA-3 Swinoujscie, generated SA-6 (Peenemunde) |
| Middle | SA-2 Neubrandenburg, generated SA-11; S-60 Prenzlau |
| Rear | SA-3 Templin, SA-3 Velten, SA-3 Fehrbellin, SA-2 Werneuchen, SA-2 Szczecin, SA-3 Chojna; EWR Furstenwalde (a generated 1L13 at the template's spot: its 55G6 is not a §122 air-defense site) |
| Deep rear | **SA-5 Magdeburg**, 89 NM south-west of Templin, which owns it. Its flanks are the template's SA-2s at Stendal, Mahlwinkel, Quedlinburg, Kothen and Dessau, SA-3 Zachow and S-60 Burg (DM call: so it cannot be killed cheaply) |
| NATO | Hawks at Kastrup, Roskilde, Rodvig and Rodvig South (template), a generated Hawk at Sturup (RBS 77); EWRs at Stevns and Almindingen |

The S-60 57mm joined `russia_1980_red_tide.json` for Prenzlau (DM call, 2026-11-05).
Without it §122 put a stock AAA site there. Red Tide's generated AAA and point defense
can roll S-60s too.

The Skynet net is range mode: HQs at Neubrandenburg (the GDR 3rd Air Defense Division) and
Eberswalde (20th Guards Army), 8 comms towers, 3 power sources including the Lubmin plant.

## Neighbours

`neutral_border_postures` pins Germany (the FRG) and Sweden blue, and the Pact states red.
Without the Germany pin, the Federal Republic holds no field here and reads as an uninvolved
neutral that hails and fires on blue.

## Rail

The Barth to Neubrandenburg line is the Nordbahn through Velgast, Stralsund, Grimmen and
Demmin. It has not been probed in DCS; Fulda Gap's probe 2 found two lines that ran away
from their next station. B310 covers it.

## Open

- The Red Tide scenery sets around Copenhagen (4 of 21) are blue-owned here and only red can
  strike them. Kastrup's comms set sits on the runway strip (an Airfield clearance warning);
  scenery spawns nothing, so it does not block taxi.
- No new squadron presets. Danish F-16s and Marineflieger Tornados would fit and are not in
  the tree.
