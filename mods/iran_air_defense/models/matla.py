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
from irad_kit import _flat, _on_face  # noqa: E402,F401

STEPS = 11
ROD = lambda: mat("irad_rod", (0.55, 0.55, 0.53), 0.4, 0.8)  # noqa: E731


def yagi(prefix, x, z, parent, up):
    """One Yagi across the main boom: its own boom, six directors, a feed box, a
    small reflector grid at the back, and a brace back to the pole."""
    strut(f"{prefix}_boom", (x, -0.8, z), (x, 0.75, z), 0.02, ROD(), parent, 6)
    for k in range(6):
        y = -0.45 + k * 0.24
        half = 0.3 - k * 0.02
        strut(
            f"{prefix}_el{k}",
            (x - half, y, z),
            (x + half, y, z),
            0.009,
            ROD(),
            parent,
            4,
        )
    box(f"{prefix}_feed", (0.1, 0.08, 0.08), (x, -0.55, z), DARK(), parent, 0)
    for k in range(4):
        zz = z - 0.18 + k * 0.12
        strut(
            f"{prefix}_grid{k}",
            (x - 0.34, -0.78, zz),
            (x + 0.34, -0.78, zz),
            0.007,
            ROD(),
            parent,
            4,
        )
    for k in range(3):
        xx = x - 0.3 + k * 0.3
        strut(
            f"{prefix}_gridv{k}",
            (xx, -0.78, z - 0.2),
            (xx, -0.78, z + 0.2),
            0.007,
            ROD(),
            parent,
            4,
        )
    strut(
        f"{prefix}_brace", (x, 0, z - up * 0.45), (x, 0.45, z), 0.012, ROD(), parent, 4
    )


def boom(head):
    length, bz = 11.5, 0.6
    # thicker centre section, thinner outer sections, clamped at each pole
    strut("mf_boomc", (-2.4, 0, bz), (2.4, 0, bz), 0.09, ROD(), head, 12)
    for s in (-1, 1):
        strut(
            f"mf_boomo{s}",
            (s * 2.3, 0, bz),
            (s * length / 2, 0, bz),
            0.06,
            ROD(),
            head,
            10,
        )
        box(
            f"mf_boomsplice{s}", (0.3, 0.2, 0.2), (s * 2.35, 0, bz), METAL(), head, 0.01
        )
    # king post and guy lines to the boom tips and quarter points
    cyl("mf_braceking", 0.05, 1.6, (0, 0, 1.3), (0, 0, 0), ROD(), head, 8)
    cyl("mf_kingcap", 0.08, 0.1, (0, 0, 2.12), (0, 0, 0), METAL(), head, 8)
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
        strut(
            f"mf_guy{s}",
            (0, 0, 2.1),
            (s * length / 2 * 0.95, 0, bz),
            0.008,
            DARK(),
            head,
            4,
        )
    for i, x in enumerate((-5.25, -3.75, -2.25, -0.75, 0.75, 2.25, 3.75, 5.25)):
        strut(f"mf_pole{i}", (x, 0, bz - 1.1), (x, 0, bz + 1.1), 0.03, ROD(), head, 6)
        box(f"mf_clamp{i}", (0.14, 0.16, 0.16), (x, 0, bz), METAL(), head, 0.01)
        yagi(f"mf_yagi{i}t", x, bz + 1.1, head, 1)
        yagi(f"mf_yagi{i}b", x, bz - 1.1, head, -1)


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
            (0.16, 0.16, deck_z + 0.2),
            (s_ * 0.8, neck + 0.4, (deck_z + 0.2) / 2 + 0.1),
            PAINT(),
            root,
            0.01,
        )
        box(
            f"mf_landingfoot{s_}",
            (0.4, 0.3, 0.06),
            (s_ * 0.8, neck + 0.4, 0.03),
            DARK(),
            root,
            0.01,
        )
        strut(
            f"mf_landingbrace{s_}",
            (s_ * 0.8, neck + 0.4, 0.5),
            (s_ * 0.55, neck - 0.5, deck_z - 0.4),
            0.03,
            METAL(),
            root,
        )
    strut(
        "mf_landingshaft",
        (-0.8, neck + 0.4, deck_z - 0.3),
        (0.8, neck + 0.4, deck_z - 0.3),
        0.025,
        METAL(),
        root,
    )
    box(
        "mf_landingcrank",
        (0.04, 0.3, 0.04),
        (0.95, neck + 0.5, deck_z - 0.3),
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
            box(
                f"mf_jackarm{s_}{y:.0f}",
                (0.6, 0.2, 0.18),
                (s_ * 0.95, y, deck_z - 0.4),
                DARK(),
                root,
                0.01,
            )
            screw_jack(f"mf_jack{s_}{y:.0f}", s_ * 1.28, y, deck_z - 0.3, root)
        # fenders over the duals, mudflaps and lights
        box(
            f"mf_fender{s_}",
            (0.75, 2.3, 0.05),
            (s_ * 0.95, -4.05, 1.08),
            PAINT(),
            root,
            0.01,
        )
        for e in (-1, 1):
            box(
                f"mf_fenderlip{s_}{e}",
                (0.75, 0.05, 0.25),
                (s_ * 0.95, -4.05 + e * 1.15, 0.97),
                PAINT(),
                root,
                0,
            )
        box(
            f"mf_mudflap{s_}",
            (0.6, 0.02, 0.5),
            (s_ * 0.95, -5.25, 0.55),
            DARK(),
            root,
            0,
        )
        box(
            f"mf_taillight{s_}",
            (0.25, 0.04, 0.1),
            (s_ * 1.0, rear - 0.02, deck_z - 0.35),
            RED(),
            root,
            0,
        )
        box(
            f"mf_sidemarker{s_}",
            (0.02, 0.08, 0.06),
            (s_ * 0.65, 0.0, deck_z - 0.35),
            AMBER(),
            root,
            0,
        )
    box(
        "mf_bumper",
        (2.2, 0.15, 0.2),
        (0, rear + 0.05, deck_z - 0.55),
        DARK(),
        root,
        0.01,
    )
    box(
        "mf_plate", (0.5, 0.02, 0.15), (0, rear - 0.03, deck_z - 0.55), METAL(), root, 0
    )
    # the long corrugated shelter, ladders, roof clutter
    sy0, sy1, sh = front - 1.75, rear + 1.6, 2.35
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
    doors = {1: scy + 2.2, -1: scy - 1.0}
    for s_ in (-1, 1):
        for k in range(int(slen / 0.16)):
            ry = sy1 + 0.1 + k * 0.16
            if abs(ry - doors[s_]) < 0.55:
                continue
            box(
                f"mf_rib{s_}{k}",
                (0.05, 0.05, sh - 0.1),
                (s_ * 1.24, ry, deck_z + 0.5 + sh / 2),
                PAINT(),
                root,
                0,
            )
        door(
            f"mf_door{s_}",
            (s_ * 1.22, doors[s_], deck_z + 0.5 + 1.0),
            "x",
            s_,
            0.9,
            1.9,
            root,
        )
        box(
            f"mf_doorstep{s_}",
            (0.4, 0.9, 0.05),
            (s_ * 1.45, doors[s_], deck_z + 0.2),
            METAL(),
            root,
            0,
        )
        grille(
            f"mf_grille{s_}",
            (s_ * 1.28, scy - s_ * 3.0, deck_z + 0.5 + sh - 0.5),
            "x",
            s_,
            0.6,
            0.45,
            root,
            5,
        )
        box(
            f"mf_toprail{s_}",
            (0.07, slen, 0.08),
            (s_ * 1.25, scy, deck_z + 0.5 + sh),
            PAINT(),
            root,
            0.01,
        )
    for e in (sy0, sy1):
        for s_ in (-1, 1):
            box(
                f"mf_cornerpost{e:.0f}{s_}",
                (0.12, 0.12, sh),
                (s_ * 1.22, e - (0.06 if e == sy0 else -0.06), deck_z + 0.5 + sh / 2),
                PAINT(),
                root,
                0.01,
            )
    top = deck_z + 0.5 + sh
    # a second, smaller box on the neck, as photographed: generator with a grille
    box(
        "mf_genbox",
        (2.2, 1.3, 1.5),
        (0, front - 0.8, deck_z + 0.47 + 0.75),
        PAINT(),
        root,
        0.03,
    )
    for s_ in (-1, 1):
        grille(
            f"mf_gengrille{s_}",
            (s_ * 1.1, front - 0.8, deck_z + 1.25),
            "x",
            s_,
            0.9,
            0.9,
            root,
            8,
        )
    cyl(
        "mf_genexhaust",
        0.06,
        0.6,
        (0.7, front - 0.5, deck_z + 2.2),
        (0, 0, 0),
        METAL(),
        root,
        10,
    )
    # roof: AC units, cable tray, whips and a handrail at the front
    for k, y in enumerate((scy + 1.0, scy - 2.0)):
        box(
            f"mf_roofac{k}",
            (1.0, 0.8, 0.45),
            (-0.5, y, top + 0.23),
            PAINT(),
            root,
            0.02,
        )
        grille(f"mf_roofacg{k}", (-0.5, y + 0.4, top + 0.23), "y", 1, 0.8, 0.3, root, 4)
    box(
        "mf_cabletray",
        (0.25, slen - 1.5, 0.08),
        (0.85, scy, top + 0.05),
        METAL(),
        root,
        0,
    )
    for k, y in enumerate((scy + 3.5, scy - 3.0)):
        cyl(f"mf_whip{k}", 0.015, 2.0, (1.0, y, top + 1.0), (0, 0, 0), DARK(), root, 6)
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
    ladder(
        "mf_sideladder",
        (1.35, doors[1], deck_z + 0.2),
        (2.0, doors[1], 0.02),
        0.6,
        4,
        root,
    )
    handrail(
        "mf_sidehand",
        [(1.55, doors[1] - 0.35, deck_z + 0.2), (2.0, doors[1] - 0.35, 0.05)],
        root,
        0.9,
    )
    ladder(
        "mf_rearladder",
        (-1.3, sy1 - 0.2, deck_z + 0.2),
        (-1.9, sy1 - 0.2, 0.02),
        0.6,
        4,
        root,
    )
    # the mast at the rear, over the axles
    mx, my = 0.0, rear + 0.8
    box("mf_mastbase", (1.1, 1.1, 1.3), (mx, my, deck_z + 0.65), PAINT(), root, 0.03)
    cyl(
        "mf_mastcollar", 0.3, 0.3, (mx, my, deck_z + 1.45), (0, 0, 0), METAL(), root, 16
    )
    box("mf_rearplatform", (2.4, 1.5, 0.08), (0, my, deck_z + 0.2), DARK(), root, 0)
    handrail(
        "mf_rearrail",
        [
            (-1.15, sy1, deck_z + 0.24),
            (-1.15, rear + 0.05, deck_z + 0.24),
            (1.15, rear + 0.05, deck_z + 0.24),
            (1.15, sy1, deck_z + 0.24),
        ],
        root,
    )
    cable_reel("mf_reel0", (-0.85, my + 0.3, deck_z + 0.55), root, 0.3, 0.35)
    cable_reel("mf_reel1", (0.85, my + 0.3, deck_z + 0.55), root, 0.3, 0.35)
    box(
        "mf_drivebox",
        (0.6, 0.45, 0.6),
        (0.75, my - 0.45, deck_z + 0.55),
        PAINT(),
        root,
        0.02,
    )
    box(
        "mf_hydbox",
        (0.5, 0.4, 0.5),
        (-0.75, my - 0.45, deck_z + 0.5),
        PAINT(),
        root,
        0.02,
    )
    hose(
        "mf_mastcable",
        [
            (0.4, my - 0.45, deck_z + 0.8),
            (0.3, my - 0.35, deck_z + 1.6),
            (0.18, my, deck_z + 1.8),
        ],
        0.025,
        DARK(),
        root,
    )
    for k in range(4):
        box(
            f"mf_mastgusset{k}",
            (0.08, 0.35, 0.35),
            (mx, my, deck_z + 1.4),
            PAINT(),
            root,
            0,
            (0, 0, k * math.pi / 2),
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
    for s_ in (-1, 1):
        cyl(
            f"mf_rotmotor{s_}",
            0.1,
            0.35,
            (s_ * 0.3, -0.2, 0.2),
            (0, 0, 0),
            METAL(),
            head,
            12,
        )
    cyl("mf_rotring", 0.3, 0.06, (0, 0, 0.02), (0, 0, 0), METAL(), head, 20)
    hose(
        "mf_rotcable",
        [(0.1, 0.45, 0.3), (0.35, 0.5, -0.1), (0.2, 0.3, -0.5)],
        0.02,
        DARK(),
        head,
    )
    boom(head)
    for i in range(STEPS):
        t = i / (STEPS - 1)
        f = i * 100 // (STEPS - 1)
        sections[0].location.z = deck_z + 1.7 + 2.6 * t
        sections[1].location.z = 2.6 * t
        sections[2].location.z = 2.6 * t
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
    animate_wheels()
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
            dict(target=(0, -1.0, 6.8), dist=27, az=-95, elev=4, res=(970, 600)),
        ),
        (100, 0.9, "quarter", dict(target=(0, -1.0, 5.5), dist=26, az=-45, elev=12)),
        (0, 0.0, "travel", dict(target=(0, 0.5, 2.2), dist=14, az=-50, elev=10)),
    )
    for frame, rot, name, kw in views:
        scn.frame_set(frame)
        head.rotation_euler = (0, 0, rot)
        render(f"{out}/IRAD_MatlaUlFajr_EWR_{name}.png", **kw)
