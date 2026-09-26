"""Shared Blender building blocks for the IRAD models. Metres, +Y forward, Z up.

Proportions are matched to a Tasnim photograph of the Bavar-373 TEL (an 8x8) and to
reference renders of the complex supplied by the DM.
"""

import math
import bpy
import bmesh


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def mat(name, rgb, rough=0.8, metal=0.0):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return m


# The camouflage palette: a model script may replace it before building (the Matla ul-Fajr
# is woodland). Linear RGB.
CAMO = {
    "base": (0.62, 0.50, 0.32),
    "cloud": (0.66, 0.33, 0.13),
    "mark": (0.03, 0.03, 0.03),
}


def camo():
    """Bavar-373 camouflage as photographed: sand base, soft orange clouds and small
    black three-bladed splinter marks.

    Procedural on world position so the pattern runs across part seams; the DCS
    export needs it baked to a UV texture.
    """
    m = bpy.data.materials.get("irad_camo")
    if m:
        return m
    m = bpy.data.materials.new("irad_camo")
    m.use_nodes = True
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    bsdf = N["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.72

    def math(op, a=None, b=None, va=0.0, vb=0.0):
        n = N.new("ShaderNodeMath")
        n.operation = op
        n.inputs[0].default_value = va
        n.inputs[1].default_value = vb
        if a is not None:
            L.new(a, n.inputs[0])
        if b is not None:
            L.new(b, n.inputs[1])
        return n.outputs[0]

    geo = N.new("ShaderNodeNewGeometry")
    # soft orange clouds
    cloud = N.new("ShaderNodeTexNoise")
    cloud.inputs["Scale"].default_value = 0.6
    cloud.inputs["Detail"].default_value = 2.0
    L.new(geo.outputs["Position"], cloud.inputs["Vector"])
    cramp = N.new("ShaderNodeValToRGB")
    cramp.color_ramp.elements[0].position = 0.56
    cramp.color_ramp.elements[1].position = 0.63
    L.new(cloud.outputs["Fac"], cramp.inputs["Fac"])
    base = N.new("ShaderNodeMix")
    base.data_type = "RGBA"
    base.inputs[6].default_value = (*CAMO["base"], 1)
    base.inputs[7].default_value = (*CAMO["cloud"], 1)
    L.new(cramp.outputs["Color"], base.inputs[0])
    # splinter marks: a three-lobed shape around each Voronoi feature point
    SCALE = 1.0
    scaled = N.new("ShaderNodeVectorMath")
    scaled.operation = "SCALE"
    scaled.inputs[3].default_value = SCALE
    L.new(geo.outputs["Position"], scaled.inputs[0])
    vor = N.new("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = 1.0
    L.new(scaled.outputs[0], vor.inputs["Vector"])
    local = N.new("ShaderNodeVectorMath")
    local.operation = "SUBTRACT"
    L.new(scaled.outputs[0], local.inputs[0])
    L.new(vor.outputs["Position"], local.inputs[1])
    sep = N.new("ShaderNodeSeparateXYZ")
    L.new(local.outputs[0], sep.inputs[0])
    u = math("ADD", sep.outputs["X"], sep.outputs["Y"])
    v = sep.outputs["Z"]
    r = math("SQRT", math("ADD", math("MULTIPLY", u, u), math("MULTIPLY", v, v)))
    cseps = N.new("ShaderNodeSeparateColor")
    L.new(vor.outputs["Color"], cseps.inputs[0])
    theta = math("ARCTAN2", v, u)
    phase = math("MULTIPLY", cseps.outputs[0], vb=6.283)
    # thin pointed blades: a clamped cosine raised to a power narrows each lobe
    lobe = math("COSINE", math("ADD", math("MULTIPLY", theta, vb=3.0), phase))
    blade = math("POWER", math("MAXIMUM", lobe, vb=0.0), vb=4.0)
    radius = math("MULTIPLY", math("ADD", blade, vb=0.06), vb=0.3)
    inside = math("LESS_THAN", r, radius)
    keep = math("GREATER_THAN", cseps.outputs[1], vb=0.3)
    mark = math("MULTIPLY", inside, keep)
    final = N.new("ShaderNodeMix")
    final.data_type = "RGBA"
    final.inputs[7].default_value = (*CAMO["mark"], 1)
    L.new(mark, final.inputs[0])
    L.new(base.outputs[2], final.inputs[6])
    L.new(final.outputs[2], bsdf.inputs["Base Color"])
    return m


PAINT = camo
DARK = lambda: mat("irad_dark", (0.04, 0.04, 0.04), 0.9)
TYRE = lambda: mat("irad_tyre", (0.025, 0.025, 0.025), 0.95)
GLASS = lambda: mat("irad_glass", (0.05, 0.07, 0.09), 0.08, 0.4)
METAL = lambda: mat("irad_metal", (0.35, 0.35, 0.33), 0.45, 0.8)
TRIM = lambda: mat("irad_trim", (0.52, 0.44, 0.28))
STRIPE = lambda: mat("irad_stripe", (0.75, 0.62, 0.08), 0.6)
RED = lambda: mat("irad_red", (0.5, 0.05, 0.03), 0.5)
AMBER = lambda: mat("irad_amber", (0.9, 0.45, 0.03), 0.3)
CHROME = lambda: mat("irad_chrome", (0.8, 0.8, 0.8), 0.15, 1.0)


def box(name, size, loc, material, parent=None, bevel=0.03, rot=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if rot:
        o.rotation_euler = rot
    if bevel:
        m = o.modifiers.new("bevel", "BEVEL")
        m.width = bevel
        m.segments = 2
    o.data.materials.append(material)
    if parent:
        o.parent = parent
    return o


def cyl(name, r, depth, loc, rot, material, parent=None, verts=24):
    bpy.ops.mesh.primitive_cylinder_add(
        radius=r, depth=depth, location=loc, rotation=rot, vertices=verts
    )
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(material)
    if parent:
        o.parent = parent
    return o


def empty(name, loc, parent=None, rot=(0, 0, 0)):
    o = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = rot
    o.empty_display_size = 0.5
    if parent:
        o.parent = parent
    return o


def hose(name, points, r, material, parent=None):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = r
    cu.bevel_resolution = 2
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(len(points) - 1)
    for p, co in zip(sp.bezier_points, points):
        p.co = co
        p.handle_left_type = p.handle_right_type = "AUTO"
    o = bpy.data.objects.new(name, cu)
    bpy.context.collection.objects.link(o)
    o.data.materials.append(material)
    if parent:
        o.parent = parent
    return o


def stencil(name, text, loc, rot, size, material, parent=None):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = text
    cu.size = size
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.extrude = 0.004
    o = bpy.data.objects.new(name, cu)
    bpy.context.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = rot
    o.data.materials.append(material)
    if parent:
        o.parent = parent
    return o


def louvers(prefix, center, width, height, n, facing, parent):
    """n horizontal slats on a face; facing = +1/-1 along X."""
    x, y, z = center
    for i in range(n):
        box(
            f"{prefix}_{i}",
            (0.04, width, 0.05),
            (x + facing * 0.02, y, z - height / 2 + (i + 0.5) * height / n),
            DARK(),
            parent,
            0,
        )


def strut(name, a, b, r, material, parent=None, verts=8):
    """A round member from point a to point b."""
    ax, ay, az = a
    bx, by, bz = b
    dx, dy, dz = bx - ax, by - ay, bz - az
    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    o = cyl(
        name,
        r,
        length,
        ((ax + bx) / 2, (ay + by) / 2, (az + bz) / 2),
        (0, 0, 0),
        material,
        parent,
        verts,
    )
    from mathutils import Vector

    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(Vector((dx, dy, dz)))
    return o


def wheel(name, loc, r=0.62, w=0.45, parent=None):
    """Military tyre with tread bands, disc rim and 8 lug nuts facing outward."""
    side = 1 if loc[0] > 0 else -1
    t = cyl(name, r, w, loc, (0, math.pi / 2, 0), TYRE(), parent, 40)
    m = t.modifiers.new("bevel", "BEVEL")
    m.width = 0.08
    m.segments = 3
    # off-road tread: staggered lugs around the crown
    lugs = 28
    for k in range(lugs):
        a = 2 * math.pi * k / lugs
        for side in (-1, 1):
            if (k + (side > 0)) % 2:
                continue
            box(
                name + f"_lug_t{k}{side}",
                (w * 0.44, 0.13, 0.05),
                (
                    loc[0] + side * w * 0.2,
                    loc[1] + r * math.sin(a),
                    loc[2] + r * math.cos(a),
                ),
                TYRE(),
                parent,
                0,
                (-a, 0, 0),
            )
    rx = loc[0] + side * (w / 2)
    cyl(
        name + "_rim",
        r * 0.58,
        0.06,
        (rx, loc[1], loc[2]),
        (0, math.pi / 2, 0),
        mat("irad_rim", (0.26, 0.26, 0.24), 0.5),
        parent,
        32,
    )
    cyl(
        name + "_hub",
        r * 0.24,
        0.12,
        (rx + side * 0.03, loc[1], loc[2]),
        (0, math.pi / 2, 0),
        METAL(),
        parent,
        16,
    )
    for i in range(8):
        a = i * math.pi / 4
        cyl(
            name + f"_lug{i}",
            0.025,
            0.05,
            (
                rx + side * 0.05,
                loc[1] + math.cos(a) * r * 0.36,
                loc[2] + math.sin(a) * r * 0.36,
            ),
            (0, math.pi / 2, 0),
            METAL(),
            parent,
            8,
        )
    return t


def fan(name, loc, facing, r, parent):
    """A round fan grille on a face; facing is the outward axis, "x" or "y", signed."""
    axis, sign = facing[1], (1 if facing[0] == "+" else -1)
    rot = (0, math.pi / 2, 0) if axis == "x" else (math.pi / 2, 0, 0)
    off = lambda d: (
        (loc[0] + sign * d, loc[1], loc[2])
        if axis == "x"
        else (loc[0], loc[1] + sign * d, loc[2])
    )
    cyl(name + "_ring", r, 0.05, off(0.02), rot, METAL(), parent, 28)
    cyl(name + "_well", r * 0.92, 0.05, off(0.035), rot, DARK(), parent, 28)
    cyl(name + "_hub", r * 0.22, 0.06, off(0.05), rot, METAL(), parent, 14)
    for k in range(4):
        a = k * math.pi / 4
        if axis == "x":
            size, bar_rot = (0.02, 2 * r * 0.9, 0.025), (a, 0, 0)
        else:
            size, bar_rot = (2 * r * 0.9, 0.02, 0.025), (0, a, 0)
        box(name + f"_guard{k}", size, off(0.06), METAL(), parent, 0, bar_rot)


# ---- detail helpers (pass 2) ----------------------------------------------------------


def _on_face(center, axis, sign, depth):
    """A point pushed `depth` out of a face whose outward normal is sign * axis."""
    x, y, z = center
    return (x + sign * depth, y, z) if axis == "x" else (x, y + sign * depth, z)


def _flat(axis, w, h, t):
    """Size of a flat plate lying on a face: t thick along the normal, w along the face."""
    return (t, w, h) if axis == "x" else (w, t, h)


def door(prefix, center, axis, sign, w, h, parent, material=None, hinge_side=-1):
    """A shelter door: proud panel, seam frame, three hinges, lever handle, data plate."""
    material = material or PAINT()
    box(
        prefix + "_panel",
        _flat(axis, w, h, 0.02),
        _on_face(center, axis, sign, 0.01),
        material,
        parent,
        0.005,
    )
    x, y, z = center
    for k, (dw, dh, oa, oz) in enumerate(
        (
            (w, 0.025, 0, h / 2),
            (w, 0.025, 0, -h / 2),
            (0.025, h, w / 2, 0),
            (0.025, h, -w / 2, 0),
        )
    ):
        c = (x, y + oa, z + oz) if axis == "x" else (x + oa, y, z + oz)
        box(
            f"{prefix}_seam{k}",
            _flat(axis, dw, dh, 0.03),
            _on_face(c, axis, sign, 0.012),
            DARK(),
            parent,
            0,
        )
    along = hinge_side * (w / 2 - 0.04)
    for k, dz in enumerate((-h * 0.38, 0, h * 0.38)):
        c = (x, y + along, z + dz) if axis == "x" else (x + along, y, z + dz)
        cyl(
            f"{prefix}_hinge{k}",
            0.025,
            0.14,
            _on_face(c, axis, sign, 0.03),
            (0, 0, 0),
            METAL(),
            parent,
            8,
        )
    hc = (x, y - along * 0.85, z) if axis == "x" else (x - along * 0.85, y, z)
    box(
        prefix + "_handle",
        _flat(axis, 0.05, 0.22, 0.05),
        _on_face(hc, axis, sign, 0.04),
        METAL(),
        parent,
        0.01,
    )
    pc = (x, y, z + h * 0.3) if axis == "x" else (x, y, z + h * 0.3)
    box(
        prefix + "_plate",
        _flat(axis, 0.18, 0.1, 0.01),
        _on_face(pc, axis, sign, 0.025),
        METAL(),
        parent,
        0,
    )


def grille(prefix, center, axis, sign, w, h, parent, slats=8):
    """A framed vent grille with angled slats over a dark backing."""
    box(
        prefix + "_back",
        _flat(axis, w, h, 0.02),
        _on_face(center, axis, sign, 0.005),
        DARK(),
        parent,
        0,
    )
    x, y, z = center
    for k, (dw, dh, oa, oz) in enumerate(
        (
            (w + 0.06, 0.05, 0, h / 2),
            (w + 0.06, 0.05, 0, -h / 2),
            (0.05, h, w / 2, 0),
            (0.05, h, -w / 2, 0),
        )
    ):
        c = (x, y + oa, z + oz) if axis == "x" else (x + oa, y, z + oz)
        box(
            f"{prefix}_frame{k}",
            _flat(axis, dw, dh, 0.05),
            _on_face(c, axis, sign, 0.025),
            PAINT(),
            parent,
            0.005,
        )
    for k in range(slats):
        c = (x, y, z - h / 2 + (k + 0.5) * h / slats)
        rot = (0, 0.5 * sign, 0) if axis == "x" else (-0.5 * sign, 0, 0)
        box(
            f"{prefix}_slat{k}",
            _flat(axis, w, 0.012, 0.06),
            _on_face(c, axis, sign, 0.03),
            PAINT(),
            parent,
            0,
            rot,
        )


def ladder(prefix, top, bottom, width, rungs, parent, axis="x"):
    """A ladder from top to bottom point: two rails, rungs, top hooks."""
    for rail in (-1, 1):
        off = (0, rail * width / 2, 0) if axis == "x" else (rail * width / 2, 0, 0)
        a = tuple(t + o for t, o in zip(top, off))
        b = tuple(t + o for t, o in zip(bottom, off))
        strut(f"{prefix}_rail{rail}", a, b, 0.025, METAL(), parent, 6)
        cyl(
            f"{prefix}_hook{rail}",
            0.03,
            0.12,
            (a[0], a[1], a[2] + 0.06),
            (0, 0, 0),
            METAL(),
            parent,
            6,
        )
    for k in range(rungs):
        t = (k + 0.5) / rungs
        c = tuple(tb + (bb - tb) * t for tb, bb in zip(top, bottom))
        a = (
            (c[0], c[1] - width / 2, c[2])
            if axis == "x"
            else (c[0] - width / 2, c[1], c[2])
        )
        b = (
            (c[0], c[1] + width / 2, c[2])
            if axis == "x"
            else (c[0] + width / 2, c[1], c[2])
        )
        strut(f"{prefix}_rung{k}", a, b, 0.018, METAL(), parent, 6)


def screw_jack(prefix, x, y, top_z, parent):
    """An outrigger jack: housing, screw, crank, ribbed pad."""
    cyl(
        prefix + "_housing",
        0.12,
        0.7,
        (x, y, top_z - 0.35),
        (0, 0, 0),
        PAINT(),
        parent,
        16,
    )
    cyl(
        prefix + "_collar",
        0.15,
        0.08,
        (x, y, top_z - 0.02),
        (0, 0, 0),
        METAL(),
        parent,
        16,
    )
    cyl(
        prefix + "_screw",
        0.07,
        top_z - 0.65,
        (x, y, (top_z - 0.65) / 2 + 0.06),
        (0, 0, 0),
        CHROME(),
        parent,
        12,
    )
    box(
        prefix + "_crank",
        (0.3, 0.03, 0.03),
        (x + 0.15, y, top_z + 0.08),
        METAL(),
        parent,
        0,
    )
    cyl(prefix + "_pad", 0.26, 0.06, (x, y, 0.03), (0, 0, 0), DARK(), parent, 18)
    for k in range(4):
        box(
            f"{prefix}_padrib{k}",
            (0.4, 0.03, 0.06),
            (x, y, 0.08),
            DARK(),
            parent,
            0,
            (0, 0, k * math.pi / 4),
        )


def cable_reel(prefix, loc, parent, r=0.28, w=0.3):
    """A cable drum lying across the vehicle: flanges, wound cable, frame."""
    x, y, z = loc
    for s in (-1, 1):
        cyl(
            f"{prefix}_flange{s}",
            r,
            0.03,
            (x + s * w / 2, y, z),
            (0, math.pi / 2, 0),
            METAL(),
            parent,
            20,
        )
    cyl(
        prefix + "_cable",
        r * 0.8,
        w - 0.04,
        (x, y, z),
        (0, math.pi / 2, 0),
        DARK(),
        parent,
        20,
    )
    for s in (-1, 1):
        strut(
            f"{prefix}_leg{s}",
            (x + s * (w / 2 + 0.04), y, z),
            (x + s * (w / 2 + 0.04), y, z - r - 0.05),
            0.02,
            METAL(),
            parent,
            6,
        )


def handrail(prefix, points, parent, height=1.0):
    """Posts at each point and two rails joining them."""
    for k, p in enumerate(points):
        box(
            f"{prefix}_post{k}",
            (0.04, 0.04, height),
            (p[0], p[1], p[2] + height / 2),
            METAL(),
            parent,
            0,
        )
    for k in range(len(points) - 1):
        a, b = points[k], points[k + 1]
        for h in (0.5, 1.0):
            strut(
                f"{prefix}_rail{k}{h}",
                (a[0], a[1], a[2] + height * h),
                (b[0], b[1], b[2] + height * h),
                0.022,
                METAL(),
                parent,
                6,
            )


def iran_cab(prefix, root, front, width, cab_len, frame_h, height=2.3):
    """The Bavar-373 TEL cab as photographed: rounded front corners, two-pane
    windscreen set high, body-coloured lower front with round lamps and a mesh
    grille, two red beacons, fold-down steps."""
    bottom = frame_h - 0.2
    k_h = height / 2.3
    top = bottom + height
    cy = front - cab_len / 2
    box(
        prefix + "_cab",
        (width, cab_len, height),
        (0, cy, bottom + height / 2),
        PAINT(),
        root,
        0.16,
    )
    box(
        prefix + "_roof",
        (width - 0.1, cab_len - 0.1, 0.06),
        (0, cy, top + 0.02),
        PAINT(),
        root,
        0.03,
    )
    # windscreen high on the face, two panes with rounded corners, wipers parked on top
    wz = bottom + height - 0.58
    for s in (-1, 1):
        box(
            prefix + f"_windscreen{s}",
            (width * 0.41, 0.04, 0.72),
            (s * width * 0.225, front + 0.005, wz),
            GLASS(),
            root,
            0.06,
        )
        box(
            prefix + f"_sidewin{s}",
            (0.04, cab_len * 0.36, 0.72),
            (s * (width / 2 + 0.005), front - cab_len * 0.28, wz),
            GLASS(),
            root,
            0.04,
        )
        dy, dz, dh, dw = (
            front - cab_len * 0.3,
            bottom + 1.1 * k_h,
            1.7 * k_h,
            cab_len * 0.48,
        )
        for k, (sz, off) in enumerate(
            (
                ((0.02, dw, 0.02), (0, 0, dh / 2)),
                ((0.02, dw, 0.02), (0, 0, -dh / 2)),
                ((0.02, 0.02, dh), (0, dw / 2, 0)),
                ((0.02, 0.02, dh), (0, -dw / 2, 0)),
            )
        ):
            box(
                prefix + f"_doorseam{s}{k}",
                sz,
                (s * (width / 2 + 0.008), dy + off[1], dz + off[2]),
                DARK(),
                root,
                0,
            )
        box(
            prefix + f"_handle{s}",
            (0.06, 0.2, 0.04),
            (s * (width / 2 + 0.04), front - cab_len * 0.52, bottom + 1.0),
            METAL(),
            root,
            0,
        )
        for k in range(2):
            box(
                prefix + f"_wiper{s}{k}",
                (0.45, 0.02, 0.025),
                (s * (0.28 + k * 0.5), front + 0.035, wz + 0.2),
                DARK(),
                root,
                0,
                (0, 0, 0.35),
            )
        box(
            prefix + f"_mirrorarm{s}",
            (0.36, 0.035, 0.035),
            (s * (width / 2 + 0.17), front - 0.12, wz + 0.25),
            DARK(),
            root,
            0,
        )
        box(
            prefix + f"_mirror{s}",
            (0.07, 0.18, 0.5),
            (s * (width / 2 + 0.36), front - 0.12, wz + 0.05),
            DARK(),
            root,
            0.03,
        )
        cyl(
            prefix + f"_beacon{s}",
            0.07,
            0.14,
            (s * 0.35, front - 0.3, top + 0.1),
            (0, 0, 0),
            RED(),
            root,
            14,
        )
        cyl(
            prefix + f"_lamp{s}",
            0.1,
            0.06,
            (s * (width / 2 - 0.25), front + 0.2, bottom + 0.2),
            (math.pi / 2, 0, 0),
            GLASS(),
            root,
            20,
        )
        cyl(
            prefix + f"_marker{s}",
            0.05,
            0.05,
            (s * 0.35, front + 0.015, bottom + 1.2),
            (math.pi / 2, 0, 0),
            DARK(),
            root,
            12,
        )
        # fold-down step at the front corner and ladder under the door
        box(
            prefix + f"_cornerstep{s}",
            (0.35, 0.25, 0.04),
            (s * (width / 2 - 0.2), front + 0.05, bottom - 0.55),
            METAL(),
            root,
            0,
        )
        for k in range(3):
            box(
                prefix + f"_ladrung{s}{k}",
                (0.1, 0.46, 0.035),
                (s * (width / 2 - 0.05), front - cab_len * 0.3, bottom - 0.8 + k * 0.3),
                METAL(),
                root,
                0,
            )
    box(prefix + "_pillar", (0.09, 0.05, 0.75), (0, front + 0.01, wz), PAINT(), root, 0)
    box(
        prefix + "_plate",
        (0.5, 0.03, 0.11),
        (0, front + 0.02, wz - 0.48),
        mat("irad_plate", (0.8, 0.8, 0.8), 0.4),
        root,
        0,
    )
    # lower front: a protruding body-coloured nose with a mesh grille and tow hooks
    box(
        prefix + "_nose",
        (width, 0.26, 0.55),
        (0, front + 0.1, bottom + 0.2),
        PAINT(),
        root,
        0.08,
    )
    box(
        prefix + "_grille",
        (width * 0.34, 0.04, 0.25),
        (0, front + 0.24, bottom + 0.25),
        DARK(),
        root,
        0.01,
    )
    for i in range(5):
        box(
            prefix + f"_grillebar{i}",
            (width * 0.34, 0.05, 0.02),
            (0, front + 0.25, bottom + 0.15 + i * 0.05),
            METAL(),
            root,
            0,
        )
    for s in (-1, 1):
        box(
            prefix + f"_towhook{s}",
            (0.18, 0.1, 0.12),
            (s * 0.55, front + 0.26, bottom + 0.25),
            DARK(),
            root,
            0.01,
        )
    box(
        prefix + "_bumper",
        (width + 0.02, 0.24, 0.22),
        (0, front + 0.12, bottom - 0.18),
        DARK(),
        root,
        0.03,
    )
    # pass 3: sun visor, grab handles, marker lights, lamp guards, shackles, roof lights
    box(
        prefix + "_visor",
        (width * 0.92, 0.35, 0.05),
        (0, front + 0.15, wz + 0.45),
        PAINT(),
        root,
        0.01,
        (math.radians(-8), 0, 0),
    )
    for s in (-1, 1):
        cyl(
            f"{prefix}_grab{s}",
            0.02,
            0.9,
            (s * (width / 2 + 0.04), front - cab_len * 0.58, bottom + 1.1),
            (0, 0, 0),
            METAL(),
            root,
            6,
        )
        box(
            f"{prefix}_sidemarker{s}",
            (0.03, 0.12, 0.06),
            (s * (width / 2 + 0.01), front - 0.2, bottom + 0.35),
            AMBER(),
            root,
            0,
        )
        for k in range(3):
            box(
                f"{prefix}_lampguard{s}{k}",
                (0.24, 0.02, 0.015),
                (s * (width / 2 - 0.25), front + 0.26, bottom + 0.14 + k * 0.06),
                METAL(),
                root,
                0,
            )
        cyl(
            f"{prefix}_shackle{s}",
            0.05,
            0.04,
            (s * 0.8, front + 0.26, bottom - 0.18),
            (0, math.pi / 2, 0),
            METAL(),
            root,
            10,
        )
        box(
            f"{prefix}_roofmarker{s}",
            (0.1, 0.05, 0.05),
            (s * 0.95, front - 0.05, top + 0.05),
            AMBER(),
            root,
            0,
        )
    box(
        prefix + "_rearwindow",
        (width * 0.5, 0.03, 0.35),
        (0, front - cab_len - 0.005, wz + 0.1),
        GLASS(),
        root,
        0,
    )
    return top


def iran_truck(
    prefix,
    axle_ys,
    length,
    width=2.55,
    cab_len=2.4,
    frame_h=1.4,
    wheel_r=0.72,
    cab_h=2.3,
    cab=True,
):
    """Heavy truck on the given axle stations. Returns (root, deck_z, rear_y, cab_back_y)."""
    root = empty(prefix, (0, 0, 0))
    front = length / 2
    rear = -length / 2
    box(
        prefix + "_frame",
        (width * 0.5, length * 0.97, 0.34),
        (0, 0, frame_h - 0.2),
        DARK(),
        root,
        0.01,
    )
    if cab:
        iran_cab(prefix, root, front, width, cab_len, frame_h, cab_h)
    for i, y in enumerate(axle_ys):
        box(
            prefix + f"_axle{i}",
            (width - 0.6, 0.18, 0.18),
            (0, y, wheel_r),
            DARK(),
            root,
            0.01,
        )
        for s in (-1, 1):
            wheel(
                prefix + f"_wheel_{i}_{'L' if s < 0 else 'R'}",
                (s * (width / 2 - 0.22), y, wheel_r),
                wheel_r,
                0.48,
                root,
            )
    for s in (-1, 1):
        box(
            prefix + f"_mudflap{s}",
            (0.5, 0.03, 0.6),
            (s * (width / 2 - 0.22), axle_ys[-1] - 0.85, wheel_r * 0.8),
            DARK(),
            root,
            0,
        )
        box(
            prefix + f"_taillight{s}",
            (0.3, 0.05, 0.12),
            (s * (width / 2 - 0.2), rear - 0.02, frame_h - 0.3),
            RED(),
            root,
            0.01,
        )
    box(
        prefix + "_rearbumper",
        (width, 0.15, 0.2),
        (0, rear, frame_h - 0.45),
        DARK(),
        root,
        0.02,
    )
    # fuel tank and toolbox in the gap between the front and rear axle groups
    gaps = [(axle_ys[i] - axle_ys[i + 1], i) for i in range(len(axle_ys) - 1)]
    _, gi = max(gaps)
    gy = (axle_ys[gi] + axle_ys[gi + 1]) / 2
    gl = min(1.5, max(axle_ys[gi] - axle_ys[gi + 1] - 1.6, 0.6))
    cyl(
        prefix + "_fueltank",
        0.32,
        gl,
        (-width / 2 + 0.35, gy, frame_h - 0.45),
        (math.pi / 2, 0, 0),
        METAL(),
        root,
        20,
    )
    cyl(
        prefix + "_fuelcap",
        0.07,
        0.06,
        (-width / 2 + 0.35, gy + gl * 0.3, frame_h - 0.12),
        (0, 0, 0),
        DARK(),
        root,
        10,
    )
    for k in (-1, 1):
        cyl(
            f"{prefix}_fuelstrap{k}",
            0.335,
            0.05,
            (-width / 2 + 0.35, gy + k * gl * 0.33, frame_h - 0.45),
            (math.pi / 2, 0, 0),
            DARK(),
            root,
            20,
        )
    box(
        prefix + "_toolbox",
        (0.45, gl, 0.5),
        (width / 2 - 0.3, gy, frame_h - 0.45),
        TRIM(),
        root,
        0.03,
    )
    box(
        prefix + "_toolboxlid",
        (0.02, gl * 0.9, 0.4),
        (width / 2 - 0.07, gy, frame_h - 0.45),
        DARK(),
        root,
        0,
    )
    for k in (-1, 1):
        box(
            f"{prefix}_toolboxlatch{k}",
            (0.03, 0.06, 0.1),
            (width / 2 - 0.05, gy + k * gl * 0.3, frame_h - 0.3),
            METAL(),
            root,
            0,
        )
    # air tanks and battery box under the frame, side guards between axle groups
    for k, dy in enumerate((-0.35, 0.35)):
        cyl(
            f"{prefix}_airtank{k}",
            0.12,
            0.8,
            (-0.35, gy + dy, frame_h - 0.55),
            (0, math.pi / 2, 0),
            METAL(),
            root,
            14,
        )
    box(
        prefix + "_battery",
        (0.55, 0.5, 0.45),
        (0.45, gy - gl / 2 - 0.1, frame_h - 0.5),
        DARK(),
        root,
        0.02,
    )
    for s in (-1, 1):
        y0, y1 = axle_ys[gi] - wheel_r - 0.15, axle_ys[gi + 1] + wheel_r + 0.15
        if y0 > y1 + 0.4:
            for k, z in enumerate((frame_h - 0.75, frame_h - 0.95)):
                box(
                    f"{prefix}_guard{s}{k}",
                    (0.04, y0 - y1, 0.08),
                    (s * (width / 2 - 0.03), (y0 + y1) / 2, z),
                    METAL(),
                    root,
                    0,
                )
    # front fenders over the steering axles
    for i in range(min(2, len(axle_ys))):
        if axle_ys[i] < front - cab_len - 0.3:
            continue
        for s in (-1, 1):
            for k, a in enumerate((-0.9, -0.3, 0.3, 0.9)):
                box(
                    f"{prefix}_fender{i}{s}{k}",
                    (0.52, 0.42, 0.05),
                    (
                        s * (width / 2 - 0.22),
                        axle_ys[i] + math.sin(a) * (wheel_r + 0.1),
                        wheel_r + math.cos(a) * (wheel_r + 0.1),
                    ),
                    DARK(),
                    root,
                    0,
                    (-a, 0, 0),
                )
    # rear lights cluster, reflectors, plate
    for s in (-1, 1):
        box(
            f"{prefix}_reflector{s}",
            (0.1, 0.03, 0.1),
            (s * (width / 2 - 0.5), rear - 0.03, frame_h - 0.45),
            AMBER(),
            root,
            0,
        )
    box(
        prefix + "_rearplate",
        (0.45, 0.02, 0.12),
        (0, rear - 0.08, frame_h - 0.45),
        mat("irad_plate", (0.8, 0.8, 0.8), 0.4),
        root,
        0,
    )
    return root, frame_h, rear, front - cab_len


def finalize(prefix):
    """Apply modifiers, convert curves/text to mesh, report the triangle count."""
    for o in list(bpy.data.objects):
        if o.type in ("CURVE", "FONT"):
            bpy.ops.object.select_all(action="DESELECT")
            bpy.context.view_layer.objects.active = o
            o.select_set(True)
            bpy.ops.object.convert(target="MESH")
            o.select_set(False)
    for o in bpy.data.objects:
        if o.type == "MESH" and o.modifiers:
            bpy.context.view_layer.objects.active = o
            for m in list(o.modifiers):
                bpy.ops.object.modifier_apply(modifier=m.name)
    tris = 0
    for o in bpy.data.objects:
        if o.type == "MESH" and o.name != "collision_shell":
            tris += sum(len(p.vertices) - 2 for p in o.data.polygons)
    print(f"TRIS {prefix}: {tris}")
    return tris


def render(path, target=(0, 0, 2), dist=22, elev=18, az=35, res=(1100, 700)):
    scn = bpy.context.scene
    scn.render.engine = "CYCLES"
    scn.cycles.samples = 32
    scn.cycles.device = "CPU"
    scn.render.resolution_x, scn.render.resolution_y = res
    world = bpy.data.worlds.new("w")
    scn.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.6, 0.68, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.7
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, 0))
    g = bpy.context.active_object
    g.name = "ground_preview"
    g.data.materials.append(mat("ground", (0.28, 0.29, 0.31)))
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    bpy.context.collection.objects.link(sun)
    sun.data.energy = 4
    sun.rotation_euler = (math.radians(45), 0, math.radians(30))
    fill = bpy.data.objects.new("fill", bpy.data.lights.new("fill", "SUN"))
    bpy.context.collection.objects.link(fill)
    fill.data.energy = 1.2
    fill.rotation_euler = (math.radians(60), 0, math.radians(210))
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    bpy.context.collection.objects.link(cam)
    scn.camera = cam
    a, e = math.radians(az), math.radians(elev)
    cam.location = (
        target[0] + dist * math.cos(e) * math.sin(a),
        target[1] + dist * math.cos(e) * math.cos(a),
        target[2] + dist * math.sin(e),
    )
    d = cam.constraints.new("TRACK_TO")
    t = empty("cam_target", target)
    d.target = t
    d.track_axis = "TRACK_NEGATIVE_Z"
    d.up_axis = "UP_Y"
    cam.data.lens = 40
    scn.render.filepath = path
    bpy.ops.render.render(write_still=True)
    for o in (g, sun, fill, cam, t):
        bpy.data.objects.remove(o)


def bake_camo(out, name, size=4096):
    """Bake the procedural camouflage into one UV texture shared by every painted part,
    and swap the parts onto an image material, so the model exports to DCS as is.

    Bakes at the current frame; call it with the model in its travel pose.
    """
    src = bpy.data.materials.get("irad_camo")
    objs = [
        o for o in bpy.data.objects if o.type == "MESH" and src.name in o.data.materials
    ]
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.002)
    bpy.ops.object.mode_set(mode="OBJECT")
    img = bpy.data.images.new(f"{name}_camo", size, size, alpha=False)
    node = src.node_tree.nodes.new("ShaderNodeTexImage")
    node.image = img
    src.node_tree.nodes.active = node
    scn = bpy.context.scene
    scn.render.engine = "CYCLES"
    scn.cycles.device = "CPU"
    scn.cycles.samples = 1
    scn.render.bake.use_pass_direct = False
    scn.render.bake.use_pass_indirect = False
    scn.render.bake.margin = 4
    bpy.ops.object.bake(type="DIFFUSE", pass_filter={"COLOR"})
    img.filepath_raw = f"{out}/textures/{name}_camo.png"
    img.file_format = "PNG"
    img.save()
    img.filepath = f"//textures/{name}_camo.png"  # relative, so the .blend travels
    tex = bpy.data.materials.new(f"{name}_camo")
    tex.use_nodes = True
    bsdf = tex.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.72
    tnode = tex.node_tree.nodes.new("ShaderNodeTexImage")
    tnode.image = img
    tex.node_tree.links.new(tnode.outputs["Color"], bsdf.inputs["Base Color"])
    for o in objs:
        for i, m in enumerate(o.data.materials):
            if m == src:
                o.data.materials[i] = tex
    bpy.data.materials.remove(src)
    print(f"BAKED {len(objs)} parts into {img.filepath_raw}")


def animate_wheels(steer_deg=30):
    """Wheel spin and steering empties for DCS. Each wheel's parts go under a
    wheel_spin_<n> empty (frames 0-100: one forward turn); truck front axles also get a
    wheel_steer_<n> empty (frames 0-100: full left to full right, 50 straight ahead).
    Trailer wheels (mj_, mf_) spin only. Safe to call twice."""
    if any(o.name.startswith("wheel_spin_") for o in bpy.data.objects):
        return 0
    scn = bpy.context.scene
    scn.frame_set(0)
    bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
    named = [o for o in bpy.data.objects if "_wheel_" in o.name]
    names = {o.name for o in named}
    bases = [
        o
        for o in named
        if not any(o.name.startswith(n + "_") for n in names if n != o.name)
    ]
    truck = [o for o in bases if not o.name.startswith(("mj_", "mf_"))]
    axles = sorted({int(o.name.rsplit("_wheel_", 1)[1].split("_")[0]) for o in truck})
    steer_axles = {0: 1.0, 1: 0.7} if len(axles) >= 4 else {0: 1.0}
    for o in bases:
        parts = [
            p
            for p in bpy.data.objects
            if p.name == o.name or p.name.startswith(o.name + "_")
        ]
        centre = o.matrix_world.translation.copy()
        parent = o.parent
        tag = o.name.rsplit("_wheel_", 1)[1]
        holder = parent
        axle = int(tag.split("_")[0]) if o in truck else -1
        steer = None
        if axle in steer_axles:
            steer = empty(f"wheel_steer_{tag}", tuple(centre), parent)
            holder, centre = steer, (0, 0, 0)
        spin = empty(f"wheel_spin_{tag}", tuple(centre), holder)
        # reparent at rest, before any key moves the empties
        bpy.context.view_layer.update()
        for p in parts:
            mw = p.matrix_world.copy()
            p.parent = spin
            p.matrix_world = mw
        if steer is not None:
            for f, a in ((0, -1), (50, 0), (100, 1)):
                steer.rotation_euler = (
                    0,
                    0,
                    math.radians(a * steer_deg * steer_axles[axle]),
                )
                steer.keyframe_insert("rotation_euler", frame=f)
        for f, a in ((0, 0.0), (50, -math.pi), (100, -2 * math.pi)):
            spin.rotation_euler = (a, 0, 0)
            spin.keyframe_insert("rotation_euler", frame=f)
    scn.frame_set(0)
    print(f"WHEELS {len(bases)} spin, steer axles {sorted(steer_axles)}")
    return len(bases)
