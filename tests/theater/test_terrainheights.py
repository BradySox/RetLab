from pathlib import Path

import numpy as np
import pytest

from game.theater import terrainheights
from game.theater.terrainheights import TILE, HeightGrid, read_grid, save_grid
from scripts.dcs_terrain_heights import grid_extent, parse_probe_output


def _grid() -> HeightGrid:
    # Rows run north (x), columns east (y).
    return HeightGrid(
        x0=1000.0,
        y0=-2000.0,
        step=1000.0,
        heights=np.array([[0, 100, 200], [300, 400, 500]], dtype=np.int16),
    )


def test_height_is_bilinear_between_samples() -> None:
    grid = _grid()
    assert grid.height_at(1000.0, -2000.0) == 0.0
    assert grid.height_at(2000.0, 0.0) == 500.0
    assert grid.height_at(1500.0, -1500.0) == pytest.approx(200.0)
    assert grid.height_at(1250.0, -500.0) == pytest.approx(225.0)


def test_outside_the_grid_is_unknown() -> None:
    grid = _grid()
    assert grid.height_at(999.0, -2000.0) is None
    assert grid.height_at(1000.0, 1.0) is None


def test_a_grid_round_trips_through_the_npz(tmp_path: Path) -> None:
    path = tmp_path / "caucasus.npz"
    save_grid(path, _grid())
    loaded = read_grid(path)
    assert loaded is not None
    assert (loaded.x0, loaded.y0, loaded.step) == (1000.0, -2000.0, 1000.0)
    assert loaded.height_at(1250.0, -500.0) == pytest.approx(225.0)
    assert loaded.height_at(999.0, -2000.0) is None


def test_a_tiled_grid_reads_the_same_across_tile_edges(tmp_path: Path) -> None:
    rng = np.random.default_rng(1)
    rows, cols = TILE * 2 + 7, TILE + 3
    heights = rng.integers(-400, 5600, size=(rows, cols)).astype(np.int16)
    grid = HeightGrid(0.0, 0.0, 100.0, heights)
    path = tmp_path / "syria.npz"
    save_grid(path, grid)
    loaded = read_grid(path)
    assert loaded is not None
    for x, y in [
        (0.0, 0.0),
        (25550.0, 25550.0),
        (25600.0, 12345.0),
        (51250.0, 25800.0),
    ]:
        assert loaded.height_at(x, y) == pytest.approx(grid.height_at(x, y))


def test_a_version_1_grid_still_reads(tmp_path: Path) -> None:
    path = tmp_path / "caucasus.npz"
    np.savez_compressed(
        path,
        version=np.array(1),
        origin=np.array([1000.0, -2000.0, 1000.0]),
        heights=_grid().heights,
    )
    loaded = read_grid(path)
    assert loaded is not None
    assert loaded.height_at(2000.0, 0.0) == 500.0


def test_a_terrain_without_a_grid_answers_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(terrainheights, "HEIGHTS_DIR", tmp_path)
    terrainheights.clear_cache()
    try:
        assert terrainheights.terrain_height("Nowhere", 0.0, 0.0) is None
        save_grid(tmp_path / "syria.npz", _grid())
        terrainheights.clear_cache()
        assert terrainheights.terrain_height("Syria", 2000.0, 0.0) == 500.0
    finally:
        terrainheights.clear_cache()


def test_the_probe_output_parses_into_a_grid(tmp_path: Path) -> None:
    path = tmp_path / "heights.txt"
    path.write_text(
        "RETLAB-HEIGHTS 1 Caucasus 1000.0 -2000.0 1000.0 2 3\n"
        "0 100 200\n300 400 500\nEND\n"
    )
    terrain, grid = parse_probe_output(path)
    assert terrain == "Caucasus"
    assert grid.heights.tolist() == _grid().heights.tolist()


def test_an_unfinished_probe_run_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "heights.txt"
    path.write_text("RETLAB-HEIGHTS 1 Caucasus 1000.0 -2000.0 1000.0 2 3\n0 1 2\n")
    with pytest.raises(ValueError, match="incomplete"):
        parse_probe_output(path)


def test_the_extent_covers_every_field_plus_the_margin() -> None:
    x0, y0, nx, ny = grid_extent([(0.0, 0.0), (10500.0, 3000.0)], 2000.0, 1000.0)
    assert (x0, y0) == (-2000.0, -2000.0)
    assert x0 + (nx - 1) * 1000.0 >= 12500.0
    assert y0 + (ny - 1) * 1000.0 >= 5000.0
