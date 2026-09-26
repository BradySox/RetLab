"""Bavar-373 command post (IRAD_Bavar373_CP), matched to a parade photograph: a 6x6
carrying one long equipment shelter, a door at its front, an AC unit and a rolled
camouflage net at the rear. No moving parts."""

import math
import sys

import bpy

sys.path.insert(0, sys.argv[-1])
from irad_kit import *  # noqa: E402,F403
from irad_kit import _flat, _on_face  # noqa: E402,F401


def build():
    reset()
    axles = [3.6, -1.9, -3.25]
    root, dz, rear, cab_back = iran_truck(
        "IRAD_Bavar373_CP", axles, 9.6, cab_len=2.2, wheel_r=0.7
    )
    sy0, sy1, sh = cab_back - 0.9, rear + 0.1, 2.8
    scy, slen = (sy0 + sy1) / 2, sy0 - sy1
    box("cp_subframe", (2.3, slen, 0.2), (0, scy, dz + 0.02), DARK(), root, 0.01)
    box(
        "cp_shelter", (2.5, slen, sh), (0, scy, dz + 0.12 + sh / 2), PAINT(), root, 0.05
    )
    box(
        "cp_roofedge",
        (2.56, slen + 0.06, 0.08),
        (0, scy, dz + 0.12 + sh),
        PAINT(),
        root,
        0.02,
    )
    top = dz + 0.12 + sh
    # the gap behind the cab, as photographed: exhaust stack, air cleaner, frame cross-member
    gy = (cab_back + sy0) / 2
    cyl("cp_exhaust", 0.08, 2.6, (0.95, gy, dz + 1.1), (0, 0, 0), CHROME(), root, 14)
    cyl(
        "cp_exhaustguard", 0.12, 0.9, (0.95, gy, dz + 1.3), (0, 0, 0), METAL(), root, 14
    )
    cyl(
        "cp_exhausttip",
        0.08,
        0.2,
        (0.95, gy + 0.05, dz + 2.45),
        (0.5, 0, 0),
        METAL(),
        root,
        14,
    )
    cyl("cp_aircleaner", 0.25, 0.8, (-0.85, gy, dz + 0.8), (0, 0, 0), PAINT(), root, 20)
    cyl("cp_aircap", 0.28, 0.08, (-0.85, gy, dz + 1.22), (0, 0, 0), METAL(), root, 20)
    strut(
        "cp_airpipe",
        (-0.85, gy, dz + 1.25),
        (-0.85, gy + 0.3, dz + 1.7),
        0.08,
        DARK(),
        root,
    )
    box("cp_crossmember", (2.2, 0.25, 0.2), (0, gy, dz - 0.05), DARK(), root, 0.01)
    hose(
        "cp_airlines",
        [(-0.6, cab_back, dz + 0.4), (-0.3, gy, dz + 0.1), (0.2, sy0 + 0.1, dz + 0.1)],
        0.02,
        DARK(),
        root,
    )

    # ISO-style corner castings, a bottom rail and a roof lip on every edge
    for sx in (-1, 1):
        for sy in (sy0, sy1):
            for sz in (dz + 0.2, top - 0.08):
                box(
                    f"cp_corner{sx}{sy:.0f}{sz:.0f}",
                    (0.18, 0.18, 0.16),
                    (sx * 1.2, sy - (0.06 if sy == sy0 else -0.06), sz),
                    METAL(),
                    root,
                    0.01,
                )
        box(
            f"cp_bottomrail{sx}",
            (0.06, slen - 0.3, 0.12),
            (sx * 1.26, scy, dz + 0.2),
            PAINT(),
            root,
            0.01,
        )
    for sy in (sy0, sy1):
        box(f"cp_endlip{sy:.0f}", (2.56, 0.06, 0.08), (0, sy, top), PAINT(), root, 0.01)
    # door at the front of the left side, a folding step, a grab rail beside it
    dy = sy0 - 0.8
    door("cp_door", (-1.25, dy, dz + 1.25), "x", -1, 0.9, 1.95, root, hinge_side=1)
    ladder("cp_doorstep", (-1.45, dy, dz - 0.05), (-1.6, dy, 0.4), 0.7, 2, root)
    strut(
        "cp_grabrail",
        (-1.34, dy + 0.55, dz + 0.6),
        (-1.34, dy + 0.55, dz + 1.9),
        0.02,
        METAL(),
        root,
    )
    door("cp_door_r", (1.25, dy, dz + 1.25), "x", 1, 0.9, 1.95, root, hinge_side=-1)
    box("cp_door_rstep", (0.35, 0.8, 0.05), (1.43, dy, dz - 0.25), METAL(), root, 0)
    # cable entry panel and a vent grille on each side
    for sx in (-1, 1):
        box(
            f"cp_cablepanel{sx}",
            (0.06, 0.6, 0.45),
            (sx * 1.28, sy1 + 1.2, dz + 0.55),
            PAINT(),
            root,
            0.01,
        )
        for k in range(4):
            cyl(
                f"cp_connector{sx}{k}",
                0.045,
                0.08,
                (sx * 1.33, sy1 + 1.0 + k * 0.13, dz + 0.55),
                (0, math.pi / 2, 0),
                METAL(),
                root,
                10,
            )
        grille(
            f"cp_vent{sx}",
            (sx * 1.25, scy - 0.3, top - 0.45),
            "x",
            sx,
            0.5,
            0.35,
            root,
            5,
        )
    # front face: ladder to the roof at the corner, a cable reel, a stowage rack
    ladder(
        "cp_roofladder",
        (-1.05, sy0 + 0.08, top + 0.3),
        (-1.05, sy0 + 0.08, dz + 0.3),
        0.4,
        8,
        root,
        axis="y",
    )
    cable_reel("cp_frontreel", (0.55, sy0 + 0.3, dz + 0.55), root, 0.3, 0.45)
    box(
        "cp_frontrack",
        (0.5, 0.3, 1.5),
        (0.2, sy0 + 0.17, dz + 1.45),
        PAINT(),
        root,
        0.02,
    )
    # roof: a front grab rail, vents, walkway strip and two antenna mounts
    handrail(
        "cp_roofrail",
        [(-1.15, sy0 - 0.1, top + 0.04), (1.15, sy0 - 0.1, top + 0.04)],
        root,
        0.45,
    )
    box("cp_roofwalk", (0.6, slen - 0.8, 0.03), (0.6, scy, top + 0.05), DARK(), root, 0)
    for k in range(3):
        box(
            f"cp_roofvent{k}",
            (0.5, 0.5, 0.15),
            (-0.5, sy0 - 1.2 - k * 1.6, top + 0.1),
            PAINT(),
            root,
            0.02,
        )
        louvers(
            f"cp_roofventl{k}",
            (-0.25, sy0 - 1.2 - k * 1.6, top + 0.1),
            0.4,
            0.1,
            3,
            1,
            root,
        )
    for k, ay in enumerate((sy0 - 0.5, sy1 + 0.8)):
        cyl(
            f"cp_antbase{k}",
            0.08,
            0.2,
            (0.8, ay, top + 0.1),
            (0, 0, 0),
            DARK(),
            root,
            10,
        )
        cyl(
            f"cp_antspring{k}",
            0.035,
            0.18,
            (0.8, ay, top + 0.29),
            (0, 0, 0),
            METAL(),
            root,
            8,
        )
        cyl(
            f"cp_antenna{k}",
            0.015,
            2.2 - k * 0.8,
            (0.8, ay, top + 1.48 - k * 0.4),
            (0, 0, 0),
            DARK(),
            root,
            6,
        )
    # rear: the AC unit low on the rear face, the camouflage net rolled upright above it
    box("cp_acshelf", (1.1, 0.7, 0.06), (0.6, sy1 - 0.35, dz + 0.3), METAL(), root, 0)
    box("cp_ac", (0.9, 0.6, 0.9), (0.6, sy1 - 0.32, dz + 0.78), PAINT(), root, 0.03)
    grille("cp_acgrille", (1.05, sy1 - 0.32, dz + 0.8), "x", 1, 0.45, 0.7, root, 7)
    fan("cp_acfan", (0.6, sy1 - 0.62, dz + 0.8), "-y", 0.28, root)
    netmat = mat("irad_net", (0.3, 0.26, 0.16), 0.95)
    cyl(
        "cp_net",
        0.36,
        sh - 1.3,
        (0.55, sy1 - 0.38, dz + 1.3 + (sh - 1.3) / 2),
        (0, 0, 0),
        netmat,
        root,
        18,
    )
    for k in range(3):
        cyl(
            f"cp_netbulge{k}",
            0.39,
            0.12,
            (0.55, sy1 - 0.38, dz + 1.45 + k * 0.45),
            (0, 0, 0),
            netmat,
            root,
            18,
        )
    for k in (0, 1):
        box(
            f"cp_netstrap{k}",
            (0.8, 0.8, 0.06),
            (0.55, sy1 - 0.38, dz + 1.6 + k * 0.7),
            DARK(),
            root,
            0,
        )
    ladder(
        "cp_rearladder",
        (-0.7, sy1 - 0.08, top + 0.2),
        (-0.7, sy1 - 0.08, dz + 0.3),
        0.4,
        7,
        root,
        axis="y",
    )
    # underbody lockers between the front axle and the tandem
    ly = (axles[0] + axles[1]) / 2 - 0.4
    for sx in (-1, 1):
        box(
            f"cp_locker{sx}",
            (0.55, 1.4, 0.6),
            (sx * 0.95, ly, dz - 0.45),
            PAINT(),
            root,
            0.02,
        )
        door(f"cp_lockerdoor{sx}", (sx * 1.22, ly, dz - 0.45), "x", sx, 1.2, 0.45, root)
    # screw jacks, all four corners
    for sx in (-1, 1):
        for jy in (axles[0] - 1.2, rear + 0.4):
            screw_jack(f"cp_jack{sx}{jy:.0f}", sx * 1.32, jy, dz - 0.2, root)
    shell = box("collision_shell", (2.7, 9.8, 4.3), (0, 0, 2.15), DARK(), root, 0)
    shell.hide_render = True


if __name__ == "__main__":
    out = sys.argv[-1]
    build()
    finalize("IRAD_Bavar373_CP")
    if "--bake" in sys.argv:
        bake_camo(out, "IRAD_Bavar373_CP")
    bpy.ops.wm.save_as_mainfile(filepath=f"{out}/IRAD_Bavar373_CP.blend")
    for name, kw in (
        ("side", dict(target=(0, -0.3, 2.0), dist=15, az=-88, elev=3, res=(1100, 590))),
        ("quarter", dict(target=(0, 0.0, 2.0), dist=14, az=-50, elev=10)),
        ("rear", dict(target=(0, -3.0, 2.0), dist=12, az=-150, elev=10)),
    ):
        render(f"{out}/IRAD_Bavar373_CP_{name}.png", **kw)
