"""3rd Khordad TELAR (IRAD_3Khordad_TELAR), matched to two photographs: a 6x6 with a low
cab and an equipment body, carrying a turret with a wedge-shaped radar at its front and
three Taer-2 missiles on an elevating cradle above it. Band camouflage: sand, brown,
olive, black edges.

arg_turret_azimuth: frames 0-100, one full turn of the turret (radar and launcher).
arg_launcher_elevation: frames 0-100, 15 deg travel rest to 65 deg.
"""

import math
import sys

import bpy

sys.path.insert(0, sys.argv[-1])
import irad_kit  # noqa: E402
from irad_kit import *  # noqa: E402,F403
from irad_kit import _flat, _on_face  # noqa: E402,F401

STEPS = 11
EL0, EL1 = 15, 65
WHITE = lambda: mat("irad_nose", (0.8, 0.8, 0.78), 0.4)  # noqa: E731
BODY = lambda: mat("irad_msl", (0.1, 0.12, 0.07), 0.55)  # noqa: E731
FACE = lambda: mat("irad_radome", (0.5, 0.5, 0.47), 0.6)  # noqa: E731


def band_camo():
    """The 3rd Khordad's band camouflage as photographed: sand, broad brown and olive
    bands, a thin black edge on the brown. Named irad_camo so the kit bakes it."""
    m = bpy.data.materials.new("irad_camo")
    m.use_nodes = True
    N, L = m.node_tree.nodes, m.node_tree.links
    bsdf = N["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.72
    geo = N.new("ShaderNodeNewGeometry")
    mp = N.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (0.55, 0.3, 0.9)  # bands run long, as painted
    L.new(geo.outputs["Position"], mp.inputs["Vector"])

    def noise(seed_offset):
        n = N.new("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value = 0.7
        n.inputs["Detail"].default_value = 1.0
        n.noise_dimensions = "4D"
        n.inputs["W"].default_value = seed_offset
        L.new(mp.outputs["Vector"], n.inputs["Vector"])
        return n

    def ramp(src, stops):
        r = N.new("ShaderNodeValToRGB")
        r.color_ramp.interpolation = "CONSTANT"
        els = r.color_ramp.elements
        els[0].position, els[0].color = 0.0, (0, 0, 0, 1)
        els[1].position, els[1].color = stops[0][0], stops[0][1]
        for pos, col in stops[1:]:
            e = els.new(pos)
            e.color = col
        L.new(src.outputs["Fac"], r.inputs["Fac"])
        return r.outputs["Color"]

    sand, brown, olive, black = (
        (0.55, 0.44, 0.27),
        (0.17, 0.09, 0.04),
        (0.11, 0.12, 0.05),
        (0.02, 0.02, 0.02),
    )
    n1, n2 = noise(0.0), noise(7.3)
    edge = ramp(
        n1, [(0.555, (1, 1, 1, 1)), (0.575, (0, 0, 0, 1))]
    )  # 1 inside the black edge
    brown_m = ramp(n1, [(0.575, (1, 1, 1, 1))])
    olive_m = ramp(n2, [(0.6, (1, 1, 1, 1))])
    col = N.new("ShaderNodeMix")
    col.data_type = "RGBA"
    col.inputs[6].default_value = (*sand, 1)
    col.inputs[7].default_value = (*olive, 1)
    L.new(olive_m, col.inputs[0])
    col2 = N.new("ShaderNodeMix")
    col2.data_type = "RGBA"
    col2.inputs[7].default_value = (*brown, 1)
    L.new(col.outputs[2], col2.inputs[6])
    L.new(brown_m, col2.inputs[0])
    col3 = N.new("ShaderNodeMix")
    col3.data_type = "RGBA"
    col3.inputs[7].default_value = (*black, 1)
    L.new(col2.outputs[2], col3.inputs[6])
    L.new(edge, col3.inputs[0])
    L.new(col3.outputs[2], bsdf.inputs["Base Color"])
    return m


def missile(k, x, parent):
    """A Taer-2 on its rail: white ogive nose, dark body, long-chord mid wings,
    clipped tail fins with actuator fairings. Lies along +y from its tail at y=0."""
    ln, r = 4.8, 0.17
    msl = empty(f"kh_msl{k}", (x, 0, 0.32), parent)
    cyl(
        f"kh_msl{k}_body",
        r,
        ln - 0.9,
        (0, (ln - 0.9) / 2, 0),
        (-math.pi / 2, 0, 0),
        BODY(),
        msl,
        20,
    )
    bpy.ops.mesh.primitive_cone_add(
        vertices=20,
        radius1=r,
        radius2=0.02,
        depth=0.9,
        location=(0, ln - 0.45, 0),
        rotation=(-math.pi / 2, 0, 0),
    )
    nose = bpy.context.active_object
    nose.name = f"kh_msl{k}_nose"
    nose.data.materials.append(WHITE())
    nose.parent = msl
    cyl(
        f"kh_msl{k}_band",
        r + 0.005,
        0.06,
        (0, ln - 0.92, 0),
        (-math.pi / 2, 0, 0),
        WHITE(),
        msl,
        20,
    )
    cyl(
        f"kh_msl{k}_nozzle",
        r * 0.7,
        0.12,
        (0, -0.04, 0),
        (-math.pi / 2, 0, 0),
        DARK(),
        msl,
        16,
    )
    for q in range(4):
        a = q * math.pi / 2 + math.pi / 4
        c, s = math.cos(a), math.sin(a)
        # mid wing: long low strake
        box(
            f"kh_msl{k}_wing{q}",
            (0.02, 1.3, 0.24),
            (c * (r + 0.1), 2.3, s * (r + 0.1)),
            BODY(),
            msl,
            0,
            (0, -a + math.pi / 2, 0),
        )
        # tail fin and its actuator fairing
        box(
            f"kh_msl{k}_fin{q}",
            (0.02, 0.42, 0.3),
            (c * (r + 0.13), 0.28, s * (r + 0.13)),
            BODY(),
            msl,
            0,
            (0, -a + math.pi / 2, 0),
        )
        box(
            f"kh_msl{k}_fair{q}",
            (0.07, 0.5, 0.07),
            (c * r, 0.4, s * r),
            BODY(),
            msl,
            0.01,
            (0, -a, 0),
        )
    # the rail beam under the missile, with shoes
    box(f"kh_rail{k}", (0.12, 4.2, 0.14), (x, 2.1, 0.08), PAINT(), parent, 0.01)
    for j, y in enumerate((0.6, 2.6)):
        box(f"kh_shoe{k}{j}", (0.08, 0.2, 0.1), (x, y, 0.17), METAL(), parent, 0)
    empty(f"LAUNCH_{k + 1}", (x, ln, 0.32), parent, (-math.pi / 2, 0, 0))


def prism(name, pts, x0, x1, material, parent, bevel=0.03):
    """A profile in (y, z) extruded across x from x0 to x1."""
    bm = bmesh.new()
    rings = [[bm.verts.new((xs, y, z)) for y, z in pts] for xs in (x0, x1)]
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((rings[0][i], rings[0][j], rings[1][j], rings[1][i]))
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    ob.parent = parent
    me.materials.append(material)
    if bevel:
        ob.modifiers.new("bevel", "BEVEL").width = bevel
    return ob


def khordad_cab(root, front, width, cab_len, bottom):
    """The low wedge cab as photographed: a short upright nose, a steeply raked
    two-pane windscreen, a flat roof, a door with a window on each side."""
    nose, roof, rake = 0.9, 1.8, 0.75
    pts = [
        (front, 0),
        (front, nose),
        (front - rake, roof),
        (front - cab_len, roof),
        (front - cab_len, 0),
    ]
    prism(
        "kh_cab",
        [(y, bottom + z) for y, z in pts],
        -width / 2,
        width / 2,
        PAINT(),
        root,
        0.06,
    )
    ang = math.atan2(rake, roof - nose)  # rake from vertical
    ln = math.hypot(rake, roof - nose)
    cy, cz = front - rake / 2, bottom + (nose + roof) / 2
    ny, nz = math.cos(ang), math.sin(ang)  # outward normal of the raked face
    for s in (-1, 1):
        box(
            f"kh_windscreen{s}",
            (width * 0.43, 0.03, ln * 0.78),
            (s * width * 0.235, cy + ny * 0.012, cz + nz * 0.012),
            GLASS(),
            root,
            0.04,
            (ang, 0, 0),
        )
        for k in range(2):
            box(
                f"kh_wiper{s}{k}",
                (0.5, 0.02, 0.025),
                (
                    s * (0.3 + k * 0.55),
                    cy - ln * 0.35 * nz + ny * 0.03,
                    cz - ln * 0.35 * ny + nz * 0.03,
                ),
                DARK(),
                root,
                0,
                (ang, 0, 0.3),
            )
        # side window: a trapezoid following the rake, and the door behind it
        wpts = [
            (front - 0.12, nose + 0.12),
            (front - rake + 0.05, roof - 0.12),
            (front - 1.25, roof - 0.12),
            (front - 1.25, nose + 0.12),
        ]
        prism(
            f"kh_sidewin{s}",
            [(y, bottom + z) for y, z in wpts],
            s * (width / 2 - 0.01),
            s * (width / 2 + 0.012),
            GLASS(),
            root,
            0,
        )
        door(
            f"kh_cabdoor{s}",
            (s * width / 2, front - 1.0, bottom + 0.8),
            "x",
            s,
            0.95,
            1.5,
            root,
            material=PAINT(),
            hinge_side=1,
        )
        box(
            f"kh_mirrorarm{s}",
            (0.3, 0.03, 0.03),
            (s * (width / 2 + 0.15), front - 0.4, bottom + 1.5),
            DARK(),
            root,
            0,
        )
        box(
            f"kh_mirror{s}",
            (0.06, 0.16, 0.4),
            (s * (width / 2 + 0.3), front - 0.4, bottom + 1.35),
            DARK(),
            root,
            0.02,
        )
        cyl(
            f"kh_headlamp{s}",
            0.09,
            0.05,
            (s * (width / 2 - 0.3), front + 0.02, bottom + 0.35),
            (math.pi / 2, 0, 0),
            GLASS(),
            root,
            16,
        )
        box(
            f"kh_indicator{s}",
            (0.14, 0.03, 0.08),
            (s * (width / 2 - 0.12), front + 0.015, bottom + 0.35),
            AMBER(),
            root,
            0,
        )
        box(
            f"kh_plate{s}",
            (0.4, 0.03, 0.12),
            (s * (width / 2 - 0.45), front + 0.02, bottom + 0.7),
            mat("irad_plate", (0.8, 0.8, 0.8), 0.4),
            root,
            0,
        )
        box(
            f"kh_cornerstep{s}",
            (0.3, 0.3, 0.04),
            (s * (width / 2 - 0.2), front + 0.1, bottom - 0.35),
            METAL(),
            root,
            0,
        )
        for k in range(2):
            box(
                f"kh_cabrung{s}{k}",
                (0.1, 0.45, 0.035),
                (s * (width / 2 - 0.05), front - 1.0, bottom - 0.45 + k * 0.28),
                METAL(),
                root,
                0,
            )
    box(
        "kh_centreplate",
        (0.5, 0.03, 0.12),
        (0, front + 0.02, bottom + 0.7),
        mat("irad_plate", (0.8, 0.8, 0.8), 0.4),
        root,
        0,
    )
    box(
        "kh_grille",
        (0.9, 0.03, 0.22),
        (0, front + 0.02, bottom + 0.35),
        DARK(),
        root,
        0.01,
    )
    box(
        "kh_bumper",
        (width + 0.02, 0.22, 0.25),
        (0, front + 0.1, bottom - 0.12),
        DARK(),
        root,
        0.03,
    )
    for s in (-1, 1):
        cyl(
            f"kh_beacon{s}",
            0.06,
            0.12,
            (s * 0.4, front - rake - 0.2, bottom + roof + 0.06),
            (0, 0, 0),
            RED(),
            root,
            12,
        )
    box(
        "kh_roofrack",
        (width - 0.4, cab_len - rake - 0.3, 0.05),
        (0, front - rake - (cab_len - rake) / 2, bottom + roof + 0.03),
        DARK(),
        root,
        0,
    )


def radar(tur, z0):
    """The wedge radar at the turret's front: tall at the rear, its antenna face
    sloping down to a short front wall."""
    y0, y1, hr, hf, w = -0.6, 2.8, 1.55, 0.8, 2.45
    prism(
        "kh_radar",
        [(y0, z0), (y1, z0), (y1, z0 + hf), (y0 + 0.25, z0 + hr), (y0, z0 + hr)],
        -w / 2,
        w / 2,
        PAINT(),
        tur,
    )
    # antenna face: a lighter panel lying on the slope, with a raised rim
    ang = math.atan2(hr - hf, (y1 - (y0 + 0.25)))
    cy, cz = (y1 + y0 + 0.25) / 2, z0 + (hr + hf) / 2
    ln = math.hypot(hr - hf, y1 - y0 - 0.25)
    nz, ny = math.cos(ang), math.sin(ang)  # outward normal of the slope
    box(
        "kh_face",
        (w - 0.2, ln - 0.2, 0.03),
        (0, cy + ny * 0.015, cz + nz * 0.015),
        FACE(),
        tur,
        0.01,
        (-ang, 0, 0),
    )
    for k, dl in enumerate(((ln - 0.12) / 2, -(ln - 0.12) / 2)):
        box(
            f"kh_facerim{k}",
            (w - 0.1, 0.06, 0.06),
            (
                0,
                cy + dl * math.cos(ang) + ny * 0.03,
                cz - dl * math.sin(ang) + nz * 0.03,
            ),
            PAINT(),
            tur,
            0,
            (-ang, 0, 0),
        )
    for s in (-1, 1):
        box(
            f"kh_facerimside{s}",
            (0.06, ln, 0.06),
            (s * (w / 2 - 0.05), cy + ny * 0.03, cz + nz * 0.03),
            PAINT(),
            tur,
            0,
            (-ang, 0, 0),
        )
        # side walls: an access door and a vent on each
        door(
            f"kh_radardoor{s}", (s * w / 2, y0 + 0.6, z0 + 0.75), "x", s, 0.6, 1.0, tur
        )
        grille(
            f"kh_radargrille{s}",
            (s * w / 2, y1 - 0.6, z0 + 0.4),
            "x",
            s,
            0.6,
            0.35,
            tur,
            5,
        )
    # front wall: a dark lower strip, a vent, lamps; an IFF bar on top
    box(
        "kh_radarfrontstrip",
        (w - 0.1, 0.03, 0.1),
        (0, y1 + 0.01, z0 + 0.08),
        DARK(),
        tur,
        0,
    )
    grille("kh_radarfrontgrille", (0.7, y1, z0 + hf / 2), "y", 1, 0.6, 0.3, tur, 4)
    for s in (-1, 1):
        cyl(
            f"kh_radarlamp{s}",
            0.06,
            0.05,
            (s * 0.9, y1 + 0.03, z0 + 0.2),
            (math.pi / 2, 0, 0),
            GLASS(),
            tur,
            12,
        )
    box("kh_iff", (1.2, 0.12, 0.1), (0, y0 + 0.15, z0 + hr + 0.08), DARK(), tur, 0.01)
    for s in (-1, 1):
        cyl(
            f"kh_whip{s}",
            0.015,
            1.2,
            (s * 1.05, y0 + 0.1, z0 + hr + 0.6),
            (0, 0, 0),
            DARK(),
            tur,
            6,
        )
    return z0 + hr


def build():
    reset()
    band_camo()
    axles = [2.9, -1.55, -2.95]
    root, dz, rear, cab_back = iran_truck(
        "IRAD_3Khordad_TELAR",
        axles,
        9.0,
        width=2.5,
        cab_len=2.3,
        frame_h=1.05,
        wheel_r=0.62,
        cab=False,
    )
    khordad_cab(root, 4.5, 2.5, 2.3, dz - 0.2)
    # equipment body behind the cab, as photographed: doors, a panel window, louvers
    by0, by1, bh = cab_back - 0.08, rear + 0.2, 1.3
    bcy, blen = (by0 + by1) / 2, by0 - by1
    btop = dz + bh
    box("kh_body", (2.5, blen, bh), (0, bcy, dz + bh / 2), PAINT(), root, 0.04)
    box("kh_bodylip", (2.56, blen + 0.04, 0.06), (0, bcy, btop), PAINT(), root, 0.01)
    green = mat("irad_led", (0.1, 0.8, 0.3), 0.3)
    for s in (-1, 1):
        door(f"kh_door{s}", (s * 1.25, by0 - 0.55, dz + 0.62), "x", s, 0.75, 1.1, root)
        box(
            f"kh_doorwin{s}",
            _flat("x", 0.45, 0.4, 0.02),
            _on_face((s * 1.25, by0 - 0.55, dz + 0.85), "x", s, 0.03),
            DARK(),
            root,
            0,
        )
        for r in range(3):
            for c in range(4):
                box(
                    f"kh_led{s}{r}{c}",
                    _flat("x", 0.05, 0.035, 0.02),
                    _on_face(
                        (s * 1.25, by0 - 0.7 + c * 0.1, dz + 0.75 + r * 0.09),
                        "x",
                        s,
                        0.045,
                    ),
                    green,
                    root,
                    0,
                )
        grille(
            f"kh_louver{s}", (s * 1.25, by0 - 1.5, dz + 0.75), "x", s, 0.6, 0.6, root, 7
        )
        door(
            f"kh_bay{s}",
            (s * 1.25, bcy - 1.0, dz + 0.62),
            "x",
            s,
            1.0,
            1.0,
            root,
            hinge_side=1,
        )
        door(
            f"kh_reardoor{s}", (s * 1.25, by1 + 0.55, dz + 0.62), "x", s, 0.7, 1.0, root
        )
        stencil(
            f"kh_name{s}",
            "3 KHORDAD",
            (s * 1.28, bcy + 0.2, dz + 1.1),
            (math.pi / 2, 0, s * math.pi / 2),
            0.13,
            DARK(),
            root,
        )
        box(
            f"kh_sidestep{s}",
            (0.3, 0.8, 0.04),
            (s * 1.38, by0 - 0.55, dz - 0.15),
            METAL(),
            root,
            0,
        )
    ladder(
        "kh_rearladder",
        (0.6, rear - 0.05, btop + 0.1),
        (0.6, rear - 0.05, 0.4),
        0.4,
        5,
        root,
    )
    box(
        "kh_rearbox",
        (1.0, 0.25, 0.6),
        (-0.55, rear + 0.05, dz + 0.5),
        PAINT(),
        root,
        0.02,
    )
    # four hydraulic jacks: at the cab front corners and the rear corners
    for s in (-1, 1):
        for jy, tag in ((4.5 - 0.35, "f"), (rear + 0.35, "r")):
            box(
                f"kh_jackarm{s}{tag}",
                (0.35, 0.25, 0.2),
                (s * 1.2, jy, dz - 0.35),
                DARK(),
                root,
                0.01,
            )
            screw_jack(f"kh_jack{s}{tag}", s * 1.42, jy, dz - 0.25, root)
            hose(
                f"kh_jackhose{s}{tag}",
                [
                    (s * 1.35, jy, dz - 0.3),
                    (s * 1.3, jy + 0.2, dz - 0.6),
                    (s * 1.1, jy + 0.35, dz - 0.4),
                ],
                0.02,
                DARK(),
                root,
            )

    # turret: ring, platform, the radar at the front, the launcher cradle at the rear
    ty = bcy + 0.8  # the radar overhangs the cab, as photographed
    cyl("kh_ring", 1.05, 0.12, (0, ty, btop + 0.06), (0, 0, 0), METAL(), root, 32)
    tur = empty("arg_turret_azimuth", (0, ty, btop + 0.12), root)
    box("kh_platform", (2.45, 3.9, 0.28), (0, 0.15, 0.14), PAINT(), tur, 0.03)
    for s in (-1, 1):
        box(f"kh_skirt{s}", (0.05, 3.9, 0.12), (s * 1.24, 0.15, 0.02), PAINT(), tur, 0)
    rz = radar(tur, 0.28)
    # turret housing behind the radar: the big square AC fan on its left, doors
    hy0, hy1, hh = -0.6, -1.75, 0.95
    box(
        "kh_housing",
        (2.45, hy0 - hy1, hh),
        (0, (hy0 + hy1) / 2, 0.28 + hh / 2),
        PAINT(),
        tur,
        0.03,
    )
    box(
        "kh_acframe",
        (0.06, 0.85, 0.8),
        (-1.24, (hy0 + hy1) / 2, 0.28 + hh / 2),
        METAL(),
        tur,
        0.01,
    )
    fan("kh_acfan", (-1.25, (hy0 + hy1) / 2, 0.28 + hh / 2), "-x", 0.33, tur)
    door(
        "kh_housingdoor",
        (1.225, (hy0 + hy1) / 2, 0.28 + hh / 2),
        "x",
        1,
        0.8,
        0.75,
        tur,
    )
    grille("kh_housinggrille", (0, hy1, 0.28 + hh / 2), "y", -1, 1.2, 0.5, tur, 6)
    # cradle: two side cheeks up to the trunnion, a cross tube; launcher on the pivot
    PY, PZ = -1.7, rz - 0.15
    for s in (-1, 1):
        box(
            f"kh_cheek{s}",
            (0.14, 0.8, PZ - 0.2),
            (s * 1.0, PY + 0.1, 0.28 + (PZ - 0.28) / 2),
            PAINT(),
            tur,
            0.02,
        )
        cyl(
            f"kh_trunnion{s}",
            0.13,
            0.2,
            (s * 1.0, PY, PZ),
            (0, math.pi / 2, 0),
            METAL(),
            tur,
            16,
        )
    cyl("kh_crosstube", 0.1, 2.0, (0, PY, PZ), (0, math.pi / 2, 0), METAL(), tur, 14)
    piv = empty("arg_launcher_elevation", (0, PY, PZ), tur)
    box("kh_launchbeam", (2.2, 0.35, 0.22), (0, 0.3, -0.05), PAINT(), piv, 0.02)
    box("kh_launchspine", (0.4, 3.2, 0.2), (0, 1.9, -0.05), PAINT(), piv, 0.02)
    for j, y in enumerate((1.4, 3.1)):
        box(f"kh_crossarm{j}", (2.1, 0.18, 0.14), (0, y, 0.02), PAINT(), piv, 0.01)
        for s in (-1, 1):
            strut(
                f"kh_brace{j}{s}",
                (s * 1.0, y, 0.02),
                (0, y - 0.8, -0.1),
                0.03,
                PAINT(),
                piv,
                6,
            )
    for k, x in enumerate((-0.68, 0.0, 0.68)):
        missile(k, x, piv)
    # elevation ram from the platform to the launcher spine
    A = (1.2, -0.12)  # on the spine, pivot frame (y, z)
    B = (PY + 1.9, 0.35)  # on the platform, turret frame

    def a_tur(th):
        return (
            PY + A[0] * math.cos(th) - A[1] * math.sin(th),
            PZ + A[0] * math.sin(th) + A[1] * math.cos(th),
        )

    angles = [math.radians(EL0 + (EL1 - EL0) * i / (STEPS - 1)) for i in range(STEPS)]
    dists = [math.dist(a_tur(th), B) for th in angles]
    Ls = min(dists) - 0.05
    assert Ls * 2 - 0.1 >= max(dists), "ram cannot reach full elevation"
    box("kh_rambase", (0.3, 0.3, 0.2), (0, B[0], B[1] - 0.05), DARK(), tur, 0.01)
    barrel = empty("kh_ram_barrel_pivot", (0, B[0], B[1]), tur)
    cyl(
        "kh_ram_barrel",
        0.1,
        Ls,
        (0, -Ls / 2, 0),
        (math.pi / 2, 0, 0),
        PAINT(),
        barrel,
        14,
    )
    rod = empty("kh_ram_rod_slide", (0, 0, 0), barrel)
    cyl("kh_ram_rod", 0.06, Ls, (0, -Ls / 2, 0), (math.pi / 2, 0, 0), CHROME(), rod, 12)
    for i, th in enumerate(angles):
        f = i * 100 // (STEPS - 1)
        piv.rotation_euler = (th, 0, 0)
        piv.keyframe_insert("rotation_euler", frame=f)
        ay, az_ = a_tur(th)
        vy, vz = ay - B[0], az_ - B[1]
        barrel.rotation_euler = (math.atan2(-vz, -vy), 0, 0)
        barrel.keyframe_insert("rotation_euler", frame=f)
        rod.location = (0, -(math.hypot(vy, vz) - Ls), 0)
        rod.keyframe_insert("location", frame=f)
        tur.rotation_euler = (0, 0, 2 * math.pi * i / (STEPS - 1))
        tur.keyframe_insert("rotation_euler", frame=f)
    shell = box("collision_shell", (2.8, 9.4, 4.4), (0, 0, 2.2), DARK(), root, 0)
    shell.hide_render = True
    return tur, piv


if __name__ == "__main__":
    out = sys.argv[-1]
    tur, piv = build()
    finalize("IRAD_3Khordad_TELAR")
    bpy.context.scene.frame_set(0)
    if "--bake" in sys.argv:
        bake_camo(out, "IRAD_3Khordad_TELAR")
    bpy.ops.wm.save_as_mainfile(filepath=f"{out}/IRAD_3Khordad_TELAR.blend")
    tur.animation_data_clear()
    tur.rotation_euler = (0, 0, 0)
    scn = bpy.context.scene
    views = (
        (
            22,
            "photo",
            dict(target=(0, 0.3, 2.6), dist=15, az=38, elev=6, res=(1100, 815)),
        ),
        (
            40,
            "front",
            dict(target=(0, 1.0, 2.8), dist=13, az=12, elev=4, res=(1100, 765)),
        ),
        (0, "travel", dict(target=(0, 0.0, 2.2), dist=15, az=-60, elev=12)),
    )
    for frame, name, kw in views:
        scn.frame_set(frame)
        render(f"{out}/IRAD_3Khordad_TELAR_{name}.png", **kw)
