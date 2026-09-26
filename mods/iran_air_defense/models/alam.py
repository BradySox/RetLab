"""Alam al-Hoda TEL (IRAD_AlamAlHoda_TEL), matched to a parade photograph: the 3rd
Khordad's 6x6 with no radar, three Taer-2 lying on a truss launcher over one long
housing. Grey band camouflage. Built from khordad.py.

arg_turret_azimuth: frames 0-100, one full turn of the turret.
arg_launcher_elevation: frames 0-100, 3 deg travel rest to 65 deg.
"""

import sys

import bpy

sys.path.insert(0, sys.argv[-1])
import khordad  # noqa: E402
from irad_kit import bake_camo, finalize, animate_wheels, render  # noqa: E402

khordad.NAME = "IRAD_AlamAlHoda_TEL"
khordad.RADAR = False
khordad.EL0 = 3
khordad.PALETTE = dict(
    base=(0.5, 0.5, 0.45),
    brown=(0.2, 0.12, 0.06),
    olive=(0.16, 0.17, 0.13),
    black=(0.03, 0.03, 0.03),
)

if __name__ == "__main__":
    out = sys.argv[-1]
    name = khordad.NAME
    tur, piv = khordad.build()
    finalize(name)
    animate_wheels()
    bpy.context.scene.frame_set(0)
    if "--bake" in sys.argv:
        bake_camo(out, name)
    bpy.ops.wm.save_as_mainfile(filepath=f"{out}/{name}.blend")
    tur.animation_data_clear()
    tur.rotation_euler = (0, 0, 0)
    scn = bpy.context.scene
    for frame, view, kw in (
        (
            0,
            "photo",
            dict(target=(0, 0.0, 2.3), dist=14, az=-80, elev=3, res=(1100, 727)),
        ),
        (50, "raised", dict(target=(0, 0.0, 2.8), dist=15, az=40, elev=8)),
    ):
        scn.frame_set(frame)
        render(f"{out}/{name}_{view}.png", **kw)
