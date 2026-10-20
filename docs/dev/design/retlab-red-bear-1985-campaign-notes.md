# Afghanistan — Red Bear 1985

**Status: BUILT 2026-10-19, headless-verified (a fresh turn 0 generates a mission). In-game
pass is checklist row B255. New game required.**

Owner: this note. CI lock: `tests/retlab/test_red_bear_1985.py`.

| | |
|---|---|
| Files | `resources/campaigns/red_bear_1985.yaml` + `.miz` |
| `.miz` | **Hand-authored: the DM's laydown.** Edit it in the Mission Editor; there is no build tool |
| Routes | M-113 groups traced from real town lat/lon, first and last waypoints Off Road |
| Factions | `USAF 1985` (stock), `USSR 40th Army 1985` (stock) |
| Squadrons | existing presets plus one generic MiG-23MLD squadron |
| Checklist row | B255 |

## Why it exists

The DM wanted a reason to fly the Heatblur F-4E on the Iraq or Afghanistan maps. Every
campaign on those maps is 1991 or later and none fields an F-4E. None goes across the top
of the Afghanistan map either.

## The DM's calls (2026-10-19)

- **Red Bear, out of four ideas**: a fictional Cold War gone hot, USAF against the Soviet
  40th Army. The other three were Iran against the Taliban (1998), the Iran–Iraq War and an
  Israeli Phantom campaign over Iraq.
- **Across the top of the map.** The south is out of play.
- **Stock DCS only.** The F-100D was in the first plan and came out: it left the Air
  National Guard in 1979.
- **The heavies stay on the map.** Herat and Shindand have no stand for them, so Camp Bastion
  is a blue rear base with no road to the war.
- **Winter 1985.** The start date is 15 January.

## The DM's laydown (2026-10-20)

The first `.miz` came from a build tool (`git show 08f987be3:tools/build_red_bear_1985_miz.py`)
that ringed every base with the same markers. The DM called it generic and redid the laydown
in the Mission Editor; that save is the `.miz` now and the tool is deleted. On top of it:

- **33 added SAM markers.** Within 6 NM of a base they stay medium-SAM markers (base rings,
  `RB85-<base>-SAM-Ring-N`); the 25 along the roads became SHORAD markers (`RB85-Road-SHORAD-NN`).
- **Three AAV7s near Kabul** became armor markers (`RB85-Kabul-Garrison-AAV-N`).
- **Scenery strike targets** copied with their scenery object ids from Starfire's
  `graveyard_of_empires.miz` (Herat and Shindand sites, the Salma Dam) and
  `clash_of_the_titans.miz` (Bagram, Gulbahar, Kapisa, Parwan, the Kabul ammo depot),
  parents renamed `RB85 Scenery N`. The Parwan police centre reads as a garrison. Their
  modern insurgent joke sites are left out.

**Flavor first.** A new campaign's laydown starts from what the shipped campaigns on the same
map already carry, not from generic marker rings.

## The laydown

| Side | Base | Squadrons |
|---|---|---|
| USAF | **Herat** | 526th TFS F-4E 12 (BARCAP), 141st TFS F-4E 8 (CAS), 159th Avn Det UH-1H 4 |
| USAF | **Shindand** | 480th TFS F-4E 12 (SEAD), 512th TFS F-4E 12 (Strike), 425th TFTS F-5E 8 |
| USAF | **Camp Bastion** (rear, no road) | 20th BS B-52H 4, 960th AACS E-3A 1, 18th ARS KC-135 2, 910th AW C-130J 2 |
| USSR | **Qala i Naw** | 368th ShAP Su-25 8 |
| USSR | **Maymana** | 115th GvIAP MiG-21bis 8 |
| USSR | **Chaghcharan** | none (three stands) |
| USSR | **Bamyan** | 336th OBVP Mi-24P 4 |
| USSR | **Bagram** | 33rd IAP MiG-23MLD 12, 20th GvAPIB Su-17M4 12, 357th ShAP Su-25 12, A-50 1, An-26B 2 |
| USSR | **Kabul** | MiG-23MLD 12, 19th GvAPIB MiG-27K 12, 337th OBVP Mi-24P 6 |
| USSR | **Jalalabad** | 234th GvIAP MiG-21bis 8, 239th and 486th OVP Mi-8 4 + 4 |
| USSR | **Termez** (off-map) | 11th GvBAP Su-24M 12, 226th SAP An-26B 2 |
| USSR | **Mazar-i-Sharif**, **Pul-i-Khumri** (FOBs) | none; garrisons, SAMs, depots |

**Roads** (one M-113 route group each, On Road): Shindand – Herat (Adraskan); Herat – Qala i
Naw (Karukh, Sabzak pass); Qala i Naw – Maymana (Bala Murghab, Ghormach, Qaisar, Almar);
Maymana – Mazar-i-Sharif (Dowlatabad, Andkhoy, Sheberghan, Balkh); Mazar – Pul-i-Khumri
(Khulm, Aybak); Pul-i-Khumri – Bagram (Doshi, the Salang, Jabal Saraj, Charikar); Herat –
Chaghcharan up the Hari Rud (Obeh, Chisht-e Sharif, Shahrak); Chaghcharan – Bamyan (Lal,
Panjab); Bamyan – Kabul (Hajigak and Unai passes, Maidan Shahr); Kabul – Bagram (Qarabagh);
Kabul – Jalalabad (Sarobi). Two fronts open from Herat: north to Qala i Naw, east to
Chaghcharan.

**Air defence**: Hawk at Herat, Shindand and Camp Bastion. Medium-SAM markers ring Mazar,
Bamyan, Qala i Naw, Chaghcharan, Jalalabad, Bagram and Kabul and draw from the faction's SA-2,
SA-3, SA-2/3 and SA-6 presets. SHORAD markers at the bases and 25 along the roads draw SA-8,
SA-9 or SA-13. A Scud battery sits on the Shomali plain north of
Kabul.

## Constraints

- **Neither Herat nor Shindand has a stand for a B-52, KC-135, E-3A or C-130.** The heavies
  fly from Camp Bastion. **Never draw a road to Camp Bastion**: a road opens a southern front. A
  test pins it, and checks every squadron against the nested stand classes.
- **Mission range is 250 NM.** Herat and Shindand are 150 to 165 NM from Chaghcharan, past
  the 150 NM default; Bagram and Kabul (about 350 NM) stay out of reach at the start.
- **Motorpools sit 3,500 m or more from their base.** Parked reserve armor inside a 3,000 m
  capture zone blocks the capture, and New Game errors on it.
- **A road's first and last waypoints are Off Road.** The Mission Editor crashed
  (`calc_route_length`) on an On Road first leg it could not path from a runway.
- **Every red point carries the invert flag**; blue's do not. A test checks both.
- **Neutral fields have dynamic spawn off**, or they read as red control points.

## Stand-ins and fudges

USAF F-4Es in Afghanistan are fiction. The F-5E stands in for an aggressor-flown light fighter. The Su-24M, MiG-27K and A-50 fit 1985;
the 40th Army's MiG-23MLD and Su-25 are historical. The SA-2 and SA-3 rings are fiction:
the 40th Army fielded no long-range SAMs against an enemy with no air force.

## Not verified

Measured headless only. Nothing has been flown. Row B255 covers the first flight: Phantom
loadouts and CAP, the front lines in the winter mountains, convoy movement over the Salang
and the Hari Rud road, and whether the DCS map shows snow in January.
