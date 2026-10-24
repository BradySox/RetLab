"""Build the modern FOB layout: resources/layouts/buildings/modern_fob.{miz,yaml}.

fob1's six buildings inside a HESCO wall with four watchtowers, a gated entrance,
tents, containers, a generator and sandbag positions. Every prop is a stock DCS static
from the Massun92 asset pack that ships with the base game.

Geometry was checked against ED's own AH-64D Iraq quickstart missions: a
HESCO_wallperimeter_1 runs along its heading and they are laid 12.3 m apart.

Run from the repo root: python tools/build_modern_fob_layout.py
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import dcs
import yaml
from dcs.mapping import Point
from dcs.statics import fortification_map

NAME = "modern_fob"
OUT_DIR = Path("resources/layouts/buildings")

# Origin is the command center; +x is north, +y is east (DCS map axes).
ORIGIN_X, ORIGIN_Y = -495000.0, 320000.0

WALL_PITCH = 12.3
TOWER_GAP = 4.0  # half a tower's footprint, kept clear at each corner
SOUTH, NORTH = -60.0, 40.0
WEST, EAST = -110.0, 40.0
GATE_WIDTH = 2 * WALL_PITCH

# (type, x, y, heading) relative to the origin; fob1's buildings at fob1's offsets.
CORE: list[tuple[str, float, float, float]] = [
    (".Command Center", 0, 0, 180),
    ("Barracks 2", 9, -69, 0),
    ("Barracks 2", -1, -69, 0),
    ("Barracks 2", -12, -70, 0),
    ("Garage small B", -25, -45, 0),
    ("Garage small B", -25, -29, 0),
]

DRESSING: list[tuple[str, float, float, float]] = [
    ("Tent05", 28, -95, 90),
    ("Tent05", 28, -72, 90),
    ("Tent04", 28, -49, 90),
    ("Tent04", 28, -26, 90),
    ("Tent01", -48, -95, 0),
    ("Tent01", -48, -80, 0),
    ("container_40ft", -48, -55, 90),
    ("container_20ft", -48, -40, 90),
    ("Container_office", 28, 20, 0),
    ("HESCO_generator", -45, 25, 0),
    ("Camouflage03", -30, 10, 0),
    # Gate guard: barrier in the south wall gap, sandbag positions outside it.
    ("BoomBarrier_closed", SOUTH, -35, 90),
    ("Sandbag_17", SOUTH - 8, -50, 0),
    ("Sandbag_17", SOUTH - 8, -20, 0),
]


def wall_run(
    start: tuple[float, float], end: tuple[float, float], gate_at: float | None = None
) -> list[tuple[str, float, float, float]]:
    """HESCO segments from start to end, centered between the corner towers."""
    (x0, y0), (x1, y1) = start, end
    length = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
    ux, uy = (x1 - x0) / length, (y1 - y0) / length
    heading = 0.0 if abs(ux) > abs(uy) else 90.0
    usable = length - 2 * TOWER_GAP
    count = int(usable // WALL_PITCH)
    margin = TOWER_GAP + (usable - count * WALL_PITCH) / 2
    out = []
    for i in range(count):
        d = margin + (i + 0.5) * WALL_PITCH
        if gate_at is not None and abs(d - gate_at) < GATE_WIDTH / 2:
            continue
        out.append(("HESCO_wallperimeter_1", x0 + ux * d, y0 + uy * d, heading))
    return out


def perimeter() -> list[tuple[str, float, float, float]]:
    walls = (
        wall_run((SOUTH, WEST), (SOUTH, EAST), gate_at=-35 - WEST)
        + wall_run((NORTH, WEST), (NORTH, EAST))
        + wall_run((SOUTH, WEST), (NORTH, WEST))
        + wall_run((SOUTH, EAST), (NORTH, EAST))
    )
    towers = [
        ("HESCO_watchtower_2", x, y, h)
        for x, y, h in (
            (SOUTH, WEST, 225),
            (SOUTH, EAST, 135),
            (NORTH, WEST, 315),
            (NORTH, EAST, 45),
        )
    ]
    return walls + towers


def build() -> None:
    mission = dcs.Mission(dcs.terrain.Caucasus())
    country = mission.country("USA")

    groups: dict[str, list[str]] = {}
    types: dict[str, str] = {}
    optional: dict[str, bool] = {}
    by_type: dict[tuple[str, bool], list[tuple[float, float, float]]] = defaultdict(
        list
    )
    # The loader anchors the layout on the first unit it reads, so the command
    # center goes first.
    for unit_type, x, y, h in CORE:
        by_type[(unit_type, False)].append((x, y, h))
    for unit_type, x, y, h in perimeter() + DRESSING:
        by_type[(unit_type, True)].append((x, y, h))

    for index, ((unit_type, is_optional), spots) in enumerate(by_type.items()):
        group_name = f"{NAME} {index}"
        groups[group_name] = []
        types[group_name] = unit_type
        optional[group_name] = is_optional
        for n, (x, y, h) in enumerate(spots):
            static_name = f"{group_name}-{n}"
            mission.static_group(
                country,
                static_name,
                fortification_map[unit_type],
                Point(ORIGIN_X + x, ORIGIN_Y + y, mission.terrain),
                heading=h,
            )
            groups[group_name].append(static_name)

    miz = OUT_DIR / f"{NAME}.miz"
    mission.save(str(miz))

    layout_groups = []
    for group_name, statics in groups.items():
        entry: dict[str, object] = {
            "name": group_name,
            "statics": statics,
            "unit_count": [len(statics)],
            "unit_types": [types[group_name]],
        }
        if optional[group_name]:
            entry["optional"] = True
        layout_groups.append(entry)
    mapping = {
        "name": NAME,
        "generic": False,
        "tasks": ["FOB"],
        "groups": [{"FOB": layout_groups}],
        "layout_file": miz.as_posix(),
    }
    header = "# Generated by tools/build_modern_fob_layout.py; edit the tool, not this file.\n"
    (OUT_DIR / f"{NAME}.yaml").write_text(
        header + yaml.safe_dump(mapping, sort_keys=False), encoding="utf-8"
    )
    total = sum(len(s) for s in groups.values())
    print(f"{NAME}: {total} statics in {len(groups)} groups")


if __name__ == "__main__":
    build()
