# Modern FOB layout and stock CurrentHill units

Status: built 2026-10-24. In-game row B283.

## Modern FOB

- `resources/layouts/buildings/modern_fob.{miz,yaml}` are written by
  `tools/build_modern_fob_layout.py`. Edit the tool and rerun it; never edit the `.miz`.
- fob1's six buildings at fob1's offsets, inside a HESCO wall (`HESCO_wallperimeter_1`,
  12.3 m apart), a `HESCO_watchtower_2` at each corner, a gate with a boom barrier in the
  south wall, tents, containers, a generator and gate sandbags: 58 statics.
- Wall geometry comes from ED's AH-64D Iraq quickstart missions: a segment runs along its
  heading. The collision meshes give about 11.8 m long, 2.7 m thick, 2.8 m tall.
- Non-generic, every dressing group `optional`. A faction opts in with
  `"excluded_generic_layouts": ["fob1"]` and `"extra_layouts": ["modern_fob"]`, the same
  pair the Vietnam FOB uses. All 62 factions dated 2000 or later opt in, except the
  insurgent factions (Taliban 2001, ISIS 2016).

## FARP props

- `HelipadGenerator._dress_modern_farp` puts six props by a FOB's first helipad when its
  owner opts into `modern_fob`. Fob control points only: an airfield's helipads can sit on
  an apron (see the airfield clearance constraint).
- Props go on the side the quad FARP's extra pads never use, and any prop within 30 m of a
  pad or ground spawn is left out. Skipped when the FARP statics are culled.

## Stock CurrentHill units

- The base game ships a CurrentHill pack in `CoreMods\tech\Currenthill Assets Pack`, separate
  from the CurrentHill country mods in `pydcs_extensions/`. Most of it was already in
  RetLab; this added the seven unused pieces.
- Tiger UHT (no gun): Blufor current, NATO Baltic 2027, Bluefor modern. Loadouts are in
  `resources/customized_payloads/CHAP_TigerUHT.lua`, built from the pack's own fits.
- BMP-3 ERA and Titan: the Russia 2010 and 2020 factions, Redfor current, SMD.
- M1296 Dragoon: USA 2012, USA 2020, Blufor current, NATO Baltic 2027.
- HX77, HX81 and SLT-50: logistics for the three NATO factions.
- The pack's two Project 22160 patrol ships are left for the navy assets work.
