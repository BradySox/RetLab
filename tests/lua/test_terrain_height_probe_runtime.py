"""Headless run of the terrain height probe against the parser that reads it.

The probe only ever runs in the probe mission, never a campaign; this pins that
its output is exactly what ``scripts/dcs_terrain_heights.py apply`` accepts.
"""

from __future__ import annotations

from pathlib import Path

from scripts.dcs_terrain_heights import parse_probe_output
from tests.lua.harness import DcsPluginHarness

PROBE = "resources/plugins/base/dcs_terrain_height_probe.lua"


def test_the_probe_writes_a_grid_the_apply_step_reads(tmp_path: Path) -> None:
    harness = DcsPluginHarness()
    lua = harness.lua
    lua.execute(
        "land.getHeight = function(p) return p.x / 10 + p.y / 100 end\n"
        "RETLAB_HEIGHT_GRID = { terrain = 'Caucasus', x0 = -1000.0, y0 = 2000.0,"
        " step = 500.0, nx = 25, ny = 4 }"
    )
    # DCS always has Saved Games\DCS\Logs; Windows needs it to open the file.
    (tmp_path / "Logs").mkdir()
    writedir = str(tmp_path) + "/"
    lua.globals().lfs = harness.to_lua({})
    lua.execute(f"lfs.writedir = function() return {writedir!r} end")
    harness.load_plugin_script(PROBE)
    harness.advance_to(60.0)

    terrain, grid = parse_probe_output(
        tmp_path / "Logs\\retlab_terrain_heights_Caucasus.txt"
    )
    assert terrain == "Caucasus"
    assert grid.heights.shape == (25, 4)
    assert grid.height_at(-1000.0, 2000.0) == -80.0
    assert grid.height_at(11000.0, 3500.0) == 1135.0


def test_a_sanitized_mission_writes_nothing(tmp_path: Path) -> None:
    harness = DcsPluginHarness()
    harness.lua.execute(
        "RETLAB_HEIGHT_GRID = { terrain = 'Caucasus', x0 = 0, y0 = 0,"
        " step = 500.0, nx = 2, ny = 2 }\nlfs = nil"
    )
    harness.load_plugin_script(PROBE)
    harness.advance_to(60.0)
    assert not any(tmp_path.iterdir())
