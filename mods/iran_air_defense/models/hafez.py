"""Hafez search radar (IRAD_Hafez_SR), matched to an Iranian infographic render of the
Bavar-373 complex: a tall flat panel spinning on a drum turret, as the Pantsir's search
radar does at far smaller scale, on the same 8x8 and shelter as the engagement radar.

arg_antenna_fold: frames 0-100, stowed face-down over the cab to erect, 12 deg back.
arg_antenna_azimuth: frames 0-100, one full turn (bind to the search rotation arg).
"""

import math
import sys

import bpy

sys.path.insert(0, sys.argv[-1])
from irad_kit import *  # noqa: E402,F403

PW, PH, PD = 2.4, 3.9, 0.35  # panel width, height, depth
TILT = math.radians(12)
STEPS = 11


def panel(parent):
    """The array: a tall thin panel with row seams, an edge frame and back ribs."""
    face_y = 0.05
    box("hz_body", (PW, PD, PH), (0, face_y - PD / 2, PH / 2), PAINT(), parent, 0.04)
    for k in range(1, 6):
        box(
            f"hz_row{k}",
            (PW * 0.9, 0.03, 0.02),
            (0, face_y + 0.01, k * PH / 6),
            DARK(),
            parent,
            0,
        )
    box(
        "hz_col", (0.02, 0.03, PH * 0.95), (0, face_y + 0.01, PH / 2), DARK(), parent, 0
    )
    for s in (-1, 1):
        box(
            f"hz_edge{s}",
            (0.08, PD + 0.04, PH),
            (s * (PW / 2 - 0.02), face_y - PD / 2, PH / 2),
            PAINT(),
            parent,
            0.01,
        )
    box(
        "hz_bottomlip",
        (PW, PD + 0.1, 0.14),
        (0, face_y - PD / 2, 0.07),
        PAINT(),
        parent,
        0.02,
    )
    for x in (-0.7, 0.7):
        box(
            f"hz_backrib{x}",
            (0.1, 0.12, PH * 0.9),
            (x, face_y - PD - 0.05, PH * 0.45),
            PAINT(),
            parent,
            0.01,
        )


def build():
    reset()
    axles = [4.3, 2.85, -2.55, -4.0]
    root, dz, rear, cab_back = iran_truck(
        "IRAD_Hafez_SR", axles, 11.0, cab_len=2.3, wheel_r=0.72
    )
    dlen = cab_back - rear
    box(
        "hz_deck",
        (2.5, dlen, 0.16),
        (0, (cab_back + rear) / 2, dz + 0.06),
        DARK(),
        root,
        0.01,
    )
    for s in (-1, 1):
        box(
            f"hz_deckedge{s}",
            (0.08, dlen, 0.26),
            (s * 1.25, (cab_back + rear) / 2, dz + 0.03),
            PAINT(),
            root,
            0.01,
        )

    # generator behind the cab
    gy = cab_back - 0.55
    box("hz_gen", (2.2, 0.9, 1.35), (0, gy, dz + 0.8), PAINT(), root, 0.03)
    for s in (-1, 1):
        louvers(f"hz_genlouver{s}", (s * 1.1, gy, dz + 0.85), 0.6, 0.7, 6, s, root)
    cyl("hz_genexhaust", 0.06, 0.8, (0.8, gy, dz + 1.8), (0, 0, 0), METAL(), root, 12)

    # turret: plinth cabinets, bearing ring, rotating head with the fold hinge
    ty = 0.9
    box("hz_plinth", (2.3, 2.0, 1.0), (0, ty, dz + 0.58), PAINT(), root, 0.03)
    for s in (-1, 1):
        box(
            f"hz_sidecab{s}",
            (0.45, 1.3, 0.85),
            (s * 1.0, ty + 0.1, dz + 1.5),
            PAINT(),
            root,
            0.03,
        )
        box(
            f"hz_sidecabseam{s}",
            (0.02, 0.9, 0.6),
            (s * 1.23, ty + 0.1, dz + 1.5),
            DARK(),
            root,
            0,
        )
        box(
            f"hz_plinthdoor{s}",
            (0.02, 1.4, 0.7),
            (s * 1.16, ty, dz + 0.55),
            DARK(),
            root,
            0,
        )
    cyl("hz_ring", 0.85, 0.22, (0, ty, dz + 1.19), (0, 0, 0), METAL(), root, 36)
    az = empty("arg_antenna_azimuth", (0, ty, dz + 1.3), root)
    cyl("hz_drum", 0.95, 1.1, (0, 0, 0.55), (0, 0, 0), PAINT(), az, 40)
    cyl("hz_drumcap", 0.9, 0.08, (0, 0, 1.12), (0, 0, 0), PAINT(), az, 40)
    for s in (-1, 1):
        box(
            f"hz_drumbox{s}", (0.45, 0.8, 0.8), (s * 0.95, -0.1, 0.5), PAINT(), az, 0.04
        )
        box(
            f"hz_drumboxseam{s}",
            (0.02, 0.55, 0.55),
            (s * 1.18, -0.1, 0.5),
            DARK(),
            az,
            0,
        )
    hinge_y, hinge_z = 0.45, 1.3
    for s in (-1, 1):
        # yoke cheeks carrying the hinge, with an A-frame brace as photographed
        box(
            f"hz_cheek{s}",
            (0.14, 0.5, 0.55),
            (s * 0.95, hinge_y, 0.95),
            PAINT(),
            az,
            0.02,
        )
        strut(
            f"hz_brace{s}",
            (s * 0.6, 0.55, 0.9),
            (s * 0.95, hinge_y, hinge_z),
            0.05,
            METAL(),
            az,
        )
        cyl(
            f"hz_hingepin{s}",
            0.08,
            0.2,
            (s * 0.95, hinge_y, hinge_z),
            (0, math.pi / 2, 0),
            METAL(),
            az,
            14,
        )
    fold = empty("arg_antenna_fold", (0, hinge_y, hinge_z), az)
    panel(fold)

    # equipment shelter aft: doors, AC grilles on the rear face, ladder, roof rail
    sy0, sy1, sh = -0.3, rear + 0.35, 2.3
    scy = (sy0 + sy1) / 2
    box(
        "hz_shelter",
        (2.45, sy0 - sy1, sh),
        (0, scy, dz + 0.14 + sh / 2),
        PAINT(),
        root,
        0.04,
    )
    for s in (-1, 1):
        for k, (sz, off) in enumerate(
            (
                ((0.02, 0.9, 0.02), (0, 0.75)),
                ((0.02, 0.9, 0.02), (0, -0.75)),
                ((0.02, 0.02, 1.5), (0.45, 0)),
                ((0.02, 0.02, 1.5), (-0.45, 0)),
            )
        ):
            box(
                f"hz_doorseam{s}{k}",
                sz,
                (s * 1.232, scy + 0.9 + off[0], dz + 1.0 + off[1]),
                DARK(),
                root,
                0,
            )
        box(
            f"hz_acbox{s}",
            (0.4, 0.8, 0.9),
            (s * 1.4, scy - 1.0, dz + 1.25),
            PAINT(),
            root,
            0.02,
        )
        louvers(
            f"hz_aclouver{s}", (s * 1.6, scy - 1.0, dz + 1.25), 0.6, 0.7, 7, s, root
        )
    for k in range(2):
        box(
            f"hz_reargrille{k}",
            (0.8, 0.02, 1.3),
            (-0.5 + k * 1.0, sy1 - 0.005, dz + 1.0),
            DARK(),
            root,
            0,
        )
        for j in range(10):
            box(
                f"hz_reargrillebar{k}{j}",
                (0.8, 0.03, 0.025),
                (-0.5 + k * 1.0, sy1 - 0.02, dz + 0.4 + j * 0.13),
                PAINT(),
                root,
                0,
            )
    for rail in (-1, 1):
        strut(
            f"hz_ladrail{rail}",
            (1.3, sy1 + 0.9 + rail * 0.22, dz + 0.1),
            (1.75, sy1 + 0.9 + rail * 0.22, 0.05),
            0.025,
            METAL(),
            root,
        )
    for k in range(5):
        t = k / 4
        box(
            f"hz_ladrung{k}",
            (0.05, 0.44, 0.03),
            (1.3 + 0.45 * t, sy1 + 0.9, dz + 0.1 - (dz + 0.05) * t),
            METAL(),
            root,
            0,
        )
    for s in (-1, 1):
        box(
            f"hz_roofrail{s}",
            (0.04, sy0 - sy1, 0.04),
            (s * 1.15, scy, dz + 0.14 + sh + 0.3),
            METAL(),
            root,
            0,
        )
        for k in range(4):
            box(
                f"hz_roofpost{s}{k}",
                (0.04, 0.04, 0.3),
                (
                    s * 1.15,
                    sy1 + 0.2 + k * (sy0 - sy1 - 0.4) / 3,
                    dz + 0.14 + sh + 0.15,
                ),
                METAL(),
                root,
                0,
            )
    # cables from the shelter to the turret
    for s in (-1, 1):
        hose(
            f"hz_cable{s}",
            [
                (s * 0.5, sy0 + 0.05, dz + 0.4),
                (s * 0.6, sy0 + 0.6, dz + 0.25),
                (s * 0.8, ty - 0.9, dz + 0.5),
            ],
            0.035,
            DARK(),
            root,
        )

    # stabiliser jacks at the four corners
    for s in (-1, 1):
        for jy, tag in ((axles[1] - 0.85, "f"), (rear + 0.4, "r")):
            box(
                f"hz_jackbeam{s}{tag}",
                (0.55, 0.3, 0.25),
                (s * 1.3, jy, dz - 0.15),
                DARK(),
                root,
                0.01,
            )
            cyl(
                f"hz_jackcyl{s}{tag}",
                0.1,
                1.0,
                (s * 1.55, jy, 0.62),
                (0, 0, 0),
                METAL(),
                root,
                14,
            )
            cyl(
                f"hz_jackpad{s}{tag}",
                0.26,
                0.06,
                (s * 1.55, jy, 0.03),
                (0, 0, 0),
                DARK(),
                root,
                18,
            )

    for i in range(STEPS):
        f = i * 100 // (STEPS - 1)
        t = i / (STEPS - 1)
        fold.rotation_euler = (math.radians(-90) + (TILT + math.radians(90)) * t, 0, 0)
        fold.keyframe_insert("rotation_euler", frame=f)
        az.rotation_euler = (0, 0, 2 * math.pi * t)
        az.keyframe_insert("rotation_euler", frame=f)
    shell = box("collision_shell", (2.7, 11.6, 3.9), (0, -0.2, 1.95), DARK(), root, 0)
    shell.hide_render = True
    return az


if __name__ == "__main__":
    out = sys.argv[-1]
    az = build()
    finalize("IRAD_Hafez_SR")
    bpy.context.scene.frame_set(0)
    if "--bake" in sys.argv:
        bake_camo(out, "IRAD_Hafez_SR")
    bpy.ops.wm.save_as_mainfile(filepath=f"{out}/IRAD_Hafez_SR.blend")
    scn = bpy.context.scene
    # erect views hold the turret facing forward: azimuth keyed separately at frame 0
    az.animation_data_clear()
    az.rotation_euler = (0, 0, 0)
    views = (
        (0, "stowed", dict(target=(0, 1.0, 2.4), dist=15, az=-55, elev=10)),
        (100, "erect", dict(target=(0, 0.5, 3.4), dist=17, az=-50, elev=8)),
        (100, "photoside", dict(target=(0, 0.3, 3.4), dist=17, az=-95, elev=4)),
        (50, "folding", dict(target=(0, 0.0, 3.0), dist=15, az=-80, elev=6)),
    )
    for frame, name, kw in views:
        scn.frame_set(frame)
        render(f"{out}/IRAD_Hafez_SR_{name}.png", **kw)
