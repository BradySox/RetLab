"""Bavar-373 command post (IRAD_Bavar373_CP), matched to a parade photograph: a 6x6
carrying one long equipment shelter, a door at its front, an AC unit and a rolled
camouflage net at the rear. No moving parts."""

import math
import sys

import bpy

sys.path.insert(0, sys.argv[-1])
from irad_kit import *  # noqa: E402,F403


def build():
    reset()
    axles = [3.6, -1.9, -3.25]
    root, dz, rear, cab_back = iran_truck(
        "IRAD_Bavar373_CP", axles, 9.6, cab_len=2.2, wheel_r=0.7
    )
    sy0, sy1, sh = cab_back - 0.35, rear + 0.1, 2.45
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
    for s in (-1, 1):
        # door at the front, seams and handle; a small step below it
        dy = sy0 - 0.75
        for k, (sz, off) in enumerate(
            (
                ((0.02, 0.9, 0.03), (0, 0.95)),
                ((0.02, 0.9, 0.03), (0, -0.95)),
                ((0.02, 0.03, 1.9), (0.45, 0)),
                ((0.02, 0.03, 1.9), (-0.45, 0)),
            )
        ):
            box(
                f"cp_doorseam{s}{k}",
                sz,
                (s * 1.255, dy + off[0], dz + 1.2 + off[1]),
                DARK(),
                root,
                0,
            )
        box(
            f"cp_doorhandle{s}",
            (0.05, 0.05, 0.22),
            (s * 1.28, dy - 0.3, dz + 1.2),
            METAL(),
            root,
            0,
        )
        box(
            f"cp_doorstep{s}",
            (0.35, 0.8, 0.05),
            (s * 1.3, dy, dz - 0.25),
            METAL(),
            root,
            0,
        )
        # panel seams along the side
        for k in range(1, 4):
            box(
                f"cp_sideseam{s}{k}",
                (0.02, 0.03, sh - 0.2),
                (s * 1.255, sy1 + k * (slen - 1.6) / 4, dz + 0.12 + sh / 2),
                DARK(),
                root,
                0,
            )
        box(
            f"cp_cablebox{s}",
            (0.25, 0.7, 0.4),
            (s * 1.35, scy - 1.2, dz + 0.45),
            PAINT(),
            root,
            0.02,
        )
    # AC unit on the rear corner, a rolled camouflage net on the rear face
    box("cp_ac", (0.7, 0.55, 0.75), (0.75, sy1 - 0.27, top - 0.5), PAINT(), root, 0.03)
    louvers("cp_aclouver", (1.1, sy1 - 0.27, top - 0.5), 0.45, 0.55, 6, 1, root)
    fan("cp_acfan", (0.75, sy1 - 0.55, top - 0.5), "-y", 0.22, root)
    netmat = mat("irad_net", (0.3, 0.26, 0.16), 0.95)
    cyl(
        "cp_net",
        0.32,
        2.3,
        (0, sy1 - 0.2, top - 0.1),
        (0, math.pi / 2, 0),
        netmat,
        root,
        18,
    )
    for s in (-1, 1):
        box(
            f"cp_netstrap{s}",
            (0.06, 0.7, 0.7),
            (s * 0.7, sy1 - 0.2, top - 0.1),
            DARK(),
            root,
            0,
        )
    # roof: vents and an antenna mount
    for k in range(3):
        box(
            f"cp_roofvent{k}",
            (0.5, 0.5, 0.15),
            (-0.5, sy0 - 1.2 - k * 1.6, top + 0.1),
            PAINT(),
            root,
            0.02,
        )
    cyl(
        "cp_antbase",
        0.08,
        0.2,
        (0.8, sy0 - 0.5, top + 0.1),
        (0, 0, 0),
        DARK(),
        root,
        10,
    )
    cyl(
        "cp_antenna",
        0.015,
        2.2,
        (0.8, sy0 - 0.5, top + 1.3),
        (0, 0, 0),
        DARK(),
        root,
        6,
    )
    # stabiliser jacks at the rear
    for s in (-1, 1):
        cyl(
            f"cp_jack{s}",
            0.09,
            0.9,
            (s * 1.2, rear + 0.4, 0.55),
            (0, 0, 0),
            METAL(),
            root,
            12,
        )
        cyl(
            f"cp_jackpad{s}",
            0.22,
            0.05,
            (s * 1.2, rear + 0.4, 0.03),
            (0, 0, 0),
            DARK(),
            root,
            16,
        )
    shell = box("collision_shell", (2.7, 9.8, 3.9), (0, 0, 1.95), DARK(), root, 0)
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
    ):
        render(f"{out}/IRAD_Bavar373_CP_{name}.png", **kw)
