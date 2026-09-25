"""Shared Blender building blocks for the IRAD models. Metres, +Y forward, Z up."""

import math
import bpy
import bmesh


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def mat(name, rgb, rough=0.8, metal=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return m


PAINT = lambda: mat("irad_paint", (0.36, 0.33, 0.22))  # Iranian olive-tan
DARK = lambda: mat("irad_dark", (0.05, 0.05, 0.05), 0.9)
TYRE = lambda: mat("irad_tyre", (0.03, 0.03, 0.03), 0.95)
GLASS = lambda: mat("irad_glass", (0.08, 0.12, 0.15), 0.1, 0.3)
RADAR = lambda: mat("irad_radar", (0.30, 0.30, 0.26), 0.6)
METAL = lambda: mat("irad_metal", (0.4, 0.4, 0.4), 0.4, 0.8)


def box(name, size, loc, material, parent=None, bevel=0.03):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
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


def wheel(name, loc, r=0.62, w=0.45, parent=None):
    t = cyl(name, r, w, loc, (0, math.pi / 2, 0), TYRE(), parent, 32)
    hub = cyl(
        name + "_hub", r * 0.45, w + 0.02, loc, (0, math.pi / 2, 0), PAINT(), parent, 16
    )
    return t


def truck(
    prefix,
    axles,
    length,
    width=2.55,
    cab_len=2.6,
    frame_h=1.25,
    axle_ys=None,
    wheel_r=0.62,
):
    """Heavy military truck: cab forward, flat frame. Returns (root, deck_z, deck_rear_y, deck_front_y)."""
    root = empty(prefix, (0, 0, 0))
    half = length / 2
    front = half
    rear = -half
    # frame rails
    box(
        prefix + "_frame",
        (width * 0.55, length * 0.97, 0.35),
        (0, 0, frame_h - 0.2),
        DARK(),
        root,
        0.01,
    )
    # cab
    cz = frame_h + 1.05
    cab = box(
        prefix + "_cab",
        (width, cab_len, 1.9),
        (0, front - cab_len / 2, cz),
        PAINT(),
        root,
        0.08,
    )
    box(
        prefix + "_windscreen",
        (width * 0.9, 0.05, 0.75),
        (0, front + 0.01, cz + 0.45),
        GLASS(),
        root,
        0,
    )
    for s in (-1, 1):
        box(
            prefix + f"_sidewin{s}",
            (0.05, cab_len * 0.45, 0.6),
            (s * (width / 2 + 0.01), front - cab_len * 0.3, cz + 0.45),
            GLASS(),
            root,
            0,
        )
    box(
        prefix + "_bumper",
        (width, 0.3, 0.35),
        (0, front + 0.1, frame_h - 0.3),
        DARK(),
        root,
        0.02,
    )
    # grille, lights, mirrors, exhaust, roof hatch
    box(
        prefix + "_grille",
        (width * 0.6, 0.05, 0.55),
        (0, front + 0.02, cz - 0.45),
        DARK(),
        root,
        0.01,
    )
    for s in (-1, 1):
        cyl(
            prefix + f"_light{s}",
            0.11,
            0.06,
            (s * (width / 2 - 0.3), front + 0.03, cz - 0.55),
            (math.pi / 2, 0, 0),
            GLASS(),
            root,
            16,
        )
        box(
            prefix + f"_mirrorarm{s}",
            (0.35, 0.04, 0.04),
            (s * (width / 2 + 0.17), front - 0.25, cz + 0.55),
            DARK(),
            root,
            0,
        )
        box(
            prefix + f"_mirror{s}",
            (0.05, 0.12, 0.35),
            (s * (width / 2 + 0.34), front - 0.25, cz + 0.45),
            DARK(),
            root,
            0.01,
        )
    cyl(
        prefix + "_exhaust",
        0.07,
        1.6,
        (width / 2 - 0.15, front - cab_len - 0.15, cz + 0.2),
        (0, 0, 0),
        METAL(),
        root,
        12,
    )
    box(
        prefix + "_hatch",
        (0.7, 0.7, 0.06),
        (-0.4, front - cab_len * 0.6, cz + 0.98),
        DARK(),
        root,
        0.01,
    )
    # wheels
    if axle_ys is None:
        span = length - cab_len * 0.5 - 1.2
        first = front - 1.1
        axle_ys = [first - i * (span / max(axles - 1, 1)) for i in range(axles)]
    for i, y in enumerate(axle_ys):
        for s in (-1, 1):
            wheel(
                prefix + f"_wheel_{i}_{'L' if s<0 else 'R'}",
                (s * (width / 2 - 0.2), y, wheel_r),
                wheel_r,
                0.45,
                root,
            )
    # fenders
    for i, y in enumerate(axle_ys):
        for s in (-1, 1):
            box(
                prefix + f"_fender_{i}{s}",
                (0.5, 1.5, 0.08),
                (s * (width / 2 - 0.2), y, wheel_r * 2 + 0.08),
                PAINT(),
                root,
                0.02,
            )
    deck_z = frame_h
    return root, deck_z, rear, front - cab_len


def render(path, target=(0, 0, 2), dist=22, elev=18, az=35, res=(1100, 700)):
    scn = bpy.context.scene
    scn.render.engine = "CYCLES"
    scn.cycles.samples = 24
    scn.cycles.device = "CPU"
    scn.render.resolution_x, scn.render.resolution_y = res
    scn.render.film_transparent = False
    world = bpy.data.worlds.new("w")
    scn.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.75, 0.8, 0.85, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.6
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, 0))
    g = bpy.context.active_object
    g.name = "ground_preview"
    g.data.materials.append(mat("ground", (0.55, 0.5, 0.4)))
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


# ---- detail helpers (v2) -------------------------------------------------

STRIPE = lambda: mat("irad_stripe", (0.75, 0.62, 0.08), 0.6)
RED = lambda: mat("irad_red", (0.5, 0.05, 0.03), 0.5)
AMBER = lambda: mat("irad_amber", (0.9, 0.5, 0.05), 0.3)
TRIM = lambda: mat("irad_trim", (0.27, 0.25, 0.17))


def wheel2(name, loc, r=0.62, w=0.45, parent=None):
    """Rounded tyre with tread bands, rim and 8 lug nuts facing outward."""
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
        PAINT(),
        parent,
        32,
    )
    cyl(
        name + "_hub",
        r * 0.24,
        0.12,
        (rx + side * 0.03, loc[1], loc[2]),
        (0, math.pi / 2, 0),
        TRIM(),
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


def truck2(prefix, axles, length, width=2.55, cab_len=2.8, frame_h=1.25, wheel_r=0.62):
    """Detailed cab-forward heavy truck. Returns (root, deck_z, rear_y, deck_front_y, axle_ys)."""
    root = empty(prefix, (0, 0, 0))
    half = length / 2
    front = half
    rear = -half
    box(
        prefix + "_frame",
        (width * 0.5, length * 0.97, 0.32),
        (0, 0, frame_h - 0.2),
        DARK(),
        root,
        0.01,
    )
    # cab: lower body + upper with sloped windscreen
    cz = frame_h + 0.55
    body = box(
        prefix + "_cab_lower",
        (width, cab_len, 1.1),
        (0, front - cab_len / 2, cz),
        PAINT(),
        root,
        0.12,
    )
    up = box(
        prefix + "_cab_upper",
        (width * 0.98, cab_len * 0.9, 1.0),
        (0, front - cab_len * 0.52, cz + 1.02),
        PAINT(),
        root,
        0.15,
    )
    bm = bmesh.new()
    bm.from_mesh(up.data)
    for v in bm.verts:  # slope the windscreen: pull top-front edge back
        if v.co.y > 0 and v.co.z > 0:
            v.co.y -= 0.35
    bm.to_mesh(up.data)
    bm.free()
    # the upper cab's front face runs from (y0, z0) at the bottom back by SLOPE at the top
    y0 = front - cab_len * 0.52 + cab_len * 0.45
    z0 = cz + 0.52
    SLOPE = 0.35
    tilt = math.atan2(SLOPE, 1.0)
    wz = cz + 1.05
    wy = y0 - SLOPE * (wz - z0) + 0.025
    for s in (-1, 1):
        g = box(
            prefix + f"_windscreen{s}",
            (width * 0.42, 0.03, 0.62),
            (s * width * 0.225, wy, wz),
            GLASS(),
            root,
            0,
        )
        g.rotation_euler = (tilt, 0, 0)
        box(
            prefix + f"_sidewin{s}",
            (0.03, cab_len * 0.36, 0.5),
            (s * (width * 0.49 + 0.005), front - cab_len * 0.36, wz),
            GLASS(),
            root,
            0,
        )
        box(
            prefix + f"_door{s}",
            (0.03, cab_len * 0.42, 1.55),
            (s * (width / 2 + 0.005), front - cab_len * 0.32, cz + 0.35),
            TRIM(),
            root,
            0,
        )
        box(
            prefix + f"_handle{s}",
            (0.06, 0.18, 0.04),
            (s * (width / 2 + 0.03), front - cab_len * 0.48, cz + 0.4),
            METAL(),
            root,
            0,
        )
        for k in range(2):
            box(
                prefix + f"_step{s}{k}",
                (0.3, 0.45, 0.04),
                (
                    s * (width / 2 - 0.05),
                    front - cab_len * 0.32,
                    frame_h - 0.55 + k * 0.38,
                ),
                METAL(),
                root,
                0,
            )
        cyl(
            prefix + f"_light{s}",
            0.12,
            0.08,
            (s * (width / 2 - 0.32), front + 0.03, cz - 0.3),
            (math.pi / 2, 0, 0),
            GLASS(),
            root,
            20,
        )
        cyl(
            prefix + f"_blinker{s}",
            0.05,
            0.06,
            (s * (width / 2 - 0.1), front + 0.03, cz - 0.3),
            (math.pi / 2, 0, 0),
            AMBER(),
            root,
            12,
        )
        box(
            prefix + f"_mirrorarm{s}",
            (0.4, 0.04, 0.04),
            (s * (width / 2 + 0.2), front - 0.3, wz + 0.2),
            DARK(),
            root,
            0,
        )
        box(
            prefix + f"_mirror{s}",
            (0.06, 0.14, 0.4),
            (s * (width / 2 + 0.4), front - 0.3, wz + 0.05),
            DARK(),
            root,
            0.02,
        )
    box(
        prefix + "_pillar", (0.09, 0.05, 0.7), (0, wy + 0.01, wz), PAINT(), root, 0
    ).rotation_euler = (tilt, 0, 0)
    box(
        prefix + "_wiperL",
        (0.6, 0.02, 0.03),
        (-0.55, wy + 0.03, wz - 0.28),
        DARK(),
        root,
        0,
    ).rotation_euler = (tilt, 0, 0.3)
    box(
        prefix + "_wiperR",
        (0.6, 0.02, 0.03),
        (0.55, wy + 0.03, wz - 0.28),
        DARK(),
        root,
        0,
    ).rotation_euler = (tilt, 0, 0.3)
    box(
        prefix + "_grille",
        (width * 0.55, 0.05, 0.5),
        (0, front + 0.03, cz - 0.05),
        DARK(),
        root,
        0.01,
    )
    for i in range(6):
        box(
            prefix + f"_grillebar{i}",
            (width * 0.55, 0.06, 0.03),
            (0, front + 0.05, cz - 0.27 + i * 0.09),
            TRIM(),
            root,
            0,
        )
    box(
        prefix + "_bumper",
        (width * 1.02, 0.32, 0.36),
        (0, front + 0.12, frame_h - 0.35),
        DARK(),
        root,
        0.03,
    )
    for s in (-1, 1):
        box(
            prefix + f"_towhook{s}",
            (0.12, 0.2, 0.12),
            (s * 0.6, front + 0.32, frame_h - 0.35),
            METAL(),
            root,
            0.01,
        )
    # roof: rack, beacon, hatch, horn
    rz = cz + 1.55
    box(
        prefix + "_hatch",
        (0.7, 0.7, 0.06),
        (-0.45, front - cab_len * 0.62, rz),
        DARK(),
        root,
        0.02,
    )
    for s in (-1, 1):
        box(
            prefix + f"_rackrail{s}",
            (0.04, cab_len * 0.55, 0.04),
            (s * 0.9, front - cab_len * 0.6, rz + 0.1),
            METAL(),
            root,
            0,
        )
    cyl(
        prefix + "_beacon",
        0.08,
        0.12,
        (0.6, front - cab_len * 0.3, rz + 0.05),
        (0, 0, 0),
        AMBER(),
        root,
        12,
    )
    cyl(
        prefix + "_exhaust",
        0.08,
        1.7,
        (width / 2 - 0.12, front - cab_len - 0.12, cz + 0.8),
        (0, 0, 0),
        METAL(),
        root,
        14,
    )
    cyl(
        prefix + "_exhaustcap",
        0.1,
        0.1,
        (width / 2 - 0.12, front - cab_len - 0.12, cz + 1.68),
        (0, 0, 0),
        DARK(),
        root,
        14,
    )
    box(
        prefix + "_airfilter",
        (0.4, 0.4, 1.0),
        (-width / 2 + 0.25, front - cab_len - 0.25, cz + 0.4),
        PAINT(),
        root,
        0.05,
    )
    # axles and wheels
    span = length - cab_len * 0.5 - 1.3
    first = front - 1.1
    axle_ys = [first - i * (span / max(axles - 1, 1)) for i in range(axles)]
    # group axles like the real truck: two steering axles forward, gap, rear bogie
    if axles >= 5:
        axle_ys = [first, first - 1.55, first - 4.3, first - 5.85, first - 7.4]
    elif axles == 4:
        axle_ys = [first, first - 1.5, first - 4.2, first - 5.6]
    elif axles == 3:
        axle_ys = [first, first - 3.6, first - 5.0]
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
            wheel2(
                prefix + f"_wheel_{i}_{'L' if s<0 else 'R'}",
                (s * (width / 2 - 0.22), y, wheel_r),
                wheel_r,
                0.45,
                root,
            )
            box(
                prefix + f"_fender_{i}{s}",
                (0.55, 1.45, 0.06),
                (s * (width / 2 - 0.22), y, wheel_r * 2 + 0.1),
                PAINT(),
                root,
                0.02,
            )
    # mud flaps behind the last axle
    for s in (-1, 1):
        box(
            prefix + f"_mudflap{s}",
            (0.5, 0.03, 0.6),
            (s * (width / 2 - 0.22), axle_ys[-1] - 0.8, wheel_r * 0.8),
            DARK(),
            root,
            0,
        )
    # between steering axles and bogie: fuel tanks, toolboxes, ladder
    gy = (axle_ys[1] + axle_ys[2]) / 2 if axles >= 4 else (axle_ys[0] + axle_ys[1]) / 2
    cyl(
        prefix + "_fueltank",
        0.33,
        1.5,
        (-width / 2 + 0.35, gy, frame_h - 0.45),
        (math.pi / 2, 0, 0),
        METAL(),
        root,
        20,
    )
    box(
        prefix + "_toolbox",
        (0.45, 1.4, 0.55),
        (width / 2 - 0.3, gy, frame_h - 0.45),
        TRIM(),
        root,
        0.03,
    )
    # spare wheel behind the cab
    sy = front - cab_len - 0.3
    t = cyl(
        prefix + "_spare",
        wheel_r,
        0.4,
        (0.0, sy, frame_h + wheel_r + 0.15),
        (math.pi / 2, 0, 0),
        TYRE(),
        root,
        40,
    )
    m = t.modifiers.new("bevel", "BEVEL")
    m.width = 0.08
    m.segments = 3
    cyl(
        prefix + "_spare_rim",
        wheel_r * 0.58,
        0.44,
        (0.0, sy, frame_h + wheel_r + 0.15),
        (math.pi / 2, 0, 0),
        PAINT(),
        root,
        32,
    )
    box(
        prefix + "_spare_bracket",
        (0.2, 0.3, 0.9),
        (0.0, sy + 0.25, frame_h + 0.45),
        DARK(),
        root,
        0.01,
    )
    # rear lights
    for s in (-1, 1):
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
    return root, frame_h, rear, front - cab_len - 0.8, axle_ys


def finalize(prefix):
    """Apply modifiers, convert curves/text to mesh, report the triangle count."""
    for o in list(bpy.data.objects):
        if o.type in ("CURVE", "FONT"):
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
        if (
            o.type == "MESH"
            and o.name != "collision_shell"
            and not o.name.startswith("ground")
        ):
            tris += sum(len(p.vertices) - 2 for p in o.data.polygons)
    print(f"TRIS {prefix}: {tris}")
    return tris
