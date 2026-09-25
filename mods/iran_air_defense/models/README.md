# RetLab Iran Air Defense Pack — 3D models

Blender source for the pack's vehicles. Built by script, so every model can be regenerated
and every change is reviewable as text.

| File | What it is |
|---|---|
| `irad_kit.py` | Shared parts: the heavy-truck chassis, wheels, hoses, stencils, materials |
| `bavar_ln.py` | Bavar-373 TEL (`IRAD_Bavar373_LN`, also used for `IRAD_Bavar373_LN_4B`) |
| `IRAD_Bavar373_LN.blend` | The built model, ~30k triangles |
| `renders/` | Preview images |

## Status

| Model | Built |
|---|---|
| Bavar-373 TEL | Yes, 2026-09-25 |
| 3rd Khordad TELAR, Alam al-Hoda TEL, Bashir SR, Meraj-4 SR, Hafez AR, Bavar-373 STR, Bavar-373 CP | Not yet |

Shapes come from published dimensions and descriptions, not photos.

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
| `ln_ram_barrel_pivot±1`, `ln_ram_rod_slide±1` | Erector rams, keyed on the same 0–100 frames. Bind them to the same argument |
| `LAUNCH_1` … `LAUNCH_4` | Missile launch points; each empty's local +Z points out of the muzzle |
| `collision_shell` | Hit box; not rendered |

Materials are flat colours (`irad_*`). There are no textures or far-view LODs yet.
