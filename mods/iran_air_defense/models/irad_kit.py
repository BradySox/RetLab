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
    base.inputs[6].default_value = (0.62, 0.50, 0.32, 1)  # sand
    base.inputs[7].default_value = (0.66, 0.33, 0.13, 1)  # orange
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
    lobe = math("COSINE", math("ADD", math("MULTIPLY", theta, vb=3.0), phase))
    radius = math(
        "MULTIPLY", math("ADD", math("MULTIPLY", lobe, vb=0.5), vb=0.5), vb=0.3
    )
    inside = math("LESS_THAN", r, radius)
    keep = math("GREATER_THAN", cseps.outputs[1], vb=0.3)
    mark = math("MULTIPLY", inside, keep)
    final = N.new("ShaderNodeMix")
    final.data_type = "RGBA"
    final.inputs[7].default_value = (0.03, 0.03, 0.03, 1)
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
    for k in range(-1, 2):
        cyl(
            name + f"_tread{k}",
            r + 0.012,
            0.05,
            (loc[0] + k * w * 0.3, loc[1], loc[2]),
            (0, math.pi / 2, 0),
            TYRE(),
            parent,
            40,
        )
    rx = loc[0] + side * (w / 2)
    cyl(
        name + "_rim",
        r * 0.58,
        0.06,
        (rx, loc[1], loc[2]),
        (0, math.pi / 2, 0),
        mat("irad_rim", (0.09, 0.09, 0.08), 0.6),
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


def iran_cab(prefix, root, front, width, cab_len, frame_h):
    """The Bavar-373 TEL cab as photographed: rounded front corners, two-pane
    windscreen set high, body-coloured lower front with round lamps and a mesh
    grille, two red beacons, fold-down steps."""
    bottom = frame_h - 0.2
    height = 2.3
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
    wz = bottom + 1.72
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
        dy, dz, dh, dw = front - cab_len * 0.3, bottom + 1.1, 1.7, cab_len * 0.48
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
    return top


def iran_truck(
    prefix, axle_ys, length, width=2.55, cab_len=2.4, frame_h=1.4, wheel_r=0.72
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
    iran_cab(prefix, root, front, width, cab_len, frame_h)
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
    cyl(
        prefix + "_fueltank",
        0.32,
        1.4,
        (-width / 2 + 0.35, gy, frame_h - 0.45),
        (math.pi / 2, 0, 0),
        METAL(),
        root,
        20,
    )
    box(
        prefix + "_toolbox",
        (0.45, 1.3, 0.5),
        (width / 2 - 0.3, gy, frame_h - 0.45),
        TRIM(),
        root,
        0.03,
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
    for o in (g, sun, cam, t):
        bpy.data.objects.remove(o)
