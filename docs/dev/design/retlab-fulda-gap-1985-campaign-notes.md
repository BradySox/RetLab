# Germany — Fulda Gap 1985

**Status: BUILT 2026-10-24, headless-verified (a fresh turn 0 plans 20 blue and 10 red
packages and generates a mission). In-game pass is checklist row B278. New game required.**

Owner: this note. CI lock: `tests/retlab/test_fulda_gap_1985.py`.

| | |
|---|---|
| Files | `resources/campaigns/fulda_gap_1985.yaml` + `.miz` |
| `.miz` | **Hand-edited by the DM in the Mission Editor.** First built from `red_tide.miz` by `tools/build_fulda_gap_1985_miz.py`, deleted; it is in the first commit of PR #1377 on GitHub |
| Routes | M-113 groups traced from real town lat/lon; first and last waypoints Off Road, the rest On Road |
| Factions | `NATO Central Front 1985`, `Warsaw Pact Central Front 1985` (both new, stock DCS) |
| Squadrons | 13 new presets plus existing 480th TFS, 512th and 526th TFS, JBG 31, RAF 31 Sqn, NATO E-3A, 336 OBVP, 357 ShAP |
| Checklist row | B278 |

## Why it exists

The DM joined a squadron that recreates the 1985 23rd Tactical Fighter Squadron. He asked
for a Retribution campaign with the most historical accuracy we can get.

## The DM's calls (2026-10-24)

- **The 23rd TFS at Spangdahlem, F-4E.** He first said Ramstein; in 1985 the 23rd was in
  the 52nd TFW at Spangdahlem, flying F-4Es paired with F-4G Wild Weasels. He confirmed
  Spangdahlem. There is no F-4G in DCS: the 480th TFS flies SEAD with Shrike (and the
  AGM-78 when the §71 pack is ticked), standing in for the Weasel half of the team.
- **Central sector**: the Fulda Gap to the Harz, not the whole border.
- **September 1985** (start 10 September).
- **Luftwaffe and RAF Germany** fly beside the USAF.
- **Soviets and East Germans** on red, East German squadrons under the GDR flag.
- **No MiG-29s.** Dropped from the faction and the laydown.
- **Real SAM sites.** The DM supplied Carsten's Cold War Germany Framework (a
  free Mission Editor template by Carsten, 2025, shared for mission makers to
  build on). Its Hawk, CRC, SA-2, SA-3, SA-5 and S-60 sites inside the sector
  replace the generated rings, each within about a mile of the original spot.

## The DM's laydown (2026-10-24)

The DM checked the built laydown in the Mission Editor for overlaps and saved his own
version; that save is the `.miz` and the build tool is deleted. His first pass moved eight
EWRs, the Altes Lager guns and SHORAD, and the Juterbog comms tower off the spots the
tool picked. Edit the `.miz` in the Mission Editor from now on.

## The laydown

| Side | Base | Squadrons |
|---|---|---|
| USAF | **Spangdahlem** | 23rd TFS F-4E 12 (DEAD), 480th TFS F-4E 12 (SEAD), 81st TFS F-4E 12 (Strike) |
| USAF | **Bitburg** | 22nd, 53rd, 525th TFS F-15C, 12 each |
| USAF | **Ramstein** | 512th TFS F-4E 12, 526th TFS F-4E 12, NATO E-3A 2 |
| USAF | **Frankfurt** (Rhein-Main) | KC-135 2, C-130J 2 |
| USAF | **Sembach** | 510th TFS A-10A 12 (the 81st TFW's forward operating location) |
| Luftwaffe | **Pferdsfeld** | JaBoG 35 F-4E 12 (standing in for the F-4F) |
| Luftwaffe | **Norvenich** | JBG 31 Tornado IDS 12 |
| RAF | **Gutersloh** (rear, no road) | No. 31 Squadron Tornado GR4 12 (standing in for the GR1) |
| US Army | **Fulda** | 11th ACR UH-1H 8 |
| NATO | **Hahn, Fritzlar, Giebelstadt, Schweinfurt** | none |
| USSR | **Haina** | 336 OBVP Mi-24P 12 |
| USSR | **Obermehler Schlotheim** | Mi-8 6 (seven stands take a Hip) |
| USSR | **Allstedt** | MiG-27K 12 |
| USSR | **Merseburg** | 85 GvIAP MiG-23MLD 12 |
| USSR | **Kothen** | 73 GvIAP MiG-23MLD 12 |
| USSR | **Zerbst** | 35 IAP MiG-23MLD 12 |
| USSR | **Brandis** | 357 ShAP Su-25 12 |
| USSR | **Altes Lager** | 833 IAP MiG-23MLD 12 |
| GDR | **Holzdorf** | JG-1 MiG-21bis 12 |
| USSR | **Mahlwinkel** | Su-17M4 12 |
| USSR | **Sperenberg** | An-26B 2 |
| USSR | **Bindersleben** (Erfurt) | none; 17 stands |
| USSR | **Meiningen** (FOB) | none; the garrison on the Meiningen road |

Regiment numbers are from memory and not checked against a source. Where unsure (Allstedt,
Mahlwinkel, Obermehler) the squadron is named by its aircraft type.

**Fronts.** Fulda – Haina (Hunfeld, Geisa, Bad Salzungen, Eisenach), Fritzlar – Obermehler
(Melsungen, Eschwege, Muhlhausen), Schweinfurt – Meiningen (Bad Neustadt, Mellrichstadt).
Meiningen joins Erfurt through Suhl and Arnstadt. NATO's rear roads run to Frankfurt; the Pact's run from Gotha and Erfurt through
Halle, Leipzig and Dessau to Juterbog, Torgau and Magdeburg.

**Air defense.** NATO, at Carsten's sites: Hawks at Frielendorf, Kassel, Bruchkobel, Giessen,
Fulda, Rockenhausen, Baumholder, Schmallenberg, Steinheim and Bad Driburg, and the CRC at
Erndtebruck; plus an EWR on the Wasserkuppe, Patriot at Ramstein, and Roland, Rapier, Gepard and
Vulcan at the bases. Red, at Carsten's sites: SA-2s at Gotha, Allstedt, Quedlinburg, Merseburg,
Bad Durrenberg, Leipzig, Kothen, Dessau and Mahlwinkel; SA-3s at Meiningen and Sperenberg; SA-5s
at Kaltennordheim, Eckolstadt and Magdeburg; S-60 batteries at Leipzig, Burg and Potsdam. Each
is pinned to its own type in the yaml. Added: mobile SA-6s at Haina, Obermehler and Erfurt
(standing in for the SA-4 brigades), SHORAD at the fields and five roadside towns.
Skynet's advanced mode, wired by range from statics named `CF85-IADS-*`: HQs at Wunsdorf
(GSFG), Weimar (8th Guards Army) and Magdeburg (3rd Shock Army); 15 comms towers including the
Inselsberg and the Brocken; 6 power plants (Lippendorf, Vockerode, Zschornewitz, Erfurt,
Ludwigsfelde, Magdeburg). Scud batteries near Weimar and Juterbog.

**Flavor.** The 37 scenery target sets that Red Tide authored inside the sector come with the
map: the Staudinger power station, the Frankenbach fuel terminal, the Giessen and Mendig rail
yards, the Haina IADS buildings, the Hotensleben border tower and the Sperenberg headquarters.
Red Tide's influence zones, markers and groups are dropped. Strike statics stand on the Buna
and Leuna chemical works.

## Constraints

- **Mission range is 250 NM.** Spangdahlem to Haina is 151 NM, one past the 150 NM default;
  the Berlin fields stay out of reach at the start.
- **Gutersloh has no road.** A road there opens a northern front the DM did not ask for.
- **Obermehler takes seven Hips**; the squadron is six.
- **Meiningen is an FOB because of the SA-3.** Without a red point there, the
  Meiningen SA-3 binds to Fulda, its nearest control point, and blue cannot field it.
- **Every red point carries the invert flag**; blue's do not. A test checks both.
- **Neutral fields have dynamic spawn off**, or they read as red control points.
- **Red Tide stays untouched.** The laydown started from a copy of its map.

## Stand-ins and fudges

The F-4E-45MC stands in for the Luftwaffe F-4F; the Tornado GR4 for the RAF's GR1 (31 Squadron
was at Bruggen, which is off the map); the C-130J for the C-130E; the Patriot arrived in
Germany in 1985. The 357th's Su-25s reached Brandis in 1986. The 50th TFW's F-16As at Hahn are
missing: DCS has no F-16A. The 23rd TFS livery is the DM's own; without it the jets fly the
default.

## Not verified

Measured headless only. Row B278 covers the first flight.
