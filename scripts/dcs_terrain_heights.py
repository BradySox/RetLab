"""DCS terrain height grids for the DTC steerpoint elevation.

Two subcommands:

    generate --terrain <Name>   build a probe .miz that samples land.getHeight
    apply <heights.txt>         turn the probe output into
                                resources/terrain_heights/<terrain>.npz

See scripts/README.md for the workflow and
docs/dev/design/retlab-dtc-cartridge-notes.md for why the grid exists.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Any, Iterable, Optional

import numpy as np

from game.theater.terrainheights import HeightGrid, grid_path, save_grid

_PROBE_LUA = (
    Path(__file__).resolve().parent.parent
    / "resources"
    / "plugins"
    / "base"
    / "dcs_terrain_height_probe.lua"
)

#: Targets sit near the fields a campaign uses; this covers every one of them.
DEFAULT_MARGIN_KM = 150.0
DEFAULT_STEP_M = 1000.0


def grid_extent(
    positions: Iterable[tuple[float, float]], margin_m: float, step_m: float
) -> tuple[float, float, int, int]:
    """(x0, y0, nx, ny) covering every position plus the margin, on step_m."""
    xs, ys = zip(*positions)
    x0 = math.floor((min(xs) - margin_m) / step_m) * step_m
    y0 = math.floor((min(ys) - margin_m) / step_m) * step_m
    nx = int(math.ceil((max(xs) + margin_m - x0) / step_m)) + 1
    ny = int(math.ceil((max(ys) + margin_m - y0) / step_m)) + 1
    return x0, y0, nx, ny


def _terrain(name: str) -> Any:
    from scripts.dcs_airfield_elevations import _terrain_classes

    classes = _terrain_classes()
    if name not in classes:
        valid = ", ".join(sorted(classes))
        raise SystemExit(f"Unknown terrain {name!r}. Valid terrains: {valid}")
    return classes[name]()


def build_probe_mission(terrain_name: str, margin_km: float, step_m: float) -> Any:
    import dcs
    from dcs.action import DoScript
    from dcs.translation import String
    from dcs.triggers import TriggerStart

    terrain = _terrain(terrain_name)
    positions = [(a.position.x, a.position.y) for a in terrain.airports.values()]
    x0, y0, nx, ny = grid_extent(positions, margin_km * 1000.0, step_m)
    config = (
        f'RETLAB_HEIGHT_GRID = {{ terrain = "{terrain.name}", x0 = {x0:.1f}, '
        f"y0 = {y0:.1f}, step = {step_m:.1f}, nx = {nx}, ny = {ny} }}\n"
    )
    mission = dcs.Mission(terrain)
    trigger = TriggerStart(comment="terrain height probe")
    probe = _PROBE_LUA.read_text(encoding="utf-8")
    trigger.add_action(DoScript(String(config + probe)))
    mission.triggerrules.triggers.append(trigger)
    print(f"{terrain.name}: {nx} x {ny} points at {step_m:.0f} m")
    return mission


def parse_probe_output(path: Path) -> tuple[str, HeightGrid]:
    """Read the probe's text file; raise ValueError if it is not complete."""
    with path.open("r", encoding="utf-8") as fh:
        header = fh.readline().split()
        if len(header) != 8 or header[0] != "RETLAB-HEIGHTS" or header[1] != "1":
            raise ValueError(f"{path}: not a terrain height probe file")
        terrain = header[2]
        x0, y0, step = (float(v) for v in header[3:6])
        nx, ny = int(header[6]), int(header[7])
        rows: list[np.ndarray[Any, Any]] = []
        ended = False
        for line in fh:
            line = line.strip()
            if line == "END":
                ended = True
                break
            values = np.array(line.split(), dtype=np.int16)
            if len(values) != ny:
                raise ValueError(f"{path}: row {len(rows)} has {len(values)} values")
            rows.append(values)
    if not ended or len(rows) != nx:
        raise ValueError(
            f"{path}: incomplete, {len(rows)} of {nx} rows -- let the probe finish"
        )
    heights = np.vstack(rows)
    return terrain, HeightGrid(x0, y0, step, heights)


def _cmd_generate(args: argparse.Namespace) -> int:
    mission = build_probe_mission(args.terrain, args.margin_km, args.step)
    out: Path = args.out or Path(f"terrain_height_probe_{args.terrain.lower()}.miz")
    mission.save(str(out))
    print(f"wrote {out} -- run it in DCS, unpause, wait for 'done', then: apply")
    return 0


def _cmd_apply(args: argparse.Namespace) -> int:
    terrain, grid = parse_probe_output(args.heights)
    if args.every > 1:
        grid = HeightGrid(
            grid.x0,
            grid.y0,
            grid.step * args.every,
            grid.heights[:: args.every, :: args.every],
        )
    out = args.out or grid_path(terrain)
    save_grid(out, grid)
    rows, cols = grid.heights.shape
    print(
        f"{terrain}: wrote {out} ({rows} x {cols}, "
        f"{int(grid.heights.min())}..{int(grid.heights.max())} m, "
        f"{out.stat().st_size / 1e6:.1f} MB)"
    )
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="build the probe mission")
    gen.add_argument("--terrain", required=True)
    gen.add_argument("--margin-km", type=float, default=DEFAULT_MARGIN_KM)
    gen.add_argument("--step", type=float, default=DEFAULT_STEP_M)
    gen.add_argument("--out", type=Path)
    gen.set_defaults(func=_cmd_generate)

    app = sub.add_parser("apply", help="write the grid from the probe output")
    app.add_argument("heights", type=Path)
    app.add_argument("--out", type=Path)
    app.add_argument(
        "--every", type=int, default=1, help="keep every Nth point (a coarser grid)"
    )
    app.set_defaults(func=_cmd_apply)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
