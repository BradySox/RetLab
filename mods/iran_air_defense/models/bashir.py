"""Bashir search radar (IRAD_Bashir_SR), matched to two photographs and a render: a green
6x6 with an equipment shelter behind the cab and a whip mast, a lattice tower at the rear
carrying a planar array of thirty element rows, outriggers down. Deployed only, like the
Meraj-4: the travel fold is not shown in any reference. The truck and shelter are flat
green; the tower and array carry upright black and tan stripes.

arg_antenna_azimuth: frames 0-100, one full turn of the array.
"""

import math
import sys

import bpy

sys.path.insert(0, sys.argv[-1])
import irad_kit  # noqa: E402
import khordad  # noqa: E402
from irad_kit import *  # noqa: E402,F403
from irad_kit import _flat, _on_face  # noqa: E402,F401

NAME = "IRAD_Bashir_SR"
STEPS = 11
GREEN = lambda: mat("irad_truckgreen", (0.07, 0.1, 0.05), 0.6)  # noqa: E731
khordad.BAND_SCALE = (2.2, 2.2, 0.06)  # upright stripes, as photographed
khordad.PALETTE = dict(
    base=(0.5, 0.4, 0.24),
    brown=(0.03, 0.03, 0.02),
    olive=(0.16, 0.12, 0.06),
    black=(0.02, 0.02, 0.02),
)


def tower(root, y, z0, h):
    """Four legs tapering from 1.4 m to 1.0 m square, three X-braced bays per face,
    equipment box at the foot, the two erecting rams on its front."""
    b, t = 0.7, 0.5
    corners = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    for k, (cx, cy) in enumerate(corners):
        strut(
            f"bs_leg{k}",
            (cx * b, y + cy * b, z0),
            (cx * t, y + cy * t, z0 + h),
            0.07,
            PAINT(),
            root,
            10,
        )
    for lvl in range(4):
        f = lvl / 3
        w = b + (t - b) * f
        zz = z0 + h * f
        for k in range(4):
            (ax, ay), (bx, by) = corners[k], corners[(k + 1) % 4]
            strut(
                f"bs_ring{lvl}{k}",
                (ax * w, y + ay * w, zz),
                (bx * w, y + by * w, zz),
                0.04,
                PAINT(),
                root,
                6,
            )
    for bay in range(3):
        f0, f1 = bay / 3, (bay + 1) / 3
        w0, w1 = b + (t - b) * f0, b + (t - b) * f1
        z0b, z1b = z0 + h * f0, z0 + h * f1
        for k in range(4):
            (ax, ay), (bx, by) = corners[k], corners[(k + 1) % 4]
            strut(
                f"bs_x{bay}{k}a",
                (ax * w0, y + ay * w0, z0b),
                (bx * w1, y + by * w1, z1b),
                0.025,
                PAINT(),
                root,
                6,
            )
            strut(
                f"bs_x{bay}{k}b",
                (bx * w0, y + by * w0, z0b),
                (ax * w1, y + ay * w1, z1b),
                0.025,
                PAINT(),
                root,
                6,
            )
    box("bs_towerbox", (1.0, 0.8, 0.8), (0, y, z0 + 0.45), PAINT(), root, 0.02)
    door("bs_towerboxdoor", (0.5, y, z0 + 0.45), "x", 1, 0.6, 0.6, root)
    box(
        "bs_towerpanel",
        (0.02, 0.8, 1.0),
        (0, y, z0 + h * 0.62),
        mat("irad_sheet", (0.6, 0.62, 0.62), 0.3, 0.6),
        root,
        0,
    )
    for s in (-1, 1):
        strut(
            f"bs_ram{s}",
            (s * 0.35, y + 1.6, z0 + 0.15),
            (s * 0.5, y + b * 0.78, z0 + h * 0.55),
            0.07,
            PAINT(),
            root,
            12,
        )
        strut(
            f"bs_ramrod{s}",
            (s * 0.5, y + b * 0.78, z0 + h * 0.55),
            (s * 0.52, y + 0.62, z0 + h * 0.7),
            0.04,
            CHROME(),
            root,
            10,
        )
        ladder(
            f"bs_towerladder{s}",
            (s * (t + 0.05), y, z0 + h),
            (s * (b + 0.05), y, z0 + 0.1),
            0.35,
            12,
            root,
        )
    box("bs_towertop", (1.3, 1.3, 0.12), (0, y, z0 + h + 0.06), PAINT(), root, 0.02)
    return z0 + h + 0.12


def array(head):
    """The planar array: 5.2 m wide, 1.9 m tall, thirty element rows on its face, a
    frame and back truss, the feed comb along its lower edge; tilted back 12 deg."""
    W, H, D = 5.2, 1.9, 0.28
    tilt = empty("bs_array_tilt", (0, 0, 0.65), head, (math.radians(-12), 0, 0))
    box("bs_arrayback", (W, D, H), (0, -D / 2, H / 2 + 0.25), PAINT(), tilt, 0.02)
    for r in range(30):
        z = 0.3 + (r + 0.5) * (H - 0.1) / 30
        box(f"bs_row{r}", (W - 0.06, 0.05, 0.035), (0, 0.02, z), PAINT(), tilt, 0)
    for s in (-1, 1):
        box(
            f"bs_frameside{s}",
            (0.08, D + 0.06, H + 0.06),
            (s * W / 2, -D / 2, H / 2 + 0.25),
            PAINT(),
            tilt,
            0.01,
        )
    for zz in (0.25, H + 0.25):
        box(
            f"bs_frametop{zz:.1f}",
            (W + 0.06, D + 0.06, 0.06),
            (0, -D / 2, zz),
            PAINT(),
            tilt,
            0.01,
        )
    # back truss to the pedestal
    for s in (-1, 1):
        strut(
            f"bs_backbrace{s}",
            (0, -D - 0.1, 0.15),
            (s * W * 0.42, -D, H * 0.8),
            0.035,
            METAL(),
            tilt,
            6,
        )
        strut(
            f"bs_backbrace_low{s}",
            (0, -D - 0.1, 0.15),
            (s * W * 0.45, -D, 0.35),
            0.035,
            METAL(),
            tilt,
            6,
        )
    # feed comb under the array
    box("bs_comb", (W - 0.3, 0.12, 0.1), (0, 0.05, 0.12), PAINT(), tilt, 0.01)
    for k in range(26):
        x = -W / 2 + 0.25 + k * (W - 0.5) / 25
        box(f"bs_tooth{k}", (0.04, 0.06, 0.18), (x, 0.08, 0.02), PAINT(), tilt, 0)
    return tilt


def build():
    reset()
    khordad.band_camo()
    irad_kit.PAINT = GREEN  # truck and shelter flat green, as photographed
    axles = [3.9, -1.7, -3.1]
    root, dz, rear, cab_back = iran_truck(
        NAME, axles, 11.0, width=2.5, cab_len=2.3, frame_h=1.3, wheel_r=0.6
    )
    box(
        "bs_deck",
        (2.45, cab_back - rear, 0.14),
        (0, (cab_back + rear) / 2, dz + 0.05),
        GREEN(),
        root,
        0.01,
    )
    for s in (-1, 1):
        box(
            f"bs_deckedge{s}",
            (0.08, cab_back - rear, 0.22),
            (s * 1.23, (cab_back + rear) / 2, dz + 0.02),
            GREEN(),
            root,
            0.01,
        )
    # equipment shelter behind the cab, green like the cab: door, stair, AC, whip mast
    sy0, sy1, sh = cab_back - 0.15, cab_back - 1.75, 2.75
    scy = (sy0 + sy1) / 2
    box(
        "bs_shelter",
        (2.4, sy0 - sy1, sh),
        (0, scy, dz + 0.12 + sh / 2),
        GREEN(),
        root,
        0.04,
    )
    top = dz + 0.12 + sh
    door(
        "bs_shelterdoor",
        (1.2, scy - 0.2, dz + 1.1),
        "x",
        1,
        0.8,
        1.7,
        root,
        hinge_side=1,
    )
    ladder(
        "bs_stair", (1.45, scy - 0.2, dz + 0.05), (2.05, scy - 0.2, 0.02), 0.6, 5, root
    )
    handrail(
        "bs_stairrail",
        [(1.55, scy + 0.15, dz + 0.1), (2.05, scy + 0.15, 0.05)],
        root,
        0.9,
    )
    ladder(
        "bs_roofladder",
        (1.25, sy1 + 0.25, top + 0.4),
        (1.25, sy1 + 0.25, dz + 0.2),
        0.4,
        8,
        root,
    )
    box("bs_ac", (0.3, 0.7, 0.6), (-1.35, scy, top - 0.6), GREEN(), root, 0.02)
    grille("bs_acgrille", (-1.5, scy, top - 0.6), "x", -1, 0.55, 0.45, root, 6)
    grille("bs_sidevent", (1.2, sy1 + 0.6, top - 0.5), "x", 1, 0.5, 0.35, root, 5)
    box("bs_roofbox", (1.0, 0.8, 0.4), (-0.4, scy, top + 0.2), GREEN(), root, 0.02)
    handrail(
        "bs_roofrail",
        [(-1.1, sy0 - 0.1, top), (1.1, sy0 - 0.1, top), (1.1, sy1 + 0.1, top)],
        root,
        0.5,
    )
    cyl(
        "bs_mastbase",
        0.1,
        0.4,
        (-0.95, sy0 - 0.2, top + 0.2),
        (0, 0, 0),
        METAL(),
        root,
        12,
    )
    cyl(
        "bs_mast0",
        0.05,
        3.2,
        (-0.95, sy0 - 0.2, top + 2.0),
        (0, 0, 0),
        METAL(),
        root,
        10,
    )
    cyl(
        "bs_mast1",
        0.03,
        2.6,
        (-0.95, sy0 - 0.2, top + 4.9),
        (0, 0, 0),
        METAL(),
        root,
        8,
    )
    cyl(
        "bs_masttip",
        0.06,
        0.25,
        (-0.95, sy0 - 0.2, top + 6.3),
        (0, 0, 0),
        DARK(),
        root,
        10,
    )
    cyl("bs_whip2", 0.015, 1.6, (0.9, sy0 - 0.3, top + 0.8), (0, 0, 0), DARK(), root, 6)
    # stowage along the deck between the shelter and the tower
    for k, (y, w) in enumerate(((sy1 - 0.8, 1.0), (sy1 - 2.0, 0.8))):
        box(f"bs_stowbox{k}", (0.9, w, 0.5), (-0.7, y, dz + 0.37), GREEN(), root, 0.02)
    cable_reel("bs_reel", (0.7, sy1 - 1.2, dz + 0.45), root, 0.3, 0.4)
    irad_kit.PAINT = camo  # the tower and array carry the stripes
    # the tower at the rear
    ty = rear + 1.0
    tz = tower(root, ty, dz + 0.12, 4.2)
    cyl("bs_turntable", 0.45, 0.2, (0, ty, tz + 0.1), (0, 0, 0), METAL(), root, 24)
    head = empty("arg_antenna_azimuth", (0, ty, tz + 0.2), root)
    box("bs_pedestal", (0.7, 0.6, 0.55), (0, -0.1, 0.28), PAINT(), head, 0.02)
    cyl("bs_rotjoint", 0.2, 0.2, (0, 0, 0.1), (0, 0, 0), METAL(), head, 16)
    box("bs_iffbox", (0.4, 0.3, 0.3), (0.5, -0.3, 0.2), PAINT(), head, 0.02)
    hose(
        "bs_headcable",
        [(0.2, -0.4, 0.2), (0.35, -0.5, -0.3), (0.5, -0.4, -0.7)],
        0.02,
        DARK(),
        head,
    )
    array(head)
    # outriggers: splayed legs at the rear corners, screw jacks mid-deck
    for s in (-1, 1):
        strut(
            f"bs_rearleg{s}",
            (s * 1.0, rear + 0.4, dz - 0.2),
            (s * 2.0, rear - 0.2, 0.35),
            0.08,
            PAINT(),
            root,
            10,
        )
        screw_jack(f"bs_rearjack{s}", s * 2.0, rear - 0.2, 0.75, root)
        box(
            f"bs_midarm{s}",
            (0.5, 0.25, 0.2),
            (s * 1.15, -0.4, dz - 0.35),
            DARK(),
            root,
            0.01,
        )
        screw_jack(f"bs_midjack{s}", s * 1.42, -0.4, dz - 0.25, root)
        ladder(
            f"bs_rearstair{s}",
            (s * 0.6, rear - 0.05, dz),
            (s * 0.6, rear - 0.7, 0.02),
            0.5,
            4,
            root,
            axis="x",
        )
    for i in range(STEPS):
        f = i * 100 // (STEPS - 1)
        head.rotation_euler = (0, 0, 2 * math.pi * i / (STEPS - 1))
        head.keyframe_insert("rotation_euler", frame=f)
    shell = box("collision_shell", (4.2, 11.8, 8.8), (0, 0, 4.4), DARK(), root, 0)
    shell.hide_render = True
    return head


if __name__ == "__main__":
    out = sys.argv[-1]
    head = build()
    finalize(NAME)
    animate_wheels()
    bpy.context.scene.frame_set(0)
    if "--bake" in sys.argv:
        bake_camo(out, NAME)
    bpy.ops.wm.save_as_mainfile(filepath=f"{out}/{NAME}.blend")
    head.animation_data_clear()
    scn = bpy.context.scene
    for rot, view, kw in (
        (
            math.pi / 2,
            "photo",
            dict(target=(0, -0.5, 4.0), dist=20, az=-80, elev=4, res=(1280, 720)),
        ),
        (
            0.4,
            "quarter",
            dict(target=(0, -0.5, 3.8), dist=21, az=-40, elev=8, res=(1280, 720)),
        ),
    ):
        head.rotation_euler = (0, 0, rot)
        render(f"{out}/{NAME}_{view}.png", **kw)
