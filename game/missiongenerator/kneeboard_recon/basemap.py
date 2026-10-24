# game/missiongenerator/kneeboard_recon/basemap.py
"""Basemap façade for recon kneeboard pages.

Primary path: Esri World Imagery tile compositor (``tile_compositor.render_tiles``)
matching the layer the planner UI already uses.

Fallback path (network unreachable, ToS-blocked, or terrain without a
pyproj projection): the legacy GIF-crop / tan-landmap renderer is invoked
and an OFFLINE banner is stamped across the top of the result so the user
notices the degraded quality before printing.
"""

from __future__ import annotations

import logging
import pickle
import threading
from collections import OrderedDict
from pathlib import Path
from datetime import date
from typing import Any, Iterable, Optional, TypeVar

_VT = TypeVar("_VT")

from PIL import Image, ImageDraw, ImageEnhance, ImageFont
from dcs.mapping import Point
from dcs.terrain.terrain import Terrain

from . import airport_imagery, gif_georef
from ._fonts import PilFont
from .extent import MapExtent
from .tile_compositor import (
    FAILURE_TILE_CAP,
    last_failure_reason,
    render_tiles,
)

logger = logging.getLogger(__name__)

# Public, used by the legacy fallback path. The tile compositor handles
# resolution natively and does not consult this constant.
DETAIL_THRESHOLD_M: float = 5_000.0

# Legacy renderer palette (kept from the original implementation).
_LAND_TAN = (224, 213, 191)
_LAND_TAN_DARK = (188, 173, 142)
_GRID_LINE = (200, 190, 170)

# OFFLINE banner styling.
_OFFLINE_BAND_H = 24
_OFFLINE_BAND_RGB = (180, 25, 25)
_OFFLINE_TEXT_DEFAULT = "OFFLINE — basemap unavailable"
# Shown when the tile compositor refused due to MAX_TILE_COUNT — the cause
# is "area too large for the chosen zoom", which the user can actually
# address (shrink the corridor or extra-threat-search radius). The generic
# "basemap unavailable" message would imply a network problem instead.
_OFFLINE_TEXT_TILE_CAP = "OFFLINE — area too large for satellite tiles"

_RESOURCES_DIR = Path(__file__).resolve().parents[3] / "resources"
_THEATERS_DIR = _RESOURCES_DIR / "theaters"

# Bound the per-process caches so a long-running multi-theater process
# (campaign server, gen_recon_kneeboards.py looping over terrains) does
# not retain every theater GIF and landmap pickle ever loaded. Practical
# usage touches at most a handful of theaters in a single Retribution
# session, so a small bound is plenty.
_MAX_CACHED_THEATERS = 4

_gif_cache: "OrderedDict[str, Image.Image]" = OrderedDict()
_gif_cache_lock = threading.Lock()

_landmap_cache: "OrderedDict[str, tuple[Any, ...]]" = OrderedDict()
_landmap_cache_lock = threading.Lock()


def _cache_set(cache: "OrderedDict[str, _VT]", key: str, value: "_VT") -> None:
    """LRU-insert ``value`` under ``key``, evicting the oldest entry when
    the cache would exceed :data:`_MAX_CACHED_THEATERS`.

    Callers must already hold the matching cache lock.
    """
    cache[key] = value
    cache.move_to_end(key)
    while len(cache) > _MAX_CACHED_THEATERS:
        cache.popitem(last=False)


def render_basemap(
    extent: MapExtent,
    page_width: int,
    page_height: int,
    *,
    cache_dir: Path,
    imagery_anchor: Optional[Any] = None,
) -> Image.Image:
    """Render the basemap layer for a recon kneeboard page.

    Tries the Esri tile pipeline first. On failure (network unavailable,
    HTTP refusal, terrain projection error, degenerate extent), falls back
    to the legacy GIF/landmap renderer and stamps an OFFLINE banner across
    the top of the returned image.

    ``imagery_anchor`` is an optional pydcs ``Airport``. When provided and
    we have OSM-derived data for it (see
    ``resources/airport_imagery/<terrain>.json``), the satellite tile
    mosaic is shifted by the per-airport offset so it overlays where DCS
    draws its markers. Pages that center their extent on a target instead
    of an airport should leave this ``None``.

    Always returns an :class:`~PIL.Image.Image` of size
    ``(page_width, page_height)``.
    """
    offset_deg = _imagery_offset_for(extent, imagery_anchor)
    tiled = render_tiles(
        extent,
        page_width,
        page_height,
        cache_dir,
        imagery_offset_deg=offset_deg,
    )
    if tiled is not None:
        return tiled

    reason = last_failure_reason()
    logger.warning(
        "kneeboard_recon: tile basemap unavailable (reason=%r); rendering legacy fallback",
        reason,
    )
    fallback = _render_legacy_fallback(extent, page_width, page_height)
    _stamp_offline_banner(fallback, _banner_text_for_reason(reason))
    return fallback


# Filled-coastline palette for the static overview map (render_landmap_basemap).
_SEA_RGB = (150, 190, 220)
_SEA_RGB_DARK = (28, 42, 60)
_LAND_FILL = (228, 216, 190)
_LAND_FILL_DARK = (66, 62, 52)
_COAST_RGB = (110, 100, 80)
_BORDER_RGB = (140, 70, 140)
_BORDER_RGB_DARK = (200, 140, 200)

#: Gaps narrower than twice this between the land and sea zones are shoreline
#: and estuary, and stay sea as they always were; only ground past the landmap's
#: outer edge is drawn as land.
_FOOTPRINT_CLOSE_M = 4_000.0

#: Open sea from the border file narrower than twice this is dropped: the
#: files' clip edge is simplified, and the gap it leaves under the hull runs
#: about 20 km thick along Iraq's northern frame.
_OPEN_SEA_MIN_M = 15_000.0

_sea_cache: "OrderedDict[str, tuple[Any, ...]]" = OrderedDict()
_sea_cache_lock = threading.Lock()


def render_landmap_basemap(
    extent: MapExtent,
    page_width: int,
    page_height: int,
    *,
    dark: bool = False,
) -> Image.Image:
    """Render a tile-free filled-coastline basemap for a wide overview page.

    The theater's water (from the shipped landmap) is filled over a
    land-coloured background, with a coastline stroke and a light reference
    grid. Never touches the network and adds no OFFLINE banner, so it suits
    whole-theater overview pages where satellite tiles would be both too
    numerous and too zoomed out to be useful.

    Ground past the landmap's outer edge is drawn as land. Painting it sea put
    an ocean over Syria, Jordan and Turkey on every Iraq page that reached the
    map's west or north edge (Desert Aladeen, 2026-10-16).

    Unlike the theater-GIF crop this is correct for *any* extent: the geometry
    comes from world-coordinate polygons projected through
    :class:`~.projection.Projector`, so it aligns with markers drawn for the
    same extent and page size even where a fixed-coverage raster would not
    reach (e.g. map areas added after the shipped GIF was authored).
    """
    # Local import keeps this module's import graph minimal — Projector is
    # only needed by the tile-free paths, which the happy path bypasses.
    from dcs.mapping import Point as DcsPoint
    from .projection import Projector

    sea = _SEA_RGB_DARK if dark else _SEA_RGB
    land = _LAND_FILL_DARK if dark else _LAND_FILL
    img = Image.new("RGB", (page_width, page_height), land)
    draw = ImageDraw.Draw(img)
    projector = Projector(
        extent=extent, pixel_width=page_width, pixel_height=page_height
    )

    def project(coords: Iterable[Any]) -> list[tuple[int, int]]:
        return [projector.project(DcsPoint(x, y, extent.terrain)) for x, y in coords]

    for poly in _sea_polygons_for_terrain(extent.terrain):
        pts = project(poly.exterior.coords)
        if len(pts) < 3:
            continue
        draw.polygon(pts, fill=sea, outline=_COAST_RGB)
        for hole in poly.interiors:
            hole_pts = project(hole.coords)
            if len(hole_pts) >= 3:
                draw.polygon(hole_pts, fill=land, outline=_COAST_RGB)
    for i in range(1, 8):
        gx = i * page_width // 8
        draw.line((gx, 0, gx, page_height), fill=_GRID_LINE, width=1)
        gy = i * page_height // 8
        draw.line((0, gy, page_width, gy), fill=_GRID_LINE, width=1)
    return img


# Dim applied to the theater raster on a dark kneeboard. The raster is a
# daylight satellite render and there is no dark variant of it; 0.45 sits it
# close to the dark landmap's own land fill so the two paths read alike, and
# keeps the white label plates and haloes high-contrast.
_DARK_RASTER_DIM = 0.45


def align_extent_to_theater_raster(
    extent: MapExtent, *, keep_visible: MapExtent
) -> MapExtent:
    """``extent`` nudged onto the theater raster where a nudge is enough.

    Call this before rendering AND before building the projector — the
    backdrop and the symbology must share one extent or the markers move off
    the ground they name.

    Returns ``extent`` unchanged when no shift is possible or none is needed,
    so the caller never has to branch; :func:`render_theater_basemap` then
    falls back to the coastline draw on its own.
    """
    gif = _load_gif(extent.terrain)
    if gif is None:
        return extent
    coverage = gif_georef.coverage_for(extent.terrain, gif.size)
    if coverage is None or coverage.can_render(extent):
        return extent
    return coverage.slide_to_cover(extent, keep_visible) or extent


def render_theater_basemap(
    extent: MapExtent,
    page_width: int,
    page_height: int,
    *,
    dark: bool = False,
    on: Optional[date] = None,
) -> Image.Image:
    """Terrain imagery for a wide orientation map, else filled coastlines.

    Never touches the network: the shipped theater raster or nothing. Falls
    back to :func:`render_landmap_basemap` whenever ``gif_georef`` refuses the
    extent — no measured georeference, a raster that is not the size it was
    measured on, an extent reaching past the raster, or one over ground the
    raster never drew. Either way the page is drawn and the symbology is
    placed correctly; only the backdrop differs.
    """
    crop = _crop_from_gif(extent, page_width, page_height)
    if crop is None:
        img = render_landmap_basemap(extent, page_width, page_height, dark=dark)
    else:
        img = crop
        if dark:
            img = ImageEnhance.Brightness(img).enhance(_DARK_RASTER_DIM)
    _draw_land_borders(img, extent, dark=dark, on=on)
    return img


def _draw_land_borders(
    img: Image.Image, extent: MapExtent, *, dark: bool, on: Optional[date] = None
) -> None:
    """Thin lines along the national frontiers of the §98 terrain border file.

    Only edges two countries share are drawn; an edge one country has alone is
    coast or the file's clip edge.
    """
    from dcs.mapping import Point as DcsPoint
    from .projection import Projector

    segments = _land_border_segments(extent.terrain.name, on)
    if not segments:
        return
    projector = Projector(extent=extent, pixel_width=img.width, pixel_height=img.height)
    draw = ImageDraw.Draw(img)
    colour = _BORDER_RGB_DARK if dark else _BORDER_RGB
    for (ax, ay), (bx, by) in segments:
        if not (
            extent.min_x <= max(ax, bx)
            and min(ax, bx) <= extent.max_x
            and extent.min_y <= max(ay, by)
            and min(ay, by) <= extent.max_y
        ):
            continue
        draw.line(
            [
                projector.project(DcsPoint(ax, ay, extent.terrain)),
                projector.project(DcsPoint(bx, by, extent.terrain)),
            ],
            fill=colour,
            width=2,
        )


_border_cache: dict[
    str, tuple[tuple[tuple[float, float], tuple[float, float]], ...]
] = {}
_border_cache_lock = threading.Lock()


def _land_border_segments(
    terrain_name: str,
    on: Optional[date] = None,
) -> tuple[tuple[tuple[float, float], tuple[float, float]], ...]:
    """Every edge two countries share in the terrain's border file, cached.

    The border files are one shared coverage, so neighbours agree vertex for
    vertex (the same rule as the DTC's ``land_border_runs``).
    """
    from game.theater.terrainborders import load_terrain_borders

    with _border_cache_lock:
        key = f"{terrain_name}@{on:%Y-%m}" if on is not None else terrain_name
        cached = _border_cache.get(key)
        if cached is not None:
            return cached
        owners: dict[frozenset[tuple[float, float]], set[str]] = {}
        for zone in load_terrain_borders(terrain_name, on=on):
            ring = [(float(x), float(y)) for x, y in zone.get("border") or []]
            if len(ring) < 3:
                continue
            for a, b in zip(ring, ring[1:] + ring[:1]):
                owners.setdefault(frozenset((a, b)), set()).add(
                    str(zone.get("country"))
                )
        segments = tuple(
            (min(edge), max(edge))
            for edge, countries in owners.items()
            if len(edge) == 2 and len(countries) >= 2
        )
        _border_cache[key] = segments
        return segments


def _banner_text_for_reason(reason: str) -> str:
    """Pick the OFFLINE banner string for a ``render_tiles`` failure reason.

    The tile-cap path is broken out because it is the only failure mode the
    user can act on — they can shrink the corridor. Network/projection failures
    share the generic banner; the log line carries the underlying cause.
    """
    if reason == FAILURE_TILE_CAP:
        return _OFFLINE_TEXT_TILE_CAP
    return _OFFLINE_TEXT_DEFAULT


def _imagery_offset_for(
    extent: MapExtent, airport: Optional[Any]
) -> Optional[tuple[float, float]]:
    """The `(dlat, dlng)` imagery shift to apply to this render, or None.

    Precedence: the anchor airport's own measured OSM offset (airbase
    pages — exact prior behavior), else the robust regional offset of the
    nearest measured airports around the *extent centre*
    (:func:`airport_imagery.offset_near`). The fallback is what corrects
    the target/corridor/overview pages, which used to render with no
    correction at all and sat the full DCS-vs-real-world georeference
    error off their markers (~350 m median on Caucasus/GermanyCW — tens
    of page pixels at detail scale). Best-effort: any failure (no dataset,
    un-projectable test terrain) degrades to None = no shift.
    """
    if airport is not None:
        record = airport_imagery.load(extent.terrain.name)
        if record is not None:
            entry = record.for_airport(airport)
            if entry is not None and entry.has_offset:
                return (entry.imagery_offset_lat, entry.imagery_offset_lng)
    try:
        center = Point(
            (extent.min_x + extent.max_x) / 2.0,
            (extent.min_y + extent.max_y) / 2.0,
            extent.terrain,
        ).latlng()
        return airport_imagery.offset_near(
            extent.terrain.name, float(center.lat), float(center.lng)
        )
    except Exception:  # noqa: BLE001 -- enhancement only; never block the render
        return None


def _stamp_offline_banner(img: Image.Image, text: str = _OFFLINE_TEXT_DEFAULT) -> None:
    """Draw a red OFFLINE warning band across the top of ``img``."""
    overlay = Image.new(
        "RGBA",
        (img.width, _OFFLINE_BAND_H),
        _OFFLINE_BAND_RGB + (200,),
    )
    img.paste(overlay, (0, 0), overlay)

    font: PilFont
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 14)
    except OSError:
        font = ImageFont.load_default()
    draw = ImageDraw.Draw(img)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (img.width - tw) // 2 - bbox[0]
    ty = (_OFFLINE_BAND_H - th) // 2 - bbox[1]
    draw.text((tx, ty), text, fill=(255, 255, 255), font=font)


# ---------------------------------------------------------------------------
# Legacy fallback renderer (preserved from the original basemap.py).
# Public ``render_basemap`` invokes this only when ``render_tiles`` returns
# ``None``. Kept in this module so the failure path requires no additional
# imports.
# ---------------------------------------------------------------------------


def _render_legacy_fallback(
    extent: MapExtent, page_width: int, page_height: int
) -> Image.Image:
    """GIF-crop for wide extents; tan+landmap+grid for tight extents."""
    # Use the larger of the two world spans: a corridor that is wide
    # east-west but short north-south (or vice versa) is still a large area
    # the GIF crop handles better than the tan grid.
    if max(extent.span_x_m, extent.span_y_m) > DETAIL_THRESHOLD_M:
        gif_render = _crop_from_gif(extent, page_width, page_height)
        if gif_render is not None:
            return gif_render
    polygons = _landmap_polygons_for_terrain(extent.terrain)
    return _draw_landmap_only(extent, page_width, page_height, polygons)


def _theater_gif_path(terrain: Terrain) -> Optional[Path]:
    """Locate the shipped gif for the given terrain.

    Existing assets are named ``resources/<terrain>.gif`` (caumap.gif,
    syria.gif, persiangulf.gif, ...) with no consistent mapping to the pydcs
    terrain name. We try a small set of name normalisations before giving up.
    """
    name = terrain.name.lower()
    candidates = [
        name,
        "caumap" if name == "caucasus" else None,
        name.replace(" ", ""),
        name.replace("the", "").strip(),
    ]
    for cand in candidates:
        if not cand:
            continue
        path = _RESOURCES_DIR / f"{cand}.gif"
        if path.exists():
            return path
    return None


def _load_gif(terrain: Terrain) -> Optional[Image.Image]:
    with _gif_cache_lock:
        cached = _gif_cache.get(terrain.name)
        if cached is not None:
            _gif_cache.move_to_end(terrain.name)
            return cached
        path = _theater_gif_path(terrain)
        if path is None:
            return None
        img = Image.open(path).convert("RGB")
        _cache_set(_gif_cache, terrain.name, img)
        return img


def _crop_from_gif(
    extent: MapExtent, page_width: int, page_height: int
) -> Optional[Image.Image]:
    """Crop the theater raster to ``extent``, or None if it cannot cover it.

    Refuses rather than clamps. An earlier version clamped the crop rectangle
    to the image, so an extent reaching past the raster was stretched to fill
    the page and the markers drawn over it landed on the wrong ground with
    nothing to show for it. Returning None drops to the landmap renderer,
    which is plain but placed correctly.
    """
    gif = _load_gif(extent.terrain)
    if gif is None:
        return None
    coverage = gif_georef.coverage_for(extent.terrain, gif.size)
    if coverage is None or not coverage.can_render(extent):
        logger.debug(
            "kneeboard_recon: %s raster cannot place extent x %.0f..%.0f "
            "y %.0f..%.0f; using the landmap renderer",
            extent.terrain.name,
            extent.min_x,
            extent.max_x,
            extent.min_y,
            extent.max_y,
        )
        return None

    rect = coverage.rect
    gif_w, gif_h = gif.size
    px_per_m_x = gif_w / (rect.max_y - rect.min_y)
    px_per_m_y = gif_h / (rect.max_x - rect.min_x)
    gx0 = int(round((extent.min_y - rect.min_y) * px_per_m_x))
    gx1 = int(round((extent.max_y - rect.min_y) * px_per_m_x))
    gy0 = int(round((rect.max_x - extent.max_x) * px_per_m_y))
    gy1 = int(round((rect.max_x - extent.min_x) * px_per_m_y))
    # can_render() put the extent inside the rect, so the only way out of
    # range now is a sub-pixel extent rounding to an empty box.
    if gx1 - gx0 < 1 or gy1 - gy0 < 1:
        return None
    crop = gif.crop((gx0, gy0, gx1, gy1))
    return crop.resize((page_width, page_height), Image.LANCZOS)


def _draw_landmap_only(
    extent: MapExtent,
    page_width: int,
    page_height: int,
    landmap_polygons: Iterable[Any],
) -> Image.Image:
    # Local import keeps this module's import graph minimal — Projector
    # is only needed by the legacy fallback path, which the tile
    # pipeline bypasses entirely on the happy path.
    from dcs.mapping import Point as DcsPoint
    from .projection import Projector

    img = Image.new("RGB", (page_width, page_height), _LAND_TAN)
    draw = ImageDraw.Draw(img)
    projector = Projector(
        extent=extent,
        pixel_width=page_width,
        pixel_height=page_height,
    )
    for poly in landmap_polygons:
        pts = [
            projector.project(DcsPoint(x, y, extent.terrain))
            for x, y in poly.exterior.coords
        ]
        if len(pts) >= 2:
            draw.line(pts + [pts[0]], fill=_LAND_TAN_DARK, width=2)
    for i in range(1, 8):
        gx = i * page_width // 8
        draw.line((gx, 0, gx, page_height), fill=_GRID_LINE, width=1)
        gy = i * page_height // 8
        draw.line((0, gy, page_width, gy), fill=_GRID_LINE, width=1)
    return img


def _pydcs_name(theater_dir: Path) -> Optional[str]:
    """The ``pydcs_name`` a theater's info.yaml declares, or None."""
    import yaml

    try:
        data = yaml.safe_load((theater_dir / "info.yaml").read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return None
    name = data.get("pydcs_name") if isinstance(data, dict) else None
    return name if isinstance(name, str) else None


def _landmap_path_for_terrain(terrain: Terrain) -> Optional[Path]:
    terrain_name_lower = terrain.name.lower()
    if not _THEATERS_DIR.exists():
        return None
    # Resolve once so a symlinked _THEATERS_DIR (test fixtures, dev
    # overlays) is still validated via real-path equality.
    theaters_root = _THEATERS_DIR.resolve()
    for theater_dir in _THEATERS_DIR.iterdir():
        if not theater_dir.is_dir():
            continue
        # Refuse to traverse into anything whose resolved path escapes
        # the theaters root — symlinked theater_dir entries pointing
        # outside resources/theaters would otherwise let pickle.load
        # deserialize an attacker-controlled file.
        try:
            theater_dir.resolve().relative_to(theaters_root)
        except ValueError:
            logger.warning(
                "kneeboard_recon: skipping theater entry %s — resolved "
                "path escapes %s",
                theater_dir,
                theaters_root,
            )
            continue
        dir_name = theater_dir.name.lower().replace(" ", "").replace("_", "")
        candidate_name = terrain_name_lower.replace(" ", "").replace("_", "")
        # The folder name alone missed "SinaiMap" (sinai/) and
        # "MarianaIslandsWWII" (marianaswwii/); info.yaml names the terrain.
        if dir_name == candidate_name or _pydcs_name(theater_dir) == terrain.name:
            landmap_p = theater_dir / "landmap.p"
            if not landmap_p.exists():
                return None
            # Re-validate the file itself, not just its parent dir — a
            # `landmap.p` symlink pointing outside the theaters root would
            # otherwise feed an attacker-controlled file to pickle.load.
            try:
                landmap_p.resolve().relative_to(theaters_root)
            except ValueError:
                logger.warning(
                    "kneeboard_recon: skipping landmap %s — resolved "
                    "path escapes %s",
                    landmap_p,
                    theaters_root,
                )
                return None
            return landmap_p
    return None


def _landmap_polygons_for_terrain(terrain: Terrain) -> Iterable[Any]:
    with _landmap_cache_lock:
        cached = _landmap_cache.get(terrain.name)
        if cached is not None:
            _landmap_cache.move_to_end(terrain.name)
            return cached
        polygons = _load_landmap_polygons(terrain)
        _cache_set(_landmap_cache, terrain.name, polygons)
        return polygons


def _load_landmap(terrain: Terrain) -> Optional[Any]:
    path = _landmap_path_for_terrain(terrain)
    if path is None:
        return None
    try:
        with path.open("rb") as f:
            return pickle.load(f)
    except Exception as exc:
        logger.warning(
            "kneeboard_recon: failed to load landmap %s (%s); "
            "falling back to grid-only basemap",
            path,
            exc,
        )
        return None


def _load_landmap_polygons(terrain: Terrain) -> tuple[Any, ...]:
    data = _load_landmap(terrain)
    if data is None:
        return ()
    try:
        return tuple(data.inclusion_zones.geoms)
    except AttributeError:
        logger.warning(
            "kneeboard_recon: landmap for %s has no inclusion_zones.geoms; "
            "falling back to grid-only basemap",
            terrain.name,
        )
        return ()


def _sea_polygons_for_terrain(terrain: Terrain) -> Iterable[Any]:
    with _sea_cache_lock:
        cached = _sea_cache.get(terrain.name)
        if cached is not None:
            _sea_cache.move_to_end(terrain.name)
            return cached
        polygons = _load_sea_polygons(terrain)
        _cache_set(_sea_cache, terrain.name, polygons)
        return polygons


def _polygon_parts(geometry: Any) -> list[Any]:
    if geometry.is_empty:
        return []
    return [
        g for g in getattr(geometry, "geoms", [geometry]) if g.geom_type == "Polygon"
    ]


def _load_sea_polygons(terrain: Terrain) -> tuple[Any, ...]:
    """The landmap's water: everything inside its outer edge that is not land.

    The outer edge is the land and sea zones together, with gaps under
    ``2 * _FOOTPRINT_CLOSE_M`` between them closed, so a shoreline or estuary
    the zones both stop short of stays water as it was before.

    Past that edge, the §98 border file decides: inside the hull of its
    countries (not their bounding box, which a lat/lon clip edge leaves a
    sliver of past), ground no country covers is sea, so the Falklands' open ocean stays ocean while
    Iraq's Jordan and Syria stay land. Outside the frame, or on a terrain
    with no border file, it is land.
    """
    from shapely.geometry import Polygon
    from shapely.ops import unary_union

    from game.theater.terrainborders import load_terrain_borders

    data = _load_landmap(terrain)
    if data is None:
        return ()
    try:
        land = unary_union(
            [Polygon(p.exterior) for p in _polygon_parts(data.inclusion_zones)]
        )
        footprint = (
            unary_union([data.inclusion_zones, data.sea_zones])
            .buffer(_FOOTPRINT_CLOSE_M, quad_segs=2)
            .buffer(-_FOOTPRINT_CLOSE_M, quad_segs=2)
        )
        outline = unary_union([Polygon(p.exterior) for p in _polygon_parts(footprint)])
        sea = outline.difference(land)
        countries = [
            Polygon(zone["border"]).buffer(0)
            for zone in load_terrain_borders(terrain.name)
            if len(zone.get("border") or []) >= 3
        ]
        if countries:
            covered = unary_union(countries)
            # Opened, so a sliver between a simplified clip edge and the hull
            # is not drawn as a strip of sea along the frame.
            open_sea = (
                covered.convex_hull.difference(covered)
                .buffer(-_OPEN_SEA_MIN_M, quad_segs=2)
                .buffer(_OPEN_SEA_MIN_M, quad_segs=2)
                .difference(outline)
            )
            sea = unary_union([sea, open_sea])
        return tuple(_polygon_parts(sea))
    except (
        Exception
    ) as exc:  # noqa: BLE001 -- a bad landmap costs the sea, not the page
        logger.warning(
            "kneeboard_recon: could not build the sea for %s (%s); drawing land only",
            terrain.name,
            exc,
        )
        return ()
