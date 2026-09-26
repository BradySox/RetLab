"""Hafez search radar (IRAD_Hafez_SR), matched to an Iranian infographic render of the
Bavar-373 complex: a tall flat panel spinning on a drum turret, the HQ-22 search-radar
layout, on the engagement radar's 8x8 and shelter (built by bavar_str with this
module's head and panel swapped in).

arg_antenna_fold: frames 0-100, stowed face-down over the cab to erect, 12 deg back.
arg_antenna_azimuth: frames 0-100, one full turn (bind to the search rotation arg).
"""

import math
import sys

import bpy

sys.path.insert(0, sys.argv[-1])
from irad_kit import *  # noqa: E402,F403
import bavar_str  # noqa: E402

PW, PH, PD = 2.6, 3.4, 0.4


def panel(parent):
    """A tall thin array: raised border, a face of six row tiles, bolted edge frames,
    back ribs with a truss, a feed box."""
    face_y = 0.05
    box("hz_body", (PW, PD, PH), (0, face_y - PD / 2, PH / 2), PAINT(), parent, 0.04)
    for k, (w, h, x, z) in enumerate(
        (
            (PW, 0.12, 0, PH - 0.06),
            (PW, 0.12, 0, 0.06),
            (0.12, PH, PW / 2 - 0.06, PH / 2),
            (0.12, PH, -PW / 2 + 0.06, PH / 2),
        )
    ):
        box(f"hz_border{k}", (w, 0.07, h), (x, face_y + 0.02, z), PAINT(), parent, 0.01)
    fw, fh = PW - 0.3, PH - 0.3
    box("hz_face", (fw, 0.03, fh), (0, face_y - 0.01, PH / 2), PAINT(), parent, 0.01)
    for k in range(1, 6):
        box(
            f"hz_row{k}",
            (fw, 0.04, 0.02),
            (0, face_y + 0.005, 0.15 + k * fh / 6),
            DARK(),
            parent,
            0,
        )
    box("hz_col", (0.02, 0.04, fh), (0, face_y + 0.005, PH / 2), DARK(), parent, 0)
    for s in (-1, 1):
        box(
            f"hz_edge{s}",
            (0.1, PD + 0.06, PH),
            (s * (PW / 2 + 0.03), face_y - PD / 2, PH / 2),
            PAINT(),
            parent,
            0.01,
        )
        for k in range(9):
            cyl(
                f"hz_bolt{s}{k}",
                0.018,
                0.03,
                (s * (PW / 2 + 0.085), face_y - 0.08, 0.2 + k * (PH - 0.4) / 8),
                (0, math.pi / 2, 0),
                METAL(),
                parent,
                6,
            )
    box(
        "hz_bottomlip",
        (PW, PD + 0.12, 0.14),
        (0, face_y - PD / 2, 0.07),
        PAINT(),
        parent,
        0.02,
    )
    back_y = face_y - PD - 0.04
    for x in (-0.8, 0.0, 0.8):
        box(
            f"hz_backrib{x}",
            (0.1, 0.08, PH * 0.9),
            (x, back_y, PH * 0.45),
            PAINT(),
            parent,
            0.01,
        )
    for k in range(3):
        for s in (-1, 1):
            strut(
                f"hz_backdiag{k}{s}",
                (s * 0.8, back_y - 0.03, 0.3 + k * 1.2),
                (0, back_y - 0.03, 1.2 + k * 1.2),
                0.03,
                PAINT(),
                parent,
                6,
            )
    box("hz_feedbox", (0.7, 0.3, 0.55), (0, back_y - 0.2, 0.6), PAINT(), parent, 0.02)
    grille("hz_feedgrille", (0, back_y - 0.35, 0.6), "y", -1, 0.5, 0.35, parent, 5)


def head(az):
    """The drum turret: a drum with a cap ring, two side equipment boxes with doors,
    yoke cheeks at the front edge. Returns the fold hinge (y, z)."""
    cyl("hz_drum", 0.95, 1.6, (0, 0, 0.8), (0, 0, 0), PAINT(), az, 48)
    cyl("hz_drumcap", 0.9, 0.08, (0, 0, 1.62), (0, 0, 0), PAINT(), az, 48)
    cyl("hz_drumband", 0.97, 0.06, (0, 0, 0.3), (0, 0, 0), DARK(), az, 48)
    door("hz_drumdoor", (0, -0.94, 0.75), "y", -1, 0.6, 1.1, az)
    for s in (-1, 1):
        box(
            f"hz_drumbox{s}",
            (0.45, 0.85, 1.0),
            (s * 0.95, -0.1, 0.6),
            PAINT(),
            az,
            0.04,
        )
        door(f"hz_drumboxdoor{s}", (s * 1.175, -0.1, 0.6), "x", s, 0.6, 0.75, az)
        box(
            f"hz_drumboxroof{s}",
            (0.5, 0.9, 0.05),
            (s * 0.95, -0.1, 1.12),
            DARK(),
            az,
            0,
        )
    # the hinge sits high enough that the stowed panel clears the cab roof and beacons
    hinge_y, hinge_z = 0.45, 1.95
    for s in (-1, 1):
        box(
            f"hz_cheek{s}",
            (0.14, 0.5, 0.5),
            (s * 0.95, hinge_y, hinge_z - 0.2),
            PAINT(),
            az,
            0.02,
        )
        strut(
            f"hz_brace{s}",
            (s * 0.6, -0.3, 1.62),
            (s * 0.95, hinge_y, hinge_z),
            0.04,
            METAL(),
            az,
        )
        cyl(
            f"hz_hingepin{s}",
            0.07,
            0.22,
            (s * 0.95, hinge_y, hinge_z),
            (0, math.pi / 2, 0),
            METAL(),
            az,
            12,
        )
        hose(
            f"hz_cable{s}",
            [
                (s * 0.4, -0.3, 1.65),
                (s * 0.7, 0.1, 1.8),
                (s * 0.85, hinge_y - 0.1, hinge_z - 0.05),
            ],
            0.03,
            DARK(),
            az,
        )
    return hinge_y, hinge_z


bavar_str.NAME = "IRAD_Hafez_SR"
bavar_str.TILT = math.radians(12)
bavar_str.panel = panel
bavar_str.head = head
bavar_str.PLINTH_H = 0.3

if __name__ == "__main__":
    out = sys.argv[-1]
    az = bavar_str.build()
    finalize(bavar_str.NAME)
    bpy.context.scene.frame_set(0)
    if "--bake" in sys.argv:
        bake_camo(out, bavar_str.NAME)
    bpy.ops.wm.save_as_mainfile(filepath=f"{out}/{bavar_str.NAME}.blend")
    az.animation_data_clear()
    az.rotation_euler = (0, 0, 0)
    scn = bpy.context.scene
    views = (
        (0, "stowed", dict(target=(0, 1.0, 2.4), dist=15, az=-55, elev=10)),
        (100, "erect", dict(target=(0, 0.5, 3.4), dist=17, az=-50, elev=8)),
        (100, "infographic", dict(target=(0, 0.0, 3.4), dist=19, az=-40, elev=20)),
    )
    for frame, name, kw in views:
        scn.frame_set(frame)
        render(f"{out}/{bavar_str.NAME}_{name}.png", **kw)
