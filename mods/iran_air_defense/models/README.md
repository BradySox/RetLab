# RetLab Iran Air Defense Pack — 3D models

Blender source for the pack's vehicles. Built by script, so every model can be regenerated
and every change is reviewable as text.

| File | What it is |
|---|---|
| `irad_kit.py` | Shared parts: the Iranian heavy-truck chassis and cab, wheels, fans, hoses, the camouflage and its bake |
| `bavar_ln.py` | Bavar-373 TEL (`IRAD_Bavar373_LN`, also used for `IRAD_Bavar373_LN_4B`): an 8x8 with an AC platform over the cab, two ribbed canister towers, a grid erector and two rams |
| `bavar_str.py` | Bavar-373 engagement radar (`IRAD_Bavar373_STR`): an 8x8 with a tilted planar array on a turntable and an equipment shelter aft |
| `IRAD_*.blend` | The built models, textured |
| `textures/IRAD_*_camo.png` | Each model's camouflage baked to one 4096x4096 texture shared by its painted parts |
| `compare_views.py` | Renders the TEL views used to check it against the references |
| `renders/` | Preview images |

## Status

| Model | Built | Triangles |
|---|---|---|
| Bavar-373 TEL | 2026-09-25, matched to a Tasnim photograph | ~30.5k |
| Bavar-373 STR | 2026-09-25, matched to a photograph and two renders | ~19.7k |
| 3rd Khordad TELAR, Alam al-Hoda TEL, Bashir SR, Meraj-4 SR, Hafez AR, Bavar-373 CP | Not yet | |

Proportions are matched to photographs and reference renders the DM supplied. A photograph
wins where they disagree. None are stored here (third-party images).

## Rebuild

With Blender 5.0 installed:

```
blender --background --python bavar_ln.py -- <this folder>
blender --background --python bavar_str.py -- --bake <this folder>
```

Or with the `bpy` 5.0 wheel on Python 3.11: `python bavar_str.py --bake <this folder>`.
`bavar_ln.py` always bakes; `bavar_str.py` bakes only with `--bake` (without it, a quick
shape check in about a minute).

## What the exporter needs to know

| Blender object | Meaning in DCS |
|---|---|
| `arg_launcher_elevation` (TEL) | Empty; X rotation 0° travel to 90° erect over frames 0–100. Bind it to the launcher-elevation argument |
| `ln_ram_barrel_pivot±1`, `ln_ram_rod_slide±1` (TEL) | The two erector rams, keyed on the same 0–100 frames. Bind them to the same argument |
| `LAUNCH_1` … `LAUNCH_4` (TEL) | Missile launch points; each empty's local +Z points out of the muzzle |
| `arg_antenna_fold` (STR) | Empty; frames 0–100 fold the array from stowed flat over the shelter to erect, 20° back |
| `arg_antenna_azimuth` (STR) | Empty; frames 0–100 are one full turn of the turret. Bind it to the radar's search/track rotation argument |
| `collision_shell` | Hit box; not rendered |

Paint: sand, soft orange clouds and black three-bladed splinter marks, baked on
smart-UV-projected parts (about 15–18 minutes on CPU per model). Each `.blend` reads its
texture by a relative path. DCS takes PNG; convert to DDS if you want mipmaps. Other
materials are flat colours (`irad_*`). No far-view LODs yet.
