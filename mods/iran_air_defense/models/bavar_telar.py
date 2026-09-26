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
        for k in range(3):
            box(
                f"mast_sec{i}_panel{k}",
                (w + 0.01, 0.02, 0.6),
                (0, 0, 0.25 - k * 0.8),
                DARK(),
                sec,
                0,
            )
        sections.append(sec)
        parent = sec
    head = empty("arg_antenna_azimuth", (0, 0, 0.87), parent)
    box("mast_headbox", (0.8, 0.7, 0.7), (0, 0, 0.35), PAINT(), head, 0.04)
    for s in (-1, 1):
        box(
            f"mast_yoke{s}", (0.1, 0.35, 0.55), (s * 0.5, 0.1, 0.9), METAL(), head, 0.01
        )
        box(
            f"mast_sidebox{s}",
            (0.25, 0.3, 0.3),
            (s * 0.62, -0.2, 0.45),
            METAL(),
            head,
            0.01,
        )
    dish = empty("mast_dish_tilt", (0, 0.1, 1.1), head, (math.radians(40), 0, 0))
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=1.0, segments=32, ring_count=16, location=(0, 0, 0)
    )
    d = bpy.context.active_object
    d.name = "mast_dish"
    bm = bmesh.new()
    bm.from_mesh(d.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.y > -0.72], context="VERTS")
    bm.to_mesh(d.data)
    bm.free()
    d.scale = (0.8 / 0.69, 0.8, 0.8 / 0.69)
    d.location = (0, 0.6, 0)
    m = d.modifiers.new("solid", "SOLIDIFY")
    m.thickness = 0.03
    d.data.materials.append(PAINT())
    d.parent = dish
    box("mast_dishrim", (0.06, 0.06, 0.06), (0, 0.2, 0), DARK(), dish, 0)
    strut("mast_feed", (0, 0.2, -0.7), (0, 0.55, 0.0), 0.025, METAL(), dish)
    cyl("mast_feedhorn", 0.06, 0.15, (0, 0.6, 0), (math.pi / 2, 0, 0), DARK(), dish, 12)
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
        box(
            f"tl_housingdoor{s}",
            (0.02, 1.0, 1.5),
            (s * 1.21, hy, dz + 1.1),
            DARK(),
            root,
            0,
        )
        louvers(
            f"tl_housinglouver{s}", (s * 1.2, hy + 0.45, dz + 1.8), 0.4, 0.5, 5, s, root
        )
    cyl(
        "tl_housingtank",
        0.3,
        1.1,
        (-0.75, hy - 0.2, dz + hh + 0.35),
        (0, math.pi / 2, 0),
        METAL(),
        root,
        18,
    )
    cyl(
        "tl_housingpipe",
        0.06,
        1.8,
        (1.0, hy + 0.6, dz + hh + 0.9),
        (0, 0, 0),
        METAL(),
        root,
        10,
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
    box("tl_ctrlpanel", (0.02, 0.9, 0.7), (1.21, ey1 + 0.8, dz + 0.9), DARK(), root, 0)
    green = mat("irad_led", (0.1, 0.8, 0.3), 0.3)
    for r in range(4):
        for c in range(5):
            box(
                f"tl_led{r}{c}",
                (0.03, 0.06, 0.04),
                (1.225, ey1 + 0.5 + c * 0.14, dz + 0.7 + r * 0.12),
                green,
                root,
                0,
            )
    box(
        "tl_ctrlhood",
        (0.3, 1.0, 0.04),
        (1.3, ey1 + 0.8, dz + 1.3),
        PAINT(),
        root,
        0,
        (0, -0.3, 0),
    )
    wz = dz + 1.5
    box("tl_walkway", (2.3, ey0 - ey1, 0.06), (0, (ey0 + ey1) / 2, wz), DARK(), root, 0)
    rails("tl_walkrail", -1.12, 1.12, ey1, ey0, wz, root)
    box("tl_stepbox", (0.8, 0.6, 0.5), (1.1, ey1 - 0.1, 0.9), PAINT(), root, 0.02)

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
            cyl(
                f"tl_jackcyl{s}{tag}",
                0.1,
                1.05,
                (s * 1.55, jy, 0.65),
                (0, 0, 0),
                METAL(),
                root,
                14,
            )
            cyl(
                f"tl_jackpad{s}{tag}",
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
        sections[0].location.z = dz + hh + 0.1 + 2.0 * t
        sections[0].keyframe_insert("location", frame=f)
        sections[1].location.z = 1.4 * t
        sections[1].keyframe_insert("location", frame=f)
        sections[2].location.z = 1.3 * t
        sections[2].keyframe_insert("location", frame=f)
        head.rotation_euler = (0, 0, 2 * math.pi * t)
        head.keyframe_insert("rotation_euler", frame=f)

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
        (100, "erect", dict(target=(0, -0.5, 5.2), dist=27, az=-60, elev=6)),
        (
            100,
            "photo",
            dict(target=(0, 0.0, 5.0), dist=23, az=48, elev=4, res=(1100, 733)),
        ),
        (50, "raising", dict(target=(0, -1.5, 3.5), dist=20, az=-85, elev=5)),
    )
    for frame, name, kw in views:
        scn.frame_set(frame)
        render(f"{out}/IRAD_Bavar373_TELAR_{name}.png", **kw)
