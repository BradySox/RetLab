"""Matla ul-Fajr early-warning radar (IRAD_MatlaUlFajr_EWR), matched to a photograph:
a long boom of eight Yagi pairs on a telescopic mast at the rear of a long
corrugated shelter on a semi-trailer, in woodland camouflage.

arg_mast_extend: frames 0-100, mast nested to fully raised.
arg_antenna_azimuth: frames 0-100, one full turn of the boom.
"""

import math
import sys

import bpy

sys.path.insert(0, sys.argv[-1])
import irad_kit  # noqa: E402

irad_kit.CAMO.update(
    base=(0.10, 0.11, 0.06), cloud=(0.13, 0.08, 0.04), mark=(0.05, 0.06, 0.03)
)
from irad_kit import *  # noqa: E402,F403

STEPS = 11
ROD = lambda: mat("irad_rod", (0.55, 0.55, 0.53), 0.4, 0.8)  # noqa: E731


def yagi(prefix, x, z, parent):
    """One Yagi: a short boom across the main boom with five elements."""
    strut(f"{prefix}_boom", (x, -0.75, z), (x, 0.75, z), 0.02, ROD(), parent, 6)
    for k in range(5):
        y = -0.6 + k * 0.3
        strut(
            f"{prefix}_el{k}",
            (x - 0.32, y, z),
            (x + 0.32, y, z),
            0.01,
            ROD(),
            parent,
            4,
        )


def boom(head):
    length, bz = 11.5, 0.6
    strut("mf_boom", (-length / 2, 0, bz), (length / 2, 0, bz), 0.07, ROD(), head, 10)
    for s in (-1, 1):
        strut(
            f"mf_brace{s}",
            (0, 0, 1.6),
            (s * length * 0.3, 0, bz),
            0.035,
            ROD(),
            head,
            6,
        )
    cyl("mf_braceking", 0.05, 1.2, (0, 0, 1.1), (0, 0, 0), ROD(), head, 8)
    for i, x in enumerate((-5.25, -3.75, -2.25, -0.75, 0.75, 2.25, 3.75, 5.25)):
        strut(f"mf_pole{i}", (x, 0, bz - 1.1), (x, 0, bz + 1.1), 0.03, ROD(), head, 6)
        yagi(f"mf_yagi{i}t", x, bz + 1.1, head)
        yagi(f"mf_yagi{i}b", x, bz - 1.1, head)


def build():
    reset()
    root = empty("IRAD_MatlaUlFajr_EWR", (0, 0, 0))
    deck_z, rear, front = 1.2, -5.6, 5.6
    # semi-trailer: frame, raised neck at the front, two rear axles with duals, jacks
    neck = 3.4
    for s_ in (-1, 1):
        box(
            f"mf_rail{s_}",
            (0.18, neck - rear, 0.35),
            (s_ * 0.55, (neck + rear) / 2, deck_z - 0.3),
            DARK(),
            root,
            0.01,
        )
        box(
            f"mf_neckrail{s_}",
            (0.18, front - neck, 0.3),
            (s_ * 0.55, (front + neck) / 2, deck_z + 0.25),
            DARK(),
            root,
            0.01,
        )
    box(
        "mf_neckplate",
        (2.2, front - neck, 0.1),
        (0, (front + neck) / 2, deck_z + 0.42),
        DARK(),
        root,
        0.01,
    )
    for s_ in (-1, 1):
        box(
            f"mf_landingleg{s_}",
            (0.12, 0.12, deck_z + 0.2),
            (s_ * 0.8, neck + 0.4, (deck_z + 0.2) / 2),
            METAL(),
            root,
            0,
        )
    for i, y in enumerate((-3.5, -4.6)):
        box(f"mf_axle{i}", (2.3, 0.15, 0.15), (0, y, 0.5), DARK(), root, 0.01)
        for s_ in (-1, 1):
            for d in (0, 1):
                wheel(
                    f"mf_wheel_{i}{s_}{d}",
                    (s_ * (0.8 + d * 0.3), y, 0.5),
                    0.5,
                    0.28,
                    root,
                )
    for s_ in (-1, 1):
        for y in (rear + 0.3, neck - 0.4):
            cyl(
                f"mf_jack{s_}{y}",
                0.07,
                deck_z - 0.3,
                (s_ * 1.25, y, (deck_z - 0.3) / 2),
                (0, 0, 0),
                METAL(),
                root,
                10,
            )
            cyl(
                f"mf_jackpad{s_}{y}",
                0.2,
                0.05,
                (s_ * 1.25, y, 0.03),
                (0, 0, 0),
                DARK(),
                root,
                14,
            )
    # the long corrugated shelter, ladders, roof clutter
    sy0, sy1, sh = front - 0.2, rear + 1.6, 2.35
    scy, slen = (sy0 + sy1) / 2, sy0 - sy1
    box(
        "mf_shelter",
        (2.45, slen, sh),
        (0, scy, deck_z + 0.5 + sh / 2),
        PAINT(),
        root,
        0.03,
    )
    box(
        "mf_shelterbase",
        (2.3, sy0 - sy1, 0.5),
        (0, scy, deck_z + 0.25),
        DARK(),
        root,
        0.01,
    )
    for s_ in (-1, 1):
        for k in range(int(slen / 0.16)):
            box(
                f"mf_rib{s_}{k}",
                (0.05, 0.05, sh - 0.1),
                (s_ * 1.24, sy1 + 0.1 + k * 0.16, deck_z + 0.5 + sh / 2),
                PAINT(),
                root,
                0,
            )
    top = deck_z + 0.5 + sh
    for k, (x, y, h) in enumerate(
        (
            (0.8, scy + 3.0, 0.35),
            (-0.6, scy + 1.6, 0.25),
            (0.9, scy + 0.2, 0.4),
            (-0.8, scy - 1.4, 0.3),
            (0.5, scy - 2.6, 0.45),
        )
    ):
        box(f"mf_roofbox{k}", (0.45, 0.45, h), (x, y, top + h / 2), PAINT(), root, 0.02)
    for k in range(4):
        cyl(
            f"mf_roofpost{k}",
            0.05,
            0.5,
            (-1.0 + k * 0.65, scy + 3.8, top + 0.25),
            (0, 0, 0),
            METAL(),
            root,
            8,
        )
    for rail in (-1, 1):
        strut(
            f"mf_ladrail{rail}",
            (1.3, scy + 1.0 + rail * 0.2, deck_z + 0.5),
            (2.0, scy + 1.0 + rail * 0.2, 0.02),
            0.025,
            METAL(),
            root,
        )
    for k in range(5):
        t = (k + 0.5) / 5
        box(
            f"mf_ladrung{k}",
            (0.05, 0.4, 0.03),
            (1.3 + 0.7 * t, scy + 1.0, (deck_z + 0.5) * (1 - t)),
            METAL(),
            root,
            0,
        )
    # the mast at the rear, over the axles
    mx, my = 0.0, rear + 0.8
    box("mf_mastbase", (1.1, 1.1, 1.3), (mx, my, deck_z + 0.65), PAINT(), root, 0.03)
    cyl(
        "mf_mastcollar", 0.3, 0.3, (mx, my, deck_z + 1.45), (0, 0, 0), METAL(), root, 16
    )
    radii, sec_len = (0.2, 0.16, 0.12), 3.2
    parent, sections = root, []
    for i, r in enumerate(radii):
        at = (mx, my, deck_z + 1.7) if i == 0 else (0, 0, 0)
        sec = empty(f"mast_sec{i}_slide", at, parent)
        cyl(
            f"mast_sec{i}",
            r,
            sec_len,
            (0, 0, 0.3 - sec_len / 2 + 0.2),
            (0, 0, 0),
            ROD(),
            sec,
            16,
        )
        cyl(
            f"mast_sec{i}_collar",
            r + 0.04,
            0.12,
            (0, 0, 0.45),
            (0, 0, 0),
            METAL(),
            sec,
            16,
        )
        sections.append(sec)
        parent = sec
    head = empty("arg_antenna_azimuth", (0, 0, 0.55), parent)
    cyl("mf_rotator", 0.26, 0.5, (0, 0, 0.25), (0, 0, 0), PAINT(), head, 18)
    box("mf_rotatorbox", (0.5, 0.35, 0.3), (0, 0.3, 0.3), PAINT(), head, 0.02)
    boom(head)
    for i in range(STEPS):
        t = i / (STEPS - 1)
        f = i * 100 // (STEPS - 1)
        sections[0].location.z = deck_z + 1.7 + 1.6 * t
        sections[1].location.z = 1.6 * t
        sections[2].location.z = 1.6 * t
        for sec in sections:
            sec.keyframe_insert("location", frame=f)
        head.rotation_euler = (0, 0, 2 * math.pi * t)
        head.keyframe_insert("rotation_euler", frame=f)
    shell = box("collision_shell", (2.6, 11.4, 4.0), (0, 0, 2.0), DARK(), root, 0)
    shell.hide_render = True
    return head


if __name__ == "__main__":
    out = sys.argv[-1]
    head = build()
    finalize("IRAD_MatlaUlFajr_EWR")
    bpy.context.scene.frame_set(0)
    if "--bake" in sys.argv:
        bake_camo(out, "IRAD_MatlaUlFajr_EWR")
    bpy.ops.wm.save_as_mainfile(filepath=f"{out}/IRAD_MatlaUlFajr_EWR.blend")
    head.animation_data_clear()
    scn = bpy.context.scene
    views = (
        (
            100,
            0.2,
            "photo",
            dict(target=(0, -1.0, 4.2), dist=19, az=-95, elev=4, res=(970, 600)),
        ),
        (100, 0.9, "quarter", dict(target=(0, -1.0, 4.0), dist=22, az=-45, elev=12)),
        (0, 0.0, "travel", dict(target=(0, 0.5, 2.2), dist=14, az=-50, elev=10)),
    )
    for frame, rot, name, kw in views:
        scn.frame_set(frame)
        head.rotation_euler = (0, 0, rot)
        render(f"{out}/IRAD_MatlaUlFajr_EWR_{name}.png", **kw)
