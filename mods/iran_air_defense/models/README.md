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
| `matla.py` | Matla ul-Fajr EWR (`IRAD_MatlaUlFajr_EWR`): a boom of eight Yagi pairs on a telescopic mast at the rear of a long corrugated shelter on a semi-trailer, a generator box on the neck; woodland camouflage |
| `rasool.py` | Rasool comms shelter (`IRAD_Rasool_Comms`): a white-cab 4x4 with a pale sage shelter, roof omni antennas and a telescopic rear mast; flat paint |
| `khordad.py` | 3rd Khordad TELAR (`IRAD_3Khordad_TELAR`): a 6x6 with a raked wedge cab and an equipment body, a turret with a wedge radar over the cab and three Taer-2 missiles on an elevating cradle; band camouflage |
| `alam.py` | Alam al-Hoda TEL (`IRAD_AlamAlHoda_TEL`): the 3rd Khordad truck with no radar, three Taer-2 lying on a truss launcher over one long housing; grey band camouflage. Imports `khordad.py` |
| `bashir.py` | Bashir search radar (`IRAD_Bashir_SR`): a green 6x6 with a shelter and whip mast, a lattice tower at the rear carrying a planar array of thirty element rows; deployed only. Imports `khordad.py` for the stripes |
| `bavar_str.py` | Bavar-373 engagement radar (`IRAD_Bavar373_STR`): an 8x8 with a tilted planar array on a turntable and an equipment shelter aft |
| `IRAD_*.blend` | The built models, textured |
| `textures/IRAD_*_camo.png` | Each model's camouflage baked to one 4096x4096 texture shared by its painted parts |
| `compare_views.py` | Renders the TEL views used to check it against the references |
| `renders/` | Preview images |

## Status

| Model | Built | Triangles |
|---|---|---|
| Bavar-373 TEL | 2026-09-25, matched to a Tasnim photograph | ~30.5k |
| Bavar-373 STR | 2026-09-25, matched to a photograph and two renders | ~33.7k |
| Meraj-4 SR | 2026-09-26, matched to two photographs and a render | ~29.8k |
| Hafez AR | 2026-09-26, matched to an Iranian infographic render | ~31.8k |
| Bavar-373-II TELAR | 2026-09-26, matched to a photograph | ~46.5k |
| Bavar-373 CP | 2026-09-26, matched to a parade photograph | ~22.0k |
| Matla ul-Fajr EWR | 2026-09-26, matched to a photograph | ~28.8k |
| Rasool comms shelter | 2026-09-26, matched to a photograph | ~18.3k |
| 3rd Khordad TELAR | 2026-09-26, matched to two photographs | ~30.5k |
| Alam al-Hoda TEL | 2026-09-26, matched to a parade photograph | ~29.8k |
| Bashir SR | 2026-09-26, matched to two photographs and a render | ~21.9k |

Proportions are matched to photographs and reference renders the DM supplied. A photograph
wins where they disagree. None are stored here (third-party images).

## Rebuild

**Rebuild all eleven before exporting.** Only four `.blend` files here are baked (TEL, TELAR,
Hafez, command post), and only the command post has the wheel animations; every script now
adds them. With Blender 5.0 on the PATH, from this folder in PowerShell:

```
foreach ($m in 'bavar_ln','bavar_str','hafez','meraj','bavar_telar','bavar_cp','matla','rasool','khordad','alam','bashir') {
  blender --background --python "$m.py" -- --bake (Get-Location).Path
}
```

Each script writes `<unit>.blend`, its texture in `textures/`, and preview PNGs. With
`--bake` a model takes a few minutes on a desktop; without it, a quick shape check. The
Meraj-4 and Rasool have flat paint and skip the bake. `hafez.py` imports `bavar_str.py`,
and `alam.py` and `bashir.py` import `khordad.py`, so keep the folder together. The
`bpy` 5.0 wheel on Python 3.11 works too: `python bavar_str.py --bake <this folder>`.

## What the exporter needs to know

| Blender object | Meaning in DCS |
|---|---|
| `arg_launcher_elevation` (TEL, TELAR) | Empty; X rotation 0° travel to 90° erect over frames 0–100. Bind it to the launcher-elevation argument |
| `arg_launcher_elevation` (3rd Khordad, Alam al-Hoda) | Empty; X rotation from the travel rest (15° on the 3rd Khordad, 3° on the Alam al-Hoda) to 65° over frames 0–100, the ram keyed with it |
| `arg_turret_azimuth` (3rd Khordad, Alam al-Hoda) | Empty; frames 0–100 are one full turn of the turret, radar and launcher together |
| `ln_ram_barrel_pivot±1`, `ln_ram_rod_slide±1` (TEL) | The two erector rams, keyed on the same 0–100 frames. Bind them to the same argument |
| `arg_mast_extend` (TELAR, Matla ul-Fajr, Rasool) | `mast_sec0_slide` and up (three sections; four on the Rasool): frames 0–100 raise the mast from nested to full height, 24–26 ft of travel. Bind to a deploy argument |
| `LAUNCH_1` … `LAUNCH_4` (TEL, TELAR; `LAUNCH_1`–`3` on the 3rd Khordad and Alam al-Hoda) | Missile launch points; each empty's local +Z points out of the muzzle |
| `arg_antenna_fold` (STR, Hafez) | Empty; frames 0–100 raise the array from stowed face-down over the cab to erect, 25° back |
| `arg_antenna_azimuth` (STR, Hafez, Meraj-4, Bashir, TELAR dish head, Matla ul-Fajr boom) | Empty; frames 0–100 are one full turn of the turret. Bind it to the radar's search/track rotation argument |
| `wheel_spin_<n>` (every model) | Empty per wheel; frames 0–100 are one forward turn. Bind to the wheel-rotation argument |
| `wheel_steer_<n>` (truck front axles; both front axles on the 8x8s) | Empty; frame 0 full left, 50 straight ahead, 100 full right. Bind to the steering argument |
| `collision_shell` | Hit box; not rendered |

Paint: sand, soft orange clouds and black three-bladed splinter marks (the 3rd Khordad: sand with brown and olive bands; the Alam al-Hoda: grey with brown bands; the Bashir: green truck, tan tower and array with upright black stripes), baked on
smart-UV-projected parts (about 15–18 minutes on CPU per model). Each `.blend` reads its
texture by a relative path. DCS takes PNG; convert to DDS if you want mipmaps. Other
materials are flat colours (`irad_*`); the Meraj-4 is plain khaki throughout, so it needs no bake. No
far-view LODs and no destroyed shapes yet (v1 borrows the vanilla wrecks).
