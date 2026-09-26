"""Rasool communications shelter (IRAD_Rasool_Comms), matched to a photograph: a
white-cab 4x4 carrying a pale sage shelter with an open equipment door, an AC unit, a
roof rail with two omni antennas, and a tall telescopic mast at the rear. Flat paint,
so no bake.

arg_mast_extend: frames 0-100, rear mast nested to fully raised.
"""

import sys

import bpy

sys.path.insert(0, sys.argv[-1])
import irad_kit  # noqa: E402
from irad_kit import *  # noqa: E402,F403
from irad_kit import _flat, _on_face  # noqa: E402,F401

WHITE = lambda: mat("irad_cabwhite", (0.75, 0.76, 0.74), 0.5)  # noqa: E731
OLIVE = lambda: mat("irad_olive", (0.33, 0.34, 0.24), 0.7)  # noqa: E731
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
    # raised frame round every face and rounded corner posts, as photographed
    for sx in (-1, 1):
        for zz in (dz + 0.28, top - 0.06):
            box(
                f"rs_rimh{sx}{zz:.0f}",
                (0.06, slen, 0.1),
                (sx * 1.245, scy, zz),
                OLIVE(),
                root,
                0.02,
            )
        for yy in (sy0, sy1):
            cyl(
                f"rs_corner{sx}{yy:.0f}",
                0.08,
                sh,
                (sx * 1.19, yy - (0.04 if yy == sy0 else -0.04), dz + 0.2 + sh / 2),
                (0, 0, 0),
                OLIVE(),
                root,
                12,
            )
    for yy in (sy0, sy1):
        for zz in (dz + 0.28, top - 0.06):
            box(
                f"rs_rimend{yy:.0f}{zz:.0f}",
                (2.4, 0.06, 0.1),
                (0, yy, zz),
                OLIVE(),
                root,
                0.02,
            )
    # open door: dark opening, frame, equipment racks inside, the leaf swung out on hinges
    dy = scy + 0.35
    box("rs_dooropening", (0.01, 0.8, 1.7), (s * 1.226, dy, dz + 1.25), DARK(), root, 0)
    for k, (dw, dh, oy, oz) in enumerate(
        (
            (0.9, 0.05, 0, 0.87),
            (0.9, 0.05, 0, -0.87),
            (0.05, 1.8, 0.45, 0),
            (0.05, 1.8, -0.45, 0),
        )
    ):
        box(
            f"rs_doorframe{k}",
            (0.06, dw, dh),
            (s * 1.24, dy + oy, dz + 1.25 + oz),
            OLIVE(),
            root,
            0.005,
        )
    rack = mat("irad_rack", (0.35, 0.36, 0.38), 0.4, 0.5)
    screen = mat("irad_screen", (0.05, 0.12, 0.18), 0.2)
    for k in range(6):
        box(
            f"rs_rack{k}",
            (0.03, 0.6, 0.22),
            (s * 1.245, dy, dz + 0.6 + k * 0.27),
            rack,
            root,
            0,
        )
        for j in range(3):
            box(
                f"rs_rackknob{k}{j}",
                (0.02, 0.05, 0.05),
                (s * 1.265, dy - 0.2 + j * 0.2, dz + 0.6 + k * 0.27),
                METAL(),
                root,
                0,
            )
    box("rs_rackscreen", (0.02, 0.4, 0.25), (s * 1.265, dy, dz + 1.75), screen, root, 0)
    box(
        "rs_door",
        (0.85, 0.05, 1.7),
        (s * 1.66, dy + 0.45, dz + 1.25),
        OLIVE(),
        root,
        0.01,
    )
    for k in range(3):
        cyl(
            f"rs_doorhinge{k}",
            0.03,
            0.14,
            (s * 1.25, dy + 0.45, dz + 0.6 + k * 0.65),
            (0, 0, 0),
            METAL(),
            root,
            8,
        )
    box(
        "rs_doorhandle",
        (0.2, 0.05, 0.05),
        (s * 1.95, dy + 0.49, dz + 1.25),
        METAL(),
        root,
        0,
    )
    box(
        "rs_doorstay",
        (0.5, 0.03, 0.03),
        (s * 1.45, dy + 0.4, dz + 2.0),
        METAL(),
        root,
        0,
    )
    # AC unit toward the front, with its rain hood and a grille
    ay = sy0 - 0.7
    box("rs_ac", (0.3, 0.75, 0.62), (s * 1.34, ay, dz + 1.3), OLIVE(), root, 0.03)
    grille("rs_acgrille", (s * 1.49, ay, dz + 1.22), "x", s, 0.6, 0.38, root, 6)
    box(
        "rs_achood",
        (0.42, 0.85, 0.04),
        (s * 1.4, ay, dz + 1.66),
        OLIVE(),
        root,
        0.01,
        (0, s * 0.35, 0),
    )
    # hatches and a vent box on the rear half, as photographed
    door(
        "rs_hatch", (s * 1.22, sy1 + 0.75, dz + 0.9), "x", s, 0.65, 0.55, root, OLIVE()
    )
    box(
        "rs_ventbox",
        (0.12, 0.5, 0.35),
        (s * 1.28, sy1 + 0.75, dz + 1.95),
        OLIVE(),
        root,
        0.02,
    )
    grille(
        "rs_ventgrille", (s * 1.34, sy1 + 0.75, dz + 1.95), "x", s, 0.4, 0.25, root, 4
    )
    for k in range(3):
        box(
            f"rs_latch{k}",
            (0.04, 0.06, 0.1),
            (s * 1.26, sy0 - 1.5 + k * 0.4, top - 0.3),
            METAL(),
            root,
            0,
        )
    # the right side: a plain door, a cable entry panel
    door("rs_doorr", (1.22, scy, dz + 1.25), "x", 1, 0.85, 1.7, root, OLIVE())
    box(
        "rs_cablepanel",
        (0.05, 0.6, 0.4),
        (1.25, sy1 + 0.7, dz + 0.6),
        OLIVE(),
        root,
        0.01,
    )
    for k in range(4):
        cyl(
            f"rs_connector{k}",
            0.04,
            0.07,
            (1.3, sy1 + 0.5 + k * 0.13, dz + 0.6),
            (0, 1.5708, 0),
            METAL(),
            root,
            10,
        )
    # louvered box high on the front face
    box(
        "rs_frontbox",
        (0.8, 0.35, 0.7),
        (0.6, sy0 + 0.17, top - 0.5),
        OLIVE(),
        root,
        0.02,
    )
    grille("rs_frontgrille", (0.6, sy0 + 0.35, top - 0.5), "y", 1, 0.65, 0.55, root, 7)
    # full-height ladder at the rear corner, roof rail on posts, roof box
    ladder(
        "rs_ladder",
        (s * 1.32, sy1 + 0.3, top + 0.6),
        (s * 1.32, sy1 + 0.3, 0.35),
        0.4,
        11,
        root,
    )
    pts = [
        (-1.15, sy1 + 0.1, top),
        (-1.15, sy0 - 0.1, top),
        (1.15, sy0 - 0.1, top),
        (1.15, sy1 + 0.1, top),
        (-0.8, sy1 + 0.1, top),
    ]
    handrail("rs_roofrail", pts, root, 0.35)
    box(
        "rs_roofbox",
        (1.2, 0.8, 0.45),
        (0.2, scy + 0.3, top + 0.22),
        OLIVE(),
        root,
        0.03,
    )
    grille("rs_roofboxg", (0.8, scy + 0.3, top + 0.22), "x", 1, 0.6, 0.3, root, 4)
    # two omni antennas on tall poles: stacked radome sections as photographed
    radome = mat("irad_radome", (0.7, 0.7, 0.68), 0.5)
    for k, (x, y, h) in enumerate(((0.9, sy0 - 0.3, 1.5), (-0.9, scy - 0.3, 1.2))):
        cyl(
            f"rs_omnibase{k}",
            0.1,
            0.12,
            (x, y, top + 0.06),
            (0, 0, 0),
            METAL(),
            root,
            12,
        )
        cyl(
            f"rs_omnipole{k}", 0.04, h, (x, y, top + h / 2), (0, 0, 0), METAL(), root, 8
        )
        for j, (r, ln) in enumerate(
            ((0.07, 0.25), (0.1, 0.18), (0.08, 0.25), (0.12, 0.22))
        ):
            cyl(
                f"rs_omni{k}_{j}",
                r,
                ln,
                (x, y, top + h + 0.12 + j * 0.23),
                (0, 0, 0),
                radome,
                root,
                14,
            )
        cyl(
            f"rs_omnicap{k}",
            0.13,
            0.04,
            (x, y, top + h + 1.03),
            (0, 0, 0),
            radome,
            root,
            14,
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
        for jy in (rear + 0.35, 1.2):
            screw_jack(f"rs_jack{s2}{jy:.0f}", s2 * 1.2, jy, dz - 0.15, root)
    # mast guy clamps and a cable to the shelter
    for k in range(3):
        box(
            f"rs_mastclamp{k}",
            (0.16, 0.16, 0.06),
            (mx, my, dz + 0.5 + k * 0.6),
            METAL(),
            root,
            0,
        )
    hose(
        "rs_mastcable",
        [
            (mx, my + 0.1, dz + 1.3),
            (mx + 0.2, my + 0.35, dz + 0.9),
            (mx + 0.25, sy1 + 0.2, dz + 0.5),
        ],
        0.02,
        DARK(),
        root,
    )
    shell = box("collision_shell", (2.6, 8.2, 3.6), (0, 0, 1.8), DARK(), root, 0)
    shell.hide_render = True


if __name__ == "__main__":
    out = sys.argv[-1]
    build()
    finalize("IRAD_Rasool_Comms")
    animate_wheels()
    bpy.context.scene.frame_set(100)
    bpy.ops.wm.save_as_mainfile(filepath=f"{out}/IRAD_Rasool_Comms.blend")
    for name, kw in (
        ("photo", dict(target=(0, -0.3, 2.6), dist=12, az=-92, elev=3, res=(800, 557))),
        ("quarter", dict(target=(0, 0.0, 2.4), dist=12, az=-45, elev=10)),
    ):
        render(f"{out}/IRAD_Rasool_Comms_{name}.png", **kw)
