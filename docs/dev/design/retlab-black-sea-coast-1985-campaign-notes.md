# Caucasus — Black Sea Coast 1985

**Status: BUILT 2026-11-08, headless-verified (the laydown tests). In-game pass is
checklist row B320. New game required.**

Owner: this note. CI lock: `tests/retlab/test_black_sea_coast_1985.py`.

| | |
|---|---|
| Files | `resources/campaigns/black_sea_coast_1985.yaml` + `.miz` |
| Source | `tools/build_black_sea_coast_1985_miz.py`, on the placement tool. If the DM saves the `.miz` in the Mission Editor, his save becomes the source and the tool is dropped |
| Placement | `tools/campaign_placement.py`; the readings cache is `Saved Games\DCS\RetLab placement\Caucasus.json` |
| Factions | `Blufor Late Cold War (80s)` against `Russia 1980`, both stock DCS; no mod box to tick |
| Checklist row | B320 |

## Why it exists

Brady asked on 2026-11-08 where to fly late Cold War jets on the Caucasus. No shipped
Caucasus campaign is laid out for the 1980s: the 1980 Tblisi Gap is a small helicopter
campaign, and Northern Russia plays in 1985 only with a faction and date change. RetLab's
1980s campaigns are all on other maps (Fulda Gap, Northern Shield, Red Tide, Northern Flank,
Red Bear).

## The DM's calls (2026-11-08)

- **Blue holds the south, the fight is in the north.** The first cut (a landing at Batumi
  driving inland to Tbilisi) was turned down: "more northern end of the map while blue
  holds the south". Georgia was Soviet in 1985; the story has it break away.
- **The coast axis**, of three (the others: over the Darial pass to Beslan and Mozdok, or
  both). Up the coast road from the Enguri to Sochi, then Tuapse and Krasnodar.
- **Blue fields**: Senaki, Kutaisi, Lochini, Vaziani. Batumi, Kobuleti and Soganlug empty.
- **A carrier**: a 1985 Forrestal air wing (F-14A, A-6E, E-2C, A-6E tankers). The F-4E flies
  from land. The A-7E is a mod not on the DM's PC, so the carrier has no Corsairs.
- **Red air**: MiG-21, MiG-23 and MiG-25 regiments, one small MiG-29 regiment at Maykop,
  Su-17, Su-24 and Su-25 for attack. No Su-27 or MiG-31 squadron.
- **Period SAMs only**: the `.miz` has no long-range marker, so New Game builds no SA-5 or
  SA-10; every medium site is an SA-2, SA-3, SA-6 or SA-11.

## The laydown

| Side | Base | Squadrons |
|---|---|---|
| Blue | Senaki | 23rd TFS F-4E 16 (DEAD), 480th TFS F-4E 8 (SEAD) |
| Blue | Kutaisi | 22nd TFS F-15C 8, 510th TFS A-10A 8 |
| Blue | Lochini | KC-135 2, E-3A 2 |
| Blue | Vaziani | CH-47D 4 |
| Blue | Carrier | VF-11 F-14A 12, VF-33 F-14A 12, VA-85 A-6E 10, VAW-122 E-2C 2, VA-34 A-6E tanker 4 |
| Blue | LHA | CH-53E 6, UH-1H 6 |
| Red | Sukhumi | MiG-23MLD 8, Su-24M 4 (anti-ship; Babushara has five Fencer stands) |
| Red | Gudauta | MiG-21bis 12 |
| Red | Sochi | MiG-23MLD 12, Su-25 12, Mi-24P 8 |
| Red | Maykop | MiG-29A 8, Su-17M4 12 |
| Red | Krasnodar Center | MiG-23MLD 12, Su-24M 12 |
| Red | Krasnodar Pashkovsky | Mi-8 6 |
| Red | Krymsk | MiG-25PD 8, Tu-22M3 6 (anti-ship), A-50 2, IL-78M 2 |

Four red FOBs on the road: Gali, Lazarevskoye, Tuapse (Black Sea's "FOB Sochi" spot) and
Goryachy Klyuch. Tuapse and Goryachy Klyuch carry two Invisible FARP pads each.

Win: take both Krasnodar fields. Lose: lose Senaki. No mission range preset: a land
campaign leaves the range to the host, and blue forward-deploys as bases fall (DM call,
2026-11-08, #1476).

`neutral_border_postures`: Turkey blue; Armenia, Azerbaijan and Ukraine red.

## The roads

The coast road Senaki, Zugdidi, Gali, Ochamchire, Sukhumi, Gudauta, Sochi, Lazarevskoye,
Tuapse, then the highway over the hills by Dzhubga to Goryachy Klyuch, Krasnodar Pashkovsky,
Krasnodar Center and Krymsk. Branches: Tuapse to Maykop by Apsheronsk, and the blue rear
Lochini, Vaziani, Kutaisi, Senaki. Traced with OpenStreetMap routing on 2026-11-08, 3-5
points per leg. Senaki to Sukhumi is by hand: today's router will not cross the Enguri.

Each road's two ends are Off Road and the points between On Road. Every point On Road
crashed the Mission Editor on load (`me_mission.lua` `calc_route_length`, 2026-11-08): an
end on a base centre it could not route to.

## The flavor, and where it came from

- Rail stations at Psyrtsha and Bzyb (Abchazian Blitz), the Adagum works by Krymsk and the
  Tuapse FOB spot (Black Sea).
- Real industry as strike targets: the Tuapse and Krasnodar refineries, the Novorossiysk
  port. The Akhun mountain tower above Sochi is a comms node.
- Scud hides in the hills by Goryachy Klyuch and Krymsk.
- Motor pools at Adler and Krasnodar sit about 4 km out, outside the 3 km capture zone.

## How the .miz is built

- The map, coalitions and weather come from `northern_russia.miz`; every group and zone in
  it is stripped.
- Every marker is placed by job (`Job.AIR_DEFENSE`, `GARRISON`, `DEPOT`, `EWR`, `TOWN`,
  `SPOT`). The first build writes the check mission
  `Saved Games\DCS\Missions\RetLab probes\black_sea_coast_1985_placement.miz`; the DM runs
  it once and the tool reads its output from `Saved Games\DCS\Logs` itself.
- Town anchors (Gudauta, Krasnodar, Krymsk, Novorossiysk, the FOB at Gali) sit on the edge
  of the landmap's town exclusions, where a unit can stand.
- Red markers are generic types; the faction picks the system.
