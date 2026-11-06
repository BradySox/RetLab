# Real SAM sites in Syria and Germany campaigns

**Standing goal (DM call, 2026-11-06):** every Syria and Germany campaign that can use the
real, drawn air-defense sites does. The mechanism is §122 (`FIXED` groups generate as drawn,
`retlab-exact-site-layouts-notes.md`). Ugra Media's Syria and Germany Cold War maps model the
real SAM sites as permanent emplacements in the terrain; a drawn site puts each launcher and
radar in its own revetment. This is a long project: one campaign per PR, each planned with the
DM first (which sites, how far out, faction changes).

## Status

| Campaign | Map | Source | Status |
|---|---|---|---|
| Fulda Gap 1985 | Germany CW | drawn by hand in the ME | built (§122's first user) |
| Northern Shield 1988 | Germany CW | drawn by hand in the ME | built, laydown still being edited |
| Anatolian Reach | Syria | Levant template | built 2026-11-06, row B312 |
| other Syria and Germany campaigns | | | not started |

## The Levant template (Syria)

- **Source:** DCS user files 3321812, "Levant SAM Template", for Ugra Media's Syria map.
  License on the page: freeware, unlimited distribution. The page names no author. It builds
  on Pikes' Syrian Air Defence Network 2012 (forum.dcs.world topic 243078).
- **Extract:** `tools/data/levant_sam_template.json`: every vehicle group, with the template's
  country and group name, each unit's type, x/y (Syria-map metres) and heading. The template's
  Skynet, MOOSE dispatcher and ~1,700 scenery statics are not carried.
- **Contents:** Syria 148 SAM sites (60 SA-6, 39 SA-2, 37 SA-3, 6 SA-8, 5 SA-5, 1 SA-10) and
  41 EWRs (CJTF Red); Iraq and Jordan 38 sites; Turkey, Israel, Cyprus, UK and US about 30.
  Turkey is thin: 3 Hawks, 11 Rapiers, 5 FPS-117s.
- **Group names** carry the kind second: `RSAM-SA2-Damascus-4`, `REW-1L13-YE56`,
  `TAF(SAM)-Hawk-Adana-2`. `--drop` matches that field.

## The tool

`python tools/place_levant_sam_sites.py <campaign> --radius-nm 40 --drop SA10`

- Picks every template group of the named countries whose first unit is within the radius of
  a red airfield, and writes it to CJTF Red as `FIXED <template name>`.
- Leaves out any drawn unit on a runway strip or a stand (`airfieldclearance.field_under`);
  a site with nothing left is not placed. In Anatolian Reach this dropped the whole Sanliurfa
  Hawk (inside the strip band) and one SA-6 launcher at Kuweires.
- Puts a launcher a stock Retribution marker reader knows first (Hawk, SA-2, SA-3, Rapier,
  1L13), so a build without §122 still puts a stock site there. SA-5, SA-6 and FPS-117 sites
  have no stock marker and are dropped by such a build.
- Removes a SAM or radar marker within 1.8 NM of a placed site (the same real site, already
  authored as a marker). Gun markers stay: the template draws no AAA.
- Re-runnable: it replaces the FIXED groups an earlier run wrote.

## Lessons

- **A drawn unit the owner cannot field turns the whole site into a stock layout.** Check the
  New Game log for `FIXED site ... cannot field`. Anatolian Reach needed SA-2/S-75 and
  SA-5/S-200 presets, `SAM Hawk CWAR AN/MPQ-55` (in no preset group) and the domed FPS-117 and
  its control shelter. `test_drawn_levant_sites_build_as_drawn` locks it.
- **A drawn radar on its own** is classified as an EWR (§122, 2026-11-06); before that it was
  skipped as unclassifiable.
- **The template sits in country blocks Retribution never reads** (Syria, Iraq, Turkey ...).
  Only the CJTF blocks are campaign data, so the template cannot be pasted in directly.
