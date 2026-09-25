"""Bavar-373 TEL on the Zoljanah 10x10: two ribbed canister towers (two canisters
deep each) on a lattice erector, one central ram. 0 = travel, 90 deg = erect."""

import math
import sys

import bpy

sys.path.insert(0, sys.argv[-1])
from irad_kit import *  # noqa: E402,F403

L = 8.6  # canister length
CW, CD, GAP = 0.9, 1.75, 0.6  # tower width, depth (two canisters), gap between towers
ZB = 0.38  # towers sit this far above the erector truss
STEPS = 11


def build():
    reset()
    axles = [5.8, 4.15, -1.7, -3.4, -5.1]
    root, dz, rear, cab_back = iran_truck("IRAD_Bavar373_LN", axles, 14.0)
    # deck and side rails
    dlen = cab_back - rear
    box(
        "ln_deck",
        (2.5, dlen, 0.16),
        (0, (cab_back + rear) / 2, dz + 0.06),
        DARK(),
        root,
        0.01,
    )
    for s in (-1, 1):
        box(
            f"ln_deckedge{s}",
            (0.08, dlen, 0.24),
            (s * 1.25, (cab_back + rear) / 2, dz + 0.04),
            TRIM(),
            root,
            0.01,
        )
    # behind the cab: tall power unit, and the unit with the round intake
    box(
        "ln_powerunit",
        (1.25, 1.9, 1.95),
        (-0.6, cab_back - 1.1, dz + 1.1),
        PAINT(),
        root,
        0.05,
    )
    louvers("ln_pu_louver", (-1.22, cab_back - 1.1, dz + 1.2), 1.2, 0.9, 8, -1, root)
    box(
        "ln_pu_door",
        (0.02, 0.8, 1.3),
        (-1.235, cab_back - 1.6, dz + 1.0),
        TRIM(),
        root,
        0,
    )
    box(
        "ln_intakeunit",
        (1.05, 1.25, 1.15),
        (0.7, cab_back - 1.0, dz + 1.45),
        PAINT(),
        root,
        0.05,
    )
    box(
        "ln_intakeriser",
        (0.9, 1.05, 0.75),
        (0.7, cab_back - 1.0, dz + 0.5),
        DARK(),
        root,
        0.02,
    )
    cyl(
        "ln_intake",
        0.36,
        0.08,
        (1.23, cab_back - 1.0, dz + 1.45),
        (0, math.pi / 2, 0),
        DARK(),
        root,
        28,
    )
    cyl(
        "ln_intakering",
        0.42,
        0.06,
        (1.24, cab_back - 1.0, dz + 1.45),
        (0, math.pi / 2, 0),
        METAL(),
        root,
        28,
    )
    for k in range(4):
        box(
            f"ln_intakebar{k}",
            (0.03, 0.04, 0.7),
            (1.27, cab_back - 1.2 + k * 0.13, dz + 1.45),
            METAL(),
            root,
            0,
        )
    cyl(
        "ln_pu_exhaust",
        0.07,
        0.6,
        (-0.3, cab_back - 0.5, dz + 2.3),
        (0, 0, 0),
        METAL(),
        root,
        12,
    )
    # stabiliser jacks: two at the tail, two behind the cab
    for s in (-1, 1):
        for jy, tag in ((rear + 0.4, "r"), (cab_back - 0.2, "f")):
            box(
                f"ln_jackbeam{s}{tag}",
                (0.6, 0.3, 0.25),
                (s * 1.35, jy, dz - 0.15),
                DARK(),
                root,
                0.01,
            )
            cyl(
                f"ln_jackcyl{s}{tag}",
                0.12,
                1.05,
                (s * 1.6, jy, 0.65),
                (0, 0, 0),
                METAL(),
                root,
                16,
            )
            cyl(
                f"ln_jackpad{s}{tag}",
                0.3,
                0.07,
                (s * 1.6, jy, 0.04),
                (0, 0, 0),
                DARK(),
                root,
                20,
            )

    PZ = dz + 0.78
    P = (0, rear + 0.3, PZ)
    pivot = empty("arg_launcher_elevation", P, root)
    for s in (-1, 1):
        box(
            f"ln_pivotblock{s}",
            (0.3, 0.55, 1.0),
            (s * 1.1, P[1], dz + 0.5),
            DARK(),
            root,
            0.02,
        )
        cyl(
            f"ln_pivotpin{s}",
            0.13,
            0.4,
            (s * 1.1, P[1], PZ),
            (0, math.pi / 2, 0),
            METAL(),
            root,
            16,
        )
    OVER = PZ - 0.15  # tail overhang, so the erect base plate reaches the ground
    pack = empty("ln_pack", (0, 0, 0), pivot)

    # the two towers
    for t, tx in enumerate((-(GAP + CW) / 2, (GAP + CW) / 2)):
        zc = ZB + CD / 2
        box(f"ln_tower{t}", (CW, L, CD), (tx, L / 2 - OVER, zc), PAINT(), pack, 0.04)
        n = int(L / 0.32)
        for k in range(1, n):
            box(
                f"ln_t{t}_rib{k}",
                (CW + 0.2, 0.13, CD + 0.2),
                (tx, k * 0.32 - OVER, zc),
                PAINT(),
                pack,
                0.02,
            )
        box(
            f"ln_t{t}_topcap",
            (CW + 0.22, 0.16, CD + 0.22),
            (tx, L - OVER + 0.02, zc),
            PAINT(),
            pack,
            0.03,
        )
        box(
            f"ln_t{t}_topblock",
            (CW - 0.05, 0.22, CD - 0.05),
            (tx, L - OVER + 0.18, zc),
            PAINT(),
            pack,
            0.03,
        )
        box(
            f"ln_t{t}_foot",
            (CW + 0.25, 0.14, CD + 0.25),
            (tx, -OVER + 0.07, zc),
            METAL(),
            pack,
            0.02,
        )
        # square ports on the truck-facing face, above the erector
        for py in (0.74, 0.84):
            box(
                f"ln_t{t}_port{py}",
                (0.3, 0.3, 0.12),
                (tx, L * py - OVER, ZB + 0.02),
                DARK(),
                pack,
                0,
            )
        for d, dzc in enumerate((ZB + CD / 4, ZB + 3 * CD / 4)):
            empty(
                f"LAUNCH_{2 * t + d + 1}",
                (tx, L - OVER + 0.3, dzc),
                pack,
                (-math.pi / 2, 0, 0),
            )
        stencil(
            f"ln_t{t}_num",
            f"{2 * t + 1}-{2 * t + 2}",
            (tx, -OVER - 0.005, zc),
            (math.pi / 2, 0, 0),
            0.35,
            STRIPE(),
            pack,
        )
    box(
        "ln_baseplate",
        (2.9, 0.12, CD + 0.9),
        (0, -OVER - 0.02, ZB + CD / 2 - 0.2),
        METAL(),
        pack,
        0.02,
    )

    # lattice erector truss between the towers and the truck
    ty0, ty1, tz = -OVER + 0.2, -OVER + 5.6, 0.16
    for s in (-1, 1):
        box(
            f"ln_truss_chord{s}",
            (0.16, ty1 - ty0, 0.16),
            (s * 1.08, (ty0 + ty1) / 2, tz),
            PAINT(),
            pack,
            0.01,
        )
        for k in range(6):
            box(
                f"ln_truss_post{s}{k}",
                (0.1, 0.1, ZB),
                (s * 1.08, ty0 + k * (ty1 - ty0) / 5, tz + ZB / 2),
                PAINT(),
                pack,
                0,
            )
    box(
        "ln_truss_spine",
        (0.14, ty1 - ty0, 0.14),
        (0, (ty0 + ty1) / 2, tz),
        PAINT(),
        pack,
        0.01,
    )
    bays = 5
    for k in range(bays + 1):
        y = ty0 + k * (ty1 - ty0) / bays
        box(f"ln_truss_cross{k}", (2.3, 0.12, 0.12), (0, y, tz), PAINT(), pack, 0.01)
        if k < bays:
            y2 = ty0 + (k + 1) * (ty1 - ty0) / bays
            for s in (-1, 1):
                strut(
                    f"ln_truss_x{k}{s}a",
                    (s * 1.05, y, tz),
                    (0, y2, tz),
                    0.05,
                    PAINT(),
                    pack,
                )
                strut(
                    f"ln_truss_x{k}{s}b",
                    (0, y, tz),
                    (s * 1.05, y2, tz),
                    0.05,
                    PAINT(),
                    pack,
                )
    box("ln_truss_head", (2.4, 0.2, 0.3), (0, ty1, tz + 0.1), PAINT(), pack, 0.02)
    for s in (-1, 1):
        hose(
            f"ln_conduit{s}",
            [
                (s * 1.12, -OVER + 0.4, tz + 0.2),
                (s * 1.14, L * 0.4 - OVER, tz + 0.25),
                (s * 1.12, ty1, tz + 0.2),
            ],
            0.035,
            DARK(),
            pack,
        )
        hose(
            f"ln_hose{s}",
            [
                (s * 0.4, cab_back - 2.1, dz + 0.3),
                (s * 0.45, cab_back - 5.0, dz + 0.2),
                (s * 0.6, rear + 2.0, dz + 0.2),
                (s * 0.95, P[1] + 0.4, dz + 0.55),
            ],
            0.03,
            DARK(),
            root,
        )

    # the central ram: a 3-stage telescopic cylinder from the deck near the tail
    # to high on the truss, steep when erect as on the reference
    A_local = (0.0, 3.6, -0.26)
    B = (P[1] + 2.0, dz + 0.3)

    def a_world(th):
        y, z = A_local[1], A_local[2]
        return (
            P[1] + y * math.cos(th) - z * math.sin(th),
            PZ + y * math.sin(th) + z * math.cos(th),
        )

    dists = [
        math.dist(a_world(math.radians(90 * i / (STEPS - 1))), B) for i in range(STEPS)
    ]
    Ls = min(dists) - 0.04  # every stage is this long; retracted they nest
    assert Ls + 2 * (Ls - 0.1) >= max(dists), "ram cannot reach full erection"
    box("ln_rambase", (0.5, 0.45, 0.26), (0, B[0], B[1] - 0.12), DARK(), root, 0.02)
    barrel = empty("ln_ram_barrel_pivot", (0, B[0], B[1]), root)
    cyl(
        "ln_ram_barrel",
        0.2,
        Ls,
        (0, -Ls / 2, 0),
        (math.pi / 2, 0, 0),
        METAL(),
        barrel,
        20,
    )
    stage1 = empty("ln_ram_stage1_slide", (0, 0, 0), barrel)
    cyl(
        "ln_ram_stage1",
        0.16,
        Ls,
        (0, -Ls / 2, 0),
        (math.pi / 2, 0, 0),
        CHROME(),
        stage1,
        18,
    )
    slide = empty("ln_ram_stage2_slide", (0, 0, 0), stage1)
    cyl(
        "ln_ram_stage2",
        0.12,
        Ls,
        (0, -Ls / 2, 0),
        (math.pi / 2, 0, 0),
        CHROME(),
        slide,
        16,
    )
    box(
        "ln_ramlug",
        (0.4, 0.3, 0.3),
        (0, A_local[1], A_local[2] + 0.1),
        DARK(),
        pack,
        0.02,
    )
    for i in range(STEPS):
        th = math.radians(90 * i / (STEPS - 1))
        f = i * 100 // (STEPS - 1)
        ay, az = a_world(th)
        vy, vz = ay - B[0], az - B[1]
        barrel.rotation_euler = (math.atan2(-vz, -vy), 0, 0)
        barrel.keyframe_insert("rotation_euler", frame=f)
        ext = (math.hypot(vy, vz) - Ls) / 2
        for stage in (stage1, slide):
            stage.location = (0, -ext, 0)
            stage.keyframe_insert("location", frame=f)
        pivot.rotation_euler = (th, 0, 0)
        pivot.keyframe_insert("rotation_euler", frame=f)

    shell = box("collision_shell", (2.9, 16.0, 4.4), (0, -1.0, 2.2), DARK(), root, 0)
    shell.hide_render = True


if __name__ == "__main__":
    out = sys.argv[-1]
    build()
    finalize("IRAD_Bavar373_LN")
    bpy.ops.wm.save_as_mainfile(filepath=f"{out}/IRAD_Bavar373_LN.blend")
    scn = bpy.context.scene
    views = (
        (0, "travel", dict(target=(0, 0.5, 2.0), dist=20, az=-40, elev=22)),
        (0, "cab", dict(target=(0, 5.5, 2.2), dist=9, az=-35, elev=12)),
        (50, "raising", dict(target=(0, -3, 3.2), dist=22, az=-70, elev=10)),
        (100, "erect", dict(target=(0, -3, 4.2), dist=24, az=-40, elev=12)),
        (100, "tail", dict(target=(0, -7.5, 3.5), dist=13, az=-150, elev=12)),
    )
    for frame, name, kw in views:
        scn.frame_set(frame)
        render(f"{out}/IRAD_Bavar373_LN_{name}.png", **kw)
