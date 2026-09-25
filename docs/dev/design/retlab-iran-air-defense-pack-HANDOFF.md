# HANDOFF — build the RetLab Iran Air Defense Pack (3rd Khordad + Bavar-373)

**For:** a local agent on the DM's Windows PC, with DCS installed and the mod folders readable.
**From:** a cloud session (2026-09-25) that had no DCS. It built the Retribution side; you
build the DCS mod and fly-check it.
**Read first:** [`retlab-iran-air-defense-pack-notes.md`](retlab-iran-air-defense-pack-notes.md)
— the unit contract (§1), the research and best-estimate numbers (§3).

## Who has what

| Thing | Where it lives | Done? |
|---|---|---|
| Retribution side (unit types, layouts, Skynet, factions, toggle, tests) | the RetLab repo, branch `claude/iran-dcs-asset-priority-4w0920` | **Done** |
| The DCS mod (vehicles, radars, missiles) | `<Saved Games>\DCS\Mods\tech\RetLab Iran Air Defense\` on the DM's PC | **Your job** |
| Research numbers | design note §3 | Done |

The DCS install is `E:\DCS World`. The mod goes under **Saved Games**, not the install.

## Hard rules

1. **The nine type ids in design note §1 are fixed.** Your `Database` lua must use them
   character for character. If one must change, change it in the repo in the same commit
   (the pydcs extension, the unit yaml filename, the layouts, Skynet, `faction.py`, the test).
2. **Never call `enableEmission`** in anything you write (a hard constraint in `CLAUDE.md`).
3. **No Retribution Lua plugin may name an `IRAD_` unit.** Mod awareness stays in Python.
4. **Licence check before copying.** Read the licence of any mod you use as a template (High
   Digit SAMs Ultimate Compilation, CurrentHill). Copying structure is fine; copying files is
   fine only if its licence allows it. If unclear, write the file fresh and say so.
5. Commit messages and docs: plain style, no paid-campaign names (see `CLAUDE.md`).

## Steps

### 1. Sync (2 min)

```powershell
git fetch origin
git checkout claude/iran-dcs-asset-priority-4w0920
git pull
```

### 2. Find your templates (15 min)

1. In the DCS install, find the vanilla Buk and S-300PS definitions: search `E:\DCS World`
   for `SA-11 Buk LN 9A310M1` and `S-300PS 5P85D ln`. Note the files, the shape (3D model)
   names, and the weapon names each launcher fires.
2. In `<Saved Games>\DCS\Mods\tech\`, open the High Digit SAMs Ultimate Compilation folder.
   Its `entry.lua` and `Database\*.lua` are the working example of a SAM mod that defines
   its own vehicles **and** its own missiles. Read its licence (rule 4).
3. Write down the shape names you will borrow (step 3 table). v0.1 borrows vanilla models.

### 3. Build Phase A: sites that spawn and fight (1–2 h)

Make `<Saved Games>\DCS\Mods\tech\RetLab Iran Air Defense\` with an `entry.lua` and one
`Database` lua per unit, copying the structure you found in step 2.

| Type id | Borrow the model of | Borrow the behaviour of | Missile (Phase A) |
|---|---|---|---|
| `IRAD_Bashir_SR` | Buk 9S18M1 SR | 9S18M1, detection 108 NM | — |
| `IRAD_3Khordad_TELAR` | Buk 9A310M1 TELAR | 9A310M1, radar 49 NM, 3 missiles | vanilla Buk missile |
| `IRAD_AlamAlHoda_TEL` | Buk loader-launcher, or the TELAR | launcher with no radar, 3 missiles | vanilla Buk missile |
| `IRAD_Meraj4_SR` | S-300PS 64H6E | detection 135 NM | — |
| `IRAD_Hafez_SR` | S-300PS 40B6MD | detection 108 NM | — |
| `IRAD_Bavar373_STR` | S-300PS 40B6M (30N6) | tracking 108 NM, 6 targets | — |
| `IRAD_Bavar373_CP` | S-300PS 54K6 | command post | — |
| `IRAD_Bavar373_LN` | S-300PS 5P85D | 4 vertical canisters | vanilla 5V55 |
| `IRAD_Bavar373_LN_4B` | S-300PS 5P85D | 4 vertical canisters | vanilla 5V55 |

Display names come from design note §1, exactly.

**Phase A check:** in the Mission Editor, place one of each under Iran. Every unit appears,
and `dcs.log` has no error naming `IRAD_`. Then place a 3rd Khordad site (SR + TELAR + 2 TELs)
and a Bavar-373 site (both SRs, CP, STR, 2 LNs), put an AI F-16 on a path through each, and run
it. Each site should engage.

### 3b. Our own 3D models (1 h per model once the exporter works)

The cloud session is building the models in Blender, by script:
`mods/iran_air_defense/models/` (read its `README.md`). **Done so far: the Bavar-373 TEL and
the Bavar-373 engagement radar (STR).** The other five are in progress. Export each the same way.

1. Find out whether this PC has a DCS EDM exporter for Blender or 3ds Max. **If it has
   neither, stop here and tell the DM** — nothing else in this step can happen without one.
2. Open `IRAD_Bavar373_LN.blend` and export it to `.edm` into the mod's `Shapes` folder.
   Copy `textures/IRAD_Bavar373_LN_camo.png` into the mod's `Textures` folder; the painted
   parts already use it through their UVs.
3. Bind `arg_launcher_elevation` and both rams to the launcher-elevation argument the vanilla
   S-300PS 5P85 uses (read it from the vanilla definition you found in step 2).
4. Point `IRAD_Bavar373_LN` and `IRAD_Bavar373_LN_4B` at the new shape instead of the
   borrowed 5P85D. Keep the borrowed shape for any model not built yet.
5. Check in the Model Viewer: the canisters rise on the argument, the rams follow without
   clipping, and a missile leaves each `LAUNCH_n` point.

### 4. Build Phase B: the real missiles (2–4 h)

Define three missiles, starting from the nearest missile definition you can read, with the
design note §3 best estimates:

| Missile | Based on | Range | Max alt | Speed | Guidance | Warhead |
|---|---|---|---|---|---|---|
| Taer-2B | Buk 9M317 | 27 NM | 82,000 ft | Mach 3–3.5 | command + SARH | 110 lb |
| Sayyad-4 | 48N6 / 5V55 family | 81 NM | 88,600 ft | Mach 5 | TVM-style | 400 lb |
| Sayyad-4B | the same, active terminal | 108 NM | 98,400 ft | Mach 5 | active terminal | 400 lb |

Min range and altitude: 1.6 NM / 65 ft (Taer-2B) and 2.7 NM / 82 ft (Sayyad). DCS weapon
files take meters: multiply NM by 1,852 and feet by 0.3048. Point each launcher at
its missile.

**If Phase B is too hard,** stop after Phase A. Record the real Phase A ranges in design note
§1 and in `pydcs_extensions/iranairdefensepack/iranairdefensepack.py` (the `threat_range` and
`air_weapon_dist` values), so Retribution's threat rings match what the sites actually do.

### 5. Prove the ids and numbers match (20 min)

1. Run the pydcs export with the mod installed. The runbook is the header of
   `tools/verify_mod_export.py`; read its heavy-mod gotcha before launching DCS.
2. `python tools\verify_mod_export.py <export folder> --extension iranairdefensepack --markdown`
3. It compares all nine `IRAD_` units field for field. Fix the side that is wrong.

### 6. Retribution check (30 min)

```powershell
.venv\Scripts\python.exe -m pytest tests/retlab/test_iran_air_defense_pack.py tests/armedforces tests/retlab/test_faction_mod_presets.py -q
```

Then: New Game → Mods page → tick **RetLab Iran Air Defense Pack (v0.1+)** and CurrentHill Iran
→ red faction `[CH] Iran 2020`. Generate a turn and find a 3rd Khordad and a Bavar-373 site on
the map.

### 7. Fly row B148 (30–45 min)

`docs/dev/retlab-ingame-pass-checklist.md`, search `^### B148 `. It has the pass criteria and
fail signatures. If a launcher model faces backwards, add `reversed_heading: true` to its
`resources/units/ground_units/IRAD_*.yaml` (the Buk TELAR needs it in vanilla).

### 8. Commit and report

- Repo changes (any id, range or `reversed_heading` fix): commit on the branch above, push.
  Update design note §1 and the status line of both notes.
- The mod files: **ask the DM before committing them to the repo.** The question is whether
  they go in a `mods/` folder here (only if rule 4 is clean) or stay on the PC.
- Report back to the DM in five lines or fewer:
  1. Phase A done or not
  2. Phase B done or not
  3. Any id or number you changed, and why
  4. The B148 result: pass, partial or fail
  5. The one thing still broken, if any

## Not in scope

15th Khordad and an Iran 2026 faction. They are listed in design note §5.
