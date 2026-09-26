"""Bavar-373 engagement radar (IRAD_Bavar373_STR), matched to a photograph and two
renders: an 8x8 with a thick tilted planar array on a turntable over a cabinet
stack, and an equipment shelter aft.

arg_antenna_fold: frames 0-100, stowed face-down over the cab to erect, 25 deg back.
arg_antenna_azimuth: frames 0-100, one full turn of the turret (bind to the search arg).
"""

import math
import sys

import bpy

sys.path.insert(0, sys.argv[-1])
from irad_kit import *  # noqa: E402,F403

PW, PH, PD = 3.2, 3.8, 0.9  # panel width, height, depth
TILT = math.radians(25)
STEPS = 11
NAME = "IRAD_Bavar373_STR"
PLINTH_H = 1.0  # the cabinet stack under the turret; a low riser when under 0.5


def panel(parent):
    """The array: body with an inset face and tile seams, an angled top band, bolted
    side frames, a back truss and feed boxes."""
    face_y = 0.05
    body_h = PH * 0.76
    box(
        "str_body",
        (PW, PD, body_h),
        (0, face_y - PD / 2, body_h / 2),
        PAINT(),
        parent,
        0.05,
    )
    # face: a raised border round a recessed radiating face, 2 x 3 tiles
    for k, (w, h, x, z) in enumerate(
        (
            (PW, 0.14, 0, body_h - 0.07),
            (PW, 0.14, 0, 0.07),
            (0.14, body_h, PW / 2 - 0.07, body_h / 2),
            (0.14, body_h, -PW / 2 + 0.07, body_h / 2),
        )
    ):
        box(
            f"str_border{k}", (w, 0.08, h), (x, face_y + 0.02, z), PAINT(), parent, 0.01
        )
    fw, fh = PW - 0.4, body_h - 0.4
    box(
        "str_face",
        (fw, 0.03, fh),
        (0, face_y - 0.01, body_h / 2),
        PAINT(),
        parent,
        0.01,
    )
    for k in range(1, 3):
        box(
            f"str_tilev{k}",
            (0.025, 0.04, fh),
            (-fw / 2 + k * fw / 3, face_y + 0.005, body_h / 2),
            DARK(),
            parent,
            0,
        )
    box(
        "str_tileh",
        (fw, 0.04, 0.025),
        (0, face_y + 0.005, body_h / 2),
        DARK(),
        parent,
        0,
    )
    # top band, tilted forward a little, with its own face panel
    band = empty(
        "str_topband_tilt",
        (0, face_y - PD * 0.1, body_h + 0.02),
        parent,
        (math.radians(-8), 0, 0),
    )
    bh = PH - body_h - 0.05
    box(
        "str_topband",
        (PW + 0.06, PD * 0.8, bh),
        (0, -PD * 0.35, bh / 2),
        PAINT(),
        band,
        0.05,
    )
    box(
        "str_topface",
        (PW - 0.3, 0.03, bh - 0.2),
        (0, 0.06, bh / 2),
        PAINT(),
        band,
        0.01,
    )
    # bolted side frames
    for s in (-1, 1):
        box(
            f"str_sideframe{s}",
            (0.14, PD + 0.06, body_h),
            (s * (PW / 2 + 0.03), face_y - PD / 2, body_h / 2),
            PAINT(),
            parent,
            0.02,
        )
        for k in range(8):
            cyl(
                f"str_bolt{s}{k}",
                0.02,
                0.03,
                (s * (PW / 2 + 0.105), face_y - 0.1, 0.2 + k * (body_h - 0.4) / 7),
                (0, math.pi / 2, 0),
                METAL(),
                parent,
                6,
            )
    box(
        "str_bottomlip",
        (PW, PD + 0.1, 0.16),
        (0, face_y - PD / 2, 0.08),
        PAINT(),
        parent,
        0.02,
    )
    # back: vertical ribs, a diagonal truss, two feed boxes
    back_y = face_y - PD - 0.04
    for x in (-1.2, -0.4, 0.4, 1.2):
        box(
            f"str_backrib{x}",
            (0.1, 0.08, PH * 0.88),
            (x, back_y, PH * 0.45),
            PAINT(),
            parent,
            0.01,
        )
    for k in range(3):
        z0, z1 = 0.3 + k * 1.0, 1.3 + k * 1.0
        for s in (-1, 1):
            strut(
                f"str_backdiag{k}{s}",
                (s * 1.2, back_y - 0.03, z0),
                (-s * 0.4, back_y - 0.03, z1),
                0.03,
                PAINT(),
                parent,
                6,
            )
    for k, x in enumerate((-0.6, 0.6)):
        box(
            f"str_feedbox{k}",
            (0.6, 0.3, 0.5),
            (x, back_y - 0.2, 0.7),
            PAINT(),
            parent,
            0.02,
        )
        grille(
            f"str_feedgrille{k}", (x, back_y - 0.35, 0.7), "y", -1, 0.4, 0.3, parent, 5
        )
    cyl(
        "str_antennacap",
        0.08,
        0.12,
        (0.9, face_y - PD * 0.4, PH + 0.02),
        (0, 0, 0),
        DARK(),
        parent,
        12,
    )


def head(az):
    """The rotating head on the turntable: cabinet, pedestal, yoke cheeks, braces.
    Returns the fold hinge (y, z) in the head's frame."""
    box("str_head", (1.5, 1.4, 0.9), (0, 0, 0.45), PAINT(), az, 0.04)
    door("str_headdoor", (0.75, 0, 0.45), "x", 1, 0.7, 0.6, az)
    grille("str_headgrille", (-0.75, 0, 0.45), "x", -1, 0.6, 0.5, az, 5)
    box("str_pedestal", (0.8, 0.8, 0.35), (0, 0.2, 1.05), PAINT(), az, 0.02)
    hinge_y, hinge_z = 0.55, 1.25
    for s in (-1, 1):
        # yoke cheeks carrying the hinge, with an A-frame brace as photographed
        box(
            f"str_cheek{s}",
            (0.16, 0.55, 0.6),
            (s * 0.95, hinge_y, 0.95),
            PAINT(),
            az,
            0.02,
        )
        strut(
            f"str_brace{s}",
            (s * 0.6, -0.55, 0.9),
            (s * 0.95, hinge_y, hinge_z),
            0.05,
            METAL(),
            az,
        )
        strut(
            f"str_brace2{s}",
            (s * 0.6, 0.55, 0.9),
            (s * 0.95, hinge_y, hinge_z),
            0.05,
            METAL(),
            az,
        )
        cyl(
            f"str_hingepin{s}",
            0.08,
            0.24,
            (s * 0.95, hinge_y, hinge_z),
            (0, math.pi / 2, 0),
            METAL(),
            az,
            14,
        )
        hose(
            f"str_headcable{s}",
            [
                (s * 0.5, -0.5, 0.9),
                (s * 0.7, 0.0, 1.2),
                (s * 0.85, hinge_y - 0.1, hinge_z - 0.1),
            ],
            0.03,
            DARK(),
            az,
        )
    return hinge_y, hinge_z


def build():
    reset()
    axles = [4.3, 2.85, -2.55, -4.0]
    root, dz, rear, cab_back = iran_truck(NAME, axles, 11.0, cab_len=2.3, wheel_r=0.72)
    dlen = cab_back - rear
    box(
        "str_deck",
        (2.5, dlen, 0.16),
        (0, (cab_back + rear) / 2, dz + 0.06),
        DARK(),
        root,
        0.01,
    )
    for s in (-1, 1):
        box(
            f"str_deckedge{s}",
            (0.08, dlen, 0.26),
            (s * 1.25, (cab_back + rear) / 2, dz + 0.03),
            PAINT(),
            root,
            0.01,
        )
    for k in range(int(dlen / 0.6)):
        box(
            f"str_tiedown{k}",
            (2.54, 0.06, 0.05),
            (0, rear + 0.3 + k * 0.6, dz + 0.16),
            DARK(),
            root,
            0,
        )

    # generator behind the cab: door, grille, exhaust stack with a rain cap
    gy = cab_back - 0.55
    box("str_gen", (2.2, 0.9, 1.35), (0, gy, dz + 0.8), PAINT(), root, 0.03)
    for s in (-1, 1):
        grille(
            f"str_gengrille{s}",
            (s * 1.1, gy + 0.1, dz + 0.9),
            "x",
            s,
            0.55,
            0.7,
            root,
            7,
        )
    door("str_gendoor", (0, gy - 0.45, dz + 0.8), "y", -1, 0.8, 1.0, root)
    cyl(
        "str_genexhaust",
        0.06,
        0.9,
        (0.8, gy + 0.2, dz + 1.9),
        (0, 0, 0),
        METAL(),
        root,
        12,
    )
    cyl(
        "str_genexhaustcap",
        0.09,
        0.05,
        (0.8, gy + 0.2, dz + 2.37),
        (0, 0, 0),
        DARK(),
        root,
        12,
    )

    # turret: two-tier cabinet stack, turntable with a bolt ring, rotating head
    ty = 0.9
    ph = PLINTH_H
    box("str_plinth", (2.3, 2.0, ph), (0, ty, dz + 0.08 + ph / 2), PAINT(), root, 0.03)
    for s in (-1, 1):
        if ph >= 0.5:
            door(
                f"str_plinthdoor{s}",
                (s * 1.15, ty - 0.45, dz + 0.08 + ph / 2),
                "x",
                s,
                0.8,
                ph * 0.75,
                root,
            )
            grille(
                f"str_plinthgrille{s}",
                (s * 1.15, ty + 0.5, dz + 0.08 + ph / 2),
                "x",
                s,
                0.6,
                ph * 0.55,
                root,
                6,
            )
            box(
                f"str_sidecab{s}",
                (0.45, 1.3, 0.85),
                (s * 1.0, ty + 0.1, dz + ph + 0.5),
                PAINT(),
                root,
                0.03,
            )
            door(
                f"str_sidecabdoor{s}",
                (s * 1.225, ty + 0.1, dz + ph + 0.5),
                "x",
                s,
                1.0,
                0.65,
                root,
            )
            box(
                f"str_sidecabroof{s}",
                (0.5, 1.35, 0.05),
                (s * 1.0, ty + 0.1, dz + ph + 0.95),
                DARK(),
                root,
                0,
            )
        else:
            grille(
                f"str_plinthgrille{s}",
                (s * 1.15, ty, dz + 0.08 + ph / 2),
                "x",
                s,
                1.2,
                ph * 0.6,
                root,
                3,
            )
    box("str_turntable", (1.9, 1.9, 0.1), (0, ty, dz + ph + 0.13), METAL(), root, 0.01)
    cyl("str_ring", 0.85, 0.22, (0, ty, dz + ph + 0.19), (0, 0, 0), METAL(), root, 36)
    for k in range(16):
        a = k * math.pi / 8
        cyl(
            f"str_ringbolt{k}",
            0.03,
            0.05,
            (math.cos(a) * 0.78, ty + math.sin(a) * 0.78, dz + ph + 0.31),
            (0, 0, 0),
            DARK(),
            root,
            6,
        )
    az = empty("arg_antenna_azimuth", (0, ty, dz + ph + 0.3), root)
    hinge_y, hinge_z = head(az)
    fold = empty("arg_antenna_fold", (0, hinge_y, hinge_z), az)
    panel(fold)

    # equipment shelter aft
    sy0, sy1, sh = -0.3, rear + 0.35, 2.3
    scy, slen = (sy0 + sy1) / 2, sy0 - sy1
    top = dz + 0.14 + sh
    box(
        "str_shelter",
        (2.45, slen, sh),
        (0, scy, dz + 0.14 + sh / 2),
        PAINT(),
        root,
        0.04,
    )
    box("str_shelterroof", (2.5, slen + 0.05, 0.08), (0, scy, top), PAINT(), root, 0.02)
    for s in (-1, 1):
        door(f"str_door{s}", (s * 1.225, scy + 0.9, dz + 1.05), "x", s, 0.9, 1.6, root)
        box(
            f"str_doorstep{s}",
            (0.35, 0.8, 0.05),
            (s * 1.35, scy + 0.9, dz - 0.1),
            METAL(),
            root,
            0,
        )
        box(
            f"str_acbox{s}",
            (0.4, 0.9, 0.9),
            (s * 1.42, scy - 1.0, dz + 1.3),
            PAINT(),
            root,
            0.03,
        )
        grille(
            f"str_acgrille{s}",
            (s * 1.62, scy - 1.0, dz + 1.3),
            "x",
            s,
            0.75,
            0.7,
            root,
            8,
        )
        for k in range(1, 3):
            box(
                f"str_panelseam{s}{k}",
                (0.02, 0.03, sh - 0.2),
                (s * 1.232, sy1 + k * 0.7, dz + 0.14 + sh / 2),
                DARK(),
                root,
                0,
            )
    for k in range(2):
        grille(
            f"str_reargrille{k}",
            (-0.55 + k * 1.1, sy1, dz + 1.1),
            "y",
            -1,
            0.8,
            1.3,
            root,
            10,
        )
    # ladder up the rear corner to the roof, roof rail round the shelter
    ladder("str_ladder", (1.3, sy1 + 0.6, top), (1.75, sy1 + 0.6, 0.05), 0.44, 8, root)
    handrail(
        "str_roofrail",
        [
            (-1.15, sy1 + 0.1, top),
            (-1.15, sy0 - 0.1, top),
            (1.15, sy0 - 0.1, top),
            (1.15, sy1 + 0.1, top),
        ],
        root,
        0.9,
    )
    for k in range(3):
        box(
            f"str_roofvent{k}",
            (0.45, 0.45, 0.18),
            (-0.4, sy0 - 0.8 - k * 1.1, top + 0.13),
            PAINT(),
            root,
            0.02,
        )
    cyl(
        "str_whipbase",
        0.07,
        0.15,
        (0.9, sy1 + 0.5, top + 0.1),
        (0, 0, 0),
        DARK(),
        root,
        10,
    )
    cyl("str_whip", 0.012, 2.4, (0.9, sy1 + 0.5, top + 1.3), (0, 0, 0), DARK(), root, 6)
    for s_ in (-1, 1):
        box(
            f"str_stowbox{s_}",
            (0.4, 1.1, 0.45),
            (s_ * 1.0, (axles[2] + axles[1]) / 2 - 1.3, dz - 0.4),
            PAINT(),
            root,
            0.02,
        )
        box(
            f"str_stowlatch{s_}",
            (0.03, 0.08, 0.1),
            (s_ * 1.21, (axles[2] + axles[1]) / 2 - 1.3, dz - 0.3),
            METAL(),
            root,
            0,
        )
    # cable reels and runs between the shelter and the turret
    for k, x in enumerate((-0.7, 0.7)):
        cable_reel(f"str_reel{k}", (x, sy0 + 0.4, dz + 0.5), root)
    for s in (-1, 1):
        hose(
            f"str_cable{s}",
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
                f"str_jackbeam{s}{tag}",
                (0.55, 0.3, 0.25),
                (s * 1.3, jy, dz - 0.15),
                DARK(),
                root,
                0.01,
            )
            screw_jack(f"str_jack{s}{tag}", s * 1.55, jy, dz - 0.2, root)

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
    finalize(NAME)
    animate_wheels()
    bpy.context.scene.frame_set(0)
    if "--bake" in sys.argv:
        bake_camo(out, NAME)
    bpy.ops.wm.save_as_mainfile(filepath=f"{out}/{NAME}.blend")
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
        render(f"{out}/{NAME}_{name}.png", **kw)
