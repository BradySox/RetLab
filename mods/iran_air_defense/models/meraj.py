"""Meraj-4 search radar (IRAD_Meraj4_SR), matched to two photographs and a render:
a slatted planar array with an IFF column and a top antenna, on two A-frame legs over
a turntable, on a tri-axle semi-trailer standing on four outrigger jacks. Plain
khaki, as photographed. Modelled deployed; the towed travel fit is deferred.

arg_antenna_azimuth: frames 0-100, one full turn of the array.
"""

import math
import sys

import bpy

sys.path.insert(0, sys.argv[-1])
import irad_kit  # noqa: E402
from irad_kit import *  # noqa: E402,F403

KHAKI = lambda: mat("irad_khaki", (0.30, 0.29, 0.17), 0.75)  # noqa: E731
AW, AH, AD = 8.3, 3.9, 0.45  # array width, height, depth
TILT = math.radians(10)
STEPS = 11


def array(parent):
    """The planar array: fine horizontal slats over a dark face, a braced back frame,
    end caps, a thick bottom beam, the IFF column and the secondary radome on top."""
    box("mj_back", (AW, AD, AH), (0, -AD / 2, AH / 2), KHAKI(), parent, 0.04)
    box(
        "mj_facebacking",
        (AW - 0.3, 0.02, AH - 0.1),
        (0, 0.005, AH / 2),
        DARK(),
        parent,
        0,
    )
    rows = 44
    for k in range(rows):
        z = 0.12 + k * (AH - 0.24) / (rows - 1)
        box(f"mj_slat{k}", (AW - 0.3, 0.12, 0.045), (0, 0.07, z), KHAKI(), parent, 0)
    for s in (-1, 1):
        box(
            f"mj_endcap{s}",
            (0.12, AD + 0.16, AH),
            (s * (AW / 2 - 0.06), -AD / 2 + 0.08, AH / 2),
            KHAKI(),
            parent,
            0.02,
        )
    box(
        "mj_bottomframe",
        (AW + 0.1, AD + 0.3, 0.24),
        (0, -AD / 2, 0.0),
        KHAKI(),
        parent,
        0.02,
    )
    box("mj_topframe", (AW, AD + 0.1, 0.12), (0, -AD / 2, AH), KHAKI(), parent, 0.02)
    # back: vertical ribs, two horizontal beams, diagonal bracing
    back_y = -AD - 0.06
    for x in (-3.6, -2.0, -0.6, 0.6, 2.0, 3.6):
        box(
            f"mj_backrib{x}",
            (0.12, 0.12, AH),
            (x, back_y, AH / 2),
            KHAKI(),
            parent,
            0.01,
        )
    for z in (AH * 0.3, AH * 0.7):
        box(
            f"mj_backbeam{z:.1f}",
            (AW - 0.2, 0.14, 0.14),
            (0, back_y - 0.1, z),
            KHAKI(),
            parent,
            0.01,
        )
    for k, (x0, x1) in enumerate(((-3.6, -2.0), (-2.0, -0.6), (0.6, 2.0), (2.0, 3.6))):
        strut(
            f"mj_backdiag{k}",
            (x0, back_y - 0.12, AH * 0.3),
            (x1, back_y - 0.12, AH * 0.7),
            0.04,
            KHAKI(),
            parent,
            6,
        )
    white = mat("irad_white", (0.8, 0.8, 0.78), 0.5)
    for k in range(5):
        box(
            f"mj_iff{k}",
            (0.32, 0.25, 0.6),
            (AW / 2 + 0.18, 0.02, 0.45 + k * 0.72),
            white,
            parent,
            0.02,
        )
        box(
            f"mj_iffmount{k}",
            (0.1, 0.12, 0.1),
            (AW / 2 + 0.05, -0.05, 0.45 + k * 0.72),
            KHAKI(),
            parent,
            0,
        )
    box(
        "mj_iffrail",
        (0.08, 0.1, AH),
        (AW / 2 + 0.05, -0.05, AH / 2),
        KHAKI(),
        parent,
        0,
    )
    # the secondary radome on top, on brackets, with small whips at the corners
    for s in (-1, 1):
        box(
            f"mj_topbracket{s}",
            (0.14, 0.35, 0.4),
            (s * 1.2, -AD / 2, AH + 0.25),
            KHAKI(),
            parent,
            0.01,
        )
        box(
            f"mj_topbracketfoot{s}",
            (0.4, 0.5, 0.06),
            (s * 1.2, -AD / 2, AH + 0.06),
            KHAKI(),
            parent,
            0,
        )
    box(
        "mj_topradome",
        (3.3, 0.55, 0.45),
        (0, -AD / 2 + 0.05, AH + 0.62),
        KHAKI(),
        parent,
        0.18,
    )
    for s in (-1, 1):
        box(
            f"mj_toparm{s}",
            (0.06, 0.06, 0.8),
            (s * (AW / 2 - 0.4), -AD / 2, AH + 0.35),
            KHAKI(),
            parent,
            0,
            (0.4, 0, 0),
        )
        box(
            f"mj_topend{s}",
            (0.2, 0.2, 0.25),
            (s * (AW / 2 - 0.3), -AD / 2, AH + 0.15),
            KHAKI(),
            parent,
            0.02,
        )


def trapezoid(name, w0, w1, h, t, center, parent, material):
    """A flat trapezoid plate standing in the Y-Z plane: w0 wide at the base, w1 at the top."""
    x, y, z = center
    mesh = bpy.data.meshes.new(name)
    hx = t / 2
    verts = [
        (-hx, -w0 / 2, 0),
        (-hx, w0 / 2, 0),
        (-hx, w1 / 2, h),
        (-hx, -w1 / 2, h),
        (hx, -w0 / 2, 0),
        (hx, w0 / 2, 0),
        (hx, w1 / 2, h),
        (hx, -w1 / 2, h),
    ]
    faces = [
        (0, 1, 2, 3),
        (7, 6, 5, 4),
        (0, 4, 5, 1),
        (1, 5, 6, 2),
        (2, 6, 7, 3),
        (3, 7, 4, 0),
    ]
    mesh.from_pydata(verts, [], faces)
    o = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(o)
    o.location = (x, y, z)
    o.data.materials.append(material)
    b = o.modifiers.new("bevel", "BEVEL")
    b.width = 0.03
    b.segments = 2
    o.parent = parent
    return o


def trailer(root):
    """Tri-axle semi-trailer: low main deck, raised gooseneck with an open frame."""
    deck_z = 1.2
    rear, neck, front = -6.5, 2.6, 6.5
    box(
        "mj_deck",
        (2.5, neck - rear, 0.25),
        (0, (neck + rear) / 2, deck_z - 0.12),
        KHAKI(),
        root,
        0.02,
    )
    for s in (-1, 1):
        box(
            f"mj_rail{s}",
            (0.2, neck - rear, 0.4),
            (s * 0.5, (neck + rear) / 2, deck_z - 0.4),
            KHAKI(),
            root,
            0.01,
        )
        box(
            f"mj_edge{s}",
            (0.06, neck - rear, 0.14),
            (s * 1.24, (neck + rear) / 2, deck_z - 0.14),
            KHAKI(),
            root,
            0,
        )
        box(
            f"mj_neckrail{s}",
            (0.22, front - neck - 0.4, 0.4),
            (s * 0.95, (front + neck) / 2 + 0.2, 1.7),
            KHAKI(),
            root,
            0.01,
        )
        strut(
            f"mj_neckrise{s}",
            (s * 1.0, neck - 0.3, deck_z - 0.1),
            (s * 0.95, neck + 1.0, 1.7),
            0.14,
            KHAKI(),
            root,
        )
    for k in range(4):
        box(
            f"mj_neckcross{k}",
            (1.9, 0.14, 0.14),
            (0, neck + 0.9 + k * 0.95, 1.7),
            KHAKI(),
            root,
            0,
        )
    box("mj_neckplate", (2.1, 0.8, 0.12), (0, front - 0.5, 1.85), KHAKI(), root, 0.01)
    cyl("mj_kingpin", 0.06, 0.3, (0, front - 1.1, 1.45), (0, 0, 0), METAL(), root, 10)
    # landing legs under the neck
    for s in (-1, 1):
        box(
            f"mj_landingleg{s}",
            (0.14, 0.14, 1.5),
            (s * 0.9, neck + 1.2, 0.8),
            KHAKI(),
            root,
            0,
        )
        box(
            f"mj_landingfoot{s}",
            (0.35, 0.35, 0.05),
            (s * 0.9, neck + 1.2, 0.03),
            DARK(),
            root,
            0,
        )
    # tri-axle bogie with dual wheels
    for i, y in enumerate((-5.4, -4.35, -3.3)):
        box(f"mj_axle{i}", (2.4, 0.16, 0.16), (0, y, 0.5), DARK(), root, 0.01)
        for s in (-1, 1):
            for d in (0, 1):
                wheel(
                    f"mj_wheel_{i}{s}{d}",
                    (s * (0.8 + d * 0.33), y, 0.5),
                    0.5,
                    0.3,
                    root,
                )
        for s in (-1, 1):
            box(
                f"mj_mudguard{i}{s}",
                (0.75, 1.0, 0.05),
                (s * 0.97, y, 1.02),
                DARK(),
                root,
                0,
            )
    for s in (-1, 1):
        box(
            f"mj_taillight{s}",
            (0.25, 0.04, 0.1),
            (s * 1.0, rear - 0.02, deck_z - 0.4),
            RED(),
            root,
            0,
        )
    # four outrigger jacks on swing arms, deployed
    for s_ in (-1, 1):
        for y, tag in ((rear + 0.5, "r"), (front - 0.6, "f")):
            z = deck_z - 0.2 if tag == "r" else 1.6
            # heavy boxed outrigger beam angling out and down to the jack head
            strut(
                f"mj_outbeam{s_}{tag}",
                (s_ * 0.6, y, z + 0.1),
                (s_ * 2.25, y, z - 0.1),
                0.15,
                KHAKI(),
                root,
                4,
            )
            strut(
                f"mj_outbrace{s_}{tag}",
                (s_ * 0.6, y, z - 0.45),
                (s_ * 2.1, y, z - 0.1),
                0.07,
                KHAKI(),
                root,
                6,
            )
            box(
                f"mj_outhead{s_}{tag}",
                (0.35, 0.35, 0.3),
                (s_ * 2.3, y, z - 0.1),
                KHAKI(),
                root,
                0.02,
            )
            screw_jack(f"mj_jack{s_}{tag}", s_ * 2.3, y, z - 0.2, root)
            for k in range(4):
                cyl(
                    f"mj_jackspring{s_}{tag}{k}",
                    0.16,
                    0.04,
                    (s_ * 2.3, y, z - 0.65 - k * 0.08),
                    (0, 0, 0),
                    KHAKI(),
                    root,
                    14,
                )
    # deck equipment: two cabinets with doors and grilles, a cable reel, a ladder
    for k, (x, w) in enumerate(((0.65, 1.0), (-0.65, 0.9))):
        box(
            f"mj_cabinet{k}", (w, 1.0, 1.0), (x, 0.6, deck_z + 0.5), KHAKI(), root, 0.03
        )
        door(
            f"mj_cabdoor{k}",
            (x, 1.1, deck_z + 0.5),
            "y",
            1,
            w * 0.7,
            0.8,
            root,
            KHAKI(),
        )
    grille("mj_cabgrille", (1.15, 0.6, deck_z + 0.55), "x", 1, 0.7, 0.6, root, 6)
    cable_reel("mj_reel", (0.0, -0.9, deck_z + 0.4), root)
    ladder("mj_deckladder", (-1.25, -0.6, deck_z), (-1.8, -0.6, 0.03), 0.44, 4, root)
    return deck_z


def build():
    reset()
    irad_kit.PAINT = KHAKI  # kit doors and grilles take the trailer's plain khaki
    root = empty("IRAD_Meraj4_SR", (0, 0, 0))
    deck_z = trailer(root)
    ty = -3.1
    cyl("mj_ring", 1.3, 0.25, (0, ty, deck_z + 0.12), (0, 0, 0), METAL(), root, 40)
    az = empty("arg_antenna_azimuth", (0, ty, deck_z + 0.25), root)
    box("mj_platform", (3.4, 2.4, 0.2), (0, 0, 0.1), KHAKI(), az, 0.02)
    box("mj_drive", (1.2, 0.8, 0.6), (-0.3, -0.6, 0.5), KHAKI(), az, 0.03)
    grille("mj_drivegrille", (-0.3, -1.0, 0.5), "y", -1, 0.8, 0.4, az, 5)
    hinge_z = 1.75
    for s in (-1, 1):
        # solid trapezoid pedestal legs, wide at the platform, narrow at the trunnion
        trapezoid(
            f"mj_leg{s}",
            2.3,
            0.9,
            hinge_z - 0.2,
            0.36,
            (s * 1.72, -0.05, 0.2),
            az,
            KHAKI(),
        )
        box(
            f"mj_legflange{s}",
            (0.5, 2.4, 0.12),
            (s * 1.72, -0.05, 0.26),
            KHAKI(),
            az,
            0.01,
        )
        for k in range(3):
            box(
                f"mj_legstiff{s}{k}",
                (0.12, 0.08, 1.1),
                (s * (1.72 - 0.22), -0.6 + k * 0.55, 0.8),
                KHAKI(),
                az,
                0.01,
            )
        box(
            f"mj_trunnion{s}",
            (0.42, 0.7, 0.4),
            (s * 1.85, -0.05, hinge_z),
            KHAKI(),
            az,
            0.02,
        )
        cyl(
            f"mj_trunnionpin{s}",
            0.12,
            0.2,
            (s * 2.1, -0.05, hinge_z),
            (0, math.pi / 2, 0),
            METAL(),
            az,
            14,
        )
    box("mj_crossbeam", (3.3, 0.35, 0.3), (0, -0.05, hinge_z - 0.35), KHAKI(), az, 0.02)
    box("mj_centercab", (1.1, 0.9, 0.9), (0.45, 0.35, 0.65), KHAKI(), az, 0.03)
    grille("mj_centergrille", (0.45, 0.8, 0.65), "y", 1, 0.8, 0.6, az, 6)
    door("mj_centerdoor", (1.0, 0.35, 0.65), "x", 1, 0.6, 0.7, az, KHAKI())
    ladder(
        "mj_pedladder",
        (-0.55, 0.45, hinge_z - 0.2),
        (-0.55, 0.9, 0.2),
        0.4,
        5,
        az,
        axis="y",
    )
    for s in (-1, 1):
        hose(
            f"mj_pedcable{s}",
            [
                (s * 0.3, -0.5, 0.25),
                (s * 0.8, -0.5, 1.0),
                (s * 1.6, -0.3, hinge_z - 0.2),
            ],
            0.03,
            DARK(),
            az,
        )
    tilt = empty("mj_array_tilt", (0, -0.05, hinge_z), az, (TILT, 0, 0))
    array(tilt)
    for i in range(STEPS):
        f = i * 100 // (STEPS - 1)
        az.rotation_euler = (0, 0, 2 * math.pi * i / (STEPS - 1))
        az.keyframe_insert("rotation_euler", frame=f)
    shell = box("collision_shell", (2.6, 13.0, 2.0), (0, 0, 1.0), DARK(), root, 0)
    shell.hide_render = True
    shell2 = box(
        "collision_shell_array", (AW, 1.0, AH), (0, 0, hinge_z + AH / 2), DARK(), az, 0
    )
    shell2.hide_render = True
    return az


if __name__ == "__main__":
    out = sys.argv[-1]
    az = build()
    finalize("IRAD_Meraj4_SR")
    animate_wheels()
    bpy.context.scene.frame_set(0)
    bpy.ops.wm.save_as_mainfile(filepath=f"{out}/IRAD_Meraj4_SR.blend")
    az.animation_data_clear()
    views = (
        (0.0, "front", dict(target=(0, 0, 3.0), dist=20, az=-20, elev=6)),
        (0.0, "side", dict(target=(0, 0, 2.6), dist=21, az=-100, elev=4)),
        (0.6, "quarter", dict(target=(0, 0, 3.0), dist=20, az=-55, elev=12)),
    )
    for rot, name, kw in views:
        az.rotation_euler = (0, 0, rot)
        render(f"{out}/IRAD_Meraj4_SR_{name}.png", **kw)
