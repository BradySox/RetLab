# RetLab Iran Air Defense Pack — 3D models

Blender source for the pack's vehicles. Built by script, so every model can be regenerated
and every change is reviewable as text.

| File | What it is |
|---|---|
| `irad_kit.py` | Shared parts: the heavy-truck chassis, wheels, hoses, stencils, materials |
| `bavar_ln.py` | Bavar-373 TEL (`IRAD_Bavar373_LN`, also used for `IRAD_Bavar373_LN_4B`): an 8x8 with an AC platform over the cab, two ribbed canister towers, a grid erector and two rams |
| `IRAD_Bavar373_LN.blend` | The built model, ~31.5k triangles |
| `compare_views.py` | Renders the three views used to check the model against the references |
| `renders/` | Preview images |

## Status

| Model | Built |
|---|---|
| Bavar-373 TEL | Yes, 2026-09-25; matched to reference renders |
| 3rd Khordad TELAR, Alam al-Hoda TEL, Bashir SR, Meraj-4 SR, Hafez AR, Bavar-373 STR, Bavar-373 CP | Not yet |

Proportions are matched to a Tasnim photograph of the Bavar-373 TEL and to three reference
renders the DM supplied. The photograph wins where they disagree. None are stored here
(third-party images).

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
| `ln_ram_barrel_pivot±1`, `ln_ram_rod_slide±1` | The two erector rams, keyed on the same 0–100 frames. Bind them to the same argument |
| `LAUNCH_1` … `LAUNCH_4` | Missile launch points; each empty's local +Z points out of the muzzle |
| `collision_shell` | Hit box; not rendered |

Paint is `irad_camo`: sand, soft orange clouds and black three-bladed splinter marks, procedural on world position; it must be
baked to a UV texture for DCS. Other materials are flat colours (`irad_*`). No far-view LODs yet.
