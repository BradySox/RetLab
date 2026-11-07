# F-15EX V3 mod support

Support for Spino's F-15EX V3 mod (version 3.0, installed as `Mods\aircraft\F-15EX V3`).
Built 2026-11-06. Off unless **F-15EX V3 (Spino v3.0)** is ticked in New Game.

## What is supported

| DCS id | RetLab name | Factions |
|---|---|---|
| `F15EX_CFT` | F-15EX Eagle II (CFTs) | USA 2020, Bluefor Modern, Blufor Current, NATO Baltic 2027, WRL - Task Force Blue |
| `F15IA` | F-15IA Eagle II | Israel 2017, Bluefor Modern |

- The mod's non-CFT `F15EX` is left out of RetLab (Brady's call, 2026-11-06). It only
  exists when the mod's CFT-removal switch (`F15EX_nocft.lua`) is on.
- V3 ships air-to-air weapons only, so both jets plan BARCAP, TARCAP, Escort and Fighter
  sweep. Revisit the task list when the mod brings bombs back.

## Loadouts (`resources/customized_payloads/F15EX_CFT.lua`, `F15IA.lua`)

Every fit is the mod's own standard layout: 10 AMRAAMs (two wing doubles, four CFT
stations, two outer rails), 2 inner-rail short-range missiles, 3 x 610 gal tanks.

- F-15EX: Escort and Fighter sweep carry AIM-260A; BARCAP, TARCAP and Intercept carry
  AIM-120D-3. With weapons restricted by date, AIM-260A falls back to AIM-120D before 2026.
- F-15IA: AIM-120D-3 and Python-5 on every task. The mod gives the F-15IA no AIM-260A.

## Station and store ids

- `pydcs_extensions/f15ex/f15ex.py` lists every store the mod's pylon tables accept, by
  the mod's own ids. Most are built in a loop by the mod (`{F15EX_<missile>_<station>}`),
  so they were read from the pylon tables, not grepped from the loadout files.
- Left out: `<CLEAN>` and `{AIM200_X3_F-15EX}`, which a pylon table lists but no loadout
  file declares.
- Three stores share their id with the F-22A pack (`{LAU_115_2x...}` for AIM-120C-7,
  AIM-120D-3 and AIM-260A) and reuse its entries.
- No mod file is copied: the mod's readme forbids redistribution.
- AIM-174B and AIM-200A are in no fit. Each has a weapon group so a hand-load is date-gated
  (2024 and 2027). Python-5 is ungated, as it is for the F-15D Baz.

## Upstream

Brady wants this carved upstream after it lands, with all three jets including the
non-CFT F-15EX.

## In-game check

Row B315.
