"""AH-64D BLK.II DTC cartridge builder (§74).

Schema mined from ``CoreMods/aircraft/AH-64D/DTC`` plus an ME-saved cartridge
(2.9.29.27278, the shape audit in the DCS-update design note §3). Sections
emitted, all inside ``NAV.Mission_1``:

* ``Points.WPTHZ`` -- the flight's route as waypoints W01.., named via
  ``note``, ground elevation in ``alt``, map metres in ``x``/``y``.
* ``Routes[1]`` ("ALPHA") -- the route sequence over those waypoints with
  per-leg speed (kts), leg distance and cumulative ETA seconds, the shape the
  editor's own add-point handler writes.
* ``Points.TGT`` -- viewer-fogged enemy SAM sites as target points T01..
  (the TSD has no ring radius; the site name rides ``note``).
* ``Lines`` -- the active front lines (FLOT) as TSD lines.

Partitions the planner computes nothing for (Laser, Radios, Weapon, MISC,
Presets, IDM, ADF, CTRLM, Areas, Zones) are omitted or left empty-but-present
per the sample's skeleton -- the aircraft's own defaults stand, the viper
precedent. ADF stays empty deliberately: the sample's ``Freq`` integers carry
no stated unit, so the CSAR beacon slot (checklist G33) waits on a flown
round-trip before anything writes it.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

from game.missiongenerator.dtc.cartridge import DtcCartridge
from game.missiongenerator.dtc.savedpoints import (
    closed_ring,
    cockpit_numbers,
    kept_waypoints,
    player_shapes,
)
from game.missiongenerator.dtc.common import (
    red_land_boundary,
    support_boxes,
    is_route_waypoint,
    threat_sites_for,
    leg_speed_kmh,
    nearest_field_elevation,
    seconds_of_day,
    steerpoint_altitude,
    waypoint_display_name,
)

if TYPE_CHECKING:
    from game import Game
    from game.missiongenerator.aircraft.flightdata import FlightData
    from game.missiongenerator.missiondata import MissionData

APACHE_UNIT_TYPE = "AH-64D_BLK_II"

#: WPTHZ owns waypoints 1-50 (CTRLM takes 51-99).
MAX_WAYPOINTS = 50
#: TGT/THRT points 1-50.
MAX_TARGET_POINTS = 50
#: The editor keeps a TSD line of 2-4 vertices and deletes any other
#: (``NAV/Lines.lua:52,241``); an area has exactly 4 (``NAV/Areas.lua``).
MAX_LINES = 15
MAX_LINE_VERTICES = 4
AREA_VERTICES = 4
MAX_AREAS = 12
#: The boundary is asked for runs this long, then split into 4-vertex lines.
BOUNDARY_RUNS = 3
BOUNDARY_RUN_POINTS = 10
#: The tanker boxes are areas; they take at most this many of the 12.
MAX_SUPPORT_BOXES = 3

#: Symbol ids from the ME-saved sample: 6 = waypoint, 1 = generic target.
_WPTHZ_SYMBOL = 6
_TGT_SYMBOL = 1
#: The sample's line style for a plain TSD line.
_LINE_TYPE = 6

#: The editor's ten route slots, in its own order and spelling (two carry a
#: trailing space in the schema; keep them byte-identical).
_ROUTE_NAMES = [
    "ALPHA",
    "BRAVO",
    "DELTA",
    "ECHO ",
    "HOTEL",
    "INDIA",
    "LIMA ",
    "OSCAR",
    "ROMEO",
    "TANGO",
]


def _nav_point(
    num: int,
    prefix: str,
    symbol: int,
    name: str,
    x: float,
    y: float,
    elevation_m: float,
) -> dict[str, Any]:
    return {
        "num": num,
        "id": symbol,
        "text": f"{prefix}{num:02d}",
        "note": name,
        "x": x,
        "y": y,
        "alt": round(elevation_m),
    }


def _build_waypoints(flight: FlightData, game: Game) -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []
    # Match the kneeboard's numbering: row 0 (takeoff/spawn) is not emitted,
    # so W-number n is kneeboard waypoint n (the Hornet/Viper convention).
    for waypoint in kept_waypoints(flight):
        if len(points) >= MAX_WAYPOINTS:
            break
        points.append(
            _nav_point(
                len(points) + 1,
                "W",
                _WPTHZ_SYMBOL,
                waypoint_display_name(waypoint.display_name or waypoint.name),
                waypoint.position.x,
                waypoint.position.y,
                steerpoint_altitude(waypoint, game),
            )
        )
    return points


def _build_route(
    flight: FlightData, game: Game, waypoints: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """The ALPHA route over the WPTHZ points, in the editor's own element shape.

    Only waypoints the jet actually flies join the sequence -- an off-route
    point (a briefed reference) stays a WPTHZ entry the crew can direct-to.
    ``eta`` is the leg's own seconds, the first point's the start time
    (``NAV/Routes.lua:540-549,857-874``), not a running total.
    """
    legs: list[dict[str, Any]] = []
    prev_wp = None
    prev_point: dict[str, Any] | None = None
    eta = 0.0
    for waypoint, point in zip(kept_waypoints(flight), waypoints):
        if not is_route_waypoint(waypoint):
            continue
        speed_kts = leg_speed_kmh(prev_wp, waypoint) / 1.852
        if prev_point is None:
            distance = 0.0
            eta = float(seconds_of_day(game, waypoint.tot)) if waypoint.tot else 0.0
        else:
            distance = math.hypot(
                point["x"] - prev_point["x"], point["y"] - prev_point["y"]
            )
            eta = distance / (speed_kts * 0.514) if speed_kts > 0 else 0.0
        legs.append(
            {
                "num": point["num"],
                "alt": point["alt"],
                "speed": round(speed_kts, 1),
                "dist": round(distance, 1),
                "eta": round(eta, 1),
                "fix": False,
            }
        )
        prev_wp = waypoint
        prev_point = point
    return legs


#: WPTHZ symbol per saved kind; a kind with no symbol of its own is a waypoint.
_SAVED_SYMBOLS: dict[str, int] = {}


def _saved_waypoints(flight: FlightData) -> list[dict[str, Any]]:
    """The player's saved points (§102) as W-points after the route."""
    points: list[dict[str, Any]] = []
    numbers = cockpit_numbers(flight, flight.saved_points)
    for number, point in zip(numbers, flight.saved_points):
        if number is None:
            continue
        points.append(
            _nav_point(
                number,
                "W",
                _SAVED_SYMBOLS.get(point.kind.value, _WPTHZ_SYMBOL),
                waypoint_display_name(point.name),
                point.x,
                point.y,
                point.altitude_ft * 0.3048,
            )
        )
    return points


def _saved_route(points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Route BRAVO over the saved points, so stepping through them is a switch."""
    legs: list[dict[str, Any]] = []
    for point in points:
        legs.append(
            {
                "num": point["num"],
                "alt": point["alt"],
                "speed": 0.0,
                "dist": 0.0,
                "eta": 0.0,
                "fix": False,
            }
        )
    return legs


def _build_targets(flight: FlightData, game: Game) -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []
    for site in threat_sites_for(game, flight)[:MAX_TARGET_POINTS]:
        points.append(
            _nav_point(
                len(points) + 1,
                "T",
                _TGT_SYMBOL,
                site.name,
                site.x,
                site.y,
                # The sight slaves to the point in 3D (manual, TADS acquisition), so
                # sea level would put the cue under a site on high ground.
                nearest_field_elevation(game, site.x, site.y),
            )
        )
    return points


def _chunks(corners: list[tuple[float, float]]) -> list[list[tuple[float, float]]]:
    """A long line as consecutive 4-vertex lines that share their joining corner."""
    step = MAX_LINE_VERTICES - 1
    return [
        corners[start : start + MAX_LINE_VERTICES]
        for start in range(0, max(len(corners) - 1, 1), step)
        if len(corners[start : start + MAX_LINE_VERTICES]) >= 2
    ]


def _line(name: str, piece: list[tuple[float, float]]) -> dict[str, Any]:
    return {
        "note": name,
        "text": "",
        "type_num": _LINE_TYPE,
        "vertices": [{"x": x, "y": y} for x, y in piece],
    }


def _area(name: str, corners: list[tuple[float, float]]) -> dict[str, Any]:
    """The editor's own shape for a new area (``NAV/Areas.lua:498-501``)."""
    return {
        "note": name,
        "vertices": [{"x": x, "y": y} for x, y in corners],
        "caption_pos": [],
        "center_pos": {"x": 0, "y": 0},
    }


def _build_lines(
    game: Game, mission_data: MissionData, flight: FlightData
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """The red-land boundary as 4-vertex lines, and each usable tanker as an area."""
    options = flight.dtc_options
    lines: list[dict[str, Any]] = []
    areas: list[dict[str, Any]] = []
    if options.flot_and_zones:
        for name, points in red_land_boundary(game, BOUNDARY_RUNS, BOUNDARY_RUN_POINTS):
            for piece in _chunks(points):
                if len(lines) < MAX_LINES:
                    lines.append(_line(name, piece))
    if options.friendly_orbits:
        for name, box in support_boxes(mission_data, MAX_SUPPORT_BOXES, flight):
            corners = box[:-1] if len(box) > 1 and box[0] == box[-1] else box
            if len(corners) == AREA_VERTICES:
                areas.append(_area(name, corners))
    return lines, areas


def _player_drawings(
    flight: FlightData, lines_used: int, areas_used: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """The player's orbits and drawings (§102) as TSD lines and areas."""
    lines: list[dict[str, Any]] = []
    areas: list[dict[str, Any]] = []
    for name, corners, closed in player_shapes(flight, orbits_as_boxes=True):
        if (
            closed
            and len(corners) == AREA_VERTICES
            and areas_used + len(areas) < MAX_AREAS
        ):
            areas.append(_area(name, corners))
            continue
        pieces = _chunks(closed_ring(corners) if closed else corners)
        if lines_used + len(lines) + len(pieces) > MAX_LINES:
            continue
        lines.extend(_line(name, piece) for piece in pieces)
    return lines, areas


def _empty_mission() -> dict[str, Any]:
    return {
        "Points": {
            "WPTHZ": {"isEnabled": True, "POINTS": []},
            "CTRLM": {"isEnabled": True, "POINTS": []},
            "TGT": {"isEnabled": True, "POINTS": []},
        },
        "Routes": [
            {"isEnabled": False, "Name": name, "POINTS": []} for name in _ROUTE_NAMES
        ],
        "Lines": [],
        "Areas": [],
        "Zones": {"NFZ": [], "PFZ": []},
    }


def build_apache_cartridge(
    flight: FlightData, mission_data: MissionData, game: Game, name: str
) -> DtcCartridge:
    terrain = game.theater.terrain.name
    options = flight.dtc_options
    mission = _empty_mission()
    if options.route:
        waypoints = _build_waypoints(flight, game)
        mission["Points"]["WPTHZ"]["POINTS"] = waypoints
        legs = _build_route(flight, game, waypoints)
        if legs:
            mission["Routes"][0]["isEnabled"] = True
            mission["Routes"][0]["POINTS"] = legs
        if options.saved_points:
            saved = _saved_waypoints(flight)
            if saved:
                waypoints.extend(saved)
                mission["Routes"][1]["isEnabled"] = True
                mission["Routes"][1]["POINTS"] = _saved_route(saved)
    if options.threat_rings:
        mission["Points"]["TGT"]["POINTS"] = _build_targets(flight, game)
    support_areas: list[dict[str, Any]] = []
    if options.flot_and_zones or options.friendly_orbits:
        mission["Lines"], support_areas = _build_lines(game, mission_data, flight)
    player_lines, player_areas = _player_drawings(
        flight, len(mission["Lines"]), len(support_areas)
    )
    mission["Lines"].extend(player_lines)
    mission["Areas"] = support_areas + player_areas

    data: dict[str, Any] = {
        "type": APACHE_UNIT_TYPE,
        "name": name,
        "terrain": terrain,
        "NAV": {
            "MissionFile": 1,
            "Mission_1": mission,
            "Mission_2": _empty_mission(),
        },
    }
    return DtcCartridge(
        name=name, unit_type=APACHE_UNIT_TYPE, terrain=terrain, data=data
    )
