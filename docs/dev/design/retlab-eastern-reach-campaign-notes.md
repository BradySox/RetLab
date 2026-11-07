# Persian Gulf — Eastern Reach 2025

**Status: BUILT 2026-11-07, headless-verified (the laydown tests). In-game pass is
checklist row B317. New game required.**

Owner: this note. CI lock: `tests/retlab/test_eastern_reach_2025.py`.

| | |
|---|---|
| Files | `resources/campaigns/eastern_reach_2025.yaml` + `.miz` |
| Build tool | `python tools/build_eastern_reach_miz.py --template <Arabian_SAM_Template.miz>` — **never hand-edit the `.miz`** |
| Placement | `tools/campaign_placement.py`; the readings cache is `Saved Games\DCS\RetLab placement\PersianGulf.json` |
| Factions | `USA 2020` (stock + CurrentHill USA + F-15EX V3), `[CH] Iran 2025` (CurrentHill Iran + RetLab Iran Air Defense Pack) |
| Checklist row | B317 |

## Why it exists

Every shipped Persian Gulf campaign fights the Hormuz coast (Bandar Abbas, Qeshm, Kish,
then Lar and Shiraz). This one is the long-range campaign Brady asked for on 2026-11-07: the
east end of the map, inland, with every deep strike 300 NM or more from the UAE fields.

## The DM's calls (2026-11-07)

- **Concept A of three** (the other two: a western island chain to Shiraz, and a 1988
  Phantom war on the same ground).
- **One axis**: Jask north up the real highway through Sirik, Minab, Kahnuj, Jiroft and
  the Jebal Barez pass to Kerman.
- **Bandar Abbas and Havadarya out of play**: neutral, empty.
- **A carrier and an LHA** in the Gulf of Oman.
- **Heavier red fighters**: Tomcats and Fulcrums, the F-4E the only striker; no F-5E, F1,
  Su-24 or Su-25. The Su-35S mod is not on the DM's PC, so no Su-35.
- **Red fills Kerman**: Jiroft has 3 DCS parking spots and Lar 5, so nearly the whole air
  force bases at Kerman (42 spots). Jiroft keeps 3 MiG-29s, Lar 5 F-14s.
- **The Arabian SAM Template** (freeware, unlimited distribution): only four UAE sites, at
  the fields blue flies from, copied as drawn as FIXED groups. The template's Iran sites are
  all outside the valley.

## The laydown

| Side | Base | Squadrons |
|---|---|---|
| Blue | Al Dhafra | E-3A 2, KC-135 3, F-15EX 12, F-22A 8 |
| Blue | Al Minhad | F-16CM 12 (SEAD), F-15E 12, KC-135 MPRS 2 |
| Blue | Al Ain | B-1B 3, C-130J-30 2 |
| Blue | Fujairah | CH-47F 3 |
| Blue | Jask | AH-64D 2 |
| Blue | Carrier | F/A-18C 12, F/A-18E 12, EA-18G 4, E-2D 2 |
| Blue | LHA | AV-8B 8, AH-1W 4, CH-53E 4, UH-60L 4 |
| Red | Kerman | F-14A 12 and 8, MiG-29A 10, F-4E 10 (strike), A-50, IL-78M |
| Red | Jiroft | MiG-29A 3 |
| Red | Lar | F-14A 5 (no road to the front) |
| Red | Minab, Kahnuj | Mi-28N 4 each (four helipads each) |

Win: take Kerman. Lose: lose Jask. `max_mission_range_planes` is 420 (Al Dhafra to Kerman
is 383 NM).

## How the .miz is built

- The map, coalitions and weather come from `operation_noisy_cricket.miz`; every group and
  zone in it is stripped.
- The six roads are the real highway, traced with OpenStreetMap routing on 2026-11-07,
  3-4 junctions per leg, every waypoint On Road.
- Every marker is placed by job (`Job.AIR_DEFENSE`, `GARRISON`, `DEPOT`, `EWR`, `TOWN`,
  `SPOT`). The tool reads the check mission's output from `Saved Games\DCS\Logs` itself.
- Six spots moved after the first check run (2026-11-07): Kerman's town centre is inside
  the landmap exclusion, and the hills east of Kerman and west of Jiroft are 9-16 degrees.
  They now anchor on flat ground the first run read (`PLACES_XY`).
- Red markers are generic types; the faction picks the system (Bavar-373 and 3rd Khordad
  for the long and medium sites, Kheibar, Fattah-2 and Shahed 238 launchers for missile
  sites, Silkworm on the coast).

## Open

- Not flown (B317).
- Scenery targets (dams, bridges, the Kerman power plant) are not authored; the town nodes
  sit at the edge of the buildings, not on a named one.
