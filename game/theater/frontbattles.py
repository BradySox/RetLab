"""Where a front's ground battles stand along the shared border (§111).

A front takes the stretch of the border between the two sides' territory nearest
it, up to the Maximum frontline width measured along the border, and keeps the
drivable part. Each sector that stretch crosses holds one battle. Fronts that
share a border split it: a stretch of border belongs to the nearest front.
See docs/dev/design/retlab-sector-war-notes.md.
"""

from __future__ import annotations

import logging
import math
import threading
from collections import OrderedDict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

import numpy as np
import shapely
from shapely.geometry import LineString
from shapely.ops import substring

from game.theater.sectors import (
    NM,
    RED,
    Territory,
    _territory_key,
    sector_map_for,
    territory_for,
)

if TYPE_CHECKING:
    from game.theater import ConflictTheater, FrontLine

#: Spacing of the samples taken along the border.
SAMPLE_M = 0.25 * NM
#: A sector the border crosses for less than this holds no battle.
MIN_BATTLE_RUN_M = 1.0 * NM
#: How far along the border one battle's groups spread: half a sector.
MAX_BATTLE_SPREAD_M = 5.0 * NM
#: A front's battles cover this many times Maximum frontline width of border
#: (one width left most of a 240 mile Sinai border quiet, 2026-10-13).
BORDER_WIDTH_FACTOR = 2.0
#: How far across the border to look when working out which way is red.
SIDE_PROBE_M = 1.5 * NM


@dataclass(frozen=True)
class BattleSite:
    """One battle on the border: a point on it and the way blue attacks."""

    x: float
    y: float
    #: Blue's forward direction across the border here, in degrees.
    blue_forward: float
    #: How far along the border this battle's groups spread, in metres.
    width: float
    sector: str
    #: Distance along the front's stretch of border, for ordering.
    along: float
    #: The drivable run of border this battle stands on, inside its sector.
    trace: tuple[tuple[float, float], ...] = ()

    def point_along(self, offset: float) -> tuple[float, float]:
        """The border `offset` metres either side of the battle's centre.

        Follows the border rather than a straight line, so a group never lands
        off the drivable ground the battle was found on.
        """
        if len(self.trace) < 2:
            return self.x, self.y
        line = LineString(self.trace)
        middle = line.project(shapely.Point(self.x, self.y))
        point = line.interpolate(min(max(middle + offset, 0.0), line.length))
        return point.x, point.y

    @property
    def left_to_right(self) -> float:
        """Along the border, matching `FrontLineBounds.heading_from_left_to_right`."""
        return (self.blue_forward - 90.0) % 360.0


@dataclass(frozen=True)
class FrontBattles:
    #: The border from the first battle to the last, for drawing.
    line: tuple[tuple[float, float], ...]
    #: Ordered along the line.
    sites: tuple[BattleSite, ...]


NO_BATTLES = FrontBattles((), ())


def _shared_border(territory: Territory) -> list[LineString]:
    shared = territory.blue.boundary.intersection(territory.red.boundary)
    lines = [
        part
        for part in getattr(shared, "geoms", [shared])
        if part.geom_type in ("LineString", "MultiLineString") and not part.is_empty
    ]
    if not lines:
        return []
    merged = shapely.line_merge(shapely.union_all(lines))
    return [
        line
        for line in getattr(merged, "geoms", [merged])
        if line.geom_type == "LineString" and line.length > 0
    ]


def _stretch(line: LineString, centre: shapely.Point, width: float) -> LineString:
    """`width` of `line` centred on the point nearest `centre`, slid off an end."""
    middle = line.project(centre)
    half = width / 2
    start, end = middle - half, middle + half
    if start < 0:
        start, end = 0.0, min(line.length, end - start)
    if end > line.length:
        start, end = max(0.0, start - (end - line.length)), line.length
    return substring(line, start, end)


def _heading(dx: float, dy: float) -> float:
    """DCS heading of a step north by `dx` and east by `dy`."""
    return math.degrees(math.atan2(dy, dx)) % 360.0


def build_front_battles(
    theater: ConflictTheater, front: FrontLine, width: float
) -> FrontBattles:
    landmap = theater.landmap
    if landmap is None:
        return NO_BATTLES
    territory = territory_for(theater)
    sector_map = sector_map_for(theater)
    raster = sector_map.raster
    if territory.blue.is_empty or territory.red.is_empty or raster.rows == 0:
        return NO_BATTLES
    border = _shared_border(territory)
    centre = shapely.Point(front.position.x, front.position.y)
    if not border:
        return NO_BATTLES
    nearest = min(border, key=centre.distance)
    if nearest.distance(centre) > width:
        return NO_BATTLES
    stretch = _stretch(nearest, centre, width)
    if stretch.is_empty or stretch.length < MIN_BATTLE_RUN_M:
        return NO_BATTLES

    distances = np.arange(0.0, stretch.length, SAMPLE_M)
    points = shapely.line_interpolate_point(stretch, distances)
    xs = shapely.get_x(points)
    ys = shapely.get_y(points)

    drivable = landmap.inclusion_zone_only
    shapely.prepare(drivable)
    keep = shapely.contains_xy(drivable, xs, ys)
    own = np.hypot(xs - front.position.x, ys - front.position.y)
    for other in theater.conflicts():
        if other.name == front.name:
            continue
        keep &= own <= np.hypot(xs - other.position.x, ys - other.position.y)

    rows = ((xs - raster.origin_x) // raster.cell).astype(int)
    cols = ((ys - raster.origin_y) // raster.cell).astype(int)
    inside = (rows >= 0) & (rows < raster.rows) & (cols >= 0) & (cols < raster.cols)
    sector_ids = np.full(len(xs), -1, dtype=int)
    flat = rows[inside] * raster.cols + cols[inside]
    sector_ids[inside] = sector_map.labels[flat]
    keep &= sector_ids >= 0

    # The longest unbroken run of border inside each sector.
    runs: dict[int, tuple[int, int]] = {}
    index = 0
    while index < len(xs):
        if not keep[index]:
            index += 1
            continue
        sector_id = int(sector_ids[index])
        end = index
        while end + 1 < len(xs) and keep[end + 1] and sector_ids[end + 1] == sector_id:
            end += 1
        best = runs.get(sector_id)
        if best is None or end - index > best[1] - best[0]:
            runs[sector_id] = (index, end)
        index = end + 1

    sites = []
    for sector_id, (first, last) in runs.items():
        length = (last - first) * SAMPLE_M
        if length < MIN_BATTLE_RUN_M:
            continue
        middle = (first + last) // 2
        before = max(first, middle - 4)
        after = min(last, middle + 4)
        tangent = _heading(xs[after] - xs[before], ys[after] - ys[before])
        sites.append(
            BattleSite(
                x=float(xs[middle]),
                y=float(ys[middle]),
                blue_forward=_blue_forward(
                    territory,
                    raster,
                    float(xs[middle]),
                    float(ys[middle]),
                    tangent,
                    front.blue_forward_heading.degrees,
                ),
                width=min(length, MAX_BATTLE_SPREAD_M),
                sector=sector_map.sectors[sector_id].name,
                along=float(distances[middle]),
                trace=tuple(
                    (float(xs[i]), float(ys[i])) for i in range(first, last + 1, 2)
                )
                + ((float(xs[last]), float(ys[last])),),
            )
        )
    if not sites:
        return NO_BATTLES
    sites.sort(key=lambda site: site.along)
    fought = substring(
        stretch,
        max(0.0, sites[0].along - sites[0].width / 2),
        min(stretch.length, sites[-1].along + sites[-1].width / 2),
    )
    return FrontBattles(tuple(fought.coords), tuple(sites))


def _blue_forward(
    territory: Territory,
    raster: Any,
    x: float,
    y: float,
    tangent: float,
    fallback: float,
) -> float:
    """The normal to the border that points into red's ground."""
    candidates = ((tangent + 90.0) % 360.0, (tangent - 90.0) % 360.0)
    red_side = []
    for heading in candidates:
        probe_x = x + math.cos(math.radians(heading)) * SIDE_PROBE_M
        probe_y = y + math.sin(math.radians(heading)) * SIDE_PROBE_M
        index = raster.index_at(probe_x, probe_y)
        red_side.append(index is not None and territory.labels[index] == RED)
    if red_side[0] != red_side[1]:
        return candidates[0] if red_side[0] else candidates[1]

    def off(heading: float) -> float:
        return abs((heading - fallback + 180.0) % 360.0 - 180.0)

    return min(candidates, key=off)


_cache_lock = threading.Lock()
_cache: "OrderedDict[tuple[Any, ...], FrontBattles]" = OrderedDict()
_CACHE_SIZE = 16


def front_battles(theater: ConflictTheater, front: FrontLine) -> FrontBattles:
    """The front's battles, kept while no base changes hands and no front moves."""
    width = battle_stretch_m(front)
    key = (_territory_key(theater), front.name, width)
    with _cache_lock:
        found = _cache.get(key)
    if found is not None:
        return found
    found = build_front_battles(theater, front, width)
    with _cache_lock:
        _cache[key] = found
        _cache.move_to_end(key)
        while len(_cache) > _CACHE_SIZE:
            _cache.popitem(last=False)
    return found


def battle_stretch_m(front: FrontLine) -> float:
    """Length of border a front's battles may cover, in metres."""
    settings = front.coalition.game.settings
    return float(settings.max_frontline_width * 1000 * BORDER_WIDTH_FACTOR)


def battles_for(theater: ConflictTheater, front: FrontLine) -> Optional[FrontBattles]:
    """The front's battles when the setting is on and there are any, else None."""
    if not front.coalition.game.settings.front_line_battles_along_border:
        return None
    try:
        battles = front_battles(theater, front)
    except Exception:
        logging.exception("Battles along the border failed for %s", front.name)
        return None
    return battles if battles.sites else None
