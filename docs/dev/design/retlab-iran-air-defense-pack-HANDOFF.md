# HANDOFF — build the RetLab Iran Air Defense Pack (3rd Khordad + Bavar-373)

**For:** a local agent on the DM's Windows PC, with DCS installed and the mod folders readable.
**From:** a cloud session (2026-09-25/26) that had no DCS. It built the Retribution side and
all eleven 3D models as scripts. You bake and export the models, build the DCS mod, and
fly-check it.
**Read first:** [`retlab-iran-air-defense-pack-notes.md`](retlab-iran-air-defense-pack-notes.md)
— the unit contract (§1), the research and best-estimate numbers (§3), the models (§4).

## Who has what

| Thing | Where it lives | Done? |
|---|---|---|
| Retribution side (unit types, layouts, Skynet, factions, toggle, tests) | the RetLab repo, branch `claude/iran-dcs-asset-priority-4w0920` (PR #1083) | **Done** |
| 3D models (Blender scripts, all 11 baked) | private repo `BradySox/RetLab-Iran-Air-Defense`, `Source/models/` | **Done 2026-09-25** (step 3b) |
| The DCS mod (vehicles, radars, sensors, exported shapes) | the same private repo; its working copy is `<Saved Games>\DCS\Mods\tech\RetLab Iran Air Defense\` | **v0.1 built, not yet loaded in DCS** |
| Research numbers | design note §3 | Done |

The DCS install is `E:\DCS World`. The mod goes under **Saved Games**, not the install.

**The mod is its own pack (DM call 2026-09-25),** like HDS and CurrentHill, in a private repo;
it is not publicly downloadable. Mod files never go in this repo, which answers step 8's
question. Only the type-id contract crosses between the two.

### Done in the 2026-09-25 local session

- Step 3b: the PC had no exporter. ED's Blender exporter supports Blender 4.2, 4.5 and
  5.1 LTS, not 5.0, so all eleven models were rebuilt and baked in 5.1.2 and exported with
  the pack's `Source/models/export_edm.py`. It converts materials, marks connectors and binds
  arguments; the exporter reads frame F as argument F/100 - 1, so the scripts' 0-100 frames are
  resampled at export. The argument table is in the pack's model README.
- Step 3, written but not yet run in DCS: all twelve units, own radar sensors at the §1
  ranges, vanilla 5V55 and 9M38M1 missiles, vanilla wrecks, encyclopedia entries.
- Not done: the Phase A check in DCS (start at step 3's *Phase A check*), step 4, steps 5-7.

## Hard rules

1. **The twelve type ids in design note §1 are fixed.** Your `Database` lua must use them
   character for character. If one must change, change it in the repo in the same commit
   (the pydcs extension, the unit yaml filename, the layouts, Skynet, `faction.py`, the test).
2. **Never call `enableEmission`** in anything you write (a hard constraint in `CLAUDE.md`).
3. **No Retribution Lua plugin may name an `IRAD_` unit.** Mod awareness stays in Python.
4. **Licence check before copying.** Read the licence of any mod you use as a template (High
   Digit SAMs Ultimate Compilation, CurrentHill). Copying structure is fine; copying files is
   fine only if its licence allows it. If unclear, write the file fresh and say so.
5. **Never hand-edit a `.blend` the scripts own.** Change the `.py` and rebuild (the model
   README has the command). A hand edit is lost on the next rebuild.
6. Commit messages and docs: plain style, no paid-campaign names (see `CLAUDE.md`).

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
   names, the weapon names each launcher fires, and the **animation argument numbers** for
   launcher elevation, turret or antenna rotation, and mast deploy. Step 3b needs them.
2. In `<Saved Games>\DCS\Mods\tech\`, open the High Digit SAMs Ultimate Compilation folder.
   Its `entry.lua` and `Database\*.lua` are the working example of a SAM mod that defines
   its own vehicles **and** its own missiles. Read its licence (rule 4).
3. Write down the shape names you will borrow (step 3 table) until a model is exported.

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
| `IRAD_Bavar373_TELAR` | S-300PS 5P85D | 4 vertical canisters **and** its own radar, 65 NM, like the S-300V 9A83 | vanilla 5V55 |
| `IRAD_MatlaUlFajr_EWR` | vanilla 1L13 | early-warning radar, 135 NM | — |
| `IRAD_Rasool_Comms` | vanilla ZIL-131 KUNG | no weapons, no radar; a comms van | — |

Display names come from design note §1, exactly.

**Sounds:** copy each unit's sound entries from the same vanilla unit in the behaviour column.
The Matla ul-Fajr and Rasool take a truck's (the 1L13 is a static site with no engine). Launch
sounds come with the missile definition.

**Wrecks:** the models have no destroyed shape. Point each unit's destroyed shape at the
vanilla unit it borrows from. Our own wrecks come after v1 works (DM call 2026-09-26).

**Phase A check:** in the Mission Editor, place one of each under Iran. Every unit appears,
and `dcs.log` has no error naming `IRAD_`. Then place a 3rd Khordad site (SR + TELAR + 2 TELs)
and a Bavar-373 site (both SRs, CP, STR, 2 LNs), put an AI F-16 on a path through each, and run
it. Each site should engage.

### 3b. Export our own 3D models (30 min per model once the exporter works)

1. Find out whether this PC has a DCS EDM exporter for Blender or 3ds Max. **If it has
   neither, stop here and tell the DM** — nothing else in this step can happen without one.
   The `.blend` files are Blender 5.0. **Check which Blender versions the exporter supports.**
   If it needs an older Blender, a 5.0 file may not open there: rebuild the model in that
   version from its `.py` (the model README has the command), or tell the DM.
2. **Rebuild all eleven models** with the loop in the pack's `Source/models/README.md`,
   section *Rebuild* (a few minutes each). Only four are baked in the repo, and only the
   command post has the wheel animations. Check each preview PNG against the renders in
   `renders/`.
3. Read the same README, section *What the exporter needs to know*. It names every
   animated empty and what it means.
4. For each row below: open the `.blend`, export it to `.edm` into the mod's `Shapes`
   folder, copy its texture (if any) into the mod's `Textures` folder, bind the empties to the
   argument numbers you wrote down in step 2, and point the unit's `Database` lua at the new
   shape instead of the borrowed one.

| Model file | Unit(s) | Texture | Empties to bind (vanilla argument to copy) |
|---|---|---|---|
| `IRAD_Bavar373_LN.blend` | `IRAD_Bavar373_LN`, `IRAD_Bavar373_LN_4B` | `IRAD_Bavar373_LN_camo.png` | `arg_launcher_elevation` + both rams (5P85 elevation) |
| `IRAD_Bavar373_TELAR.blend` | `IRAD_Bavar373_TELAR` | `IRAD_Bavar373_TELAR_camo.png` | `arg_launcher_elevation` + ram (5P85 elevation); `arg_mast_extend` (a deploy argument); `arg_antenna_azimuth` (radar rotation) |
| `IRAD_Bavar373_STR.blend` | `IRAD_Bavar373_STR` | `IRAD_Bavar373_STR_camo.png` | `arg_antenna_fold` (40B6M deploy); `arg_antenna_azimuth` (40B6M rotation) |
| `IRAD_Hafez_SR.blend` | `IRAD_Hafez_SR` | `IRAD_Hafez_SR_camo.png` | `arg_antenna_fold`; `arg_antenna_azimuth` (40B6MD rotation) |
| `IRAD_Meraj4_SR.blend` | `IRAD_Meraj4_SR` | none (flat khaki) | `arg_antenna_azimuth` (64H6E rotation) |
| `IRAD_Bavar373_CP.blend` | `IRAD_Bavar373_CP` | `IRAD_Bavar373_CP_camo.png` | none |
| `IRAD_MatlaUlFajr_EWR.blend` | `IRAD_MatlaUlFajr_EWR` | `IRAD_MatlaUlFajr_EWR_camo.png` | `arg_mast_extend`; `arg_antenna_azimuth` (1L13 rotation) |
| `IRAD_Rasool_Comms.blend` | `IRAD_Rasool_Comms` | none (flat paint) | `arg_mast_extend` |
| `IRAD_3Khordad_TELAR.blend` | `IRAD_3Khordad_TELAR` | `IRAD_3Khordad_TELAR_camo.png` | `arg_turret_azimuth` (9A310 turret); `arg_launcher_elevation` + ram (9A310 elevation) |
| `IRAD_AlamAlHoda_TEL.blend` | `IRAD_AlamAlHoda_TEL` | `IRAD_AlamAlHoda_TEL_camo.png` | `arg_turret_azimuth`; `arg_launcher_elevation` + ram (the Buk launcher's) |
| `IRAD_Bashir_SR.blend` | `IRAD_Bashir_SR` | `IRAD_Bashir_SR_camo.png` | `arg_antenna_azimuth` (9S18M1 rotation) |

Every model also has `wheel_spin_<n>` empties (bind to the vanilla truck's wheel-rotation
argument) and `wheel_steer_<n>` on the front axles (its steering argument). Every animation
runs over frames 0–100. `LAUNCH_n` empties are the missile launch points (local +Z out of
the muzzle); `collision_shell` is the hit box and is not rendered.

**Model check,** per model, in the Model Viewer: every argument moves the right part without
clipping; the wheels turn and the front axles steer; launchers fire from each `LAUNCH_n`;
the texture shows (not pink or white).

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
3. It compares all twelve `IRAD_` units field for field. Fix the side that is wrong.

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
- Report back to the DM in six lines or fewer:
  1. Phase A done or not
  2. Models exported: which, and any that failed
  3. Phase B done or not
  4. Any id or number you changed, and why
  5. The B148 result: pass, partial or fail
  6. The one thing still broken, if any

## Not in scope

15th Khordad, an Iran 2026 faction, far-view LODs, and our own wreck models (after v1). See
design note §5.
