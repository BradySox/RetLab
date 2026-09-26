# RetLab Iran Air Defense Pack — 3D models

Blender source for the pack's vehicles. Built by script, so every model can be regenerated
and every change is reviewable as text.

| File | What it is |
|---|---|
| `irad_kit.py` | Shared parts: the Iranian heavy-truck chassis and cab, wheels, fans, hoses, the camouflage and its bake |
| `bavar_ln.py` | Bavar-373 TEL (`IRAD_Bavar373_LN`, also used for `IRAD_Bavar373_LN_4B`): an 8x8 with an AC platform over the cab, two ribbed canister towers, a grid erector and two rams |
| `meraj.py` | Meraj-4 search radar (`IRAD_Meraj4_SR`): a slatted planar array with an IFF column on a tri-axle semi-trailer, deployed on four jacks; plain khaki |
| `hafez.py` | Hafez search radar (`IRAD_Hafez_SR`): a tall flat panel spinning on a drum turret, on the engagement radar's 8x8 and shelter |
| `bavar_telar.py` | Bavar-373-II TELAR (`IRAD_Bavar373_TELAR`): the TEL's 8x8 and towers plus a telescopic radar mast with a dish, an hourglass erector with one ram, a railed walkway |
| `bavar_cp.py` | Bavar-373 command post (`IRAD_Bavar373_CP`): a 6x6 with one long shelter, a door forward, an AC unit and rolled net aft; no moving parts |
| `matla.py` | Matla ul-Fajr EWR (`IRAD_MatlaUlFajr_EWR`): a boom of eight Yagi pairs on a telescopic mast at the rear of a long corrugated shelter on a semi-trailer; woodland camouflage |
| `rasool.py` | Rasool comms shelter (`IRAD_Rasool_Comms`): a white-cab 4x4 with an olive shelter, roof omni antennas and a telescopic rear mast; flat paint |
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
| Meraj-4 SR | 2026-09-26, matched to two photographs and a render | ~23.2k |
| Hafez AR | 2026-09-26, matched to an Iranian infographic render | ~19.8k |
| Bavar-373-II TELAR | 2026-09-26, matched to a photograph | ~26.4k |
| Bavar-373 CP | 2026-09-26, matched to a parade photograph | ~13.3k |
| Matla ul-Fajr EWR | 2026-09-26, matched to a photograph | ~16.8k |
| Rasool comms shelter | 2026-09-26, matched to a photograph | ~10.1k |
| 3rd Khordad TELAR, Alam al-Hoda TEL, Bashir SR | Not yet | |

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
| `arg_launcher_elevation` (TEL, TELAR) | Empty; X rotation 0° travel to 90° erect over frames 0–100. Bind it to the launcher-elevation argument |
| `ln_ram_barrel_pivot±1`, `ln_ram_rod_slide±1` (TEL) | The two erector rams, keyed on the same 0–100 frames. Bind them to the same argument |
| `arg_mast_extend` (TELAR, Matla ul-Fajr, Rasool) | `mast_sec0..2_slide`: frames 0–100 raise the mast from nested to full height, about 30 ft. Bind to a deploy argument |
| `LAUNCH_1` … `LAUNCH_4` (TEL, TELAR) | Missile launch points; each empty's local +Z points out of the muzzle |
| `arg_antenna_fold` (STR, Hafez) | Empty; frames 0–100 raise the array from stowed face-down over the cab to erect, 25° back |
| `arg_antenna_azimuth` (STR, Hafez, Meraj-4, TELAR dish head, Matla ul-Fajr boom) | Empty; frames 0–100 are one full turn of the turret. Bind it to the radar's search/track rotation argument |
| `collision_shell` | Hit box; not rendered |

Paint: sand, soft orange clouds and black three-bladed splinter marks, baked on
smart-UV-projected parts (about 15–18 minutes on CPU per model). Each `.blend` reads its
texture by a relative path. DCS takes PNG; convert to DDS if you want mipmaps. Other
materials are flat colours (`irad_*`); the Meraj-4 is plain khaki throughout, so it needs no bake. No
far-view LODs yet.
