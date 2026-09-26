"""Meraj-4 search radar (IRAD_Meraj4_SR), matched to two photographs and a render:
a slatted planar array with an IFF column and a top antenna, on two A-frame legs over
a turntable, on a tri-axle semi-trailer standing on four outrigger jacks. Plain
khaki, as photographed. Modelled deployed; the towed travel fit is deferred.

arg_antenna_azimuth: frames 0-100, one full turn of the array.
"""

import math
import sys

import bpy

sys.path.insert(0, sys.argv[-1])
from irad_kit import *  # noqa: E402,F403

KHAKI = lambda: mat("irad_khaki", (0.30, 0.29, 0.17), 0.75)  # noqa: E731
AW, AH, AD = 8.3, 3.9, 0.45  # array width, height, depth
TILT = math.radians(10)
STEPS = 11


def array(parent):
    """The planar array: back frame, horizontal slats on the face, IFF column, top antenna."""
    box("mj_back", (AW, AD, AH), (0, -AD / 2, AH / 2), KHAKI(), parent, 0.04)
    box(
        "mj_facebacking",
        (AW - 0.3, 0.02, AH - 0.1),
        (0, 0.005, AH / 2),
        DARK(),
        parent,
        0,
    )
    for x in (-3.0, -1.0, 1.0, 3.0):
        box(
            f"mj_backrib{x}",
            (0.14, 0.12, AH),
            (x, -AD - 0.06, AH / 2),
            KHAKI(),
            parent,
            0.01,
        )
    rows = 34
    for k in range(rows):
        z = 0.12 + k * (AH - 0.24) / (rows - 1)
        box(f"mj_slat{k}", (AW - 0.3, 0.12, 0.06), (0, 0.07, z), KHAKI(), parent, 0)
    for s in (-1, 1):
        box(
            f"mj_endcap{s}",
            (0.12, AD + 0.16, AH),
            (s * (AW / 2 - 0.06), -AD / 2 + 0.08, AH / 2),
            KHAKI(),
            parent,
            0.02,
        )
    box(
        "mj_bottomframe",
        (AW, AD + 0.2, 0.16),
        (0, -AD / 2, 0.02),
        KHAKI(),
        parent,
        0.02,
    )
    white = mat("irad_white", (0.8, 0.8, 0.78), 0.5)
    for k in range(5):
        box(
            f"mj_iff{k}",
            (0.32, 0.25, 0.62),
            (AW / 2 + 0.18, 0.02, 0.45 + k * 0.72),
            white,
            parent,
            0.02,
        )
    box(
        "mj_iffrail",
        (0.08, 0.1, AH),
        (AW / 2 + 0.05, -0.05, AH / 2),
        KHAKI(),
        parent,
        0,
    )
    # the secondary antenna on top, on two brackets
    for s in (-1, 1):
        box(
            f"mj_topbracket{s}",
            (0.12, 0.3, 0.5),
            (s * 1.1, -AD / 2, AH + 0.25),
            KHAKI(),
            parent,
            0.01,
        )
    cyl(
        "mj_topantenna",
        0.28,
        2.6,
        (0, -AD / 2, AH + 0.5),
        (0, math.pi / 2, 0),
        KHAKI(),
        parent,
        20,
    )
    box(
        "mj_topradome",
        (2.6, 0.5, 0.35),
        (0, -AD / 2 + 0.05, AH + 0.5),
        KHAKI(),
        parent,
        0.1,
    )
    for s in (-1, 1):
        box(
            f"mj_toparm{s}",
            (0.06, 0.06, 0.8),
            (s * (AW / 2 - 0.4), -AD / 2, AH + 0.35),
            KHAKI(),
            parent,
            0,
            (0.4, 0, 0),
        )


def trailer(root):
    """Tri-axle semi-trailer: low main deck, raised gooseneck with an open frame."""
    deck_z = 1.2
    rear, neck, front = -6.5, 2.6, 6.5
    box(
        "mj_deck",
        (2.5, neck - rear, 0.25),
        (0, (neck + rear) / 2, deck_z - 0.12),
        KHAKI(),
        root,
        0.02,
    )
    for s in (-1, 1):
        box(
            f"mj_rail{s}",
            (0.2, neck - rear, 0.4),
            (s * 0.5, (neck + rear) / 2, deck_z - 0.4),
            KHAKI(),
            root,
            0.01,
        )
        box(
            f"mj_edge{s}",
            (0.06, neck - rear, 0.14),
            (s * 1.24, (neck + rear) / 2, deck_z - 0.14),
            KHAKI(),
            root,
            0,
        )
        box(
            f"mj_neckrail{s}",
            (0.22, front - neck - 0.4, 0.4),
            (s * 0.95, (front + neck) / 2 + 0.2, 1.7),
            KHAKI(),
            root,
            0.01,
        )
        strut(
            f"mj_neckrise{s}",
            (s * 1.0, neck - 0.3, deck_z - 0.1),
            (s * 0.95, neck + 1.0, 1.7),
            0.14,
            KHAKI(),
            root,
        )
    for k in range(4):
        box(
            f"mj_neckcross{k}",
            (1.9, 0.14, 0.14),
            (0, neck + 0.9 + k * 0.95, 1.7),
            KHAKI(),
            root,
            0,
        )
    box("mj_neckplate", (2.1, 0.8, 0.12), (0, front - 0.5, 1.85), KHAKI(), root, 0.01)
    cyl("mj_kingpin", 0.06, 0.3, (0, front - 1.1, 1.45), (0, 0, 0), METAL(), root, 10)
    # landing legs under the neck
    for s in (-1, 1):
        box(
            f"mj_landingleg{s}",
            (0.14, 0.14, 1.5),
            (s * 0.9, neck + 1.2, 0.8),
            KHAKI(),
            root,
            0,
        )
        box(
            f"mj_landingfoot{s}",
            (0.35, 0.35, 0.05),
            (s * 0.9, neck + 1.2, 0.03),
            DARK(),
            root,
            0,
        )
    # tri-axle bogie with dual wheels
    for i, y in enumerate((-5.4, -4.35, -3.3)):
        box(f"mj_axle{i}", (2.4, 0.16, 0.16), (0, y, 0.5), DARK(), root, 0.01)
        for s in (-1, 1):
            for d in (0, 1):
                wheel(
                    f"mj_wheel_{i}{s}{d}",
                    (s * (0.8 + d * 0.33), y, 0.5),
                    0.5,
                    0.3,
                    root,
                )
        for s in (-1, 1):
            box(
                f"mj_mudguard{i}{s}",
                (0.75, 1.0, 0.05),
                (s * 0.97, y, 1.02),
                DARK(),
                root,
                0,
            )
    for s in (-1, 1):
        box(
            f"mj_taillight{s}",
            (0.25, 0.04, 0.1),
            (s * 1.0, rear - 0.02, deck_z - 0.4),
            RED(),
            root,
            0,
        )
    # four outrigger jacks on swing arms, deployed
    for s in (-1, 1):
        for y, tag in ((rear + 0.5, "r"), (front - 0.6, "f")):
            z = deck_z - 0.2 if tag == "r" else 1.6
            box(
                f"mj_outarm{s}{tag}",
                (0.9, 0.2, 0.2),
                (s * 1.6, y, z),
                KHAKI(),
                root,
                0.01,
            )
            cyl(
                f"mj_jackscrew{s}{tag}",
                0.08,
                z,
                (s * 2.0, y, z / 2),
                (0, 0, 0),
                METAL(),
                root,
                12,
            )
            cyl(
                f"mj_jackhousing{s}{tag}",
                0.13,
                0.7,
                (s * 2.0, y, z - 0.2),
                (0, 0, 0),
                KHAKI(),
                root,
                14,
            )
            for k in range(3):
                cyl(
                    f"mj_jackspring{s}{tag}{k}",
                    0.16,
                    0.05,
                    (s * 2.0, y, z - 0.5 - k * 0.1),
                    (0, 0, 0),
                    KHAKI(),
                    root,
                    14,
                )
            cyl(
                f"mj_jackpad{s}{tag}",
                0.25,
                0.05,
                (s * 2.0, y, 0.03),
                (0, 0, 0),
                DARK(),
                root,
                16,
            )
    # deck equipment: a vented cabinet and a ladder
    box("mj_cabinet", (1.0, 0.9, 1.0), (0.7, 0.6, deck_z + 0.5), KHAKI(), root, 0.03)
    box("mj_cabinet2", (0.9, 0.9, 0.8), (-0.6, 0.6, deck_z + 0.4), KHAKI(), root, 0.03)
    louvers("mj_cablouver", (1.2, 0.6, deck_z + 0.55), 0.6, 0.6, 6, 1, root)
    for rail in (-1, 1):
        strut(
            f"mj_ladrail{rail}",
            (-1.2, -0.6 + rail * 0.22, deck_z),
            (-1.75, -0.6 + rail * 0.22, 0.02),
            0.025,
            METAL(),
            root,
        )
    for k in range(4):
        t = (k + 0.5) / 4
        box(
            f"mj_ladrung{k}",
            (0.05, 0.44, 0.03),
            (-1.2 - 0.55 * t, -0.6, deck_z - deck_z * t),
            METAL(),
            root,
            0,
        )
    return deck_z


def build():
    reset()
    root = empty("IRAD_Meraj4_SR", (0, 0, 0))
    deck_z = trailer(root)
    ty = -3.1
    cyl("mj_ring", 1.3, 0.25, (0, ty, deck_z + 0.12), (0, 0, 0), METAL(), root, 40)
    az = empty("arg_antenna_azimuth", (0, ty, deck_z + 0.25), root)
    box("mj_platform", (3.4, 2.4, 0.2), (0, 0, 0.1), KHAKI(), az, 0.02)
    box("mj_drive", (1.2, 1.0, 0.7), (0, -0.4, 0.55), KHAKI(), az, 0.03)
    hinge_z = 1.75
    for s in (-1, 1):
        # A-frame pedestal legs, wide at the platform, narrow at the array
        strut(
            f"mj_legf{s}",
            (s * 1.5, 0.9, 0.2),
            (s * 1.9, 0.15, hinge_z),
            0.16,
            KHAKI(),
            az,
        )
        strut(
            f"mj_legr{s}",
            (s * 1.5, -0.9, 0.2),
            (s * 1.9, -0.25, hinge_z),
            0.16,
            KHAKI(),
            az,
        )
        box(f"mj_legplate{s}", (0.2, 1.4, 0.5), (s * 1.62, 0, 0.55), KHAKI(), az, 0.02)
        box(
            f"mj_trunnion{s}",
            (0.4, 0.6, 0.35),
            (s * 1.9, -0.05, hinge_z),
            KHAKI(),
            az,
            0.02,
        )
    ladder_x = -0.6
    for rail in (-1, 1):
        box(
            f"mj_pedladrail{rail}",
            (0.04, 0.04, 1.6),
            (ladder_x + rail * 0.2, 0.3, 1.0),
            METAL(),
            az,
            0,
        )
    for k in range(5):
        box(
            f"mj_pedladrung{k}",
            (0.42, 0.04, 0.03),
            (ladder_x, 0.3, 0.35 + k * 0.32),
            METAL(),
            az,
            0,
        )
    tilt = empty("mj_array_tilt", (0, -0.05, hinge_z), az, (TILT, 0, 0))
    array(tilt)
    for i in range(STEPS):
        f = i * 100 // (STEPS - 1)
        az.rotation_euler = (0, 0, 2 * math.pi * i / (STEPS - 1))
        az.keyframe_insert("rotation_euler", frame=f)
    shell = box("collision_shell", (2.6, 13.0, 2.0), (0, 0, 1.0), DARK(), root, 0)
    shell.hide_render = True
    shell2 = box(
        "collision_shell_array", (AW, 1.0, AH), (0, 0, hinge_z + AH / 2), DARK(), az, 0
    )
    shell2.hide_render = True
    return az


if __name__ == "__main__":
    out = sys.argv[-1]
    az = build()
    finalize("IRAD_Meraj4_SR")
    bpy.context.scene.frame_set(0)
    bpy.ops.wm.save_as_mainfile(filepath=f"{out}/IRAD_Meraj4_SR.blend")
    az.animation_data_clear()
    views = (
        (0.0, "front", dict(target=(0, 0, 3.0), dist=20, az=-20, elev=6)),
        (0.0, "side", dict(target=(0, 0, 2.6), dist=21, az=-100, elev=4)),
        (0.6, "quarter", dict(target=(0, 0, 3.0), dist=20, az=-55, elev=12)),
    )
    for rot, name, kw in views:
        az.rotation_euler = (0, 0, rot)
        render(f"{out}/IRAD_Meraj4_SR_{name}.png", **kw)
