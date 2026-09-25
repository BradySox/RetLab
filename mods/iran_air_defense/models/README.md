# RetLab Iran Air Defense Pack — 3D models

Blender source for the pack's vehicles. Built by script, so every model can be regenerated
and every change is reviewable as text.

| File | What it is |
|---|---|
| `irad_kit.py` | Shared parts: the heavy-truck chassis, wheels, hoses, stencils, materials |
| `bavar_ln.py` | Bavar-373 TEL (`IRAD_Bavar373_LN`, also used for `IRAD_Bavar373_LN_4B`): two ribbed canister towers on a lattice erector, one 3-stage ram |
| `IRAD_Bavar373_LN.blend` | The built model, ~32k triangles |
| `renders/` | Preview images |

## Status

| Model | Built |
|---|---|
| Bavar-373 TEL | Yes, 2026-09-25; matched to reference renders |
| 3rd Khordad TELAR, Alam al-Hoda TEL, Bashir SR, Meraj-4 SR, Hafez AR, Bavar-373 STR, Bavar-373 CP | Not yet |

Proportions are matched to two reference renders the DM supplied: a sim-model render of the
Zafar 8x8 radar truck, and an Iranian press infographic of the Bavar-373 complex. Both are
3D renders, not photographs. They are not stored here (third-party artwork).

## Rebuild

With Blender 5.0 installed:

```
blender --background --python bavar_ln.py -- <this folder>
```

Or with the `bpy` 5.0 wheel on Python 3.11: `python bavar_ln.py <this folder>`.

## What the exporter needs to know

| Blender object | Meaning in DCS |
|---|---|
| `arg_launcher_elevation` | Empty; X rotation 0° travel to 90° erect over frames 0–100. Bind it to the launcher-elevation argument |
| `ln_ram_barrel_pivot`, `ln_ram_stage1_slide`, `ln_ram_stage2_slide` | The telescopic erector ram, keyed on the same 0–100 frames. Bind them to the same argument |
| `LAUNCH_1` … `LAUNCH_4` | Missile launch points; each empty's local +Z points out of the muzzle |
| `collision_shell` | Hit box; not rendered |

Paint is `irad_camo`, a procedural three-tone desert camouflage on world position; it must be
baked to a UV texture for DCS. Other materials are flat colours (`irad_*`). No far-view LODs yet.
