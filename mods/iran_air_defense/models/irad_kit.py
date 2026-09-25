"""Shared Blender building blocks for the IRAD models. Metres, +Y forward, Z up.

Proportions are matched to reference renders of the Zafar 8x8 and Zoljanah 10x10
(flat-fronted Iranian heavy-truck cab) and the Bavar-373 complex.
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
    """Iranian three-tone desert camouflage: cream base, tan and brown blotches.

    Procedural on world position so blotches run across part seams; the DCS export
    needs it baked to a UV texture.
    """
    m = bpy.data.materials.get("irad_camo")
    if m:
        return m
    m = bpy.data.materials.new("irad_camo")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.75
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 0.85
    noise.inputs["Detail"].default_value = 3.0
    noise.inputs["Roughness"].default_value = 0.55
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    els = ramp.color_ramp.elements
    els[0].position = 0.0
    els[0].color = (0.70, 0.62, 0.42, 1)  # cream
    els[1].position = 0.56
    els[1].color = (0.45, 0.30, 0.14, 1)  # tan
    brown = els.new(0.64)
    brown.color = (0.17, 0.09, 0.04, 1)  # brown
    nt.links.new(geo.outputs["Position"], noise.inputs["Vector"])
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
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
        r * 0.6,
        0.06,
        (rx, loc[1], loc[2]),
        (0, math.pi / 2, 0),
        TRIM(),
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


def iran_cab(prefix, root, front, width, cab_len, frame_h):
    """The flat-fronted Zafar/Zoljanah cab: vertical two-pane windscreen, flat
    overhanging roof, low slotted grille, full-width steel bumper."""
    bottom = frame_h - 0.25
    height = 2.35
    top = bottom + height
    cy = front - cab_len / 2
    box(
        prefix + "_cab",
        (width, cab_len, height),
        (0, cy, bottom + height / 2),
        PAINT(),
        root,
        0.05,
    )
    box(
        prefix + "_roof",
        (width + 0.08, cab_len + 0.08, 0.1),
        (0, cy + 0.02, top + 0.03),
        PAINT(),
        root,
        0.03,
    )
    # windscreen: two near-vertical panes and a centre pillar
    wz = bottom + 1.72
    tilt = math.radians(6)
    for s in (-1, 1):
        box(
            prefix + f"_windscreen{s}",
            (width * 0.455, 0.03, 1.08),
            (s * width * 0.24, front + 0.005, wz),
            GLASS(),
            root,
            0,
            (tilt, 0, 0),
        )
        box(
            prefix + f"_sidewin{s}",
            (0.03, cab_len * 0.42, 0.9),
            (s * (width / 2 + 0.005), front - cab_len * 0.27, wz + 0.05),
            GLASS(),
            root,
            0,
        )
        box(
            prefix + f"_door{s}",
            (0.02, cab_len * 0.5, 1.9),
            (s * (width / 2 + 0.012), front - cab_len * 0.3, bottom + 1.05),
            TRIM(),
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
        # fold-down ladder under the door
        for rail in (-1, 1):
            box(
                prefix + f"_ladrail{s}{rail}",
                (0.04, 0.04, 0.95),
                (
                    s * (width / 2 - 0.05),
                    front - cab_len * 0.3 + rail * 0.22,
                    bottom - 0.45,
                ),
                METAL(),
                root,
                0,
            )
        for k in range(3):
            box(
                prefix + f"_ladrung{s}{k}",
                (0.1, 0.46, 0.035),
                (
                    s * (width / 2 - 0.05),
                    front - cab_len * 0.3,
                    bottom - 0.85 + k * 0.33,
                ),
                METAL(),
                root,
                0,
            )
        box(
            prefix + f"_mirrorarm{s}",
            (0.42, 0.035, 0.035),
            (s * (width / 2 + 0.2), front - 0.15, wz + 0.35),
            DARK(),
            root,
            0,
        )
        box(
            prefix + f"_mirror{s}",
            (0.06, 0.16, 0.42),
            (s * (width / 2 + 0.42), front - 0.15, wz + 0.2),
            DARK(),
            root,
            0.02,
        )
        cyl(
            prefix + f"_light{s}",
            0.1,
            0.06,
            (s * (width / 2 - 0.2), front + 0.2, frame_h - 0.3),
            (math.pi / 2, 0, 0),
            GLASS(),
            root,
            20,
        )
        cyl(
            prefix + f"_blinker{s}",
            0.045,
            0.06,
            (s * (width / 2 - 0.42), front + 0.2, frame_h - 0.3),
            (math.pi / 2, 0, 0),
            AMBER(),
            root,
            12,
        )
    box(prefix + "_pillar", (0.07, 0.05, 1.1), (0, front + 0.01, wz), PAINT(), root, 0)
    for s in (-1, 1):
        box(
            prefix + f"_wiper{s}",
            (0.55, 0.02, 0.03),
            (s * 0.55, front + 0.03, wz - 0.5),
            DARK(),
            root,
            0,
            (0, 0, s * 0.25),
        )
    # grille: a recessed panel with horizontal slots and a badge
    gz = bottom + 0.55
    box(
        prefix + "_grille",
        (width * 0.46, 0.04, 0.5),
        (0, front + 0.01, gz),
        TRIM(),
        root,
        0.01,
    )
    for i in range(5):
        box(
            prefix + f"_grilleslot{i}",
            (width * 0.4, 0.05, 0.035),
            (0, front + 0.02, gz - 0.18 + i * 0.09),
            DARK(),
            root,
            0,
        )
    box(
        prefix + "_badge",
        (0.18, 0.05, 0.08),
        (0, front + 0.035, gz + 0.3),
        METAL(),
        root,
        0.01,
    )
    # bumper and tow eyes
    box(
        prefix + "_bumper",
        (width + 0.05, 0.3, 0.38),
        (0, front + 0.18, frame_h - 0.3),
        DARK(),
        root,
        0.03,
    )
    for s in (-1, 1):
        cyl(
            prefix + f"_toweye{s}",
            0.08,
            0.06,
            (s * 0.55, front + 0.35, frame_h - 0.3),
            (math.pi / 2, 0, 0),
            METAL(),
            root,
            12,
        )
    # roof: hatch, beacon, horn
    box(
        prefix + "_hatch",
        (0.65, 0.65, 0.05),
        (0.35, cy - 0.2, top + 0.1),
        DARK(),
        root,
        0.02,
    )
    cyl(
        prefix + "_beacon",
        0.09,
        0.14,
        (-0.55, front - 0.35, top + 0.14),
        (0, 0, 0),
        AMBER(),
        root,
        14,
    )
    cyl(
        prefix + "_horn",
        0.05,
        0.3,
        (0.7, front - 0.3, top + 0.12),
        (math.pi / 2, 0, 0),
        METAL(),
        root,
        10,
    )
    return top


def iran_truck(
    prefix, axle_ys, length, width=2.55, cab_len=2.4, frame_h=1.3, wheel_r=0.66
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
