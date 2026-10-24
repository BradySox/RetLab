# Germany — Fulda Gap 1985

**Status: BUILT 2026-10-24, cut to 13 bases the same day; headless-verified (a fresh turn 0
plans 11 blue and 8 red packages and generates a mission). In-game pass is checklist row B278. New game required.**

Owner: this note. CI lock: `tests/retlab/test_fulda_gap_1985.py`.

| | |
|---|---|
| Files | `resources/campaigns/fulda_gap_1985.yaml` + `.miz` |
| `.miz` | **Hand-edited by the DM in the Mission Editor.** First built from `red_tide.miz` by `tools/build_fulda_gap_1985_miz.py`, deleted; it is in the first commit of PR #1377 on GitHub |
| Routes | M-113 groups traced from real town lat/lon; first and last waypoints Off Road, the rest On Road |
| Factions | `NATO Central Front 1985`, `Warsaw Pact Central Front 1985` (both new, stock DCS) |
| Squadrons | 18 squadrons, 89 blue and 54 red aircraft; presets new and existing (480th TFS, 526th TFS, JBG 31, RAF 31 Sqn, NATO E-3A, 336 OBVP, 357 ShAP) |
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
  replace the generated rings. Since §122 (#1378) they are `FIXED` groups (22 after the cut),
  every radar, launcher and truck in his revetments.

## The DM's laydown (2026-10-24)

The DM checked the built laydown in the Mission Editor for overlaps and saved his own
version; that save is the `.miz` and the build tool is deleted. His first pass moved eight
EWRs, the Altes Lager guns and SHORAD, and the Juterbog comms tower off the spots the
tool picked. Edit the `.miz` in the Mission Editor from now on.

**Cut to 13 bases the same day** ("way too many bases and air units"): the front and key
fields only, squadrons of 8 except the 23rd. Dropped: Hahn, Sembach, Pferdsfeld,
Norvenich, Gutersloh, Giebelstadt, Kothen, Zerbst, Brandis, Altes Lager, Holzdorf,
Mahlwinkel and Sperenberg, with their markers, roads and depots, and every red-side object
more than 50 miles from a kept red base (five FIXED sites, the GSFG and 3rd Shock Army
HQs, three comms towers, two power plants, the Juterbog Scud) and the eleven Red Tide
scenery sets around Berlin and Sperenberg. The squadrons dropped: the 81st, 53rd, 525th
and 512th TFS, JaBoG 35, the 35th and 833rd IAP, the Su-17s and the An-26s.

## The laydown

| Side | Base | Squadrons |
|---|---|---|
| USAF | **Spangdahlem** | 23rd TFS F-4E 24 (DEAD), 480th TFS F-4E 16 (SEAD) — doubled on the DM's call, 2026-10-24 |
| USAF + Luftwaffe | **Bitburg** | 22nd TFS F-15C 8, JBG 31 Tornado IDS 8 |
| USAF + RAF | **Ramstein** | 526th TFS F-4E 8, No. 31 Squadron Tornado GR4 8 (standing in for the GR1), NATO E-3A 1 |
| USAF | **Frankfurt** (Rhein-Main) | 510th TFS A-10A 8, KC-135 2, C-130J 2 |
| US Army | **Fulda** | 11th ACR UH-1H 4 |
| NATO | **Fritzlar, Schweinfurt** | none |
| USSR | **Haina** | 336 OBVP Mi-24P 8 |
| USSR | **Obermehler Schlotheim** | Mi-8 6 (seven stands take a Hip) |
| GDR | **Bindersleben** (Erfurt) | JG-1 MiG-21bis 8 |
| USSR | **Allstedt** | 73 GvIAP MiG-23MLD 8, MiG-27K 8 |
| USSR | **Merseburg** | 85 GvIAP MiG-23MLD 8, 357 ShAP Su-25 8 |
| USSR | **Meiningen** (FOB) | none; the garrison on the Meiningen road |

Regiment numbers are from memory and not checked against a source. Where unsure (Allstedt's
MiG-27s, Obermehler) the squadron is named by its aircraft type. JG-1 was at Holzdorf and the
Tornados at Norvenich and Bruggen: they moved with the cut.

**Fronts.** Fulda – Haina (Hunfeld, Geisa, Bad Salzungen, Eisenach), Fritzlar – Obermehler
(Melsungen, Eschwege, Muhlhausen), Schweinfurt – Meiningen (Bad Neustadt, Mellrichstadt).
Meiningen joins Erfurt through Suhl and Arnstadt. NATO's roads run to Frankfurt from
Spangdahlem (through the Hunsruck and Mainz), Ramstein (Kaiserslautern, Alzey) and Schweinfurt
(Wurzburg); the Pact's run from Gotha and Erfurt to Allstedt and Merseburg.

**Air defense.** NATO, at Carsten's sites: Hawks at Frielendorf, Kassel, Bruchkobel, Giessen,
Fulda, Rockenhausen, Baumholder, Schmallenberg, Steinheim and Bad Driburg, and the CRC at
Erndtebruck; plus an EWR on the Wasserkuppe, Patriot at Ramstein, and Roland, Rapier, Gepard and
Vulcan at the bases. Red, at Carsten's sites: SA-2s at Gotha, Allstedt, Quedlinburg, Merseburg,
Bad Durrenberg, Leipzig, Kothen and Dessau; an SA-3 at Meiningen; an S-60 battery at Leipzig.
Each is a `FIXED` group copied unit by unit from his mission. **No SA-5s (DM call, same
day):** at about 140 NM their rings covered all of West Germany. Kaltennordheim and
Eckolstadt keep their revetments as SA-2 sites: each S-200 launcher became an SA-2
launcher, the 5N62 tracking radar a Fan Song, the command post was dropped. His
Kaltennordheim group was three radars with no launchers; the DM placed its launchers in
the Mission Editor. The faction has no SA-5 preset, so none can be bought. The Hawks sit in the blue
country block, red's in the red. The red faction carries the S-60 and the KS-19/SON-9 preset so
it can field the S-60 site's Fire Can. The CRC at Erndtebruck is still a marker. Added: mobile
SA-6s at Haina, Obermehler and Erfurt (standing in for the SA-4 brigades), SHORAD at the fields
and five roadside towns. Skynet's advanced mode, wired by range from statics named
`CF85-IADS-*`: the 8th Guards Army HQ at Weimar; 12 comms towers including the Inselsberg and
the Brocken; 4 power plants (Lippendorf, Vockerode, Zschornewitz, Erfurt). A Scud battery near
Weimar.

**Flavor.** 26 of the scenery target sets Red Tide authored come with the map: the
Staudinger power station, the Frankenbach fuel terminal, the Giessen and Mendig rail yards and
the Haina IADS buildings. Red Tide's influence zones, markers and groups are dropped. Strike
statics stand on the Buna and Leuna chemical works.

## Constraints

- **Mission range is 250 NM.** Spangdahlem to Haina is 151 NM, one past the 150 NM default;
  250 reaches Merseburg.
- **Obermehler takes seven Hips**; the squadron is six.
- **Meiningen is an FOB because of the SA-3.** Without a red point there, the
  Meiningen SA-3 binds to Fulda, its nearest control point, and blue cannot field it.
- **A red-side object binds to the nearest base.** After the cut, anything far east of
  Merseburg would belong to a base 100 miles away; such objects were deleted, not moved.
- **Every red point carries the invert flag**; blue's do not. A test checks both.
- **Neutral fields have dynamic spawn off**, or they read as red control points.
- **Red Tide stays untouched.** The laydown started from a copy of its map.

## Stand-ins and fudges

The Tornado GR4 stands in for the RAF's GR1; the C-130J for the C-130E; the Patriot arrived in
Germany in 1985. The 357th's Su-25s reached Brandis in 1986, and fly from Merseburg here. The
50th TFW's F-16As at Hahn are missing: DCS has no F-16A. The 23rd TFS livery is the DM's own;
without it the jets fly the default.

## Not verified

Measured headless only. Row B278 covers the first flight.
