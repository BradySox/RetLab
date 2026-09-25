import math, sys, bpy

sys.path.insert(0, sys.argv[-1])
from irad_kit import *

L, S = 8.3, 0.78  # canister length and section (m)
ANG_STEPS = 11  # keyframes across the erect animation


def build():
    reset()
    root, deck_z, rear, deck_front, axles = truck2(
        "IRAD_Bavar373_LN", axles=5, length=13.6
    )
    dz = deck_z
    # deck: plate, side rails with stanchions, tie-downs
    dlen = deck_front - rear
    box(
        "ln_deck",
        (2.5, dlen, 0.16),
        (0, (deck_front + rear) / 2, dz + 0.06),
        DARK(),
        root,
        0.01,
    )
    for s in (-1, 1):
        box(
            f"ln_deckedge{s}",
            (0.08, dlen, 0.22),
            (s * 1.25, (deck_front + rear) / 2, dz + 0.05),
            TRIM(),
            root,
            0.01,
        )
        for k in range(7):
            y = rear + 0.6 + k * (dlen - 1.2) / 6
            box(
                f"ln_tiedown{s}{k}",
                (0.1, 0.1, 0.06),
                (s * 1.18, y, dz + 0.17),
                METAL(),
                root,
                0,
            )
    # power pack cabinet behind the cab
    pp_y, pp_len = deck_front - 1.1, 2.0
    box("ln_powerpack", (2.4, pp_len, 1.5), (0, pp_y, dz + 0.9), PAINT(), root, 0.06)
    for s in (-1, 1):
        louvers(
            f"ln_louver{s}", (s * 1.2, pp_y + 0.35, dz + 1.05), 0.8, 0.7, 7, s, root
        )
        box(
            f"ln_ppdoor{s}",
            (0.02, 0.8, 1.1),
            (s * 1.21, pp_y - 0.5, dz + 0.9),
            TRIM(),
            root,
            0,
        )
        box(
            f"ln_pphandle{s}",
            (0.05, 0.05, 0.2),
            (s * 1.23, pp_y - 0.2, dz + 0.9),
            METAL(),
            root,
            0,
        )
    cyl(
        "ln_ppexhaust",
        0.07,
        0.5,
        (0.8, pp_y + 0.5, dz + 1.85),
        (0, 0, 0),
        METAL(),
        root,
        12,
    )
    # stabiliser jacks: two at the tail, two behind the cab
    for s in (-1, 1):
        for jy, tag in ((rear + 0.35, "r"), (deck_front + 0.3, "f")):
            box(
                f"ln_jackbeam{s}{tag}",
                (0.6, 0.3, 0.25),
                (s * 1.35, jy, dz - 0.15),
                DARK(),
                root,
                0.01,
            )
            cyl(
                f"ln_jackcyl{s}{tag}",
                0.12,
                1.0,
                (s * 1.6, jy, 0.62),
                (0, 0, 0),
                METAL(),
                root,
                16,
            )
            cyl(
                f"ln_jackpad{s}{tag}",
                0.3,
                0.07,
                (s * 1.6, jy, 0.04),
                (0, 0, 0),
                DARK(),
                root,
                20,
            )
    # launcher pivot at the tail: 0 = travel, 90 deg = erect; the canisters
    # overhang the tail so, erect, their base plate rests on the ground
    PZ = dz + 0.9
    P = (0, rear + 0.2, PZ)
    pivot = empty("arg_launcher_elevation", P, root)
    for s in (-1, 1):
        box(
            f"ln_pivotblock{s}",
            (0.3, 0.5, 0.9),
            (s * 1.05, P[1], dz + 0.45),
            DARK(),
            root,
            0.02,
        )
        cyl(
            f"ln_pivotpin{s}",
            0.12,
            0.35,
            (s * 1.05, P[1], PZ),
            (0, math.pi / 2, 0),
            METAL(),
            root,
            16,
        )
    OVER = PZ - 0.15
    pack = empty("ln_pack", (0, 0, 0), pivot)
    cells = [
        (-S / 2 - 0.03, S / 2 + 0.03),
        (S / 2 + 0.03, S / 2 + 0.03),
        (-S / 2 - 0.03, -S / 2 - 0.03),
        (S / 2 + 0.03, -S / 2 - 0.03),
    ]
    lift = 0.47
    for i, (x, z) in enumerate(cells):
        zc = z + lift
        box(f"ln_canister_{i+1}", (S, L, S), (x, L / 2 - OVER, zc), PAINT(), pack, 0.06)
        for k in (0.08, 0.35, 0.65, 0.92):
            box(
                f"ln_c{i+1}_band{k}",
                (S + 0.05, 0.14, S + 0.05),
                (x, L * k - OVER, zc),
                TRIM(),
                pack,
                0.02,
            )
        # tail end cap with frame and stencil; hazard band next to it
        box(
            f"ln_c{i+1}_tailcap",
            (S * 0.94, 0.05, S * 0.94),
            (x, -OVER - 0.02, zc),
            METAL(),
            pack,
            0.01,
        )
        box(
            f"ln_c{i+1}_tailframe",
            (S + 0.06, 0.08, S + 0.06),
            (x, -OVER + 0.02, zc),
            DARK(),
            pack,
            0.01,
        )
        stencil(
            f"ln_c{i+1}_num",
            str(i + 1),
            (x, -OVER - 0.06, zc),
            (math.pi / 2, 0, 0),
            0.4,
            STRIPE(),
            pack,
        )
        box(
            f"ln_c{i+1}_hazard",
            (S + 0.055, 0.1, S + 0.055),
            (x, 0.2 - OVER, zc),
            STRIPE(),
            pack,
            0.01,
        )
        # muzzle cap and launch connector
        box(
            f"ln_c{i+1}_cap",
            (S * 0.9, 0.05, S * 0.9),
            (x, L - OVER + 0.02, zc),
            METAL(),
            pack,
            0.01,
        )
        for r in range(3):
            box(
                f"ln_c{i+1}_caprib{r}",
                (S * 0.9, 0.06, 0.04),
                (x, L - OVER + 0.05, zc - 0.25 + r * 0.25),
                DARK(),
                pack,
                0,
            )
        empty(f"LAUNCH_{i+1}", (x, L - OVER + 0.1, zc), pack, (-math.pi / 2, 0, 0))
        # lifting lugs on the top row
        if z > 0:
            for k in (0.25, 0.75):
                cyl(
                    f"ln_c{i+1}_lug{k}",
                    0.08,
                    0.04,
                    (x, L * k - OVER, zc + S / 2 + 0.08),
                    (0, math.pi / 2, 0),
                    METAL(),
                    pack,
                    12,
                )
    # cradle, side frame, cable conduits
    box(
        "ln_cradle",
        (2.0, L * 0.9, 0.18),
        (0, L * 0.45 - OVER + 0.3, lift - S - 0.12),
        DARK(),
        pack,
        0.02,
    )
    for s in (-1, 1):
        box(
            f"ln_sideframe{s}",
            (0.1, L * 0.85, 0.22),
            (s * (S + 0.1), L * 0.45 - OVER + 0.3, lift - S * 0.3),
            DARK(),
            pack,
            0.01,
        )
        hose(
            f"ln_conduit{s}",
            [
                (s * (S + 0.18), -OVER + 0.5, lift + 0.2),
                (s * (S + 0.2), L * 0.5 - OVER, lift + 0.25),
                (s * (S + 0.18), L - OVER - 0.4, lift + 0.2),
            ],
            0.035,
            DARK(),
            pack,
        )
    # hydraulic hoses from the power pack to the pivot, along the deck
    for s in (-1, 1):
        hose(
            f"ln_hose{s}",
            [
                (s * 0.35, pp_y - pp_len / 2, dz + 0.3),
                (s * 0.4, pp_y - 3.0, dz + 0.2),
                (s * 0.5, rear + 2.0, dz + 0.2),
                (s * 0.95, P[1] + 0.4, dz + 0.5),
            ],
            0.03,
            DARK(),
            root,
        )
    # erector rams: barrel pivots on the truck, rod slides out of it
    A_local = (
        0.0,
        3.2 - 0.0,
        -0.55,
    )  # attach on the pack, pack-local (y along pack, z below)
    Bp = (P[1] + 6.9, dz + 0.32)  # barrel base on the truck (y, z)

    def A_world(th):
        y, z = A_local[1], A_local[2]
        return (
            P[1] + y * math.cos(th) - z * math.sin(th),
            PZ + y * math.sin(th) + z * math.cos(th),
        )

    dists = [
        math.dist(A_world(math.radians(90 * i / (ANG_STEPS - 1))), Bp)
        for i in range(ANG_STEPS)
    ]
    Lb = min(dists) - 0.05
    Lr = max(dists) - Lb + 0.25
    for s in (-1, 1):
        bx = s * 0.6
        box(
            f"ln_rambase{s}",
            (0.3, 0.35, 0.25),
            (bx, Bp[0], Bp[1] - 0.12),
            DARK(),
            root,
            0.02,
        )
        barrel = empty(f"ln_ram_barrel_pivot{s}", (bx, Bp[0], Bp[1]), root)
        b = cyl(
            f"ln_ram_barrel{s}",
            0.13,
            Lb,
            (0, -Lb / 2, 0),
            (math.pi / 2, 0, 0),
            METAL(),
            barrel,
            18,
        )
        rod_pivot = empty(f"ln_ram_rod_slide{s}", (0, 0, 0), barrel)
        cyl(
            f"ln_ram_rod{s}",
            0.075,
            Lr,
            (0, -Lr / 2, 0),
            (math.pi / 2, 0, 0),
            mat("irad_chrome", (0.8, 0.8, 0.8), 0.15, 1.0),
            rod_pivot,
            14,
        )
        for i in range(ANG_STEPS):
            th = math.radians(90 * i / (ANG_STEPS - 1))
            f = i * 100 // (ANG_STEPS - 1)
            ay, az = A_world(th)
            vy, vz = (
                ay - Bp[0],
                az - Bp[1],
            )  # barrel points from B toward A along its local -Y
            barrel.rotation_euler = (math.atan2(-vz, -vy), 0, 0)
            barrel.keyframe_insert("rotation_euler", frame=f)
            rod_pivot.location = (0, -(math.hypot(vy, vz) - Lr), 0)
            rod_pivot.keyframe_insert("location", frame=f)
    shell = box("collision_shell", (2.8, 15.6, 3.4), (0, -1.0, 1.7), DARK(), root, 0)
    shell.hide_render = True
    for i in range(ANG_STEPS):
        f = i * 100 // (ANG_STEPS - 1)
        pivot.rotation_euler = (math.radians(90 * i / (ANG_STEPS - 1)), 0, 0)
        pivot.keyframe_insert("rotation_euler", frame=f)
    return pivot


if __name__ == "__main__":
    out = sys.argv[-1]
    build()
    finalize("IRAD_Bavar373_LN")
    bpy.ops.wm.save_as_mainfile(filepath=f"{out}/IRAD_Bavar373_LN.blend")
    scn = bpy.context.scene
    for frame, name, kw in (
        (0, "travel", dict(target=(0, 0.5, 1.8), dist=19, az=38)),
        (0, "cab", dict(target=(0, 5.5, 2.2), dist=8.5, az=30, elev=12)),
        (50, "raising", dict(target=(0, -3, 3.0), dist=22, az=70, elev=10)),
        (100, "erect", dict(target=(0, -3, 3.8), dist=22, az=125, elev=10)),
        (100, "tail", dict(target=(0, -6.5, 1.5), dist=9, az=160, elev=15)),
    ):
        scn.frame_set(frame)
        render(f"{out}/IRAD_Bavar373_LN_{name}.png", **kw)
