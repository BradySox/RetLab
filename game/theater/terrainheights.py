"""DCS terrain height grids, sampled from ``land.getHeight`` in DCS itself.

A grid per terrain lives in ``resources/terrain_heights/<terrain>.npz`` and is
built by ``scripts/dcs_terrain_heights.py``. A terrain with no grid answers
None, and callers fall back to their own estimate. Design note:
docs/dev/design/retlab-dtc-cartridge-notes.md ("Terrain height grids").
"""

from __future__ import annotations

import math
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional, Union

import numpy as np

HEIGHTS_DIR = Path(__file__).resolve().parents[2] / "resources" / "terrain_heights"

#: Bumped when the .npz layout changes; a grid with another version is ignored.
#: 1: one ``heights`` array. 2: ``TILE``-square tiles, each stored as the
#: difference along y, so a fine grid loads only the tiles a mission touches.
FORMAT_VERSION = 2
TILE = 256


def _bilinear(
    value: Callable[[int, int], float],
    rows: int,
    cols: int,
    fi: float,
    fj: float,
) -> Optional[float]:
    if not (0.0 <= fi <= rows - 1 and 0.0 <= fj <= cols - 1):
        return None
    i = max(min(int(math.floor(fi)), rows - 2), 0)
    j = max(min(int(math.floor(fj)), cols - 2), 0)
    di = fi - i
    dj = fj - j
    i1 = min(i + 1, rows - 1)
    j1 = min(j + 1, cols - 1)
    top = value(i, j) * (1 - dj) + value(i, j1) * dj
    bottom = value(i1, j) * (1 - dj) + value(i1, j1) * dj
    return top * (1 - di) + bottom * di


@dataclass(frozen=True)
class HeightGrid:
    """Heights in metres AMSL on a regular grid of DCS x (north) and y (east).

    ``heights[i, j]`` is the ground at ``x0 + i * step``, ``y0 + j * step``.
    """

    x0: float
    y0: float
    step: float
    heights: np.ndarray[Any, Any]

    def height_at(self, x: float, y: float) -> Optional[float]:
        """Bilinear height at a point, or None outside the grid."""
        rows, cols = self.heights.shape
        h = self.heights
        return _bilinear(
            lambda i, j: float(h[i, j]),
            rows,
            cols,
            (x - self.x0) / self.step,
            (y - self.y0) / self.step,
        )


class TiledHeightGrid:
    """A version-2 grid read from disk, decoding each tile on first use."""

    def __init__(self, data: Any) -> None:
        self._data = data
        self.x0, self.y0, self.step = (float(v) for v in data["origin"])
        self.rows, self.cols = (int(v) for v in data["shape"])
        self._tiles: dict[tuple[int, int], np.ndarray[Any, Any]] = {}
        self._lock = threading.Lock()

    def _tile(self, ti: int, tj: int) -> np.ndarray[Any, Any]:
        with self._lock:
            tile = self._tiles.get((ti, tj))
            if tile is None:
                deltas = self._data[f"t{ti}_{tj}"]
                tile = np.cumsum(deltas, axis=1, dtype=np.int32)
                self._tiles[(ti, tj)] = tile
            return tile

    def _value(self, i: int, j: int) -> float:
        return float(self._tile(i // TILE, j // TILE)[i % TILE, j % TILE])

    def height_at(self, x: float, y: float) -> Optional[float]:
        return _bilinear(
            self._value,
            self.rows,
            self.cols,
            (x - self.x0) / self.step,
            (y - self.y0) / self.step,
        )


Grid = Union[HeightGrid, TiledHeightGrid]


def grid_path(terrain_name: str) -> Path:
    return HEIGHTS_DIR / f"{terrain_name.lower().replace(' ', '')}.npz"


def save_grid(path: Path, grid: HeightGrid) -> None:
    heights = grid.heights.astype(np.int16)
    rows, cols = heights.shape
    tiles: dict[str, np.ndarray[Any, Any]] = {}
    for ti in range(0, (rows + TILE - 1) // TILE):
        for tj in range(0, (cols + TILE - 1) // TILE):
            block = heights[ti * TILE : (ti + 1) * TILE, tj * TILE : (tj + 1) * TILE]
            tiles[f"t{ti}_{tj}"] = np.diff(block, axis=1, prepend=0).astype(np.int16)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as fh:
        np.savez_compressed(
            fh,
            version=np.array(FORMAT_VERSION),
            origin=np.array([grid.x0, grid.y0, grid.step], dtype=np.float64),
            shape=np.array([rows, cols], dtype=np.int64),
            **tiles,
        )


def read_grid(path: Path) -> Optional[Grid]:
    """The grid in a file. A version-2 file stays open to decode tiles lazily."""
    data = np.load(path, allow_pickle=False)
    version = int(data["version"])
    if version == FORMAT_VERSION:
        return TiledHeightGrid(data)
    try:
        if version != 1:
            return None
        x0, y0, step = (float(v) for v in data["origin"])
        return HeightGrid(x0, y0, step, np.array(data["heights"]))
    finally:
        data.close()


_cache: dict[str, Optional[Grid]] = {}
_cache_lock = threading.Lock()


def load_grid(terrain_name: str) -> Optional[Grid]:
    """The grid for a terrain, or None when none ships. Cached, misses too."""
    key = terrain_name.lower()
    with _cache_lock:
        if key not in _cache:
            path = grid_path(terrain_name)
            _cache[key] = read_grid(path) if path.exists() else None
        return _cache[key]


def terrain_height(terrain_name: str, x: float, y: float) -> Optional[float]:
    """DCS ground height at a point in metres AMSL, or None if unknown."""
    grid = load_grid(terrain_name)
    return grid.height_at(x, y) if grid is not None else None


def clear_cache() -> None:
    """Test hook."""
    with _cache_lock:
        _cache.clear()
