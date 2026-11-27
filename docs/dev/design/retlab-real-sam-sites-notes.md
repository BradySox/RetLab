# Real SAM sites in Germany campaigns

**Goal (DM call, 2026-11-06):** Germany campaigns use real, drawn air-defense sites with a
launcher on every pad. The mechanism is §122 (`FIXED` groups generate as drawn,
`retlab-exact-site-layouts-notes.md`).

## Status

| Campaign | Source | Status |
|---|---|---|
| Fulda Gap 1985 | Carsten's framework, hand-edited; S3ntry's template | every SA-2 has 6 launchers (2026-11-06); +16 S3ntry sites (2026-11-26) |
| Northern Shield 1988 | Carsten's framework, hand-edited; S3ntry's template | every SA-2 has 6; Magdeburg SA-5 has 18 (2026-11-06); +3 S3ntry radars (2026-11-26) |
| Red Tide | S3ntry's template | +29 sites (2026-11-26) |
| Crossing the Rubicon | S3ntry's template | +22 sites (2026-11-26) |
| Baltic Fury | S3ntry's template | +27 sites (2026-11-26) |
| Northern Guardian | S3ntry's template | +21 sites (2026-11-26) |

## S3ntry's Germany CW Template (DM call, 2026-11-26)

S3ntry's Germany CW Template v1.3.1 (June 2026) is a free Mission Editor template: about 2,400
units at real 1985-89 sites, positions from public sources it lists. It states no license; we
copy positions and layouts only, never the file or its scripts. Credit: S3ntry.

- **Only sites on a revetment.** The author marks each site with no revetment in DCS
  "(missing in DCS)" on its map point. The DM checked 10 sites in the Mission Editor
  (2026-11-26): all 10 matched the flag. About half the template is usable.
- **Rules (DM picks):** every usable SAM, AAA and EWR site within 16 NM of a campaign base, as a
  `FIXED S3-<n>` group in the CJTF block of the nearest base's side. A generated marker of the
  same band (long, medium, short range, AAA, EWR) within 3 NM of a new site is removed. A site
  within 1,500 m of an existing `FIXED` group is already drawn and skipped.
- **Kept out:** Northern Shield's Badingen SA-5 and Rostock SA-3 and radar (earlier DM calls),
  and Baltic Fury's two radars that bound to the inert spare H FRG 12.
- **Kept out, runway clearance:** New Game flagged units on a runway strip or apron (§1 hard
  constraint): the airfield SHORAD sites S3-1 to S3-4 (Ramstein, Bitburg, Spangdahlem, Hahn),
  Fulda's AAA S3-9 at Obermehler Schlotheim, and Baltic Fury's SA-3 S3-36 at Kluczewo, whose
  apron is newer than the template.
- The template's waypoint options (evade ARM) are stripped: pydcs cannot read option 31.
- A Sinai template by the same author (v1.2) was looked at, not used.

## Syria dropped (DM call, 2026-11-06)

The Levant SAM Template (DCS user files 3321812) was built on an older Syria map. The DM checked
it in the Mission Editor: most sites sit off the map's current revetments. Anatolian Reach (41
sites, #1451) and 15 other campaigns (140 swaps, #1452) went back to their stock markers the same
day, with the faction support radars added for them. The tool, the template extract and the
tests are at `git show a02e314:tools/place_levant_sam_sites.py` and
`tools/data/levant_sam_template.json`.

## Finding the pads

- **The pads are part of the terrain, not map objects.** A probe mission listed every scenery
  object within 1,500 m of 307 sites with `world.searchObjects(Object.Category.SCENERY, ...)`.
  At Magdeburg, whose 12 pads are known, the nearest object to any pad was 41 m away. Do not
  re-run it to find pads.
- **What works:** a zoomed F10 screenshot with the site's drawn units on it. Fitting the drawn
  units' pixels to their mission positions put each pad within about 1 m (Magdeburg).
- **Or the DM places them:** a mission holding only the short sites, with guessed extra
  launchers named `<site> NEW n`, edited in the Mission Editor and copied back by matching
  each unit's original position (the 8 SA-2s, 2026-11-06).
