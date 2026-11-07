"""Unit placement for campaign build tools, checked against DCS's own ground.

A build tool asks for a spot by job (depot, air defense, EWR, garrison, town node,
named spot) instead of one ring around every base; each job has its own candidate
pattern, and the ground under every candidate is read inside DCS by a check mission,
because slope, roads and buildings exist only there. Why, and the 2026-11-07
measurements behind each pattern: docs/dev/design/retlab-campaign-placement-notes.md.

    # 1. a check mission for every unit in a .miz (or a build tool's candidates)
    python tools/campaign_placement.py check resources/campaigns/<name>.miz
    # 2. run it in DCS, press Fly (unpause), wait for "[PLACEMENT] done", quit
    # 3. the flagged units, and a review map in the browser
    python tools/campaign_placement.py report resources/campaigns/<name>.miz

Needs Retribution's de-sanitized MissionScripting.lua: the check mission writes a file.
"""

from __future__ import annotations

import argparse
import html
import json
import math
import os
import re
import sys
import zipfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
PROBE_LUA = REPO_ROOT / "resources/plugins/base/dcs_placement_probe.lua"
SAVED_GAMES = Path.home() / "Saved Games" / "DCS"

#: An erecting SAM launcher never raises past this tilt (ED's 5P85D; the Bavar pack).
MAX_SLOPE_DEG = 5.0
#: A building this close to a unit (about 100 ft) is flagged.
MIN_BUILDING_M = 30.0
#: Parking stands and the runway strip, as New Game's airfield clearance check.
RUNWAY_HALF_LENGTH_M = 1600.0
RUNWAY_STRIP_HALF_WIDTH_M = 300.0
PARKING_CLEARANCE_M = 80.0

SURFACE_LAND, SURFACE_SHALLOW, SURFACE_WATER, SURFACE_ROAD, SURFACE_RUNWAY = (
    1,
    2,
    3,
    4,
    5,
)

#: The miz ``theatre`` string to the pydcs terrain class name.
THEATRES = {
    "Afghanistan": "Afghanistan",
    "Caucasus": "Caucasus",
    "Falklands": "Falklands",
    "GermanyCW": "GermanyColdWar",
    "Iraq": "Iraq",
    "Kola": "Kola",
    "MarianaIslands": "MarianaIslands",
    "MarianaIslandsWWII": "MarianaIslandsWWII",
    "Nevada": "Nevada",
    "Normandy": "Normandy",
    "PersianGulf": "PersianGulf",
    "SinaiMap": "Sinai",
    "Syria": "Syria",
    "TheChannel": "TheChannel",
}


# -- the ground, as DCS reads it ---------------------------------------------------


def point_id(x: float, y: float) -> str:
    """A spot's key: its map position to the metre."""
    return f"{round(x)}_{round(y)}"


@dataclass(frozen=True)
class Reading:
    """The ground under one spot, from the check mission."""

    height_m: float
    slope_deg: float
    surface: int
    buildings: int
    nearest_building_m: float
    building_type: str

    def problems(self, max_slope_deg: float = MAX_SLOPE_DEG) -> list[str]:
        found = []
        if self.slope_deg > max_slope_deg:
            found.append(f"slope {self.slope_deg:.0f} deg")
        if self.surface in (SURFACE_WATER, SURFACE_SHALLOW):
            found.append("water")
        elif self.surface == SURFACE_RUNWAY:
            found.append("runway or taxiway")
        elif self.surface == SURFACE_ROAD:
            found.append("road")
        if 0 <= self.nearest_building_m < MIN_BUILDING_M:
            feet = self.nearest_building_m * 3.281
            found.append(f"building {feet:.0f} ft away ({self.building_type})")
        return found


def parse_probe_output(path: Path) -> tuple[str, dict[str, Reading]]:
    """The check mission's file: a header, one row per spot, then END."""
    lines = path.read_text(encoding="utf-8").splitlines()
    header = lines[0].split() if lines else []
    if header[:2] != ["RETLAB-PLACEMENT", "1"]:
        raise ValueError(f"{path} is not a placement check file")
    if lines[-1].strip() != "END":
        raise ValueError(f"{path} stops early: the check mission did not finish")
    readings = {}
    for line in lines[1:-1]:
        pid, h, slope, surface, count, nearest, kind = line.split(" ", 6)
        readings[pid] = Reading(
            float(h), float(slope), int(surface), int(count), float(nearest), kind
        )
    return header[2], readings


class ReadingCache:
    """Every spot DCS has read, per terrain, kept outside the repo between builds."""

    def __init__(self, terrain: str, directory: Optional[Path] = None) -> None:
        directory = directory or Path(
            os.environ.get("RETLAB_PLACEMENT_CACHE", SAVED_GAMES / "RetLab placement")
        )
        self.path = directory / f"{terrain}.json"
        self.readings: dict[str, Reading] = {}
        if self.path.exists():
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            self.readings = {k: Reading(*v) for k, v in raw.items()}

    def get(self, x: float, y: float) -> Optional[Reading]:
        return self.readings.get(point_id(x, y))

    def add(self, readings: dict[str, Reading]) -> None:
        self.readings.update(readings)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        raw = {
            k: [
                r.height_m,
                r.slope_deg,
                r.surface,
                r.buildings,
                r.nearest_building_m,
                r.building_type,
            ]
            for k, r in sorted(self.readings.items())
        }
        self.path.write_text(json.dumps(raw), encoding="utf-8")


# -- airfields ---------------------------------------------------------------------


def _runway_offsets(airport: Any, x: float, y: float) -> list[tuple[float, float]]:
    """(along, perp) of a point against each runway centreline through the field."""
    out = []
    for runway in getattr(airport, "runways", []) or []:
        heading = math.radians(float(runway.heading))
        dx, dy = math.cos(heading), math.sin(heading)
        vx, vy = x - airport.position.x, y - airport.position.y
        out.append((vx * dx + vy * dy, vx * dy - vy * dx))
    return out


def airfield_problem(airports: Iterable[Any], x: float, y: float) -> Optional[str]:
    """A ground unit here would hold every AI taxi at the field (features doc §1)."""
    for airport in airports:
        if math.hypot(x - airport.position.x, y - airport.position.y) > 4000.0:
            continue
        for along, perp in _runway_offsets(airport, x, y):
            if (
                abs(perp) < RUNWAY_STRIP_HALF_WIDTH_M
                and abs(along) < RUNWAY_HALF_LENGTH_M
            ):
                return f"{airport.name} runway strip"
        for slot in getattr(airport, "parking_slots", []) or []:
            if (
                math.hypot(x - slot.position.x, y - slot.position.y)
                < PARKING_CLEARANCE_M
            ):
                return f"{airport.name} parking stand"
    return None


# -- placement by job --------------------------------------------------------------


class Job(Enum):
    #: Ammo dumps, factories, motor pools, workshops: in close to the field.
    DEPOT = "depot"
    #: Guns and SHORAD: under the runway approaches.
    AIR_DEFENSE = "air defense"
    #: Early-warning radars: the highest flat ground nearby.
    EWR = "ewr"
    #: Garrison armor: inside a field's 3 km capture zone.
    GARRISON = "garrison"
    #: IADS comms, power and HQs: on the edge of the named town's buildings.
    TOWN = "town"
    #: A named spot: as close to it as good ground allows.
    SPOT = "spot"


#: Minimum distance from every earlier pick, by job.
SEPARATION_M = {
    Job.DEPOT: 250.0,
    Job.AIR_DEFENSE: 900.0,
    Job.EWR: 2000.0,
    Job.GARRISON: 400.0,
    Job.TOWN: 200.0,
    Job.SPOT: 100.0,
}


@dataclass(frozen=True)
class Candidate:
    x: float
    y: float
    #: Lower is better, before the ground is read; EWR candidates re-rank by height.
    rank: float
    #: Which runway end an air-defense candidate covers, to spread them.
    tag: str = ""


def _ring(
    cx: float, cy: float, radii: Iterable[float], step_deg: int = 15
) -> list[tuple[float, float, float]]:
    out = []
    for r in radii:
        for bearing in range(0, 360, step_deg):
            a = math.radians(bearing)
            out.append((cx + r * math.cos(a), cy + r * math.sin(a), r))
    return out


def _span(start: float, stop: float, step: float) -> list[float]:
    count = int(round((stop - start) / step))
    return [start + i * step for i in range(count + 1)]


def candidates(
    job: Job, x: float, y: float, airport: Optional[Any] = None
) -> list[Candidate]:
    """Every spot worth reading for one job, best first, around (x, y)."""
    if job is Job.DEPOT:
        return [
            Candidate(px, py, r) for px, py, r in _ring(x, y, _span(600, 1800, 200))
        ]
    if job is Job.GARRISON:
        return [
            Candidate(px, py, r) for px, py, r in _ring(x, y, _span(1500, 2700, 200))
        ]
    if job is Job.AIR_DEFENSE:
        if airport is None or not getattr(airport, "runways", None):
            return [
                Candidate(px, py, r)
                for px, py, r in _ring(x, y, _span(1500, 3500, 500))
            ]
        out = []
        for runway in airport.runways:
            for end, sign in (("a", 1.0), ("b", -1.0)):
                heading = math.radians(float(runway.heading))
                dx, dy = sign * math.cos(heading), sign * math.sin(heading)
                for beyond in (800.0, 1600.0, 2400.0):
                    along = RUNWAY_HALF_LENGTH_M + beyond
                    for perp in (0.0, 500.0, -500.0, 1000.0, -1000.0):
                        px = x + along * dx - perp * dy
                        py = y + along * dy + perp * dx
                        rank = beyond + abs(perp) * 0.5
                        out.append(Candidate(px, py, rank, f"{runway.heading}{end}"))
        return sorted(out, key=lambda c: c.rank)
    if job is Job.EWR:
        out = []
        for gx in _span(-12000, 12000, 1000):
            for gy in _span(-12000, 12000, 1000):
                d = math.hypot(gx, gy)
                if 2000 <= d <= 12000:
                    out.append(Candidate(x + gx, y + gy, d))
        return out
    if job is Job.TOWN:
        out = []
        for gx in _span(-1500, 1500, 100):
            for gy in _span(-1500, 1500, 100):
                d = math.hypot(gx, gy)
                if d <= 1500:
                    out.append(Candidate(x + gx, y + gy, d))
        return sorted(out, key=lambda c: c.rank)
    out = [Candidate(x, y, 0.0)]
    for r in _span(50, 600, 50):
        out += [Candidate(px, py, r) for px, py, _ in _ring(x, y, [r], 30)]
    return out


@dataclass
class Request:
    name: str
    job: Job
    x: float
    y: float
    airport: Optional[Any] = None
    max_slope_deg: float = MAX_SLOPE_DEG


@dataclass
class Placement:
    request: Request
    x: Optional[float]
    y: Optional[float]
    reading: Optional[Reading]
    #: Why the best candidates were passed over, for the review map.
    skipped: list[str] = field(default_factory=list)


class NeedsCheck(Exception):
    """Some candidates have never been read: run the check mission, then rebuild."""

    def __init__(self, path: Path, count: int) -> None:
        super().__init__(
            f"{count} spots have never been read. Run {path} in DCS, press Fly, wait "
            "for '[PLACEMENT] done', quit, then run the build again."
        )
        self.path = path
        self.count = count


class Placer:
    """Places a build tool's units by job, on ground the check mission has read.

    Request every spot, then call ``resolve``. The first build raises NeedsCheck
    with a check mission to run; after that run the readings are cached and the
    same build resolves without DCS.
    """

    def __init__(
        self,
        terrain: Any,
        name: str,
        cache: Optional[ReadingCache] = None,
        on_land: Optional[Callable[[float, float], bool]] = None,
    ) -> None:
        self.terrain = terrain
        self.name = name
        self.cache = cache or ReadingCache(terrain.name)
        self.on_land = on_land
        self.airports = list(terrain.airport_list())
        self.requests: list[Request] = []
        self.placements: dict[str, Placement] = {}

    def request(
        self,
        name: str,
        job: Job,
        x: float,
        y: float,
        airport: Optional[Any] = None,
        max_slope_deg: float = MAX_SLOPE_DEG,
    ) -> None:
        self.requests.append(Request(name, job, x, y, airport, max_slope_deg))

    def _usable(self, request: Request) -> list[Candidate]:
        out = []
        for c in candidates(request.job, request.x, request.y, request.airport):
            if self.on_land is not None and not self.on_land(c.x, c.y):
                continue
            if airfield_problem(self.airports, c.x, c.y) is not None:
                continue
            out.append(c)
        return out

    def unread(self) -> list[tuple[float, float]]:
        seen: dict[str, tuple[float, float]] = {}
        for request in self.requests:
            for c in self._usable(request):
                if self.cache.get(c.x, c.y) is None:
                    seen.setdefault(point_id(c.x, c.y), (c.x, c.y))
        return list(seen.values())

    def resolve(self, check_dir: Optional[Path] = None) -> dict[str, Placement]:
        missing = self.unread()
        if missing:
            path = (check_dir or default_check_dir()) / f"{self.name}_placement.miz"
            write_check_mission(self.terrain, self.name, missing, path)
            raise NeedsCheck(path, len(missing))
        taken: list[tuple[float, float]] = []
        ends: dict[str, int] = {}
        for request in self.requests:
            placement = self._pick(request, taken, ends)
            self.placements[request.name] = placement
            if placement.x is not None and placement.y is not None:
                taken.append((placement.x, placement.y))
        return self.placements

    def _pick(
        self,
        request: Request,
        taken: list[tuple[float, float]],
        ends: dict[str, int],
    ) -> Placement:
        scored = []
        for c in self._usable(request):
            reading = self.cache.get(c.x, c.y)
            assert reading is not None
            rank = c.rank
            if request.job is Job.EWR:
                rank = -reading.height_m + c.rank * 0.001
            elif request.job is Job.TOWN and reading.buildings == 0:
                rank += 2000.0
            elif request.job is Job.AIR_DEFENSE:
                rank += 3000.0 * ends.get(c.tag, 0)
            scored.append((rank, c, reading))
        scored.sort(key=lambda s: s[0])
        skipped: list[str] = []
        separation = SEPARATION_M[request.job]
        for _, c, reading in scored:
            problems = reading.problems(request.max_slope_deg)
            if not problems and any(
                math.hypot(c.x - tx, c.y - ty) < separation for tx, ty in taken
            ):
                problems = ["too close to another unit"]
            if problems:
                if len(skipped) < 5:
                    skipped.append("; ".join(problems))
                continue
            if c.tag:
                ends[c.tag] = ends.get(c.tag, 0) + 1
            return Placement(request, c.x, c.y, reading, skipped)
        return Placement(request, None, None, None, skipped)


# -- the check mission -------------------------------------------------------------


def default_check_dir() -> Path:
    return SAVED_GAMES / "Missions" / "RetLab probes"


def _safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", name).strip("_") or "check"


def probe_config(name: str, points: Iterable[tuple[float, float]]) -> str:
    rows = ",\n".join(
        f'{{id="{point_id(x, y)}",x={round(x)},y={round(y)}}}' for x, y in points
    )
    return f'RETLAB_PLACEMENT = {{ name = "{_safe_name(name)}", points = {{\n{rows}\n}} }}\n'


def write_check_mission(
    terrain: Any, name: str, points: Iterable[tuple[float, float]], path: Path
) -> Path:
    import dcs
    from dcs.action import DoScript
    from dcs.translation import String
    from dcs.triggers import TriggerStart

    mission = dcs.Mission(terrain)
    trigger = TriggerStart(comment="placement check")
    script = probe_config(name, points) + PROBE_LUA.read_text(encoding="utf-8")
    trigger.add_action(DoScript(String(script)))
    mission.triggerrules.triggers.append(trigger)
    path.parent.mkdir(parents=True, exist_ok=True)
    mission.save(str(path))
    return path


def probe_output_path(name: str) -> Path:
    return SAVED_GAMES / "Logs" / f"retlab_placement_{_safe_name(name)}.txt"


# -- units in a .miz ---------------------------------------------------------------


@dataclass(frozen=True)
class MizUnit:
    group: str
    unit: str
    unit_type: str
    side: str
    x: float
    y: float
    #: A FIXED site (§122) or a route marker: placed on purpose, never checked. A
    #: template SAM site's revetment pad reads as road and its berms as slope.
    drawn: bool = False


def _is_drawn(group: dict[str, Any]) -> bool:
    if str(group.get("name", "")).startswith("FIXED"):
        return True
    points = ((group.get("route") or {}).get("points")) or {}
    return len(points) > 1


def read_miz(path: Path) -> tuple[str, list[MizUnit]]:
    """The theatre and every ground unit and static; ships and aircraft are left out."""
    from dcs import lua

    with zipfile.ZipFile(path) as archive:
        mission = lua.loads(archive.read("mission").decode("utf-8"))["mission"]
    units = []
    for side, coalition in mission["coalition"].items():
        for country in (coalition.get("country") or {}).values():
            for category in ("vehicle", "static"):
                groups = (country.get(category) or {}).get("group") or {}
                for group in groups.values():
                    for unit in (group.get("units") or {}).values():
                        units.append(
                            MizUnit(
                                str(group.get("name")),
                                str(unit.get("name")),
                                str(unit.get("type")),
                                side,
                                float(unit["x"]),
                                float(unit["y"]),
                                _is_drawn(group),
                            )
                        )
    return mission["theatre"], units


def terrain_for(theatre: str) -> Any:
    import dcs.terrain

    if theatre not in THEATRES:
        raise SystemExit(f"Unknown theatre {theatre!r}")
    return getattr(dcs.terrain, THEATRES[theatre])()


# -- the review map ----------------------------------------------------------------


@dataclass(frozen=True)
class Marker:
    lat: float
    lon: float
    label: str
    lines: list[str]
    status: str  # "ok", "flagged", "unread", "anchor", "drawn"


_MAP_TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Placement review</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<style>
:root { --bg: #f6f6f4; --fg: #1d1d1b; --panel: #ffffff; --muted: #66665f; }
@media (prefers-color-scheme: dark) {
  :root { --bg: #161615; --fg: #ececea; --panel: #222220; --muted: #a3a39c; }
}
html, body { margin: 0; height: 100%; background: var(--bg); color: var(--fg);
  font: 14px/1.4 system-ui, sans-serif; }
#map { position: absolute; inset: 0 0 0 340px; }
#side { position: absolute; inset: 0 auto 0 0; width: 340px; overflow-y: auto;
  background: var(--panel); padding: 12px 16px; box-sizing: border-box; }
#side h1 { font-size: 16px; margin: 0 0 4px; }
#side p { color: var(--muted); margin: 0 0 12px; }
#side li { cursor: pointer; margin-bottom: 6px; }
.flagged { color: #c0392b; } .unread { color: #b9770e; }
@media (max-width: 700px) {
  #side { width: auto; inset: auto 0 0 0; height: 40%; }
  #map { inset: 0 0 40% 0; }
}
</style></head><body>
<div id="side"><h1>__TITLE__</h1><p>__SUMMARY__</p><ul id="list"></ul></div>
<div id="map"></div>
<script>
const markers = __MARKERS__;
const colors = { ok: "#27ae60", flagged: "#c0392b", unread: "#b9770e", anchor: "#2e86c1", drawn: "#8a8a84" };
const map = L.map("map");
L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
  { maxZoom: 19, attribution: "Imagery: Esri" }).addTo(map);
const list = document.getElementById("list");
const bounds = [];
for (const m of markers) {
  const dot = L.circleMarker([m.lat, m.lon], { radius: m.status === "ok" || m.status === "drawn" ? 5 : 8,
    color: colors[m.status], fillOpacity: 0.85 }).addTo(map);
  dot.bindPopup("<b>" + m.label + "</b><br>" + m.lines.join("<br>"));
  bounds.push([m.lat, m.lon]);
  if (m.status === "flagged" || m.status === "unread") {
    const li = document.createElement("li");
    li.className = m.status;
    li.innerHTML = m.label + ": " + m.lines[m.lines.length - 1];
    li.onclick = () => { map.setView([m.lat, m.lon], 16); dot.openPopup(); };
    list.appendChild(li);
  }
}
if (bounds.length) { map.fitBounds(bounds); } else { map.setView([0, 0], 2); }
</script></body></html>
"""


def write_review_map(
    path: Path, title: str, summary: str, markers: list[Marker]
) -> Path:
    data = json.dumps(
        [
            {
                "lat": m.lat,
                "lon": m.lon,
                "label": html.escape(m.label),
                "lines": [html.escape(line) for line in m.lines],
                "status": m.status,
            }
            for m in markers
        ]
    )
    page = (
        _MAP_TEMPLATE.replace("__TITLE__", html.escape(title))
        .replace("__SUMMARY__", html.escape(summary))
        .replace("__MARKERS__", data.replace("</", "<\\/"))
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(page, encoding="utf-8")
    return path


def describe(reading: Reading) -> list[str]:
    surfaces = {1: "land", 2: "shallow water", 3: "water", 4: "road", 5: "runway"}
    lines = [
        f"ground {reading.height_m * 3.281:.0f} ft, slope {reading.slope_deg:.1f} deg, "
        f"{surfaces.get(reading.surface, '?')}"
    ]
    if reading.nearest_building_m >= 0:
        lines.append(
            f"nearest building {reading.nearest_building_m * 3.281:.0f} ft "
            f"({reading.building_type})"
        )
    return lines


def _latlon(terrain: Any, x: float, y: float) -> tuple[float, float]:
    from dcs.mapping import Point

    ll = Point(x, y, terrain).latlng()
    return ll.lat, ll.lng


def placement_markers(terrain: Any, placer: Placer) -> list[Marker]:
    """A build tool's picks for the review map, each with its anchor."""
    markers = []
    for name, p in placer.placements.items():
        r = p.request
        lat, lon = _latlon(terrain, r.x, r.y)
        markers.append(Marker(lat, lon, f"{name} anchor", [r.job.value], "anchor"))
        if p.x is None or p.y is None or p.reading is None:
            markers.append(
                Marker(
                    lat, lon, name, ["no good ground in reach"] + p.skipped, "flagged"
                )
            )
            continue
        lat, lon = _latlon(terrain, p.x, p.y)
        lines = [r.job.value] + describe(p.reading)
        if p.skipped:
            lines.append("passed over: " + " | ".join(p.skipped))
        markers.append(Marker(lat, lon, name, lines, "ok"))
    return markers


# -- command line ------------------------------------------------------------------


def _cmd_check(args: argparse.Namespace) -> int:
    theatre, units = read_miz(args.miz)
    terrain = terrain_for(theatre)
    name = _safe_name(args.miz.stem)
    out = args.out or default_check_dir() / f"{name}_placement.miz"
    spots = {point_id(u.x, u.y): (u.x, u.y) for u in units}
    write_check_mission(terrain, name, spots.values(), out)
    print(f"{len(spots)} spots on {theatre}: run {out} in DCS, press Fly,")
    print("wait for '[PLACEMENT] done', quit, then run the report.")
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    theatre, units = read_miz(args.miz)
    terrain = terrain_for(theatre)
    name = _safe_name(args.miz.stem)
    cache = ReadingCache(terrain.name)
    output = args.probe_output or probe_output_path(name)
    if output.exists():
        _, readings = parse_probe_output(output)
        cache.add(readings)
        cache.save()
    airports = list(terrain.airport_list())
    markers = []
    flagged = unread = drawn = 0
    for u in units:
        lat, lon = _latlon(terrain, u.x, u.y)
        label = f"{u.group} / {u.unit_type}"
        if u.drawn:
            drawn += 1
            markers.append(Marker(lat, lon, label, ["drawn, not checked"], "drawn"))
            continue
        problems = []
        on_field = airfield_problem(airports, u.x, u.y)
        if on_field:
            problems.append(on_field)
        reading = cache.get(u.x, u.y)
        if reading is None:
            unread += 1
            markers.append(Marker(lat, lon, label, ["not read yet"], "unread"))
            continue
        problems += reading.problems()
        lines = describe(reading)
        if problems:
            flagged += 1
            lines.append("; ".join(problems))
            print(f"{u.group} ({u.unit_type}): {'; '.join(problems)}")
        markers.append(Marker(lat, lon, label, lines, "flagged" if problems else "ok"))
    summary = (
        f"{len(units)} units, {flagged} flagged, {unread} not read yet, "
        f"{drawn} drawn sites and route markers not checked."
    )
    page = args.map or REPO_ROOT / "tmp" / "placement" / f"{name}_review.html"
    write_review_map(page, args.miz.stem, summary, markers)
    print(summary)
    print(f"review map: {page}")
    return 1 if unread else 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="a check mission for every unit in a .miz")
    check.add_argument("miz", type=Path)
    check.add_argument("--out", type=Path)
    report = sub.add_parser("report", help="flag bad ground and draw the review map")
    report.add_argument("miz", type=Path)
    report.add_argument("--probe-output", type=Path)
    report.add_argument("--map", type=Path)
    args = parser.parse_args(argv)
    if args.command == "check":
        return _cmd_check(args)
    return _cmd_report(args)


if __name__ == "__main__":
    sys.exit(main())
