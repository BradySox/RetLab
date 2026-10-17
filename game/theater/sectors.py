"""Sectors and territory (§111).

The war region is cut into named sectors about 10 NM across. Each sector grows
from a seed over a 1 NM grid by driving cost, so its edges follow ridges, rivers
and coasts instead of cutting straight across them. Every land base seeds its own
sector.

Territory is worked out the same way from each side's bases and its side of
every front, so the border between the two sides runs through each front line.
Nothing here changes the ground war; step 1 of the sector war only draws it.

Design note: docs/dev/design/retlab-sector-war-notes.md
"""

from __future__ import annotations

import heapq
import logging
import math
import random
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Iterable, Optional, Sequence

import numpy as np
import numpy.typing as npt
import shapely
from shapely.geometry import LineString, MultiPolygon, Polygon, box
from shapely.geometry.base import BaseGeometry

from game.theater.frontline import MAX_TERRAIN_DIFFICULTY
from game.theater.landmap import _PREPARED_LOCK

if TYPE_CHECKING:
    from game.theater import ConflictTheater, ControlPoint, FrontLine

NM = 1852.0
CELL_M = 1.0 * NM
SECTOR_SPACING_M = 10.0 * NM
#: Land this far beyond the outermost land bases is part of the war even where
#: no country border covers it. A country holding a base is in whole.
WAR_MARGIN_M = 60.0 * NM
#: A grid seed this close to a base's seed would leave a sliver; the base's
#: sector takes the ground instead.
BASE_SEED_CLEARANCE_M = 5.0 * NM
#: How far a grid seed may wander from its square's centre, as a share of the
#: spacing. A plain lattice on open ground grows plain squares.
SEED_JITTER = 0.35
#: Each side's ground starts this far behind its side of a front line, so the
#: border is pinned to the line rather than drifting a cell either way.
FRONT_SOURCE_OFFSET_M = 1.2 * NM

#: Coast detail kept in drawn shapes. A Jutland outline at full detail was
#: 2,490 corners in one F10 drawing.
COAST_TOLERANCE_M = 250.0
#: Islets and slivers smaller than this are not drawn.
MIN_DRAWN_AREA_M2 = 2 * CELL_M * CELL_M

BLUE = 0
RED = 1

PHONETIC = (
    "ALPHA",
    "BRAVO",
    "CHARLIE",
    "DELTA",
    "ECHO",
    "FOXTROT",
    "GOLF",
    "HOTEL",
    "INDIA",
    "JULIETT",
    "KILO",
    "LIMA",
    "MIKE",
    "NOVEMBER",
    "OSCAR",
    "PAPA",
    "QUEBEC",
    "ROMEO",
    "SIERRA",
    "TANGO",
    "UNIFORM",
    "VICTOR",
    "WHISKEY",
    "XRAY",
    "YANKEE",
    "ZULU",
)

_SQRT2 = math.sqrt(2.0)
_NEIGHBOURS = (
    (-1, 0, 1.0),
    (1, 0, 1.0),
    (0, -1, 1.0),
    (0, 1, 1.0),
    (-1, -1, _SQRT2),
    (-1, 1, _SQRT2),
    (1, -1, _SQRT2),
    (1, 1, _SQRT2),
)


@dataclass(frozen=True)
class TerrainRaster:
    """A grid over the war region. Rows run north along DCS x, columns east."""

    origin_x: float
    origin_y: float
    cell: float
    rows: int
    cols: int
    #: Cost of crossing each cell; 0 where there is no land to hold.
    cost: npt.NDArray[Any] = field(repr=False)
    #: The land the grid stands for, used to clip drawn shapes to the coast.
    land: BaseGeometry = field(repr=False)

    def index_at(self, x: float, y: float) -> Optional[int]:
        row = int((x - self.origin_x) // self.cell)
        col = int((y - self.origin_y) // self.cell)
        if not (0 <= row < self.rows and 0 <= col < self.cols):
            return None
        return row * self.cols + col

    def land_index_near(
        self, x: float, y: float, reach_cells: int = 3
    ) -> Optional[int]:
        """The land cell holding (x, y), else the nearest within reach."""
        index = self.index_at(x, y)
        if index is not None and self.cost[index] > 0:
            return index
        row = int((x - self.origin_x) // self.cell)
        col = int((y - self.origin_y) // self.cell)
        best: Optional[int] = None
        best_d = math.inf
        for dr in range(-reach_cells, reach_cells + 1):
            for dc in range(-reach_cells, reach_cells + 1):
                r, c = row + dr, col + dc
                if not (0 <= r < self.rows and 0 <= c < self.cols):
                    continue
                candidate = r * self.cols + c
                if self.cost[candidate] <= 0:
                    continue
                d = dr * dr + dc * dc
                if d < best_d:
                    best, best_d = candidate, d
        return best

    def center(self, index: int) -> tuple[float, float]:
        row, col = divmod(index, self.cols)
        return (
            self.origin_x + (row + 0.5) * self.cell,
            self.origin_y + (col + 0.5) * self.cell,
        )


def _land_shape(theater: ConflictTheater) -> BaseGeometry:
    landmap = theater.landmap
    if landmap is None:
        return Polygon()
    land: BaseGeometry = landmap.inclusion_zones.difference(landmap.sea_zones)
    _, neutral = _countries(theater)
    if not neutral.is_empty:
        land = land.difference(neutral)
    return land


def _countries(theater: ConflictTheater) -> tuple[BaseGeometry, BaseGeometry]:
    """(at war, neutral): the countries holding a base, and those holding none."""
    from game.theater.neutralborder import NEUTRAL
    from game.theater.terrainborders import load_terrain_borders

    at_war = []
    neutral = []
    for zone in getattr(theater, "neutral_border_zones", None) or []:
        if len(zone.border) < 3:
            continue
        try:
            shape = Polygon(zone.border).buffer(0)
            if zone.posture_in(theater) == NEUTRAL:
                neutral.append(shape)
            else:
                at_war.append(shape)
        except Exception:
            continue
    # A campaign that authors its own borders lists its neighbours, not the
    # country the war is in (COIN has no Afghanistan zone); the map's file does.
    held = [
        shapely.Point(cp.position.x, cp.position.y)
        for cp in land_control_points(theater)
        if not cp.captured.is_neutral
    ]
    for entry in load_terrain_borders(theater.terrain.name):
        try:
            shape = Polygon(entry["border"]).buffer(0)
        except Exception:
            continue
        if any(shape.contains(point) for point in held):
            at_war.append(shape)
    return (
        shapely.union_all(at_war) if at_war else Polygon(),
        shapely.union_all(neutral) if neutral else Polygon(),
    )


def _war_region(
    theater: ConflictTheater, bases: Sequence[ControlPoint]
) -> BaseGeometry:
    """Every country holding a base, plus the margin around the bases.

    The margin alone drew a plain rectangle on open ground: Iraq, 2026-10-12.
    """
    xs = [cp.position.x for cp in bases]
    ys = [cp.position.y for cp in bases]
    near = box(
        min(xs) - WAR_MARGIN_M,
        min(ys) - WAR_MARGIN_M,
        max(xs) + WAR_MARGIN_M,
        max(ys) + WAR_MARGIN_M,
    )
    at_war, _ = _countries(theater)
    return near if at_war.is_empty else near.union(at_war)


def land_control_points(theater: ConflictTheater) -> list[ControlPoint]:
    """Bases that stand on the ground: no ships, no off-map spawns."""
    return [
        cp
        for cp in theater.controlpoints
        if not cp.is_fleet and not cp.is_offmap and not cp.is_carrier
    ]


def build_raster(theater: ConflictTheater, cell: float = CELL_M) -> TerrainRaster:
    landmap = theater.landmap
    bases = land_control_points(theater)
    if landmap is None or not bases:
        return TerrainRaster(0, 0, cell, 0, 0, np.zeros(0, np.float32), Polygon())
    region = _war_region(theater, bases)
    region_bounds = region.bounds
    land_bounds = landmap.inclusion_zones.bounds
    min_x = max(region_bounds[0], land_bounds[0])
    max_x = min(region_bounds[2], land_bounds[2])
    min_y = max(region_bounds[1], land_bounds[1])
    max_y = min(region_bounds[3], land_bounds[3])
    rows = max(1, int(math.ceil((max_x - min_x) / cell)))
    cols = max(1, int(math.ceil((max_y - min_y) / cell)))
    land = (
        _land_shape(theater)
        .intersection(region)
        .intersection(box(min_x, min_y, min_x + rows * cell, min_y + cols * cell))
        .simplify(COAST_TOLERANCE_M)
    )

    centers_x = min_x + (np.arange(rows) + 0.5) * cell
    centers_y = min_y + (np.arange(cols) + 0.5) * cell
    grid_x, grid_y = np.meshgrid(centers_x, centers_y, indexing="ij")
    flat_x = grid_x.ravel()
    flat_y = grid_y.ravel()
    shapely.prepare(land)
    on_land = shapely.contains_xy(land, flat_x, flat_y)
    with _PREPARED_LOCK:
        rough = shapely.contains_xy(landmap.exclusion_zones, flat_x, flat_y)
    cost = np.where(on_land, np.where(rough, MAX_TERRAIN_DIFFICULTY, 1.0), 0.0)
    return TerrainRaster(min_x, min_y, cell, rows, cols, cost.astype(np.float32), land)


def grow(raster: TerrainRaster, sources: Iterable[tuple[int, int]]) -> npt.NDArray[Any]:
    """Give every land cell the label of the source that can drive to it first.

    A multi-source shortest path over the grid; stepping between two cells costs
    the distance times the mean of their crossing costs. Unreached cells are -1.
    """
    n = raster.rows * raster.cols
    cost = raster.cost.tolist()
    cols = raster.cols
    rows = raster.rows
    dist = [math.inf] * n
    label = [-1] * n
    heap: list[tuple[float, int, int]] = []
    for index, lab in sources:
        if 0 <= index < n and cost[index] > 0 and dist[index] > 0:
            dist[index] = 0.0
            label[index] = lab
            heap.append((0.0, index, lab))
    heapq.heapify(heap)
    pop = heapq.heappop
    push = heapq.heappush
    while heap:
        d, index, lab = pop(heap)
        if d > dist[index]:
            continue
        row, col = divmod(index, cols)
        here = cost[index]
        for dr, dc, length in _NEIGHBOURS:
            r = row + dr
            c = col + dc
            if r < 0 or r >= rows or c < 0 or c >= cols:
                continue
            other = r * cols + c
            there = cost[other]
            if there <= 0:
                continue
            nd = d + length * (here + there) * 0.5
            if nd < dist[other]:
                dist[other] = nd
                label[other] = lab
                push(heap, (nd, other, lab))
    return np.array(label, dtype=np.int32)


def _cells_to_shape(raster: TerrainRaster, mask: npt.NDArray[Any]) -> BaseGeometry:
    """The union of the masked cells, built from one box per run in each row."""
    boxes = []
    grid = mask.reshape(raster.rows, raster.cols)
    for row in range(raster.rows):
        line = grid[row]
        if not line.any():
            continue
        padded = np.concatenate(([False], line, [False]))
        edges = np.flatnonzero(padded[1:] != padded[:-1])
        x0 = raster.origin_x + row * raster.cell
        for start, stop in zip(edges[::2], edges[1::2]):
            boxes.append(
                box(
                    x0,
                    raster.origin_y + start * raster.cell,
                    x0 + raster.cell,
                    raster.origin_y + stop * raster.cell,
                )
            )
    if not boxes:
        return Polygon()
    return shapely.union_all(boxes)


def _smooth(shape: BaseGeometry, cell: float) -> BaseGeometry:
    """Round off the grid's stair steps without moving the edge more than a cell."""
    if shape.is_empty:
        return shape
    radius = cell * 0.6
    smoothed = shape.buffer(radius, quad_segs=2).buffer(-2 * radius, quad_segs=2)
    smoothed = smoothed.buffer(radius, quad_segs=2)
    return smoothed.simplify(cell * 0.25)


def _polygons(shape: BaseGeometry) -> list[Polygon]:
    if shape.is_empty:
        return []
    if isinstance(shape, Polygon):
        return [shape]
    if isinstance(shape, MultiPolygon):
        return list(shape.geoms)
    return [g for g in getattr(shape, "geoms", []) if isinstance(g, Polygon)]


def _row_name(index: int) -> str:
    word = PHONETIC[index % len(PHONETIC)]
    lap = index // len(PHONETIC)
    return word if lap == 0 else f"{word}{lap + 1}"


@dataclass(frozen=True)
class Sector:
    id: int
    #: Phonetic row from the north and column from the west, like WHISKEY-14.
    name: str
    seed: tuple[float, float]
    #: The base this sector was grown around, if any.
    control_point_id: Optional[Any] = None


class SectorMap:
    """The sectors of one campaign's war region. Fixed for the whole campaign."""

    def __init__(
        self,
        raster: TerrainRaster,
        labels: npt.NDArray[Any],
        sectors: Sequence[Sector],
    ) -> None:
        self.raster = raster
        self.labels = labels
        self.sectors = tuple(sectors)
        self._shapes: dict[int, BaseGeometry] = {}
        self._edges: Optional[BaseGeometry] = None
        self._lock = threading.Lock()

    @property
    def edges(self) -> BaseGeometry:
        """Every edge between two sectors; see `sector_edges`."""
        with self._lock:
            if self._edges is None:
                self._edges = sector_edges(self)
            return self._edges

    def sector_at(self, x: float, y: float) -> Optional[Sector]:
        # A base on the water's edge can sit in a sea cell; take the land beside it.
        index = self.raster.land_index_near(x, y)
        if index is None:
            return None
        sector_id = int(self.labels[index])
        if sector_id < 0:
            return None
        return self.sectors[sector_id]

    def shape(self, sector_id: int) -> BaseGeometry:
        """The sector's outline, smoothed and clipped to the coast."""
        with self._lock:
            cached = self._shapes.get(sector_id)
            if cached is None:
                cells = _cells_to_shape(self.raster, self.labels == sector_id)
                cached = _smooth(cells, self.raster.cell)
                if not cached.is_empty:
                    cached = cached.intersection(self.raster.land)
                self._shapes[sector_id] = cached
            return cached

    def owners(self, territory: "Territory") -> dict[int, Optional[int]]:
        """Each sector's side: whoever holds most of its cells."""
        result: dict[int, Optional[int]] = {}
        sector_ids = self.labels
        sides = territory.labels
        for sector in self.sectors:
            inside = sides[sector_ids == sector.id]
            blue = int(np.count_nonzero(inside == BLUE))
            red = int(np.count_nonzero(inside == RED))
            if blue == 0 and red == 0:
                result[sector.id] = None
            else:
                result[sector.id] = BLUE if blue >= red else RED
        return result


def build_sector_map(theater: ConflictTheater) -> SectorMap:
    raster = build_raster(theater)
    if raster.rows == 0:
        return SectorMap(raster, np.zeros(0, np.int32), ())
    top_x = raster.origin_x + raster.rows * raster.cell

    def square(x: float, y: float) -> tuple[int, int]:
        return (
            int((top_x - x) // SECTOR_SPACING_M),
            int((y - raster.origin_y) // SECTOR_SPACING_M),
        )

    seeds: list[tuple[int, tuple[float, float], Optional[Any]]] = []
    taken: set[tuple[int, int]] = set()
    base_seeds: list[tuple[float, float]] = []
    for cp in sorted(land_control_points(theater), key=lambda cp: cp.name):
        index = raster.land_index_near(cp.position.x, cp.position.y)
        if index is None:
            continue
        seeds.append((index, (cp.position.x, cp.position.y), cp.id))
        taken.add(square(cp.position.x, cp.position.y))
        base_seeds.append((cp.position.x, cp.position.y))

    clearance = BASE_SEED_CLEARANCE_M**2
    rows = int(math.ceil(raster.rows * raster.cell / SECTOR_SPACING_M))
    cols = int(math.ceil(raster.cols * raster.cell / SECTOR_SPACING_M))
    reach = int(SECTOR_SPACING_M / raster.cell / 3)
    for row in range(rows):
        for col in range(cols):
            if (row, col) in taken:
                continue
            # Seeded by the square, so a campaign's sectors never change.
            rng = random.Random(row * 100_003 + col)
            spread = SEED_JITTER * SECTOR_SPACING_M
            x = top_x - (row + 0.5) * SECTOR_SPACING_M + rng.uniform(-spread, spread)
            y = (
                raster.origin_y
                + (col + 0.5) * SECTOR_SPACING_M
                + rng.uniform(-spread, spread)
            )
            if any((x - bx) ** 2 + (y - by) ** 2 < clearance for bx, by in base_seeds):
                continue
            index = raster.land_index_near(x, y, reach)
            if index is None:
                continue
            seeds.append((index, raster.center(index), None))

    labels = grow(raster, ((index, i) for i, (index, _, _) in enumerate(seeds)))

    sectors: list[Sector] = []
    used: dict[str, int] = {}
    for i, (_, position, cp_id) in enumerate(seeds):
        row, col = square(*position)
        name = f"{_row_name(row)}-{col + 1}"
        repeat = used.get(name, 0)
        used[name] = repeat + 1
        if repeat:
            name = f"{name}{chr(ord('A') + repeat)}"
        sectors.append(Sector(i, name, position, cp_id))
    return SectorMap(raster, labels, sectors)


@dataclass(frozen=True)
class Territory:
    """Who holds each cell of the war region, and the drawn shape of each side."""

    labels: npt.NDArray[Any] = field(repr=False)
    blue: BaseGeometry = field(repr=False)
    red: BaseGeometry = field(repr=False)

    def polygons(self, side: int) -> list[Polygon]:
        shapes = _polygons(self.blue if side == BLUE else self.red)
        return [shape for shape in shapes if shape.area >= MIN_DRAWN_AREA_M2]


def _route_progress(front: FrontLine) -> tuple[LineString, float]:
    route = LineString([(p.x, p.y) for p in front.points])
    return route, route.project(shapely.Point(front.position.x, front.position.y))


def _front_sources(
    raster: TerrainRaster, theater: ConflictTheater, front: FrontLine
) -> list[tuple[int, int]]:
    from game.missiongenerator.frontlineconflictdescription import (
        FrontLineConflictDescription,
    )

    sources: list[tuple[int, int]] = []

    def add(x: float, y: float, side: int) -> None:
        index = raster.land_index_near(x, y, 1)
        if index is not None:
            sources.append((index, side))

    route, progress = _route_progress(front)
    step = raster.cell * 0.5
    distance = 0.0
    while distance <= route.length:
        if abs(distance - progress) > FRONT_SOURCE_OFFSET_M:
            point = route.interpolate(distance)
            add(point.x, point.y, BLUE if distance < progress else RED)
        distance += step

    try:
        bounds = FrontLineConflictDescription.frontline_bounds(front, theater)
    except Exception:
        return sources
    forward = bounds.advance_heading.degrees
    trace = bounds.polyline
    for a, b in zip(trace, trace[1:]):
        length = a.distance_to_point(b)
        count = max(1, int(length // step))
        for i in range(count + 1):
            point = a + (b - a) * (i / count)
            ahead = point.point_from_heading(forward, FRONT_SOURCE_OFFSET_M)
            behind = point.point_from_heading(forward + 180, FRONT_SOURCE_OFFSET_M)
            add(behind.x, behind.y, BLUE)
            add(ahead.x, ahead.y, RED)
    return sources


def build_territory(theater: ConflictTheater, sector_map: SectorMap) -> Territory:
    raster = sector_map.raster
    if raster.rows == 0:
        return Territory(np.zeros(0, np.int32), Polygon(), Polygon())
    sources: list[tuple[int, int]] = []
    for front in theater.conflicts():
        sources.extend(_front_sources(raster, theater, front))
    for cp in land_control_points(theater):
        if cp.captured.is_neutral:
            continue
        index = raster.land_index_near(cp.position.x, cp.position.y)
        if index is not None:
            sources.append((index, BLUE if cp.captured.is_blue else RED))
    return territory_from_labels(raster, grow(raster, sources))


def territory_from_labels(raster: TerrainRaster, labels: npt.NDArray[Any]) -> Territory:
    """Each side's drawn shape from who holds each cell."""
    held = _smooth(_cells_to_shape(raster, labels >= 0), raster.cell)
    held = held.intersection(raster.land)
    blue = _smooth(_cells_to_shape(raster, labels == BLUE), raster.cell)
    blue = blue.intersection(held)
    red = held.difference(blue)
    # Simplified as one coverage, so the two sides keep a single shared edge.
    blue, red = shapely.coverage_simplify(
        [_polygonal(blue), _polygonal(red)], COAST_TOLERANCE_M
    )
    return Territory(labels, blue, red)


def _polygonal(shape: BaseGeometry) -> BaseGeometry:
    polygons = _polygons(shape)
    return MultiPolygon(polygons) if polygons else MultiPolygon()


_cache_lock = threading.Lock()
_sector_maps: "OrderedDict[tuple[Any, ...], SectorMap]" = OrderedDict()
_territories: "OrderedDict[tuple[Any, ...], Territory]" = OrderedDict()
_CACHE_SIZE = 3


def _sector_key(theater: ConflictTheater) -> tuple[Any, ...]:
    bases = tuple(
        sorted(
            (cp.name, str(cp.id), round(cp.position.x), round(cp.position.y))
            for cp in land_control_points(theater)
        )
    )
    # The ids too: two games of one campaign share names but not base ids.
    return (theater.terrain.name, bases)


def _war(theater: ConflictTheater) -> Optional[Any]:
    from game.theater.sectorwar import war_for

    return war_for(theater)


def _territory_key(theater: ConflictTheater) -> tuple[Any, ...]:
    war = _war(theater)
    if war is not None:
        return (_sector_key(theater), "war", war.owner_key())
    owners = tuple(
        sorted((cp.name, cp.captured.value) for cp in land_control_points(theater))
    )
    fronts = tuple(
        sorted(
            (front.name, round(front.position.x), round(front.position.y))
            for front in theater.conflicts()
        )
    )
    return (_sector_key(theater), owners, fronts)


def _remember(cache: "OrderedDict[Any, Any]", key: Any, value: Any) -> None:
    cache[key] = value
    cache.move_to_end(key)
    while len(cache) > _CACHE_SIZE:
        cache.popitem(last=False)


def sector_map_for(theater: ConflictTheater) -> SectorMap:
    """The theater's sectors, built once and kept while the bases stay put."""
    key = _sector_key(theater)
    with _cache_lock:
        found = _sector_maps.get(key)
        if found is None:
            started = time.perf_counter()
            found = build_sector_map(theater)
            raster = found.raster
            logging.info(
                "Sectors built: %d sectors on a %dx%d grid in %.1f s",
                len(found.sectors),
                raster.rows,
                raster.cols,
                time.perf_counter() - started,
            )
            _remember(_sector_maps, key, found)
        return found


def territory_for(theater: ConflictTheater) -> Territory:
    """Each side's ground right now, rebuilt only when a base or a front moves."""
    key = _territory_key(theater)
    sector_map = sector_map_for(theater)
    with _cache_lock:
        found = _territories.get(key)
        if found is None:
            started = time.perf_counter()
            war = _war(theater)
            if war is not None:
                found = war.territory(sector_map)
            else:
                found = build_territory(theater, sector_map)
            logging.info(
                "Territory built: blue %d, red %d shapes in %.1f s",
                len(found.polygons(BLUE)),
                len(found.polygons(RED)),
                time.perf_counter() - started,
            )
            _remember(_territories, key, found)
        return found


def hole_free_pieces(polygon: Polygon) -> list[Polygon]:
    """Cut a polygon with holes into pieces without any.

    A DCS drawing has one ring, so a pocket of the other side inside a territory
    is drawn by splitting the territory through the pocket.
    """
    from shapely.ops import split

    if not polygon.interiors:
        return [polygon]
    hole = polygon.interiors[0]
    x = hole.centroid.x
    min_x, min_y, max_x, max_y = polygon.bounds
    cutter = LineString([(x, min_y - 1), (x, max_y + 1)])
    parts = [
        part
        for part in split(polygon, cutter).geoms
        if isinstance(part, Polygon) and not part.is_empty
    ]
    if len(parts) < 2:
        return [Polygon(polygon.exterior)]
    pieces: list[Polygon] = []
    for part in parts:
        pieces.extend(hole_free_pieces(part))
    return pieces


def sector_edges(sector_map: SectorMap) -> BaseGeometry:
    """Every edge between two neighbouring sectors, as merged, smoothed lines.

    Built from the grid in one pass: a sector's own outline is a polygon
    operation per sector, which is too slow to run for a thousand of them on
    every map refresh.
    """
    raster = sector_map.raster
    if raster.rows == 0:
        return shapely.MultiLineString()
    grid = sector_map.labels.reshape(raster.rows, raster.cols)
    cell = raster.cell
    segments: list[tuple[tuple[float, float], tuple[float, float]]] = []
    # Between rows r and r+1: a line of constant x.
    rows, cols = np.nonzero(
        (grid[:-1, :] != grid[1:, :]) & (grid[:-1, :] >= 0) & (grid[1:, :] >= 0)
    )
    for r, c in zip(rows.tolist(), cols.tolist()):
        x = raster.origin_x + (r + 1) * cell
        y = raster.origin_y + c * cell
        segments.append(((x, y), (x, y + cell)))
    # Between columns c and c+1: a line of constant y.
    rows, cols = np.nonzero(
        (grid[:, :-1] != grid[:, 1:]) & (grid[:, :-1] >= 0) & (grid[:, 1:] >= 0)
    )
    for r, c in zip(rows.tolist(), cols.tolist()):
        x = raster.origin_x + r * cell
        y = raster.origin_y + (c + 1) * cell
        segments.append(((x, y), (x + cell, y)))
    if not segments:
        return shapely.MultiLineString()
    merged = shapely.line_merge(shapely.MultiLineString(segments))
    return merged.simplify(cell * 0.6)
