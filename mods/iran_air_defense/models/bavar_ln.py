"""Bavar-373 TEL, matched to a Tasnim photograph: an 8x8 with an AC platform over
the cab, two ribbed canister towers (two canisters deep each) on a grid erector
raised by two rams from mid-deck. 0 = travel, 90 deg = erect."""

import math
import sys

import bpy

sys.path.insert(0, sys.argv[-1])
from irad_kit import *  # noqa: E402,F403

L = 7.8  # canister length
CW, CD, GAP = 0.95, 1.35, 0.25  # tower width, depth (two canisters), gap between towers
ZB = 0.34  # towers stand this far off the erector frame
STEPS = 11


def tower(t, tx, OVER, pack):
    """One tower: skin, grid of bands and stringers, flanges, the mid-depth clamp."""
    zc = ZB + CD / 2
    box(f"ln_tower{t}", (CW, L, CD), (tx, L / 2 - OVER, zc), PAINT(), pack, 0.03)
    for k in range(1, int(L / 0.42)):
        y = k * 0.42 - OVER
        box(
            f"ln_t{t}_band{k}",
            (CW + 0.07, 0.06, CD + 0.07),
            (tx, y, zc),
            PAINT(),
            pack,
            0.01,
        )
    for side in (-1, 1):
        for f in (-0.33, 0.33):
            box(
                f"ln_t{t}_strx{side}{f}",
                (0.05, L, 0.06),
                (tx + side * (CW / 2 + 0.03), L / 2 - OVER, zc + f * CD),
                PAINT(),
                pack,
                0,
            )
            box(
                f"ln_t{t}_strz{side}{f}",
                (0.06, L, 0.05),
                (tx + f * CW, L / 2 - OVER, zc + side * (CD / 2 + 0.03)),
                PAINT(),
                pack,
                0,
            )
    # flanges every quarter: the transport clamps between the upper and lower canister
    for q in (0.12, 0.38, 0.62, 0.88):
        for side in (-1, 1):
            box(
                f"ln_t{t}_clamp{q}{side}",
                (0.14, 0.22, 0.16),
                (tx + side * (CW / 2 + 0.08), L * q - OVER, zc),
                DARK(),
                pack,
                0.01,
            )
    box(
        f"ln_t{t}_topflange",
        (CW + 0.16, 0.12, CD + 0.16),
        (tx, L - OVER, zc),
        PAINT(),
        pack,
        0.02,
    )
    for c, (dx, dz) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
        box(
            f"ln_t{t}_post{c}",
            (0.08, 0.35, 0.08),
            (tx + dx * CW / 2, L - OVER + 0.15, zc + dz * CD / 2),
            PAINT(),
            pack,
            0,
        )
    box(
        f"ln_t{t}_foot",
        (CW + 0.14, 0.12, CD + 0.14),
        (tx, -OVER + 0.06, zc),
        METAL(),
        pack,
        0.01,
    )
    for d, dzc in enumerate((ZB + CD / 4, ZB + 3 * CD / 4)):
        empty(
            f"LAUNCH_{2 * t + d + 1}",
            (tx, L - OVER + 0.2, dzc),
            pack,
            (-math.pi / 2, 0, 0),
        )


def build():
    reset()
    axles = [4.9, 3.3, -2.5, -4.1]
    root, dz, rear, cab_back = iran_truck(
        "IRAD_Bavar373_LN", axles, 12.6, cab_len=2.3, wheel_r=0.76
    )
    front = 12.6 / 2
    cab_top = dz - 0.2 + 2.3
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
            (0.08, dlen, 0.26),
            (s * 1.25, (cab_back + rear) / 2, dz + 0.03),
            PAINT(),
            root,
            0.01,
        )

    # behind the cab: a low cabinet, then a tall one; ladder up the side to the platform
    c1y, c2y = cab_back - 0.55, cab_back - 1.75
    box("ln_cab1", (2.45, 1.0, 1.95), (0, c1y, dz + 1.05), PAINT(), root, 0.03)
    box("ln_cab2", (2.45, 1.3, 2.55), (0, c2y, dz + 1.35), PAINT(), root, 0.03)
    for s in (-1, 1):
        for n, (y, h, z) in enumerate(((c1y, 1.2, dz + 1.25), (c2y, 1.6, dz + 1.6))):
            for k, (sz, off) in enumerate(
                (
                    ((0.02, 0.8, 0.02), (0, h / 2)),
                    ((0.02, 0.8, 0.02), (0, -h / 2)),
                    ((0.02, 0.02, h), (0.4, 0)),
                    ((0.02, 0.02, h), (-0.4, 0)),
                )
            ):
                box(
                    f"ln_cabseam{s}{n}{k}",
                    sz,
                    (s * 1.232, y + off[0], z + off[1]),
                    DARK(),
                    root,
                    0,
                )
            box(
                f"ln_cablatch{s}{n}",
                (0.04, 0.08, 0.12),
                (s * 1.25, y - 0.3, z),
                METAL(),
                root,
                0,
            )
            louvers(
                f"ln_cabvent{s}{n}", (s * 1.23, y, dz + 0.45), 0.7, 0.35, 4, s, root
            )
    for rail in (-1, 1):
        box(
            f"ln_ladrail{rail}",
            (0.04, 0.04, 2.3),
            (1.28, c1y + rail * 0.2, dz + 1.3),
            METAL(),
            root,
            0,
        )
    for k in range(8):
        box(
            f"ln_ladrung{k}",
            (0.06, 0.42, 0.03),
            (1.28, c1y, dz + 0.3 + k * 0.28),
            METAL(),
            root,
            0,
        )

    # AC platform over the cab: posts, frame, two fan boxes forward and two vent boxes aft
    pz = cab_top + 0.45
    py0, py1 = c1y - 0.2, front - 0.1
    box(
        "ln_platform",
        (2.5, py1 - py0, 0.1),
        (0, (py0 + py1) / 2, pz),
        DARK(),
        root,
        0.01,
    )
    for s in (-1, 1):
        box(
            f"ln_platrail{s}",
            (0.06, py1 - py0, 0.14),
            (s * 1.24, (py0 + py1) / 2, pz - 0.05),
            PAINT(),
            root,
            0,
        )
        cyl(
            f"ln_platpost{s}",
            0.04,
            pz - (dz - 0.3),
            (s * 1.2, front - 0.15, (pz + dz - 0.3) / 2),
            (0, 0, 0),
            PAINT(),
            root,
            10,
        )
        strut(
            f"ln_platbrace{s}",
            (s * 1.1, cab_back + 0.1, cab_top - 0.1),
            (s * 1.1, cab_back + 1.1, pz - 0.05),
            0.04,
            PAINT(),
            root,
        )
    hose(
        "ln_platpipes",
        [
            (0.3, c1y + 0.2, cab_top + 0.1),
            (0.3, cab_back + 0.6, cab_top + 0.2),
            (0.3, cab_back + 1.4, pz - 0.1),
        ],
        0.07,
        METAL(),
        root,
    )
    unit_z = pz + 0.45
    fwd = [py1 - 0.65, py1 - 1.85]
    aft = py0 + 0.55
    for s in (-1, 1):
        for n, y in enumerate(fwd):
            box(
                f"ln_acbox{s}{n}",
                (1.2, 1.15, 0.8),
                (s * 0.62, y, unit_z),
                PAINT(),
                root,
                0.02,
            )
            for k, dy in enumerate((-0.28, 0.28)):
                fan(
                    f"ln_acfan{s}{n}{k}",
                    (s * 1.22, y + dy, unit_z),
                    ("+x" if s > 0 else "-x"),
                    0.25,
                    root,
                )
            for c in (-1, 1):
                cyl(
                    f"ln_aceye{s}{n}{c}",
                    0.04,
                    0.02,
                    (s * 0.62 + c * 0.5, y, unit_z + 0.43),
                    (math.pi / 2, 0, 0),
                    METAL(),
                    root,
                    10,
                )
        box(
            f"ln_ventbox{s}",
            (1.2, 0.95, 0.8),
            (s * 0.62, aft, unit_z),
            PAINT(),
            root,
            0.02,
        )
        box(
            f"ln_ventmesh{s}",
            (0.02, 0.7, 0.55),
            (s * 1.225, aft, unit_z),
            DARK(),
            root,
            0,
        )
        for k in range(6):
            box(
                f"ln_ventbar{s}{k}",
                (0.03, 0.02, 0.55),
                (s * 1.235, aft - 0.3 + k * 0.12, unit_z),
                PAINT(),
                root,
                0,
            )

    # mid-deck fan boxes, ahead of the ram bases
    fy = c2y - 1.45
    for n, y in enumerate((fy, fy - 0.9)):
        box(f"ln_fanbox{n}", (2.2, 0.85, 1.05), (0, y, dz + 0.68), PAINT(), root, 0.03)
        for s in (-1, 1):
            fan(
                f"ln_boxfan{n}{s}",
                (s * 1.1, y, dz + 0.78),
                ("+x" if s > 0 else "-x"),
                0.2,
                root,
            )

    # stabiliser jacks: behind the front axles and at the tail
    for s in (-1, 1):
        for jy, tag in ((axles[1] - 0.9, "f"), (rear + 0.35, "r")):
            box(
                f"ln_jackbeam{s}{tag}",
                (0.55, 0.3, 0.25),
                (s * 1.3, jy, dz - 0.15),
                DARK(),
                root,
                0.01,
            )
            cyl(
                f"ln_jackcyl{s}{tag}",
                0.1,
                1.05,
                (s * 1.55, jy, 0.65),
                (0, 0, 0),
                METAL(),
                root,
                14,
            )
            cyl(
                f"ln_jackpad{s}{tag}",
                0.26,
                0.06,
                (s * 1.55, jy, 0.03),
                (0, 0, 0),
                DARK(),
                root,
                18,
            )

    PZ = dz + 1.1
    P = (0, rear + 0.25, PZ)
    pivot = empty("arg_launcher_elevation", P, root)
    for s in (-1, 1):
        box(
            f"ln_hinge{s}",
            (0.28, 0.6, 1.3),
            (s * 1.12, P[1], dz + 0.55),
            PAINT(),
            root,
            0.02,
        )
        cyl(
            f"ln_hingepin{s}",
            0.12,
            0.36,
            (s * 1.12, P[1], PZ),
            (0, math.pi / 2, 0),
            METAL(),
            root,
            16,
        )
    cyl(
        "ln_tailleg",
        0.07,
        dz + 0.1,
        (0, rear + 0.1, (dz + 0.1) / 2),
        (0, 0, 0),
        METAL(),
        root,
        12,
    )
    OVER = PZ - 0.1
    pack = empty("ln_pack", (0, 0, 0), pivot)
    for t, tx in enumerate((-(GAP + CW) / 2, (GAP + CW) / 2)):
        tower(t, tx, OVER, pack)
    # base wedge under the tower feet
    box(
        "ln_basewedge",
        (2.5, 0.35, CD + 0.5),
        (0, -OVER - 0.1, ZB + CD / 2),
        PAINT(),
        pack,
        0.03,
    )

    # grid erector: side rails, a solid lower panel, a grid above it, gussets at the hinge
    fy0, fy1, fz, fw = -OVER + 0.3, -OVER + 5.3, 0.14, 2.2
    for s in (-1, 1):
        box(
            f"ln_er_rail{s}",
            (0.16, fy1 - fy0, 0.2),
            (s * fw / 2, (fy0 + fy1) / 2, fz),
            PAINT(),
            pack,
            0.01,
        )
        strut(
            f"ln_er_gusset{s}",
            (s * fw / 2, fy0, fz),
            (s * 0.3, fy0 + 1.2, fz),
            0.05,
            PAINT(),
            pack,
        )
    split = fy0 + (fy1 - fy0) * 0.5
    box(
        "ln_er_panel",
        (fw, split - fy0, 0.05),
        (0, (fy0 + split) / 2, fz),
        PAINT(),
        pack,
        0.01,
    )
    for k in range(5):
        y = split + k * (fy1 - split) / 4
        box(f"ln_er_rung{k}", (fw, 0.1, 0.12), (0, y, fz), PAINT(), pack, 0)
    for x in (-0.55, 0, 0.55):
        box(
            f"ln_er_bar{x}",
            (0.08, fy1 - split, 0.1),
            (x, (split + fy1) / 2, fz),
            PAINT(),
            pack,
            0,
        )
    for s in (-1, 1):
        strut(
            f"ln_er_diag{s}",
            (s * fw / 2, split, fz),
            (s * 0.55, split + 0.9, fz),
            0.04,
            PAINT(),
            pack,
        )
    box("ln_er_head", (fw + 0.2, 0.18, 0.28), (0, fy1, fz + 0.06), PAINT(), pack, 0.02)
    for s in (-1, 1):
        box(
            f"ln_er_ear{s}",
            (0.12, 0.3, 0.3),
            (s * (fw / 2 + 0.1), fy1 + 0.1, fz + 0.1),
            PAINT(),
            pack,
            0.01,
        )

    # two rams from mid-deck to low on the erector rails, shallow as photographed
    A = (2.0, -0.18)  # pack-local (y along the pack, z below it)
    B = (P[1] + 6.1, dz + 0.45)

    def a_world(th):
        return (
            P[1] + A[0] * math.cos(th) - A[1] * math.sin(th),
            PZ + A[0] * math.sin(th) + A[1] * math.cos(th),
        )

    dists = [
        math.dist(a_world(math.radians(90 * i / (STEPS - 1))), B) for i in range(STEPS)
    ]
    Ls = min(dists) - 0.05
    assert 2 * Ls - 0.2 >= max(dists), "ram cannot reach full erection"
    rams = []
    for s in (-1, 1):
        x = s * 0.62
        box(
            f"ln_rambase{s}",
            (0.3, 0.4, 0.28),
            (x, B[0], B[1] - 0.14),
            DARK(),
            root,
            0.02,
        )
        box(
            f"ln_ramlug{s}",
            (0.2, 0.25, 0.25),
            (x, A[0], A[1] + 0.05),
            DARK(),
            pack,
            0.01,
        )
        barrel = empty(f"ln_ram_barrel_pivot{s}", (x, B[0], B[1]), root)
        cyl(
            f"ln_ram_barrel{s}",
            0.12,
            Ls,
            (0, -Ls / 2, 0),
            (math.pi / 2, 0, 0),
            PAINT(),
            barrel,
            18,
        )
        cyl(
            f"ln_ram_collar{s}",
            0.14,
            0.12,
            (0, -Ls + 0.06, 0),
            (math.pi / 2, 0, 0),
            PAINT(),
            barrel,
            18,
        )
        rod = empty(f"ln_ram_rod_slide{s}", (0, 0, 0), barrel)
        cyl(
            f"ln_ram_rod{s}",
            0.07,
            Ls,
            (0, -Ls / 2, 0),
            (math.pi / 2, 0, 0),
            METAL(),
            rod,
            14,
        )
        rams.append((barrel, rod))
    for i in range(STEPS):
        th = math.radians(90 * i / (STEPS - 1))
        f = i * 100 // (STEPS - 1)
        ay, az = a_world(th)
        vy, vz = ay - B[0], az - B[1]
        for barrel, rod in rams:
            barrel.rotation_euler = (math.atan2(-vz, -vy), 0, 0)
            barrel.keyframe_insert("rotation_euler", frame=f)
            rod.location = (0, -(math.hypot(vy, vz) - Ls), 0)
            rod.keyframe_insert("location", frame=f)
        pivot.rotation_euler = (th, 0, 0)
        pivot.keyframe_insert("rotation_euler", frame=f)

    shell = box("collision_shell", (2.8, 14.6, 4.2), (0, -1.0, 2.1), DARK(), root, 0)
    shell.hide_render = True


if __name__ == "__main__":
    out = sys.argv[-1]
    build()
    finalize("IRAD_Bavar373_LN")
    bpy.context.scene.frame_set(0)
    bake_camo(out, "IRAD_Bavar373_LN")
    bpy.ops.wm.save_as_mainfile(filepath=f"{out}/IRAD_Bavar373_LN.blend")
    scn = bpy.context.scene
    views = (
        (0, "travel", dict(target=(0, -0.5, 2.0), dist=17, az=-60, elev=8)),
        (0, "cab", dict(target=(0.5, 4.0, 2.4), dist=8.5, az=-40, elev=6)),
        (50, "raising", dict(target=(0, -2.5, 3.0), dist=19, az=-80, elev=6)),
        (100, "erect", dict(target=(0, -2.0, 3.6), dist=19, az=-55, elev=6)),
        (100, "side", dict(target=(0, -1.5, 3.5), dist=20, az=-90, elev=2)),
    )
    for frame, name, kw in views:
        scn.frame_set(frame)
        render(f"{out}/IRAD_Bavar373_LN_{name}.png", **kw)
