"""Voice ATC step 2 (§119): chart entry and exit points for Approach and Departure.

Caucasus is the one DCS map whose kneeboard charts draw visual arrival and departure
routes (checked 2026-10-29): Nevada, Kola and the Falklands carry instrument plates only,
Syria three airport diagrams. Its points live in ``resources/voice_atc/caucasus.yaml``;
any other field gets the plugin's generated route, an entry 10 NM out on the inbound
bearing and an initial 5 NM out (user call, 2026-10-29).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

import yaml
from dcs.mapping import LatLng, Point

if TYPE_CHECKING:
    from dcs.terrain import Terrain

ROUTES_DIR = Path("resources/voice_atc")

#: A chart runway matches the DCS end within this many runway numbers (10 degrees each):
#: DCS numbers some Caucasus ends up to 30 degrees off the 2010 charts.
MAX_RUNWAY_NUMBER_OFF = 3


@dataclass(frozen=True)
class RoutePoint:
    name: str
    position: Point
    #: DCS runway ends an inbound flight may enter for here; empty for an exit only.
    entry_runways: tuple[str, ...]
    exit: bool


@dataclass(frozen=True)
class FieldRoutes:
    chart: str
    max_altitude_ft: int
    pattern_ft: int
    points: tuple[RoutePoint, ...]


def _degrees(text: str) -> float:
    """``"42 01.126"`` is 42 degrees 1.126 minutes."""
    whole, minutes = text.split()
    return int(whole) + float(minutes) / 60


def _number(runway: str) -> int:
    match = re.match(r"\d+", runway)
    return int(match.group()) if match else -1


def dcs_runway(chart_runway: str, ends: list[str]) -> Optional[str]:
    """The DCS runway end a chart runway is, by heading; None when none is close."""
    wanted = _number(chart_runway)
    best: Optional[str] = None
    best_off = MAX_RUNWAY_NUMBER_OFF + 1
    for end in ends:
        off = abs(_number(end) - wanted) % 36
        off = min(off, 36 - off)
        if off < best_off:
            best, best_off = end, off
    return best


_COMPASS = (
    "north",
    "northeast",
    "east",
    "southeast",
    "south",
    "southwest",
    "west",
    "northwest",
)


def point_lines(routes: FieldRoutes, field: Point) -> list[str]:
    """``North-East: 7.6 NM northeast, entry runway 25, exit``: the ATC card's rows."""
    lines = []
    for point in routes.points:
        heading = field.heading_between_point(point.position)
        where = _COMPASS[round(heading / 45) % 8]
        distance = field.distance_to_point(point.position) / 1852
        uses = []
        if point.entry_runways:
            uses.append("entry runway " + "/".join(point.entry_runways))
        if point.exit:
            uses.append("exit")
        lines.append(f"{point.name}: {distance:.1f} NM {where}, {', '.join(uses)}")
    return lines


@cache
def _chart_file(terrain_name: str) -> dict[str, Any]:
    path = ROUTES_DIR / f"{terrain_name.lower()}.yaml"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def chart_routes(terrain: Terrain, airfield_name: str) -> Optional[FieldRoutes]:
    """The field's chart routes, or None for a field without a chart."""
    entry = _chart_file(terrain.name).get(airfield_name)
    if entry is None:
        return None
    airport = terrain.airports.get(airfield_name)
    ends: list[str] = []
    for runway in getattr(airport, "runways", []):
        ends.extend([runway.main.name, runway.opposite.name])
    points = []
    for point in entry["points"]:
        runways = []
        for chart_runway in point.get("entry", []):
            if (end := dcs_runway(str(chart_runway), ends)) is None:
                logging.warning(
                    "Voice ATC: %s chart runway %s matches no DCS runway",
                    airfield_name,
                    chart_runway,
                )
            elif end not in runways:
                runways.append(end)
        position = Point.from_latlng(
            LatLng(_degrees(point["lat"]), _degrees(point["lon"])), terrain
        )
        points.append(
            RoutePoint(
                point["name"], position, tuple(runways), bool(point.get("exit", True))
            )
        )
    return FieldRoutes(
        str(entry["chart"]),
        int(entry["max_altitude_ft"]),
        int(entry["pattern_ft"]),
        tuple(points),
    )
