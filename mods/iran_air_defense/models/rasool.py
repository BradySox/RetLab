"""Rasool communications shelter (IRAD_Rasool_Comms), matched to a photograph: a
white-cab 4x4 carrying an olive shelter with an open equipment door, an AC unit, a
roof rail with two omni antennas, and a tall telescopic mast at the rear. Flat paint,
so no bake.

arg_mast_extend: frames 0-100, rear mast nested to fully raised.
"""

import sys

import bpy

sys.path.insert(0, sys.argv[-1])
import irad_kit  # noqa: E402
from irad_kit import *  # noqa: E402,F403

WHITE = lambda: mat("irad_cabwhite", (0.75, 0.76, 0.74), 0.5)  # noqa: E731
OLIVE = lambda: mat("irad_olive", (0.17, 0.19, 0.12), 0.7)  # noqa: E731
STEPS = 11


def build():
    reset()
    irad_kit.PAINT = WHITE  # the cab is factory white; the shelter below is olive
    root, dz, rear, cab_back = iran_truck(
        "IRAD_Rasool_Comms", [2.55, -1.6], 8.0, cab_len=2.2, wheel_r=0.62
    )
    irad_kit.PAINT = camo
    box(
        "rs_exhaust",
        (0.15, 0.15, 1.7),
        (1.05, cab_back - 0.2, dz + 1.2),
        METAL(),
        root,
        0,
    )
    sy0, sy1, sh = cab_back - 0.4, rear + 0.15, 2.2
    scy, slen = (sy0 + sy1) / 2, sy0 - sy1
    box("rs_subframe", (2.2, slen, 0.25), (0, scy, dz + 0.05), DARK(), root, 0.01)
    box("rs_shelter", (2.45, slen, sh), (0, scy, dz + 0.2 + sh / 2), OLIVE(), root, 0.1)
    top = dz + 0.2 + sh
    s = -1  # the photographed side
    # open door with racks, AC unit, access panels
    box(
        "rs_dooropening", (0.03, 0.8, 1.6), (s * 1.228, scy, dz + 1.25), DARK(), root, 0
    )
    rack = mat("irad_rack", (0.35, 0.36, 0.38), 0.4, 0.5)
    for k in range(5):
        box(
            f"rs_rack{k}",
            (0.03, 0.6, 0.22),
            (s * 1.232, scy, dz + 0.65 + k * 0.28),
            rack,
            root,
            0,
        )
    box(
        "rs_door",
        (0.8, 0.04, 1.6),
        (s * 1.62, scy + 0.42, dz + 1.25),
        OLIVE(),
        root,
        0.01,
    )
    box("rs_ac", (0.3, 0.75, 0.6), (s * 1.34, sy0 - 0.7, dz + 1.3), OLIVE(), root, 0.03)
    louvers("rs_aclouver", (s * 1.49, sy0 - 0.7, dz + 1.25), 0.55, 0.4, 5, s, root)
    for k, (y, z, w, h) in enumerate(
        ((sy1 + 0.8, dz + 1.9, 0.5, 0.35), (sy1 + 0.8, dz + 0.9, 0.6, 0.55))
    ):
        box(f"rs_panel{k}", (0.02, w, h), (s * 1.228, y, z), DARK(), root, 0)
    box("rs_frontvent", (0.35, 0.05, 0.6), (0.7, sy0 + 0.02, dz + 1.7), DARK(), root, 0)
    # ladder up the rear corner, roof rail, roof box
    for rail in (-1, 1):
        box(
            f"rs_ladrail{rail}",
            (0.04, 0.04, sh + 0.9),
            (s * 1.3, sy1 + 0.25 + rail * 0.2, dz + (sh + 0.9) / 2),
            METAL(),
            root,
            0,
        )
    for k in range(8):
        box(
            f"rs_ladrung{k}",
            (0.04, 0.4, 0.03),
            (s * 1.3, sy1 + 0.25, dz + 0.3 + k * 0.3),
            METAL(),
            root,
            0,
        )
    for x in (-1.15, 1.15):
        strut(
            f"rs_railside{x}",
            (x, sy1 + 0.1, top + 0.3),
            (x, sy0 - 0.1, top + 0.3),
            0.025,
            METAL(),
            root,
            6,
        )
    for y in (sy1 + 0.1, sy0 - 0.1):
        strut(
            f"rs_railend{y}",
            (-1.15, y, top + 0.3),
            (1.15, y, top + 0.3),
            0.025,
            METAL(),
            root,
            6,
        )
    for x in (-1.15, 1.15):
        for k in range(4):
            box(
                f"rs_railpost{x}{k}",
                (0.04, 0.04, 0.3),
                (x, sy1 + 0.1 + k * (slen - 0.2) / 3, top + 0.15),
                METAL(),
                root,
                0,
            )
    box(
        "rs_roofbox",
        (1.2, 0.8, 0.45),
        (0.2, scy + 0.3, top + 0.22),
        OLIVE(),
        root,
        0.03,
    )
    # two omni antennas on short masts
    for k, (x, y, h) in enumerate(((0.9, sy0 - 0.3, 1.3), (-0.9, scy - 0.3, 1.0))):
        cyl(
            f"rs_omnipole{k}", 0.04, h, (x, y, top + h / 2), (0, 0, 0), METAL(), root, 8
        )
        cyl(
            f"rs_omni{k}",
            0.1,
            0.55,
            (x, y, top + h + 0.25),
            (0, 0, 0),
            mat("irad_radome", (0.7, 0.7, 0.68), 0.5),
            root,
            12,
        )
    # the tall telescopic mast at the rear corner
    mx, my = s * 0.95, sy1 - 0.15
    box("rs_mastbracket", (0.3, 0.3, 0.4), (mx, my, dz + 0.9), METAL(), root, 0.01)
    parent, sections = root, []
    for i, r in enumerate((0.09, 0.07, 0.055, 0.04)):
        at = (mx, my, dz + 1.2) if i == 0 else (0, 0, 0)
        sec = empty(f"mast_sec{i}_slide", at, parent)
        cyl(
            f"mast_sec{i}", r, 2.4, (0, 0, 0.1 - 1.2 + 0.3), (0, 0, 0), METAL(), sec, 10
        )
        sections.append(sec)
        parent = sec
    cyl(
        "rs_mastomni",
        0.08,
        0.5,
        (0, 0, 1.2),
        (0, 0, 0),
        mat("irad_radome", (0.7, 0.7, 0.68), 0.5),
        parent,
        12,
    )
    for i in range(STEPS):
        t = i / (STEPS - 1)
        f = i * 100 // (STEPS - 1)
        sections[0].location.z = dz + 1.2 + 1.6 * t
        for sec in sections[1:]:
            sec.location.z = 2.0 * t
        for sec in sections:
            sec.keyframe_insert("location", frame=f)
    for s2 in (-1, 1):
        cyl(
            f"rs_jack{s2}",
            0.08,
            0.9,
            (s2 * 1.15, rear + 0.35, 0.5),
            (0, 0, 0),
            METAL(),
            root,
            12,
        )
        cyl(
            f"rs_jackpad{s2}",
            0.2,
            0.05,
            (s2 * 1.15, rear + 0.35, 0.03),
            (0, 0, 0),
            DARK(),
            root,
            14,
        )
    shell = box("collision_shell", (2.6, 8.2, 3.6), (0, 0, 1.8), DARK(), root, 0)
    shell.hide_render = True


if __name__ == "__main__":
    out = sys.argv[-1]
    build()
    finalize("IRAD_Rasool_Comms")
    bpy.context.scene.frame_set(100)
    bpy.ops.wm.save_as_mainfile(filepath=f"{out}/IRAD_Rasool_Comms.blend")
    for name, kw in (
        ("photo", dict(target=(0, -0.3, 2.6), dist=12, az=-92, elev=3, res=(800, 557))),
        ("quarter", dict(target=(0, 0.0, 2.4), dist=12, az=-45, elev=10)),
    ):
        render(f"{out}/IRAD_Rasool_Comms_{name}.png", **kw)
