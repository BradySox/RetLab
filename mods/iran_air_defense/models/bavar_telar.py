"""Bavar-373-II TELAR (IRAD_Bavar373_TELAR), matched to a photograph: the Bavar-373
TEL's 8x8 and canister towers, plus a telescopic radar mast with a dish behind the cab,
an hourglass erector with one central ram, and a railed walkway.

arg_launcher_elevation: frames 0-100, travel to erect (towers and the ram).
arg_mast_extend: frames 0-100, mast nested to fully raised.
arg_antenna_azimuth: frames 0-100, one full turn of the dish head.
"""

import math
import sys

import bpy

sys.path.insert(0, sys.argv[-1])
from irad_kit import *  # noqa: E402,F403
import bavar_ln  # noqa: E402
from irad_kit import _flat, _on_face  # noqa: E402

STEPS = 11


def rails(prefix, x0, x1, y0, y1, z, parent):
    """Guard rails round a rectangle: posts, a top rail and a mid rail."""
    for name, a, b in (
        ("l", (x0, y0), (x0, y1)),
        ("r", (x1, y0), (x1, y1)),
        ("b", (x0, y0), (x1, y0)),
    ):
        for h in (0.5, 1.0):
            strut(
                f"{prefix}_{name}{h}",
                (a[0], a[1], z + h),
                (b[0], b[1], z + h),
                0.025,
                METAL(),
                parent,
            )
    for k in range(5):
        y = y0 + k * (y1 - y0) / 4
        for x in (x0, x1):
            box(
                f"{prefix}_post{k}{x}",
                (0.04, 0.04, 1.0),
                (x, y, z + 0.5),
                METAL(),
                parent,
                0,
            )


def hatch(prefix, w, z, h, parent, xbrace=False):
    """A recessed hatch on all four mast faces: seam frame, bolt rows, a grab handle."""
    for face, (axis, sign) in enumerate((("x", 1), ("x", -1), ("y", 1), ("y", -1))):
        c = (sign * w / 2, 0, z) if axis == "x" else (0, sign * w / 2, z)
        fw = w - 0.16
        for k, (dw, dh, oa, oz) in enumerate(
            (
                (fw, 0.025, 0, h / 2),
                (fw, 0.025, 0, -h / 2),
                (0.025, h, fw / 2, 0),
                (0.025, h, -fw / 2, 0),
            )
        ):
            cc = (c[0], oa, z + oz) if axis == "x" else (oa, c[1], z + oz)
            box(
                f"{prefix}_{face}_seam{k}",
                _flat(axis, dw, dh, 0.02),
                _on_face(cc, axis, sign, 0.008),
                DARK(),
                parent,
                0,
            )
        for k in range(5):
            for side in (-1, 1):
                oa, oz = side * (w / 2 - 0.04), -h / 2 + (k + 0.5) * h / 5
                cc = (c[0], oa, z + oz) if axis == "x" else (oa, c[1], z + oz)
                box(
                    f"{prefix}_{face}_bolt{k}{side}",
                    _flat(axis, 0.03, 0.03, 0.02),
                    _on_face(cc, axis, sign, 0.01),
                    METAL(),
                    parent,
                    0,
                )
        hc = (c[0], 0, z - h * 0.3) if axis == "x" else (0, c[1], z - h * 0.3)
        box(
            f"{prefix}_{face}_grip",
            _flat(axis, 0.1, 0.03, 0.03),
            _on_face(hc, axis, sign, 0.015),
            METAL(),
            parent,
            0,
        )
        if xbrace:
            ln = math.hypot(fw, h) - 0.05
            ang = math.atan2(h, fw)
            for d in (-1, 1):
                rot = (d * ang, 0, 0) if axis == "x" else (0, -d * ang, 0)
                box(
                    f"{prefix}_{face}_x{d}",
                    _flat(axis, ln, 0.03, 0.02),
                    _on_face((c[0], c[1], z), axis, sign, 0.01),
                    PAINT(),
                    parent,
                    0,
                    rot,
                )


def mast(root, x, y, base_z):
    """Three nested square sections, a head with a dish on top. Returns (sections, head)."""
    widths, sec_len = (1.05, 0.95, 0.85), 2.9
    parent, sections = root, []
    for i, w in enumerate(widths):
        at = (x, y, base_z) if i == 0 else (0, 0, 0)
        sec = empty(f"mast_sec{i}_slide", at, parent)
        box(
            f"mast_sec{i}",
            (w, w, sec_len),
            (0, 0, 0.8 - sec_len / 2),
            PAINT(),
            sec,
            0.02,
        )
        box(
            f"mast_sec{i}_collar",
            (w + 0.08, w + 0.08, 0.14),
            (0, 0, 0.75),
            PAINT(),
            sec,
            0.01,
        )
        box(
            f"mast_sec{i}_lip",
            (w + 0.12, w + 0.12, 0.04),
            (0, 0, 0.66),
            METAL(),
            sec,
            0,
        )
        for k in range(3):
            hatch(
                f"mast_sec{i}_h{k}",
                w,
                0.25 - k * 0.8,
                0.66,
                sec,
                xbrace=(i == 2 and k == 0),
            )
        # the side fittings the photo shows: guide rollers and a cable clamp
        for s in (-1, 1):
            box(
                f"mast_sec{i}_roller{s}",
                (0.1, 0.16, 0.12),
                (s * (w / 2 + 0.06), 0, 0.55),
                METAL(),
                sec,
                0.01,
            )
        box(
            f"mast_sec{i}_clamp",
            (0.14, 0.1, 0.1),
            (-(w / 2 + 0.07), 0.2, -0.4),
            METAL(),
            sec,
            0.01,
        )
        sections.append(sec)
        parent = sec
    head = empty("arg_antenna_azimuth", (0, 0, 0.87), parent)
    # tapered pedestal: narrow at the mast, wider under the yoke
    bpy.ops.mesh.primitive_cone_add(
        vertices=4,
        radius1=0.5,
        radius2=0.66,
        depth=0.85,
        location=(0, 0, 0.42),
        rotation=(0, 0, math.pi / 4),
    )
    ped = bpy.context.active_object
    ped.name = "mast_pedestal"
    ped.data.materials.append(PAINT())
    ped.parent = head
    cyl("mast_bearing", 0.4, 0.1, (0, 0, 0.05), (0, 0, 0), METAL(), head, 24)
    box("mast_headbox", (0.8, 0.7, 0.3), (0, 0, 1.0), PAINT(), head, 0.03)
    # one elevation drive behind the dish, as photographed: block, sector gear, motor
    box("mast_elevblock", (0.42, 0.36, 0.42), (0, 0.05, 1.3), METAL(), head, 0.02)
    cyl(
        "mast_elevgear",
        0.3,
        0.05,
        (0.24, 0.05, 1.3),
        (0, math.pi / 2, 0),
        DARK(),
        head,
        20,
    )
    cyl(
        "mast_elevmotor",
        0.08,
        0.3,
        (-0.3, -0.05, 1.2),
        (0, math.pi / 2, 0),
        METAL(),
        head,
        12,
    )
    # camera/IFF box on an arm to one side, with its cable hanging in a loop
    strut("mast_camarm", (0.4, -0.1, 1.05), (0.85, -0.1, 1.15), 0.035, METAL(), head)
    box("mast_cambox", (0.26, 0.34, 0.26), (0.95, -0.1, 1.2), PAINT(), head, 0.02)
    box("mast_camlens", (0.18, 0.04, 0.18), (0.95, 0.08, 1.2), GLASS(), head, 0)
    hose(
        "mast_camcable",
        [(0.95, -0.2, 1.05), (1.05, -0.3, 0.6), (0.9, -0.3, 0.3), (0.45, -0.2, 0.5)],
        0.015,
        DARK(),
        head,
    )
    hose(
        "mast_cableloop",
        [(-0.3, 0.25, 1.1), (-0.5, 0.45, 0.8), (-0.35, 0.4, 0.5), (-0.2, 0.3, 0.7)],
        0.02,
        DARK(),
        head,
    )
    dish = empty("mast_dish_tilt", (0, 0.2, 1.3), head, (math.radians(40), 0, 0))
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=1.0, segments=40, ring_count=20, location=(0, 0, 0)
    )
    d = bpy.context.active_object
    d.name = "mast_dish"
    bm = bmesh.new()
    bm.from_mesh(d.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.y > -0.72], context="VERTS")
    bm.to_mesh(d.data)
    bm.free()
    d.scale = (0.85 / 0.69, 0.8, 0.85 / 0.69)
    d.location = (0, 1.0, 0)
    m = d.modifiers.new("solid", "SOLIDIFY")
    m.thickness = 0.03
    d.data.materials.append(PAINT())
    d.parent = dish
    # back ribs and the hub that carries the dish
    # dish: bowl from y 0.2 (back) to the rim at y 0.42, rim radius 0.85
    cyl("mast_dishhub", 0.18, 0.2, (0, 0.1, 0), (math.pi / 2, 0, 0), METAL(), dish, 16)
    for k in range(6):
        a = k * math.pi / 3 + math.pi / 6
        strut(
            f"mast_dishrib{k}",
            (0, 0.14, 0),
            (0.78 * math.cos(a), 0.37, 0.78 * math.sin(a)),
            0.02,
            METAL(),
            dish,
            6,
        )
    # the feed on a bent arm from the rim
    strut("mast_feedarm0", (0, 0.42, 0.84), (0, 0.85, 0.5), 0.022, METAL(), dish)
    strut("mast_feedarm1", (0, 0.85, 0.5), (0, 0.9, 0.06), 0.022, METAL(), dish)
    cyl("mast_feedhorn", 0.07, 0.16, (0, 0.9, 0), (math.pi / 2, 0, 0), DARK(), dish, 12)
    hose(
        "mast_feedcable",
        [(0.05, 0.4, 0.84), (0.1, 0.65, 0.72), (0.05, 0.85, 0.52)],
        0.012,
        DARK(),
        dish,
    )
    return sections, head


def build():
    reset()
    axles = [4.9, 3.3, -2.5, -4.1]
    root, dz, rear, cab_back = iran_truck(
        "IRAD_Bavar373_TELAR", axles, 12.6, cab_len=2.3, wheel_r=0.76
    )
    dlen = cab_back - rear
    box(
        "tl_deck",
        (2.5, dlen, 0.16),
        (0, (cab_back + rear) / 2, dz + 0.06),
        DARK(),
        root,
        0.01,
    )
    for s in (-1, 1):
        box(
            f"tl_deckedge{s}",
            (0.08, dlen, 0.26),
            (s * 1.25, (cab_back + rear) / 2, dz + 0.03),
            PAINT(),
            root,
            0.01,
        )

    # mast housing behind the cab, with the mast rising from it
    hy, hh = cab_back - 0.85, 2.25
    box("tl_housing", (2.4, 1.5, hh), (0, hy, dz + hh / 2 + 0.1), PAINT(), root, 0.03)
    for s in (-1, 1):
        door(
            f"tl_housingdoor{s}",
            (s * 1.2, hy - 0.15, dz + 1.05),
            "x",
            s,
            0.9,
            1.4,
            root,
            hinge_side=s,
        )
        grille(
            f"tl_housinggrille{s}",
            (s * 1.2, hy + 0.5, dz + 1.75),
            "x",
            s,
            0.35,
            0.6,
            root,
            6,
        )
    box("tl_housingrib", (2.44, 0.06, 0.08), (0, hy, dz + hh + 0.06), PAINT(), root, 0)
    # tank and AC unit on the housing's cab end, exhaust stack up the corner
    cyl(
        "tl_housingtank",
        0.3,
        1.1,
        (-0.6, hy + 0.35, dz + hh + 0.45),
        (0, math.pi / 2, 0),
        METAL(),
        root,
        20,
    )
    for k in (-1, 1):
        box(
            f"tl_tankstrap{k}",
            (0.05, 0.64, 0.64),
            (-0.6 + k * 0.35, hy + 0.35, dz + hh + 0.45),
            DARK(),
            root,
            0,
        )
        box(
            f"tl_tankcradle{k}",
            (0.08, 0.5, 0.18),
            (-0.6 + k * 0.35, hy + 0.35, dz + hh + 0.19),
            PAINT(),
            root,
            0,
        )
    box(
        "tl_acunit",
        (1.1, 0.9, 0.55),
        (0.55, hy + 0.3, dz + hh + 0.38),
        PAINT(),
        root,
        0.03,
    )
    grille("tl_acgrille", (0.55, hy + 0.75, dz + hh + 0.38), "y", 1, 0.9, 0.4, root, 6)
    cyl(
        "tl_acfanring",
        0.3,
        0.05,
        (0.55, hy + 0.3, dz + hh + 0.67),
        (0, 0, 0),
        METAL(),
        root,
        28,
    )
    cyl(
        "tl_acfanwell",
        0.27,
        0.05,
        (0.55, hy + 0.3, dz + hh + 0.68),
        (0, 0, 0),
        DARK(),
        root,
        28,
    )
    for k in range(4):
        box(
            f"tl_acfanguard{k}",
            (0.56, 0.02, 0.02),
            (0.55, hy + 0.3, dz + hh + 0.71),
            METAL(),
            root,
            0,
            (0, 0, k * math.pi / 4),
        )
    cyl(
        "tl_exhaust",
        0.08,
        3.4,
        (1.15, hy + 0.72, dz + 1.9),
        (0, 0, 0),
        CHROME(),
        root,
        14,
    )
    cyl(
        "tl_exhaustcap",
        0.1,
        0.18,
        (1.15, hy + 0.72, dz + 3.65),
        (0.4, 0, 0),
        METAL(),
        root,
        14,
    )
    for k in range(3):
        box(
            f"tl_exhaustclamp{k}",
            (0.2, 0.2, 0.05),
            (1.15, hy + 0.72, dz + 1.0 + k * 1.0),
            METAL(),
            root,
            0,
        )
    cyl(
        "tl_whip", 0.02, 1.6, (1.1, hy - 0.6, dz + hh + 0.9), (0, 0, 0), DARK(), root, 6
    )
    ladder(
        "tl_housingladder",
        (-1.25, hy - 0.4, dz + hh),
        (-1.25, hy - 0.4, dz + 1.6),
        0.4,
        3,
        root,
    )
    sections, head = mast(root, 0.25, hy, dz + hh + 0.1)

    # equipment boxes, the lit control panel, and the railed walkway over them
    ey0, ey1 = hy - 0.75, -0.45  # ends ahead of the towers' travel position
    box(
        "tl_equip",
        (2.4, ey0 - ey1, 1.35),
        (0, (ey0 + ey1) / 2, dz + 0.8),
        PAINT(),
        root,
        0.03,
    )
    green = mat("irad_led", (0.1, 0.8, 0.3), 0.3)

    def panel(tag, py, pz, cols, rows):
        box(f"tl_{tag}panel", (0.03, 0.9, 0.72), (1.21, py, pz), DARK(), root, 0.005)
        for k, (dw, dh, oy, oz) in enumerate(
            (
                (0.96, 0.04, 0, 0.38),
                (0.96, 0.04, 0, -0.38),
                (0.04, 0.8, 0.47, 0),
                (0.04, 0.8, -0.47, 0),
            )
        ):
            box(
                f"tl_{tag}frame{k}",
                (0.05, dw, dh),
                (1.225, py + oy, pz + oz),
                PAINT(),
                root,
                0,
            )
        for r in range(rows):
            for c in range(cols):
                box(
                    f"tl_{tag}led{r}{c}",
                    (0.03, 0.06, 0.04),
                    (
                        1.235,
                        py - 0.3 + c * 0.6 / (cols - 1),
                        pz - 0.2 + r * 0.4 / (rows - 1),
                    ),
                    green,
                    root,
                    0,
                )
        box(
            f"tl_{tag}hood",
            (0.34, 1.04, 0.035),
            (1.33, py, pz + 0.47),
            PAINT(),
            root,
            0,
            (0, -0.35, 0),
        )
        for side in (-1, 1):
            box(
                f"tl_{tag}hoodcheek{side}",
                (0.3, 0.03, 0.3),
                (1.32, py + side * 0.51, pz + 0.33),
                PAINT(),
                root,
                0,
            )

    panel("a", ey1 + 0.8, dz + 0.9, 5, 4)
    # the equipment block is under 3 m long: a door each side, a grille on the side
    # without the control panel
    door(
        "tl_equipdoor1",
        (1.2, ey0 - 0.6, dz + 0.8),
        "x",
        1,
        0.85,
        1.05,
        root,
        hinge_side=1,
    )
    door("tl_equipdoor-1", (-1.2, ey1 + 0.6, dz + 0.8), "x", -1, 0.85, 1.05, root)
    grille("tl_equipgrille", (-1.2, ey0 - 0.7, dz + 0.95), "x", -1, 0.6, 0.6, root, 6)
    for s in (-1, 1):
        stencil(
            f"tl_equipmark{s}",
            "A-2",
            (s * 1.23, (ey0 + ey1) / 2, dz + 1.35),
            (math.pi / 2, 0, s * math.pi / 2),
            0.1,
            DARK(),
            root,
        )
    # low lockers aft, under the towers' travel envelope; the second panel sits on one
    ly0, ly1 = ey1, rear + 1.2
    for s in (-1, 1):
        box(
            f"tl_locker{s}",
            (0.7, ly0 - ly1, 0.72),
            (s * 0.87, (ly0 + ly1) / 2, dz + 0.5),
            PAINT(),
            root,
            0.02,
        )
        for k in range(3):
            ly = ly1 + (k + 0.5) * (ly0 - ly1) / 3
            box(
                f"tl_lockerlid{s}{k}",
                (0.72, (ly0 - ly1) / 3 - 0.06, 0.03),
                (s * 0.87, ly, dz + 0.87),
                PAINT(),
                root,
                0.005,
            )
            for h in (-1, 1):
                box(
                    f"tl_lockerlatch{s}{k}{h}",
                    (0.03, 0.08, 0.1),
                    (s * 1.23, ly + h * 0.25, dz + 0.75),
                    METAL(),
                    root,
                    0,
                )
    panel("b", ly0 - 0.55, dz + 0.55, 4, 3)
    wz = dz + 1.5
    box("tl_walkway", (2.3, ey0 - ey1, 0.06), (0, (ey0 + ey1) / 2, wz), DARK(), root, 0)
    rails("tl_walkrail", -1.12, 1.12, ey1, ey0, wz, root)
    for s in (-1, 1):
        box(
            f"tl_toeboard{s}",
            (0.03, ey0 - ey1, 0.12),
            (s * 1.12, (ey0 + ey1) / 2, wz + 0.09),
            PAINT(),
            root,
            0,
        )
    for k in range(int((ey0 - ey1) / 0.35)):
        box(
            f"tl_tread{k}",
            (2.2, 0.03, 0.02),
            (0, ey1 + 0.2 + k * 0.35, wz + 0.04),
            METAL(),
            root,
            0,
        )
    # balcony off the housing at walkway height, rails on three sides
    handrail(
        "tl_balcony",
        [
            (-1.12, ey0, wz),
            (-1.25, hy - 0.2, wz),
            (1.25, hy - 0.2, wz),
            (1.12, ey0, wz),
        ],
        root,
    )
    box(
        "tl_balconyfloor",
        (2.5, hy - 0.2 - ey0 + 0.1, 0.05),
        (0, (hy - 0.2 + ey0) / 2, wz),
        DARK(),
        root,
        0,
    )
    ladder(
        "tl_deckladder", (1.3, ey1 + 0.3, wz), (1.55, ey1 + 0.3, 0.35), 0.45, 5, root
    )

    # step frame with rails and cable reels in the long gap between the axle pairs
    gy = (axles[1] + axles[2]) / 2 + 0.6
    fz0, fz1 = 0.5, dz - 0.2
    for s in (-1, 1):
        box(
            f"tl_stepframe{s}",
            (0.05, 1.6, fz1 - fz0),
            (1.15, gy + s * 0.8, (fz0 + fz1) / 2),
            METAL(),
            root,
            0,
        )
    box("tl_stepplate", (0.45, 1.6, 0.04), (1.1, gy, fz0), METAL(), root, 0)
    box(
        "tl_stepplate2",
        (0.35, 1.6, 0.04),
        (1.05, gy, (fz0 + fz1) / 2),
        METAL(),
        root,
        0,
    )
    handrail("tl_steprail", [(1.3, gy - 0.8, fz0), (1.3, gy + 0.8, fz0)], root, 0.7)
    cable_reel("tl_reel0", (0.6, gy, 0.95), root, 0.32, 0.4)
    cable_reel("tl_reel1", (0.6, gy - 1.6, 0.95), root, 0.32, 0.4)
    for s in (-1, 1):
        box(
            f"tl_stowbox{s}",
            (0.9, 1.0, 0.55),
            (-s * 0.75 if s > 0 else 0.0, gy - 2.8, dz - 0.5),
            PAINT(),
            root,
            0.02,
        )
    hose(
        "tl_cablerun",
        [
            (1.2, gy + 0.9, dz - 0.25),
            (1.35, gy, 0.3),
            (1.2, gy - 1.2, 0.08),
            (0.4, gy - 3, 0.05),
        ],
        0.02,
        DARK(),
        root,
    )

    # stabiliser jacks
    for s in (-1, 1):
        for jy, tag in ((axles[1] - 0.9, "f"), (rear + 0.35, "r")):
            box(
                f"tl_jackbeam{s}{tag}",
                (0.55, 0.3, 0.25),
                (s * 1.3, jy, dz - 0.15),
                DARK(),
                root,
                0.01,
            )
            screw_jack(f"tl_jack{s}{tag}", s * 1.55, jy, dz - 0.2, root)

    PZ = dz + 1.1
    P = (0, rear + 0.25, PZ)
    pivot = empty("arg_launcher_elevation", P, root)
    for s in (-1, 1):
        box(
            f"tl_hinge{s}",
            (0.28, 0.6, 1.3),
            (s * 1.12, P[1], dz + 0.55),
            PAINT(),
            root,
            0.02,
        )
        cyl(
            f"tl_hingepin{s}",
            0.12,
            0.36,
            (s * 1.12, P[1], PZ),
            (0, math.pi / 2, 0),
            METAL(),
            root,
            16,
        )
    OVER = PZ - 0.1
    pack = empty("tl_pack", (0, 0, 0), pivot)
    CW, GAP, CD, ZB = bavar_ln.CW, bavar_ln.GAP, bavar_ln.CD, bavar_ln.ZB
    for t, tx in enumerate((-(GAP + CW) / 2, (GAP + CW) / 2)):
        bavar_ln.tower(t, tx, OVER, pack)
    box(
        "tl_basewedge",
        (2.5, 0.35, CD + 0.5),
        (0, -OVER - 0.1, ZB + CD / 2),
        PAINT(),
        pack,
        0.03,
    )

    # hourglass erector: top and bottom beams, two wide diagonals crossing at a waist
    fy0, fy1, fz, fw = -OVER + 0.6, -OVER + 5.8, 0.14, 2.3
    ym = (fy0 + fy1) / 2
    for name, y in (("bottom", fy0), ("top", fy1)):
        box(f"tl_er_{name}", (fw, 0.35, 0.22), (0, y, fz), PAINT(), pack, 0.02)
    ang = math.atan2(fy1 - fy0, fw * 0.8)
    diag = math.hypot(fy1 - fy0, fw * 0.8)
    for s in (-1, 1):
        box(
            f"tl_er_diag{s}",
            (0.75, diag, 0.16),
            (0, ym, fz),
            PAINT(),
            pack,
            0.02,
            (0, 0, s * (math.pi / 2 - ang)),
        )
        box(
            f"tl_er_side{s}",
            (0.14, 1.4, 0.18),
            (s * (fw / 2 - 0.07), fy0 + 0.7, fz),
            PAINT(),
            pack,
            0.01,
        )
        box(
            f"tl_er_sidetop{s}",
            (0.14, 1.4, 0.18),
            (s * (fw / 2 - 0.07), fy1 - 0.7, fz),
            PAINT(),
            pack,
            0.01,
        )
    box("tl_er_waist", (0.9, 1.3, 0.2), (0, ym, fz), PAINT(), pack, 0.02)
    # lightening holes: dark triangles and slots as photographed, both faces
    for s in (-1, 1):
        for k, t in enumerate((0.22, 0.36, 0.64, 0.78)):
            yy = fy0 + t * (fy1 - fy0)
            xx = s * (0.5 - abs(t - 0.5)) * fw * 0.8
            for face in (-1, 1):
                box(
                    f"tl_er_hole{s}{k}{face}",
                    (0.2, 0.32, 0.01),
                    (xx, yy, fz + face * 0.085),
                    DARK(),
                    pack,
                    0,
                    (0, 0, s * (math.pi / 2 - ang)),
                )
        box(
            f"tl_er_gusset{s}",
            (0.5, 0.5, 0.2),
            (s * 0.85, fy0 + 0.35, fz),
            PAINT(),
            pack,
            0.01,
            (0, 0, math.pi / 4),
        )
        box(
            f"tl_er_gussettop{s}",
            (0.5, 0.5, 0.2),
            (s * 0.85, fy1 - 0.35, fz),
            PAINT(),
            pack,
            0.01,
            (0, 0, math.pi / 4),
        )
    for face in (-1, 1):
        box(
            f"tl_er_waisthole{face}",
            (0.3, 0.6, 0.01),
            (0, ym, fz + face * 0.105),
            DARK(),
            pack,
            0,
        )
    for s in (-1, 1):
        box(
            f"tl_er_lug{s}",
            (0.14, 0.3, 0.3),
            (s * (fw / 2 + 0.08), fy1 + 0.1, fz + 0.1),
            PAINT(),
            pack,
            0.01,
        )

    # one ram up the middle, from the deck by the tail to the waist
    A = (ym + OVER, -0.2)
    B = (P[1] + 1.4, dz + 0.55)

    def a_world(th):
        return (
            P[1] + A[0] * math.cos(th) - A[1] * math.sin(th),
            PZ + A[0] * math.sin(th) + A[1] * math.cos(th),
        )

    dists = [
        math.dist(a_world(math.radians(90 * i / (STEPS - 1))), B) for i in range(STEPS)
    ]
    Ls = min(dists) - 0.05
    assert Ls + 2 * (Ls - 0.1) >= max(dists), "ram cannot reach full erection"
    box("tl_rambase", (0.4, 0.45, 0.3), (0, B[0], B[1] - 0.15), DARK(), root, 0.02)
    barrel = empty("tl_ram_barrel_pivot", (0, B[0], B[1]), root)
    cyl(
        "tl_ram_barrel",
        0.16,
        Ls,
        (0, -Ls / 2, 0),
        (math.pi / 2, 0, 0),
        PAINT(),
        barrel,
        18,
    )
    st1 = empty("tl_ram_stage1_slide", (0, 0, 0), barrel)
    cyl(
        "tl_ram_stage1",
        0.12,
        Ls,
        (0, -Ls / 2, 0),
        (math.pi / 2, 0, 0),
        CHROME(),
        st1,
        16,
    )
    st2 = empty("tl_ram_stage2_slide", (0, 0, 0), st1)
    cyl(
        "tl_ram_stage2",
        0.09,
        Ls,
        (0, -Ls / 2, 0),
        (math.pi / 2, 0, 0),
        CHROME(),
        st2,
        14,
    )

    for i in range(STEPS):
        t = i / (STEPS - 1)
        f = i * 100 // (STEPS - 1)
        th = math.radians(90 * t)
        ay, az_ = a_world(th)
        vy, vz = ay - B[0], az_ - B[1]
        barrel.rotation_euler = (math.atan2(-vz, -vy), 0, 0)
        barrel.keyframe_insert("rotation_euler", frame=f)
        ext = (math.hypot(vy, vz) - Ls) / 2
        for stg in (st1, st2):
            stg.location = (0, -ext, 0)
            stg.keyframe_insert("location", frame=f)
        pivot.rotation_euler = (th, 0, 0)
        pivot.keyframe_insert("rotation_euler", frame=f)
        sections[0].location.z = dz + hh + 0.1 + 2.5 * t
        sections[0].keyframe_insert("location", frame=f)
        sections[1].location.z = 2.4 * t
        sections[1].keyframe_insert("location", frame=f)
        sections[2].location.z = 2.3 * t
        sections[2].keyframe_insert("location", frame=f)
        head.rotation_euler = (0, 0, 2 * math.pi * t)
        head.keyframe_insert("rotation_euler", frame=f)

    # hinged ground plate at the tail, down on the ground as photographed
    box(
        "tl_groundplate",
        (2.2, 1.3, 0.05),
        (0, rear - 0.9, 0.12),
        METAL(),
        root,
        0.005,
        (-0.18, 0, 0),
    )
    for s in (-1, 1):
        strut(
            f"tl_plateleg{s}",
            (s * 0.9, rear - 0.2, 0.9),
            (s * 0.9, rear - 0.5, 0.2),
            0.04,
            METAL(),
            root,
        )

    shell = box("collision_shell", (2.8, 14.6, 4.2), (0, -1.0, 2.1), DARK(), root, 0)
    shell.hide_render = True
    return head


if __name__ == "__main__":
    out = sys.argv[-1]
    head = build()
    finalize("IRAD_Bavar373_TELAR")
    bpy.context.scene.frame_set(0)
    if "--bake" in sys.argv:
        bake_camo(out, "IRAD_Bavar373_TELAR")
    bpy.ops.wm.save_as_mainfile(filepath=f"{out}/IRAD_Bavar373_TELAR.blend")
    head.animation_data_clear()
    head.rotation_euler = (0, 0, 0)
    scn = bpy.context.scene
    views = (
        (0, "travel", dict(target=(0, 0.0, 2.6), dist=18, az=-55, elev=8)),
        (100, "erect", dict(target=(0, -0.5, 6.5), dist=30, az=-60, elev=6)),
        (
            100,
            "photo",
            dict(target=(0, 0.0, 6.5), dist=28, az=48, elev=4, res=(1100, 733)),
        ),
        (100, "head", dict(target=(0.25, 1.2, 11.2), dist=6, az=40, elev=10)),
        (50, "raising", dict(target=(0, -1.5, 3.5), dist=20, az=-85, elev=5)),
    )
    for frame, name, kw in views:
        scn.frame_set(frame)
        if name == "head":
            hp = head.matrix_world.translation
            kw["target"] = (hp.x, hp.y + 0.3, hp.z + 1.0)
        render(f"{out}/IRAD_Bavar373_TELAR_{name}.png", **kw)
