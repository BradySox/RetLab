# Real SAM sites in Germany campaigns

**Goal (DM call, 2026-11-06):** Germany campaigns use real, drawn air-defense sites with a
launcher on every pad. The mechanism is §122 (`FIXED` groups generate as drawn,
`retlab-exact-site-layouts-notes.md`).

## Status

| Campaign | Source | Status |
|---|---|---|
| Fulda Gap 1985 | Carsten's framework, hand-edited | every SA-2 has 6 launchers (2026-11-06) |
| Northern Shield 1988 | Carsten's framework, hand-edited | every SA-2 has 6; Magdeburg SA-5 has 18 (2026-11-06) |
| other Germany campaigns | | not started |

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
