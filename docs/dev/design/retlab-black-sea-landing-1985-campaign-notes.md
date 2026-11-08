# Caucasus — Black Sea Landing 1985

**Status: BUILT 2026-11-08, headless-verified (the laydown tests). In-game pass is
checklist row B320. New game required.**

Owner: this note. CI lock: `tests/retlab/test_black_sea_landing_1985.py`.

| | |
|---|---|
| Files | `resources/campaigns/black_sea_landing_1985.yaml` + `.miz` |
| Source | `tools/build_black_sea_landing_1985_miz.py`, on the placement tool. If the DM saves the `.miz` in the Mission Editor, his save becomes the source and the tool is dropped |
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

- **Black Sea landing**, of three pitches (the others: a Georgian breakaway with the
  Soviets coming south through the passes, and a landing at Sochi fighting north to
  Krasnodar). Georgia was Soviet in 1985, so NATO's foothold is on the map, never off it.
- **Medium**: 8 airfields plus the carrier and the LHA.
- **Red air**: MiG-21, MiG-23 and MiG-25 regiments, one small MiG-29 regiment at Tbilisi,
  Su-17, Su-24 and Su-25 for attack. No Su-27 or MiG-31 squadron.
- **A carrier**: a 1985 Forrestal air wing (F-14A, A-6E, E-2C, A-6E tankers). The F-4E flies
  from land. The A-7E is a mod not on the DM's PC, so the carrier has no Corsairs.
- **Period SAMs only**: the `.miz` has no long-range marker, so New Game builds no SA-5 or
  SA-10; every medium site is an SA-2, SA-3, SA-6 or SA-11.

## The laydown

| Side | Base | Squadrons |
|---|---|---|
| Blue | Kobuleti | 23rd TFS F-4E 16 (DEAD), 480th TFS F-4E 8 (SEAD), 22nd TFS F-15C 8, KC-135 2 |
| Blue | Batumi | 510th TFS A-10A 8 |
| Blue | Carrier | VF-11 F-14A 12, VF-33 F-14A 12, VA-85 A-6E 10, VAW-122 E-2C 2, VA-34 A-6E tanker 4 |
| Blue | LHA | CH-53E 6, UH-1H 6 |
| Red | Senaki | MiG-23MLD 12, Su-25 12 |
| Red | Kutaisi | MiG-21bis 12, Su-17M4 12, Mi-24P 8 |
| Red | Sukhumi | MiG-23MLD 8, Su-24M 4 (anti-ship; Babushara has five Fencer stands) |
| Red | Tbilisi-Lochini | MiG-29A 8, Mi-8 6 |
| Red | Vaziani | MiG-23MLD 12, Su-24M 12 |
| Red | Mozdok | MiG-25PD 8, Tu-22M3 6 (anti-ship), A-50 2, IL-78M 2 |

Five red FOBs on the road: Poti, Zugdidi, Zestafoni, Khashuri (the spot Northern Russia and
Iron Gate use) and Gori. Gori and Zestafoni carry two Invisible FARP pads each.
The landmap has no buildable ground in the Rioni delta, so FOB Poti sits on the Poti road
about 15 km inland, and the town-centre anchors at Tbilisi, Kutaisi, Sukhumi and Zugdidi
moved to the town edges (second check run, 2026-11-08).

Win: take Tbilisi-Lochini and Vaziani. Lose: lose Kobuleti. `max_mission_range_planes` is 250
(Kobuleti to Vaziani is about 170 NM).

`neutral_border_postures`: Turkey blue; Armenia, Azerbaijan and Ukraine red (Soviet in 1985).

## The roads

The coast road Batumi, Kobuleti, Poti, Senaki; the main highway Senaki, Kutaisi, Zestafoni,
the Rikoti pass, Khashuri, Gori, Mtskheta, Tbilisi, Vaziani; the branch Senaki, Zugdidi,
Gali, Ochamchire, Sukhumi. Traced with OpenStreetMap routing on 2026-11-08, 3-5 points per
leg, every waypoint On Road. Zugdidi to Sukhumi is by hand: today's router will not cross
the Enguri. Mozdok has no road: it is across the mountains, like Eastern Reach's Lar.

## The flavor, and where it came from

- Tbilisi's command post, comms tower and power plant sit where WRL Kutaisi to Vaziani puts
  its own.
- Real industry as strike targets: the Rustavi steel works, the Zestafoni ferroalloy works,
  the Kutaisi auto works. Real power: the Zhinvali dam and Jvari by the Enguri dam.
- Scud hides on the Mukhrani plain and the Tskaltubo hills.
- SAMs at Lochini, Vaziani, the hills north of Tbilisi, Mtskheta, Gori, the Surami pass,
  Kutaisi, Senaki, Sukhumi and Mozdok.

## How the .miz is built

- The map, coalitions and weather come from `northern_russia.miz`; every group and zone in
  it is stripped.
- Every marker is placed by job (`Job.AIR_DEFENSE`, `GARRISON`, `DEPOT`, `EWR`, `TOWN`,
  `SPOT`). The first build writes the check mission
  `Saved Games\DCS\Missions\RetLab probes\black_sea_landing_1985_placement.miz`; the DM runs
  it once and the tool reads its output from `Saved Games\DCS\Logs` itself. Two runs placed
  all 119 units, 0 flagged (2026-11-08).
- Red markers are generic types; the faction picks the system.
