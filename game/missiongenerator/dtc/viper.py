"""F-16C DTC cartridge builder (§74).

Sections emitted (schema mined from ``CoreMods/aircraft/F-16C/DTC``):

* No ``COMM``: the Viper's channel schema has no name field, so the section
  could only mirror the ``Radio`` table upstream's channel allocator already
  writes into the unit. Dropped 2026-08-22 -- the presets come from the miz.
* ``MPD.NAV_PTS`` -- steerpoints with TOS + per-leg speed inline (the Viper
  keeps route timing on the point, unlike the Hornet's separate route table),
  named via the ``note`` field; the flight route first, then the flight's OWN
  orbit (racetrack or hold point) and the tanker / AEW&C anchors as extra
  steerpoints (the SA-page ask, Viper-style -- the jet has no orbit element).
  The jet auto-sequences only 1-20 and reserves 25 for the bullseye, so the
  route takes 1-20 and anchors 21-24.
* ``MPD.GEO_LINES`` -- land borders within 40 NM of the route, the player's
  drawings, a box around each tanker this jet can use, then the boundary with
  red land, in that priority. The four sets share 25 points.
* ``MPD.THREAT_PTS`` -- viewer-fogged enemy SAM rings ("Custom" type, radius
  in meters, <= 15).
* ``MPD.DEST`` -- friendly recovery fields as Destination steerpoints 81-99,
  labelled with the HSD's 3-character Destination text, plus the hostile field
  the flight is working over when there is one within 10 NM of the target.
* ``MPD.CMDS`` -- the countermeasure dispenser: MAN 1 flares only, MAN 5 chaff
  only, everything else the module's own value. ``CMDSPrograms`` carries the
  module's own per-threat auto programs in full (AUTO 2, search radars and
  AWACS NONE), exported by ``tools/export_viper_cmds_threats.py``: an empty
  table leaves AUTO and SEMI with nothing to answer.
* ``MPD.ROE`` -- the ROE tab's Air Target Data Table derived from the
  campaign's order of battle (see ``roedata``). Rows carry only
  ``{group_name, sovereignty}``: the jet's own ``make_ROE_table`` compiles
  membership from its ``threat_base`` and reads nothing else from the file.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

from game.ato.flighttype import FlightType
from game.missiongenerator.dtc.cartridge import DtcCartridge
from game.missiongenerator.dtc.roedata import build_atdt
from game.missiongenerator.dtc.savedpoints import (
    closed_ring,
    cockpit_numbers,
    kept_waypoints,
    player_shapes,
)
from game.missiongenerator.dtc.common import (
    SupportTrack,
    country_at,
    country_code,
    decimate_open,
    land_border_runs,
    leg_altitude,
    ground_elevation,
    red_land_boundary,
    support_boxes,
    SUPPORT_BOX_POINTS,
    is_route_waypoint,
    is_target_waypoint,
    threat_sites_for,
    leg_speed_kmh,
    own_orbit_track,
    seconds_of_day,
    support_tracks,
    waypoint_display_name,
)

if TYPE_CHECKING:
    from game import Game
    from game.ato.flightwaypoint import FlightWaypoint
    from game.missiongenerator.aircraft.flightdata import FlightData
    from game.missiongenerator.missiondata import MissionData

VIPER_UNIT_TYPE = "F-16C_50"

#: STPT 25 is the jet's BULLSEYE -- "automatically configured as such when a
#: mission is loaded" (EA guide p325) -- so a 25th nav point overwrites it and
#: every bullseye readout reads the anchor instead. Test 36 put the AWACS orbit
#: there. Stop at 24; DCS fills 25 from the miz, which §95 already pins.
MAX_STEERPOINTS = 24
#: The jet auto-sequences only from STPT 1-20 (EA guide p223), so the flown
#: route stops there and the support anchors take 21-24.
MAX_ROUTE_STEERPOINTS = 20
MAX_GEO_LINE_SETS = 4
#: GEO_LINES owns steerpoints 31-55 (``GEO_LINES.lua`` refuses a 26th point,
#: which would land in the pre-planned-threat partition at 56). The 25 are
#: shared across the four line sets with no per-set cap of their own, so the
#: boundary takes L1 whole and L2-L4 stay free.
MAX_GEO_POINTS = 25
#: What borders and the front line keep however much the player draws (§102).
MIN_BOUNDARY_POINTS = 10
#: A border this far either side of the route is drawn: the HSD's 60 NM scale
#: shows it from the route in DEP.
BORDER_CORRIDOR_M = 40 * 1852.0
#: Line sets borders may take, so a tanker box or the front line still fits.
MAX_BORDER_LINE_SETS = 2
#: DM split (2026-09-29): borders near a route want 16-41 points, so without a
#: cap they took everything and left the front line a 2-point stick.
MAX_BORDER_POINTS = 12
#: The front line's share when borders are drawn; alone, it takes what is left.
FRONT_POINTS_WITH_BORDERS = 4
#: ... and beside borders and a working-area box (DM pick 2026-10-08).
FRONT_POINTS_WITH_WORK_BOX = 3
#: The flights that get a box on their working area, and its tag.
WORK_BOX_TAGS = {
    FlightType.CAS: "CAS",
    FlightType.SEAD: "SD",
    FlightType.SEAD_SWEEP: "SD",
}
#: Destination slots the line tags may take; the recovery fields keep the rest.
MAX_LINE_LABELS = 8
#: How far either side of a border its two country tags sit.
BORDER_LABEL_OFFSET_M = 3 * 1852.0


@dataclass(frozen=True)
class LineLabel:
    """A Destination tag naming an HSD line; the text is cut to 3 characters."""

    text: str
    x: float
    y: float
    note: str


MAX_THREAT_POINTS = 15
#: DEST owns steerpoints 81-99, and the editor refuses a 20th.
MAX_DESTINATIONS = 19
#: A hostile field within this of the target is the one the flight is working
#: over, so it goes on the DEST page beside the recovery options.
TARGET_AIRFIELD_RADIUS_M = 18520.0  # 10 NM

#: Stock preset frequencies (MHz), from the module's COMM defaults.
_COM1_DEFAULT_FREQS = [
    305.0, 264.0, 265.0, 256.0, 254.0, 250.0, 270.0, 257.0, 255.0, 262.0,
    259.0, 268.0, 269.0, 260.0, 263.0, 261.0, 267.0, 251.0, 253.0, 266.0,
]  # fmt: skip
_COM2_DEFAULT_FREQS = [
    124.0, 135.0, 136.0, 127.0, 125.0, 121.0, 141.0, 128.0, 126.0, 133.0,
    130.0, 139.0, 140.0, 131.0, 134.0, 132.0, 138.0, 122.0, 124.0, 137.0,
]  # fmt: skip

#: The Custom threat type's stock ceiling (meters; 30,000 ft) from
#: THREAT_PTS_defs.
_CUSTOM_THREAT_ALT = 9144


def _steerpoint(
    number: int,
    name: str,
    x: float,
    y: float,
    altitude_m: float,
    altitude_type: int,
    on_route: bool,
    speed_kmh: float,
    tos: int,
    tos_enabled: bool,
    point_type: str,
) -> dict[str, Any]:
    return {
        "number": number,
        "id": f"STPT{number}",
        "type": point_type,
        "note": name,
        "x": x,
        "y": y,
        # The DED's ELEV (flown 2026-09-13); routeAltitude below is the DTC
        # Manager's planning copy of the same number.
        "alt": altitude_m,
        "altitudeType": altitude_type,
        "R1": on_route,
        "R2": False,
        "R3": False,
        "speed": speed_kmh,
        "velocityType": 3,
        "TOS": tos,
        "isTOSEnabled": tos_enabled,
        "FIX_Time": tos_enabled,
        "routeAltitude": altitude_m,
        "isOAP_1": False,
        "idOA1": f"OA1{number}",
        "idOA1_Line": f"OA1{number}Line",
        "OAP_1_X": 0,
        "OAP_1_Y": 0,
        "OAP_1_Alt": 0,
        "OAP_1_Bearing": 0,
        "OAP_1_Range": 0,
        "OAP_1_DeltaX": 0,
        "OAP_1_DeltaY": 0,
        "isOAP_2": False,
        "idOA2": f"OA2{number}",
        "idOA2_Line": f"OA2{number}Line",
        "OAP_2_X": 0,
        "OAP_2_Y": 0,
        "OAP_2_Alt": 0,
        "OAP_2_Bearing": 0,
        "OAP_2_Range": 0,
        "OAP_2_DeltaX": 0,
        "OAP_2_DeltaY": 0,
    }


#: The HSD symbol for the saved kinds that have one (square IP, triangle target).
_SAVED_TYPES = {"ip": "IP", "target": "TGT"}


def _steerpoint_type(waypoint: FlightWaypoint) -> str:
    """STPT / IP / TGT -- the three HSD symbols (circle, square, triangle)."""
    if is_target_waypoint(waypoint):
        return "TGT"
    if "INGRESS" in waypoint.waypoint_type.name:
        return "IP"
    return "STPT"


def _dest_label(name: str, taken: set[str]) -> str:
    """The HSD draws a Destination as up to 3 alphanumerics (EA guide p203)."""
    base = "".join(c for c in name.upper() if c.isalnum())[:3] or "DST"
    label, suffix = base, 2
    while label in taken and suffix < 100:
        tail = str(suffix)
        label = f"{base[: 3 - len(tail)]}{tail}"
        suffix += 1
    taken.add(label)
    return label


def _dest_reference(flight: FlightData) -> Any:
    """Sort destinations by distance from the target, else the last waypoint."""
    for waypoint in flight.waypoints:
        if is_target_waypoint(waypoint):
            return waypoint.position
    return flight.waypoints[-1].position if flight.waypoints else None


def _target_airfield(flight: FlightData, game: Game) -> Any:
    """The hostile field the flight is working over, if there is one.

    Not a recovery option -- it earns a Destination slot because the HSD is
    where the crew wants the field they are attacking or fighting above, and
    only the DEST partition draws an airfield. Keep it out of the divert slot.
    """
    reference = _dest_reference(flight)
    if reference is None:
        return None
    nearest = None
    closest = TARGET_AIRFIELD_RADIUS_M
    for cp in game.theater.controlpoints:
        if not cp.captured.is_red or cp.is_fleet:
            continue
        distance = cp.position.distance_to_point(reference)
        if distance <= closest:
            nearest, closest = cp, distance
    return nearest


def _build_dest(
    flight: FlightData, game: Game, labels: list[LineLabel]
) -> list[dict[str, Any]]:
    """Recovery fields as Destination steerpoints, plus the target's field, then
    the tags naming the HSD lines.

    The briefed divert leads the list, the hostile field the flight is working
    over follows it so the cap can never squeeze it out, and the rest sort by
    distance from the target so the nearest alternates fill what the line tags
    leave of the 19 slots. The HSD writes no text on a line (EA guide p328), so
    a Destination beside it is the only way to name one.
    """
    if not flight.dtc_options.destinations:
        return _label_dests(labels, set(), 1, game)
    reference = _dest_reference(flight)
    divert_name = flight.divert.airfield_name if flight.divert else None
    fields = []
    for cp in game.theater.controlpoints:
        if cp.captured.is_red or not cp.runway_is_operational():
            continue
        distance = (
            cp.position.distance_to_point(reference) if reference is not None else 0.0
        )
        fields.append((cp.name != divert_name, distance, cp))
    fields.sort(key=lambda entry: (entry[0], entry[1]))
    ordered = [cp for _, _, cp in fields]

    hostile = _target_airfield(flight, game)
    if hostile is not None:
        ordered.insert(1 if ordered else 0, hostile)

    taken: set[str] = set()
    field_dests = [
        {
            "number": index,
            "id": f"DEST{80 + index}",
            "x": cp.position.x,
            "y": cp.position.y,
            "alt": cp.field_elevation.meters,
            "text": _dest_label(cp.name, taken),
            "note": cp.name,
        }
        for index, cp in enumerate(ordered[: MAX_DESTINATIONS - len(labels)], start=1)
    ]
    return field_dests + _label_dests(labels, taken, len(field_dests) + 1, game)


def _label_dests(
    labels: list[LineLabel], taken: set[str], first: int, game: Game
) -> list[dict[str, Any]]:
    return [
        {
            "number": number,
            "id": f"DEST{80 + number}",
            "x": label.x,
            "y": label.y,
            "alt": ground_elevation(game, label.x, label.y),
            "text": _dest_label(label.text, taken),
            "note": label.note,
        }
        for number, label in enumerate(labels, start=first)
    ]


def _anchor_name(track: SupportTrack) -> str:
    return f"{track.kind} {track.callsign}".strip()


def _build_nav_pts(
    flight: FlightData, mission_data: MissionData, game: Game
) -> list[dict[str, Any]]:
    options = flight.dtc_options
    points: list[dict[str, Any]] = []
    prev_route_wp = None
    # Match the kneeboard's numbering: its row 0 (takeoff/spawn) is not
    # emitted, so STPT n in the jet is kneeboard waypoint n (the flown
    # Hornet off-by-one applied here identically).
    waypoints = kept_waypoints(flight) if options.route else []
    for waypoint in waypoints:
        if len(points) >= MAX_ROUTE_STEERPOINTS:
            break
        number = len(points) + 1
        on_route = is_route_waypoint(waypoint)
        altitude_m, altitude_type = leg_altitude(waypoint, game)
        points.append(
            _steerpoint(
                number,
                waypoint_display_name(waypoint.display_name or waypoint.name),
                waypoint.position.x,
                waypoint.position.y,
                altitude_m,
                altitude_type,
                on_route,
                leg_speed_kmh(prev_route_wp if on_route else None, waypoint),
                seconds_of_day(game, waypoint.tot, flight.mission_start),
                waypoint.tot is not None,
                _steerpoint_type(waypoint),
            )
        )
        if on_route:
            prev_route_wp = waypoint
    # The player's saved points (§102) come before the automatic anchors.
    if options.route and options.saved_points:
        numbers = cockpit_numbers(flight, flight.saved_points)
        for slot, point in zip(numbers, flight.saved_points):
            if slot is None:
                continue
            alt_m = point.altitude_ft * 0.3048
            steerpoint = _steerpoint(
                slot,
                waypoint_display_name(point.name),
                point.x,
                point.y,
                alt_m,
                1,
                False,
                463.0,
                0,
                False,
                _SAVED_TYPES.get(point.kind.value, "STPT"),
            )
            steerpoint["R2"] = True
            points.append(steerpoint)
    # Support anchors after the route: this flight's own orbit (racetrack, or
    # the hold point when it flies none), then the tanker/AEW&C orbits -- the
    # Viper's stand-in for the Hornet's SA racetracks. Other flights' CAP
    # stations are not this jet's business.
    if options.friendly_orbits:
        own = own_orbit_track(flight)
        anchors = ([own] if own is not None else []) + support_tracks(mission_data)
        for track in anchors:
            if len(points) >= MAX_STEERPOINTS:
                break
            number = len(points) + 1
            x, y = track.center
            points.append(
                _steerpoint(
                    number,
                    _anchor_name(track),
                    x,
                    y,
                    track.altitude_m,
                    1,
                    False,
                    463.0,
                    0,
                    False,
                    "STPT",
                )
            )
    return points


#: The module's own program values (``MPD/CMDS_defs.lua``), overridden below
#: for the two manual slots. The table is written whole because ``CMDS.lua``
#: indexes every program and dispenser without a nil guard.
_CMDS_PROGRAM_DEFAULTS: dict[str, dict[str, dict[str, float]]] = {
    "MAN1": {
        "Chaff": {
            "BurstQuantity": 1,
            "BurstInterval": 0.02,
            "SalvoQuantity": 10,
            "SalvoInterval": 1.0,
        },
        "Flare": {
            "BurstQuantity": 1,
            "BurstInterval": 0.02,
            "SalvoQuantity": 10,
            "SalvoInterval": 1.0,
        },
        "Other1": {
            "BurstQuantity": 0,
            "BurstInterval": 0.02,
            "SalvoQuantity": 0,
            "SalvoInterval": 0.5,
        },
        "Other2": {
            "BurstQuantity": 0,
            "BurstInterval": 0.02,
            "SalvoQuantity": 0,
            "SalvoInterval": 0.5,
        },
    },
    "MAN2": {
        "Chaff": {
            "BurstQuantity": 1,
            "BurstInterval": 0.02,
            "SalvoQuantity": 10,
            "SalvoInterval": 0.5,
        },
        "Flare": {
            "BurstQuantity": 1,
            "BurstInterval": 0.02,
            "SalvoQuantity": 10,
            "SalvoInterval": 0.5,
        },
        "Other1": {
            "BurstQuantity": 0,
            "BurstInterval": 0.02,
            "SalvoQuantity": 0,
            "SalvoInterval": 0.5,
        },
        "Other2": {
            "BurstQuantity": 0,
            "BurstInterval": 0.02,
            "SalvoQuantity": 0,
            "SalvoInterval": 0.5,
        },
    },
    "MAN3": {
        "Chaff": {
            "BurstQuantity": 2,
            "BurstInterval": 0.1,
            "SalvoQuantity": 5,
            "SalvoInterval": 1.0,
        },
        "Flare": {
            "BurstQuantity": 2,
            "BurstInterval": 0.1,
            "SalvoQuantity": 5,
            "SalvoInterval": 1.0,
        },
        "Other1": {
            "BurstQuantity": 0,
            "BurstInterval": 0.02,
            "SalvoQuantity": 0,
            "SalvoInterval": 0.5,
        },
        "Other2": {
            "BurstQuantity": 0,
            "BurstInterval": 0.02,
            "SalvoQuantity": 0,
            "SalvoInterval": 0.5,
        },
    },
    "MAN4": {
        "Chaff": {
            "BurstQuantity": 2,
            "BurstInterval": 0.1,
            "SalvoQuantity": 5,
            "SalvoInterval": 0.5,
        },
        "Flare": {
            "BurstQuantity": 2,
            "BurstInterval": 0.1,
            "SalvoQuantity": 5,
            "SalvoInterval": 0.5,
        },
        "Other1": {
            "BurstQuantity": 0,
            "BurstInterval": 0.02,
            "SalvoQuantity": 0,
            "SalvoInterval": 0.5,
        },
        "Other2": {
            "BurstQuantity": 0,
            "BurstInterval": 0.02,
            "SalvoQuantity": 0,
            "SalvoInterval": 0.5,
        },
    },
    "MAN5": {
        "Chaff": {
            "BurstQuantity": 2,
            "BurstInterval": 0.05,
            "SalvoQuantity": 20,
            "SalvoInterval": 0.75,
        },
        "Flare": {
            "BurstQuantity": 2,
            "BurstInterval": 0.05,
            "SalvoQuantity": 20,
            "SalvoInterval": 0.75,
        },
        "Other1": {
            "BurstQuantity": 0,
            "BurstInterval": 0.02,
            "SalvoQuantity": 0,
            "SalvoInterval": 0.5,
        },
        "Other2": {
            "BurstQuantity": 0,
            "BurstInterval": 0.02,
            "SalvoQuantity": 0,
            "SalvoInterval": 0.5,
        },
    },
    "MAN6": {
        "Chaff": {
            "BurstQuantity": 1,
            "BurstInterval": 0.02,
            "SalvoQuantity": 1,
            "SalvoInterval": 0.5,
        },
        "Flare": {
            "BurstQuantity": 1,
            "BurstInterval": 0.02,
            "SalvoQuantity": 1,
            "SalvoInterval": 0.5,
        },
        "Other1": {
            "BurstQuantity": 0,
            "BurstInterval": 0.02,
            "SalvoQuantity": 0,
            "SalvoInterval": 0.5,
        },
        "Other2": {
            "BurstQuantity": 0,
            "BurstInterval": 0.02,
            "SalvoQuantity": 0,
            "SalvoInterval": 0.5,
        },
    },
    "AUTO1": {
        "Chaff": {
            "BurstQuantity": 1,
            "BurstInterval": 0.02,
            "SalvoQuantity": 4,
            "SalvoInterval": 1.5,
        },
        "Flare": {
            "BurstQuantity": 0,
            "BurstInterval": 0.0,
            "SalvoQuantity": 0,
            "SalvoInterval": 0.0,
        },
        "Other1": {
            "BurstQuantity": 0,
            "BurstInterval": 0.02,
            "SalvoQuantity": 0,
            "SalvoInterval": 0.5,
        },
        "Other2": {
            "BurstQuantity": 0,
            "BurstInterval": 0.02,
            "SalvoQuantity": 0,
            "SalvoInterval": 0.5,
        },
    },
    "AUTO2": {
        "Chaff": {
            "BurstQuantity": 1,
            "BurstInterval": 0.02,
            "SalvoQuantity": 6,
            "SalvoInterval": 1.0,
        },
        "Flare": {
            "BurstQuantity": 0,
            "BurstInterval": 0.0,
            "SalvoQuantity": 0,
            "SalvoInterval": 0.0,
        },
        "Other1": {
            "BurstQuantity": 0,
            "BurstInterval": 0.02,
            "SalvoQuantity": 0,
            "SalvoInterval": 0.5,
        },
        "Other2": {
            "BurstQuantity": 0,
            "BurstInterval": 0.02,
            "SalvoQuantity": 0,
            "SalvoInterval": 0.5,
        },
    },
    "AUTO3": {
        "Chaff": {
            "BurstQuantity": 1,
            "BurstInterval": 0.02,
            "SalvoQuantity": 8,
            "SalvoInterval": 0.5,
        },
        "Flare": {
            "BurstQuantity": 0,
            "BurstInterval": 0.0,
            "SalvoQuantity": 0,
            "SalvoInterval": 0.0,
        },
        "Other1": {
            "BurstQuantity": 0,
            "BurstInterval": 0.02,
            "SalvoQuantity": 0,
            "SalvoInterval": 0.5,
        },
        "Other2": {
            "BurstQuantity": 0,
            "BurstInterval": 0.02,
            "SalvoQuantity": 0,
            "SalvoInterval": 0.5,
        },
    },
    "BYP": {
        "Chaff": {
            "BurstQuantity": 1,
            "BurstInterval": 0.02,
            "SalvoQuantity": 1,
            "SalvoInterval": 0.5,
        },
        "Flare": {
            "BurstQuantity": 1,
            "BurstInterval": 0.02,
            "SalvoQuantity": 1,
            "SalvoInterval": 0.5,
        },
        "Other1": {
            "BurstQuantity": 0,
            "BurstInterval": 0.02,
            "SalvoQuantity": 0,
            "SalvoInterval": 0.5,
        },
        "Other2": {
            "BurstQuantity": 0,
            "BurstInterval": 0.02,
            "SalvoQuantity": 0,
            "SalvoInterval": 0.5,
        },
    },
}

#: MAN 1 answers an IR shot and MAN 5 a radar one, so a pilot under fire picks
#: the dispenser by which missile is on them rather than reprogramming in the
#: cockpit. Single-dispenser programs, which the stock all-both values are not.
_MAN1_FLARES = {"BurstQuantity": 5, "BurstInterval": 0.5, "SalvoQuantity": 1, "SalvoInterval": 0.0}  # fmt: skip
_MAN5_CHAFF = {"BurstQuantity": 2, "BurstInterval": 0.1, "SalvoQuantity": 5, "SalvoInterval": 0.75}  # fmt: skip
_NO_DISPENSE = {"BurstQuantity": 0, "BurstInterval": 0.0, "SalvoQuantity": 0, "SalvoInterval": 0.0}  # fmt: skip


#: The jet's compiled CMDS threat table, from ``tools/export_viper_cmds_threats.py``.
CMDS_THREATS_PATH = (
    Path(__file__).resolve().parents[3] / "resources" / "dtc" / "f16c_cmds_threats.json"
)


@cache
def _cmds_threats() -> dict[str, Any]:
    with CMDS_THREATS_PATH.open(encoding="utf-8") as source:
        return json.load(source)


def _build_cmds_programs() -> dict[str, Any]:
    """The per-threat auto programs exactly as the DTC editor compiles them:
    the avionics table the jet reads, plus the per-category grid it shows."""
    exported = _cmds_threats()
    programs: dict[str, Any] = {
        "CMDS_Avionics_Threat_Table": [],
        "delayBetweenPrograms": exported["delayBetweenPrograms"],
        "Air": {},
        "Ground": {},
        "Naval": {},
        "Other": {},
    }
    for threat in exported["threats"]:
        setting = {
            "program": threat["program"],
            "thresholds": threat["thresholds"],
            "default_threshold": threat["default_threshold"],
        }
        programs["CMDS_Avionics_Threat_Table"].append(
            {
                "group_name": threat["group_name"],
                "hint": threat["hint"],
                "threats": threat["threats"],
                **setting,
            }
        )
        if threat["category"] is not None:
            programs[threat["category"]][threat["group_name"]] = setting
    return programs


def _build_cmds() -> dict[str, Any]:
    programs: dict[str, Any] = {
        name: {dispenser: dict(values) for dispenser, values in program.items()}
        for name, program in _CMDS_PROGRAM_DEFAULTS.items()
    }
    programs["MAN1"]["Chaff"] = dict(_NO_DISPENSE)
    programs["MAN1"]["Flare"] = dict(_MAN1_FLARES)
    programs["MAN5"]["Chaff"] = dict(_MAN5_CHAFF)
    programs["MAN5"]["Flare"] = dict(_NO_DISPENSE)
    return {
        "CMDSBingoSettings": {
            "ChaffNum": 10,
            "FlaresNum": 10,
            "Other1Num": 0,
            "Other2Num": 0,
            "FDBK": True,
            "REQCTR": True,
            "BINGO": True,
        },
        "CMDSProgramSettings": programs,
        "CMDSPrograms": _build_cmds_programs(),
    }


def _middle(points: list[tuple[float, float]]) -> tuple[float, float]:
    return points[len(points) // 2]


def _anchor(corners: list[tuple[float, float]]) -> tuple[float, float]:
    """A closed shape's tag goes in its middle, an open line's on its middle vertex."""
    if len(corners) > 2 and corners[0] == corners[-1]:
        ring = corners[:-1]
        return (
            sum(x for x, _ in ring) / len(ring),
            sum(y for _, y in ring) / len(ring),
        )
    return _middle(corners)


def _border_labels(game: Game, points: list[tuple[float, float]]) -> list[LineLabel]:
    """A country tag each side of the border's middle, so the crew can read which
    side is which."""
    index = max(1, len(points) // 2)
    (ax, ay), (bx, by) = points[index - 1], points[index]
    length = math.hypot(bx - ax, by - ay) or 1.0
    nx, ny = -(by - ay) / length, (bx - ax) / length
    mx, my = (ax + bx) / 2, (ay + by) / 2
    labels = []
    for side in (1.0, -1.0):
        x = mx + side * nx * BORDER_LABEL_OFFSET_M
        y = my + side * ny * BORDER_LABEL_OFFSET_M
        country = country_at(game, x, y)
        if country is not None:
            labels.append(LineLabel(country_code(country), x, y, country))
    return labels


def _work_box(flight: FlightData) -> list[tuple[float, float]] | None:
    """A closed box around the zone the map draws for a CAS or SEAD flight: its
    engagement range either side of the track, or round the point."""
    zone = flight.work_zone
    if flight.flight_type not in WORK_BOX_TAGS or zone is None or not zone.points:
        return None
    radius = zone.radius.meters
    (ax, ay), (bx, by) = (
        (zone.points[0].x, zone.points[0].y),
        (zone.points[-1].x, zone.points[-1].y),
    )
    length = math.hypot(bx - ax, by - ay)
    ux, uy = ((bx - ax) / length, (by - ay) / length) if length else (1.0, 0.0)
    nx, ny = -uy, ux
    corners = [
        (px + along * ux + side * nx, py + along * uy + side * ny)
        for (px, py), along, side in (
            ((ax, ay), -radius, -radius),
            ((bx, by), radius, -radius),
            ((bx, by), radius, radius),
            ((ax, ay), -radius, radius),
        )
    ]
    return closed_ring(corners)


def _build_geo_lines(
    game: Game, mission_data: MissionData, flight: FlightData
) -> tuple[list[dict[str, Any]], list[LineLabel]]:
    """The HSD's four line sets, filled in priority order until the sets or the
    25 shared points run out.

    1. The player's orbits and drawings (§102): drawn on purpose.
    2. Land borders near the route: crossing one can start a fight (§98). At
       most 12 points when the front line is drawn, otherwise what is left.
    3. A box on a CAS or SEAD flight's working area.
    4. A box on each tanker this jet can use, nearest first; only one beside
       borders and the front line.
    5. The boundary with red land (the front line), when ticked (by default
       on CAS flights only, DM call 2026-10-08): 4 points
       beside borders, 3 beside borders and a working box, otherwise what is
       left.

    Borders and the front line are thinned to fit; a box or a drawing missing a
    corner is nonsense, so those go in whole or not at all.
    """
    options = flight.dtc_options
    player: list[tuple[str, list[tuple[float, float]]]] = []
    player_budget = MAX_GEO_POINTS - MIN_BOUNDARY_POINTS
    for name, points, closed in player_shapes(flight, orbits_as_boxes=True):
        corners = closed_ring(points) if closed else points
        if len(player) >= MAX_GEO_LINE_SETS - 1 or len(corners) > player_budget:
            continue
        player.append((name, corners))
        player_budget -= len(corners)
    fixed = sum(len(corners) for _name, corners in player)
    sets_left = MAX_GEO_LINE_SETS - len(player)

    route = [
        (w.position.x, w.position.y) for w in flight.waypoints if is_route_waypoint(w)
    ]
    borders = (
        land_border_runs(game, route, BORDER_CORRIDOR_M)[
            : min(MAX_BORDER_LINE_SETS, sets_left)
        ]
        if options.borders
        else []
    )
    sets_left -= len(borders)
    draw_front = options.flot_and_zones
    front_set = 1 if draw_front else 0
    min_lines = MIN_BOUNDARY_POINTS if borders or draw_front else 0

    work: list[tuple[str, list[tuple[float, float]]]] = []
    work_corners = _work_box(flight) if options.route else None
    if (
        work_corners is not None
        and sets_left > front_set
        and fixed + len(work_corners) <= MAX_GEO_POINTS - min_lines
    ):
        work.append((WORK_BOX_TAGS[flight.flight_type], work_corners))
        fixed += len(work_corners)
        sets_left -= 1

    # One tanker box beside borders and the front line, so the front keeps a set.
    box_sets = min(sets_left, 1) if borders and draw_front else sets_left - front_set
    boxes = (
        support_boxes(mission_data, box_sets, flight)
        if options.friendly_orbits and box_sets > 0
        else []
    )
    while boxes and fixed + len(boxes) * SUPPORT_BOX_POINTS > (
        MAX_GEO_POINTS - min_lines
    ):
        boxes.pop()
    fixed += len(boxes) * SUPPORT_BOX_POINTS
    sets_left -= len(boxes)

    front: list[tuple[str, list[tuple[float, float]]]] = []
    if draw_front and sets_left > 0:
        front = red_land_boundary(game, 1, MAX_GEO_POINTS)
    # Thinned lines take what the whole shapes leave: the front line's share is
    # set aside first, then borders take up to their cap.
    lines: list[tuple[str, list[tuple[float, float]]]] = []
    labels: list[LineLabel] = []
    room = MAX_GEO_POINTS - fixed
    front_cap = FRONT_POINTS_WITH_WORK_BOX if work else FRONT_POINTS_WITH_BORDERS
    front_share = min(len(front[0][1]), front_cap) if front else 0
    border_cap = MAX_BORDER_POINTS if draw_front else MAX_GEO_POINTS
    border_room = min(border_cap, room - front_share)
    for index, (name, points) in enumerate(borders):
        share = min(len(points), border_room // (len(borders) - index))
        if share < 2:
            break
        lines.append((name, decimate_open(points, share)))
        labels.extend(_border_labels(game, points))
        border_room -= share
        room -= share
    if front:
        share = min(len(front[0][1]), room if not lines else front_share)
        if share >= 2:
            lines.append((front[0][0], decimate_open(front[0][1], share)))
            x, y = _middle(front[0][1])
            labels.append(LineLabel("FLT", x, y, "Front line"))
    for name, corners in player:
        x, y = _anchor(corners)
        labels.append(LineLabel(name, x, y, name))
    for tag, corners in work:
        x, y = _anchor(corners)
        labels.append(LineLabel(tag, x, y, f"{flight.flight_type.value} area"))
    for callsign, corners in boxes:
        x, y = _anchor(corners)
        labels.append(LineLabel(callsign, x, y, f"Tanker {callsign}"))

    line_sets = lines + player + work + boxes
    geo_points: list[dict[str, Any]] = []
    for set_index, (name, points) in enumerate(line_sets[:MAX_GEO_LINE_SETS]):
        flags = {f"L{i}": i == set_index + 1 for i in range(1, 5)}
        for x, y in points:
            if len(geo_points) >= MAX_GEO_POINTS:
                return geo_points, labels[:MAX_LINE_LABELS]
            number = len(geo_points) + 1
            entry: dict[str, Any] = {
                "number": number,
                "id": f"GEO_LINES{30 + number}",
                "x": x,
                "y": y,
                "alt": 0,
                "note": name,
            }
            entry.update(flags)
            geo_points.append(entry)
    return geo_points, labels[:MAX_LINE_LABELS]


def _build_threat_pts(flight: FlightData, game: Game) -> list[dict[str, Any]]:
    threats: list[dict[str, Any]] = []
    for site in threat_sites_for(game, flight)[:MAX_THREAT_POINTS]:
        number = len(threats) + 1
        threats.append(
            {
                "number": number,
                "id": f"THREAT_PTS{55 + number}",
                "x": site.x,
                "y": site.y,
                "threatName": "Custom",
                "radius": site.range_m,
                "alt": _CUSTOM_THREAT_ALT,
                "elev": ground_elevation(game, site.x, site.y),
                "text": site.label,
                "ring": True,
                "def_num": 1,
            }
        )
    return threats


def build_viper_cartridge(
    flight: FlightData, mission_data: MissionData, game: Game, name: str
) -> DtcCartridge:
    terrain = game.theater.terrain.name
    options = flight.dtc_options
    data: dict[str, Any] = {
        "type": VIPER_UNIT_TYPE,
        "name": name,
        "terrain": terrain,
    }
    # A section the planner turned off is omitted entirely so the jet's own
    # defaults stand (the §74 Edit Flight DTC tab).
    geo_lines, line_labels = _build_geo_lines(game, mission_data, flight)
    if (
        options.route
        or options.saved_points
        or options.drawings
        or options.friendly_orbits
        or options.flot_and_zones
        or options.borders
        or options.threat_rings
        or options.destinations
        or options.roe_table
        or options.countermeasures
    ):
        data["MPD"] = {
            "terrain": terrain,
            "mirror_NAV_PTS": False,
            "NAV_PTS": _build_nav_pts(flight, mission_data, game),
            "mirror_GEO_LINES": False,
            "GEO_LINES": geo_lines,
            "mirror_THREAT_PTS": False,
            "THREAT_PTS": (
                _build_threat_pts(flight, game) if options.threat_rings else []
            ),
            "mirror_DEST": False,
            "DEST": _build_dest(flight, game, line_labels),
        }
        if options.countermeasures:
            data["MPD"]["CMDS"] = _build_cmds()
        if options.roe_table:
            data["MPD"]["ROE"] = {
                "Settings": {"TypeSovereignty": True, "Mode4Status": True},
                "List": build_atdt(game),
            }
    return DtcCartridge(
        name=name, unit_type=VIPER_UNIT_TYPE, terrain=terrain, data=data
    )
