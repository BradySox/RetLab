"""FA-18C DTC cartridge builder (§74).

Sections emitted (schema mined from ``CoreMods/aircraft/FA-18C/DTC``):

* ``COMM`` -- COMM1/COMM2 mirroring the channels the radio allocator wrote
  into the unit's ``Radio`` table, each named (<=5 chars) after what it tunes.
  The names are what the miz cannot carry; unassigned channels keep the stock
  defaults.
* ``WYPT`` -- the flight's waypoints as named steerpoints + the Route 1
  sequence with per-leg altitude/speed/ETA, and ``NAV_SETTINGS`` that auto-tune
  the recovery TACAN / ICLS / ACLS (the §65 boat card, closing the loop) and
  the FPAS home waypoint.
* ``SA`` -- the SA page draws ONE item per class, the selected one (the
  cockpit's ``SA.lua``): the flight's own orbit (CAP), the nearest land border
  (FAOR, dashed), the next border or else the front line (FLOT, solid), the
  package's lane from the IP over the target (CORRIDORS), and viewer-fogged
  enemy SAM rings (MEZ, all of them).
* ``TCN`` -- the TACAN stations: the friendly boats, the home, arrival and
  divert fields, then the map's other ground TACANs nearest the route first.

Limits honored from the ME editor: 59 waypoints, 9 CAP points, 3 FAOR + 3
FLOT lines of 7 points, one corridor of 14, 40 MEZ threats, 10 TACANs.
"""

from __future__ import annotations

import math

from typing import TYPE_CHECKING, Any, Optional

from game.ato.flighttype import FlightType
from game.dcs.beacons import Beacon, Beacons
from game.missiongenerator.dtc.cartridge import DtcCartridge
from game.missiongenerator.dtc.viper import BORDER_CORRIDOR_M
from game.ato.savedpoints import SavedPoint
from game.missiongenerator.dtc.savedpoints import (
    closed_ring,
    cockpit_numbers,
    kept_waypoints,
    player_shapes,
    saved_orbits,
)
from game.missiongenerator.dtc.common import (
    SupportTrack,
    decimate_open,
    land_border_runs,
    leg_altitude,
    red_land_boundary,
    support_boxes,
    frequency_labels,
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
    from game.missiongenerator.aircraft.flightdata import FlightData
    from game.missiongenerator.missiondata import MissionData
    from game.missiongenerator.missiondata import CarrierInfo

HORNET_UNIT_TYPE = "FA-18C_hornet"

MAX_WAYPOINTS = 59
MAX_CAP_POINTS = 9
MAX_LINE_POINTS = 7
MAX_FLOT_LINES = 3
#: Only FAOR line 1 draws (SA.lua); it is the nearest border, else the tanker box.
MAX_FAOR_LINES = 3
MAX_MEZ_THREATS = 40
#: The SA page draws one corridor of up to 14 points (``CORRIDORS.lua``).
MAX_CORRIDOR_POINTS = 14
#: The editor refuses an 11th TACAN station (``TCN/TACAN.lua``).
MAX_TACAN_STATIONS = 10

#: Stock preset frequencies (MHz) for channels 1-20 of both AN/ARC-210s, from
#: the module's COMM1/COMM2 defaults -- kept for channels we don't assign.
_DEFAULT_CHANNEL_FREQS = [
    305.0, 264.0, 265.0, 256.0, 254.0, 250.0, 270.0, 257.0, 255.0, 262.0,
    259.0, 268.0, 269.0, 260.0, 263.0, 261.0, 267.0, 251.0, 253.0, 266.0,
]  # fmt: skip

#: CAP racetrack orbit diameter (the ME default, 5 NM).
_CAP_ORBIT_DIAMETER_M = 5 * 1852.0


def _default_comm_table() -> dict[str, Any]:
    """The module's stock channel table (both ARC-210s ship the same one)."""
    table: dict[str, Any] = {"Guard": False}
    for i, freq in enumerate(_DEFAULT_CHANNEL_FREQS, start=1):
        table[f"Channel_{i}"] = {
            "frequency": freq,
            "modulation": 0,
            "name": f"CH {i}",
        }
    table["Channel_G"] = {"frequency": 243.0, "modulation": 0, "name": "GUARD"}
    table["Channel_M"] = {"frequency": 305.0, "modulation": 0, "name": "MAN"}
    table["Channel_C"] = {"frequency": 30.0, "modulation": 1, "name": "CUE"}
    table["Channel_S"] = {"frequency": 156.05, "modulation": 1, "name": "MAR"}
    return table


def _build_comm(flight: FlightData, mission_data: MissionData) -> dict[str, Any]:
    tables = {1: _default_comm_table(), 2: _default_comm_table()}
    labels = frequency_labels(flight, mission_data)
    for frequency, assignments in flight.frequency_to_channel_map.items():
        label = labels.get(frequency, "")
        for assignment in assignments:
            table = tables.get(assignment.radio_id)
            if table is None or not 1 <= assignment.channel <= 20:
                continue
            table[f"Channel_{assignment.channel}"] = {
                "frequency": frequency.mhz,
                # Everything Retribution assigns above the VHF-FM band is AM.
                "modulation": 1 if frequency.mhz < 88.0 else 0,
                "name": label or f"CH {assignment.channel}",
            }
    return {
        "COMM1": tables[1],
        "COMM2": tables[2],
        "mirror_COMM1": False,
        "mirror_COMM2": False,
    }


def _oa_defaults(index: int) -> dict[str, Any]:
    """The offset-aimpoint boilerplate every ME-authored waypoint carries."""
    return {
        "isOA": False,
        "idOA": f"OA{index}",
        "idOA_Line": f"OA{index}Line",
        "OA_X": 0,
        "OA_Y": 0,
        "OA_Alt": 0,
        "OA_Bearing": 0,
        "OA_Bearing_Units": 1,
        "OA_Range": 0,
        "OA_Range_Units": 1,
        "OA_DeltaX": 0,
        "OA_DeltaY": 0,
        "OA_Elevation_Units": 1,
    }


def _nav_settings_defaults(home_wypt: int) -> dict[str, Any]:
    """The module's stock (everything off) NAV settings, for a cartridge whose
    planner turned the recovery-aids section off."""
    return {
        "TACAN": {"Mode": 1, "Channel": 1, "ChannelMode": 1, "OnOff": False},
        "ICLS": {"Channel": 1, "OnOff": False},
        "ACLS": {"Frequency": 225.0, "OnOff": False},
        "AA_Waypoint": {"AA_WP_Number": 59, "AA_WP_Enabled": False},
        "Home_Waypoint": {"FPAS_HOME_WP": home_wypt},
        "Altitude_Warning": {"Warn_Alt_Rdr": 500, "Warn_Alt_Baro": 2000},
    }


#: WYPT_NAV.lua's own limits on a waypoint's elevation. The route entry's cap
#: is 80,000 ft (ROUTE_SEQ.lua), so a leg above 25,000 ft keeps its number there.
_WYPT_ALT_MIN_M = -2000 * 0.3048
_WYPT_ALT_MAX_M = 25000 * 0.3048


def _build_wypt(
    flight: FlightData, game: Game, carrier: Optional[CarrierInfo]
) -> dict[str, Any]:
    options = flight.dtc_options
    nav_pts: list[dict[str, Any]] = []
    route_one: dict[str, Any] = {}
    home_wypt = 1
    aa_wypt: Optional[int] = None
    route_order = 0
    target_flagged = False
    prev_route_wp = None
    # The kneeboard numbers the flight plan from 0 (row 0 = takeoff/spawn).
    # Skip that row so the jet's STPT n IS the kneeboard's waypoint n — the
    # flown off-by-one had every briefed number shifted (target "wp 4" was
    # STPT 5 in the jet). The dropped point is where the jet spawns anyway.
    waypoints = kept_waypoints(flight)[:MAX_WAYPOINTS] if options.route else []
    for number, waypoint in enumerate(waypoints, start=1):
        on_route = is_route_waypoint(waypoint)
        route_alt_m, altitude_type = leg_altitude(waypoint, game)
        entry: dict[str, Any] = {
            "wypt_num": number,
            "id": f"STPT{number}",
            "text_note": waypoint_display_name(waypoint.display_name or waypoint.name),
            "note": "",
            "x": waypoint.position.x,
            "y": waypoint.position.y,
            # The HSI's waypoint elevation, the same number the miz route gives
            # the jet; NAV_ROUTE below carries the DTC Manager's planning copy.
            "alt": min(max(route_alt_m, _WYPT_ALT_MIN_M), _WYPT_ALT_MAX_M),
            "altitudeType": altitude_type,
            "velocityType": 3,
            "R1": on_route,
            "R2": False,
            "R3": False,
        }
        entry.update(_oa_defaults(number))
        if on_route:
            route_order += 1
            entry["R1_order"] = route_order
            route_one[f"STPT{number}"] = {
                "route_num": 1,
                "wypt_num": number,
                "alt": route_alt_m,
                "altitudeType": entry["altitudeType"],
                "speed": leg_speed_kmh(prev_route_wp, waypoint),
                "ETA": seconds_of_day(game, waypoint.tot, flight.mission_start),
                "FIX_Time": waypoint.tot is not None,
                # One TGT per sequence (ROUTE_SEQ.lua:1286-1300): the first.
                "TGT": is_target_waypoint(waypoint) and not target_flagged,
            }
            target_flagged = target_flagged or is_target_waypoint(waypoint)
            prev_route_wp = waypoint
        nav_pts.append(entry)
        if "LANDING" in waypoint.waypoint_type.name:
            home_wypt = number
        elif waypoint.waypoint_type.name == "BULLSEYE":
            aa_wypt = number
    if options.route and options.saved_points:
        nav_pts.extend(_saved_wypt(flight))
    if options.nav_aids:
        nav_settings = _build_nav_settings(flight, carrier, home_wypt, aa_wypt)
    else:
        nav_settings = _nav_settings_defaults(home_wypt)
    return {
        "NAV_PTS": nav_pts,
        "NAV_ROUTE": [route_one, [], []],
        "NAV_SETTINGS": nav_settings,
        "terrain": game.theater.terrain.name,
        "mirror_NAV_PTS": False,
    }


def _saved_wypt(flight: FlightData) -> list[dict[str, Any]]:
    """The player's saved points (§102), after the route, on sequence 2."""
    entries: list[dict[str, Any]] = []
    numbers = cockpit_numbers(flight, flight.saved_points)
    for order, (number, point) in enumerate(zip(numbers, flight.saved_points), 1):
        if number is None:
            continue
        alt_m = point.altitude_ft * 0.3048
        entry: dict[str, Any] = {
            "wypt_num": number,
            "id": f"STPT{number}",
            "text_note": waypoint_display_name(point.name),
            "note": "",
            "x": point.x,
            "y": point.y,
            "alt": min(max(alt_m, _WYPT_ALT_MIN_M), _WYPT_ALT_MAX_M),
            "altitudeType": 1,
            "velocityType": 3,
            "R1": False,
            "R2": True,
            "R2_order": order,
            "R3": False,
        }
        entry.update(_oa_defaults(number))
        entries.append(entry)
    return entries


def _find_carrier(
    flight: FlightData, mission_data: MissionData
) -> Optional[CarrierInfo]:
    """The carrier this flight recovers on, if its arrival is a boat."""
    arrival_name = flight.arrival.airfield_name
    for carrier in mission_data.carriers:
        if carrier.unit_name in arrival_name or arrival_name in carrier.unit_name:
            return carrier
        if carrier.callsign and carrier.callsign in arrival_name:
            return carrier
    return None


def _build_nav_settings(
    flight: FlightData,
    carrier: Optional[CarrierInfo],
    home_wypt: int,
    aa_wypt: Optional[int] = None,
) -> dict[str, Any]:
    """Recovery aids plus the A/A (bullseye) waypoint designation.

    The A/A waypoint has to BE a waypoint in the database (EA guide p158), and
    designating it is otherwise three cockpit presses the pilot makes every
    sortie. We point it at the bullseye we already emit rather than the jet's
    stock slot 59, which our routes never reach.
    """
    # A land start tunes the departure field's TACAN when it has one (DM ask
    # 2026-09-13); a boat recovery keeps the boat's card; else the arrival's.
    tacan = (
        carrier.tacan
        if carrier is not None
        else flight.departure.tacan or flight.arrival.tacan
    )
    icls = carrier.icls_channel if carrier is not None else flight.arrival.icls
    acls_freq = (
        carrier.link4_freq.mhz
        if carrier is not None and carrier.link4_freq is not None
        else None
    )
    tacan_settings: dict[str, Any] = {
        "Mode": 1,  # T/R
        "Channel": 1,
        "ChannelMode": 1,  # X
        "OnOff": False,
    }
    if tacan is not None:
        tacan_settings = {
            "Mode": 1,
            "Channel": tacan.number,
            "ChannelMode": 2 if getattr(tacan.band, "value", "X") == "Y" else 1,
            "OnOff": True,
        }
    return {
        "TACAN": tacan_settings,
        "ICLS": {
            "Channel": icls if icls is not None else 1,
            "OnOff": icls is not None,
        },
        "ACLS": {
            "Frequency": acls_freq if acls_freq is not None else 225.0,
            "OnOff": acls_freq is not None,
        },
        "AA_Waypoint": {
            "AA_WP_Number": aa_wypt if aa_wypt is not None else 59,
            "AA_WP_Enabled": aa_wypt is not None,
        },
        "Home_Waypoint": {"FPAS_HOME_WP": home_wypt},
        "Altitude_Warning": {"Warn_Alt_Rdr": 500, "Warn_Alt_Baro": 2000},
    }


def _cap_point(track: SupportTrack, number: int) -> dict[str, Any]:
    x, y = track.center
    return {
        "id": f"CAP_PTS_{number}",
        "num": number,
        "x": x,
        "y": y,
        "course": track.course,
        "length": track.length_m,
        "diameter": _CAP_ORBIT_DIAMETER_M,
        "turn_direction": "Left",
        "note": track.callsign,
    }


def _saved_cap_point(point: SavedPoint, number: int) -> dict[str, Any]:
    """A player orbit (§102): centred on its leg, flown along its heading."""
    end_x, end_y = point.orbit_end()
    return {
        "id": f"CAP_PTS_{number}",
        "num": number,
        "x": (point.x + end_x) / 2,
        "y": (point.y + end_y) / 2,
        "course": point.heading_deg,
        "length": point.length_nm * 1852.0,
        "diameter": _CAP_ORBIT_DIAMETER_M,
        "turn_direction": "Left",
        "note": point.name,
    }


def _line_points(
    prefix: str, line_num: int, points: list[tuple[float, float]]
) -> list[dict[str, Any]]:
    return [
        {"id": f"{prefix}_{line_num}_PT_{i}", "x": x, "y": y}
        for i, (x, y) in enumerate(points[:MAX_LINE_POINTS], start=1)
    ]


def _ship_tacan(carrier: CarrierInfo) -> Optional[dict[str, Any]]:
    """A boat's station, keyed the way the editor keys a ship's ActivateBeacon
    task: the unit's id and the route point that carries it (point 1)."""
    group = carrier.ship_group
    if not group.units or not group.points:
        return None
    unit = group.units[0]
    position = group.points[0].position
    return {
        "callsign": carrier.callsign,
        "channel": carrier.tacan.number,
        "modeChannel": carrier.tacan.band.value,
        "display_name": f"{unit.name}_P1",
        "elevation": 0,
        "unitId": unit.id,
        "unitPointNum": 1,
        "x": position.x,
        "y": position.y,
    }


def _ground_tacan(beacon: Beacon) -> Optional[dict[str, Any]]:
    """A ground station, keyed by the beacon's own name as the editor keys it."""
    if not beacon.is_tacan or beacon.channel is None or beacon.x is None:
        return None
    station: dict[str, Any] = {
        "callsign": beacon.callsign,
        "channel": beacon.channel,
        "display_name": beacon.name,
        "elevation": beacon.elevation or 0,
        "x": beacon.x,
        "y": beacon.y,
    }
    if beacon.hertz is not None:
        station["frequency"] = beacon.hertz
    return station


def _field_tacans(game: Game, airfield_name: str) -> list[dict[str, Any]]:
    """The field's own ground TACANs, from the terrain's beacon data."""
    stations: list[dict[str, Any]] = []
    for airport in game.theater.terrain.airports.values():
        if airport.name != airfield_name:
            continue
        for beacon_data in airport.beacons:
            try:
                beacon = Beacons.with_id(beacon_data.id, game.theater)
            except KeyError:
                continue
            station = _ground_tacan(beacon)
            if station is not None:
                stations.append(station)
    return stations


def _build_tcn(
    flight: FlightData, mission_data: MissionData, game: Game
) -> list[dict[str, Any]]:
    """The jet's TACAN station list: our boats, the home, arrival and divert
    fields, then every other TACAN on the map nearest the route first (DM
    2026-10-08), to the editor's 10. Tankers cannot be listed: the editor
    takes only ships and ground beacons."""
    stations: list[dict[str, Any]] = []

    def add(station: Optional[dict[str, Any]]) -> None:
        if station is not None and all(
            s["display_name"] != station["display_name"] for s in stations
        ):
            stations.append(station)

    for carrier in mission_data.carriers:
        if carrier.blue.is_blue == flight.friendly.is_blue:
            add(_ship_tacan(carrier))
    for runway in (flight.departure, flight.arrival, flight.divert):
        if runway is not None:
            for station in _field_tacans(game, runway.airfield_name):
                add(station)
    route = [w.position for w in flight.waypoints if is_route_waypoint(w)]
    others = [
        station
        for station in map(_ground_tacan, Beacons.iter_theater(game.theater))
        if station is not None
    ]
    if route:
        others.sort(
            key=lambda s: min(math.hypot(s["x"] - p.x, s["y"] - p.y) for p in route)
        )
    for station in others:
        add(station)
    return stations[:MAX_TACAN_STATIONS]


def _attack_lane(flight: FlightData) -> list[tuple[float, float]]:
    """The package's path from the IP over the target to the split: the legs a
    package flies together (§106). Empty for a flight with no IP."""
    points: list[tuple[float, float]] = []
    for waypoint in flight.waypoints:
        name = waypoint.waypoint_type.name
        if not points and not name.startswith("INGRESS_"):
            continue
        points.append((waypoint.position.x, waypoint.position.y))
        if name == "SPLIT":
            break
    return points if len(points) >= 2 else []


def _build_corridors(flight: FlightData) -> list[dict[str, Any]]:
    """The SA page's one corridor: the attack lane, drawn as a 10 NM lane."""
    lane = decimate_open(_attack_lane(flight), MAX_CORRIDOR_POINTS)
    if not lane:
        return []
    return [
        {
            "id": "CORR_1",
            "num": 1,
            "note": "ATTACK",
            "points": [
                {"id": f"CORR_1_PT_{i}", "x": x, "y": y}
                for i, (x, y) in enumerate(lane, start=1)
            ],
        }
    ]


def _build_sa(
    flight: FlightData, mission_data: MissionData, game: Game
) -> dict[str, Any]:
    options = flight.dtc_options
    caps: list[dict[str, Any]] = []
    default_cap_point = 1
    if options.friendly_orbits:
        # This flight's own orbit first -- its racetrack when it flies one, a
        # stand-in at the hold point when it does not -- then the tanker and
        # AEW&C orbits, so "where's my gas" stays answerable. Other flights'
        # CAP stations are not this jet's business and stay off the page. The
        # SA page DISPLAYS one CAP point at a time -- the selected one (flown
        # 2026-07-19) -- so entry 1 being your own orbit is what spawns up.
        own = own_orbit_track(flight)
        ordered = ([own] if own is not None else []) + support_tracks(mission_data)
        for track in ordered[:MAX_CAP_POINTS]:
            caps.append(_cap_point(track, len(caps) + 1))
    # The player's own orbits (§102) follow, on the same flip-through list.
    for orbit in saved_orbits(flight):
        if len(caps) >= MAX_CAP_POINTS:
            break
        caps.append(_saved_cap_point(orbit, len(caps) + 1))

    # Only the selected FAOR and FLOT line draw, so each slot leads with its
    # one job (DM 2026-10-08): the nearest border dashed, the next border
    # solid. The front line is only worth a slot to CAS (same call).
    # The bullseye is a waypoint but not a place the flight goes.
    route = [
        (w.position.x, w.position.y) for w in flight.waypoints if is_route_waypoint(w)
    ]
    borders = (
        land_border_runs(game, route, BORDER_CORRIDOR_M) if options.borders else []
    )

    faor_lines: list[dict[str, Any]] = []
    faor_shapes = [
        (name, decimate_open(points, MAX_LINE_POINTS)) for name, points in borders[:1]
    ]
    if options.friendly_orbits:
        faor_shapes += support_boxes(mission_data, MAX_FAOR_LINES, flight)
    for name, points in faor_shapes[:MAX_FAOR_LINES]:
        line_num = len(faor_lines) + 1
        faor_lines.append(
            {
                "id": f"FAOR_{line_num}",
                "num": line_num,
                "note": name,
                "points": _line_points("FAOR", line_num, points),
            }
        )

    second_border = [
        (name, decimate_open(points, MAX_LINE_POINTS)) for name, points in borders[1:2]
    ]
    flot_shapes: list[tuple[str, list[tuple[float, float]]]] = []
    # The front line gives up lines to the player's drawings (§102), down to one.
    drawn = player_shapes(flight, orbits_as_boxes=False)
    if options.flot_and_zones and flight.flight_type is FlightType.CAS:
        boundary_lines = max(1, MAX_FLOT_LINES - len(second_border) - len(drawn))
        flot_shapes += red_land_boundary(game, boundary_lines, MAX_LINE_POINTS)
    flot_shapes += second_border
    for name, points, closed in drawn:
        flot_shapes.append((name, closed_ring(points) if closed else points))
    flot_lines: list[dict[str, Any]] = []
    for name, points in flot_shapes[:MAX_FLOT_LINES]:
        line_num = len(flot_lines) + 1
        flot_lines.append(
            {
                "id": f"FLOT_{line_num}",
                "num": line_num,
                "note": name,
                "points": _line_points("FLOT", line_num, points),
            }
        )

    threats: list[dict[str, Any]] = []
    if options.threat_rings:
        for site in threat_sites_for(game, flight)[:MAX_MEZ_THREATS]:
            number = len(threats) + 1
            threats.append(
                {
                    "id": f"MEZ_THRTS_{number}",
                    "num": number,
                    "x": site.x,
                    "y": site.y,
                    "text": site.label,
                    "threat_type": "Custom",
                    "threat_ring_radius": round(site.range_m / 1852.0, 1),
                    "threat_level": 1,
                }
            )

    return {
        "CAP_PTS": caps,
        "CORRIDORS": _build_corridors(flight) if options.route else [],
        "FAOR_FLOT": {"FAOR": faor_lines, "FLOT": flot_lines},
        "MEZ_THRTS": threats,
        "SETTINGS": _sa_settings(),
        "Default_CAP_Point": default_cap_point,
        "Default_CORRIDORS_Point": 1,
        "Default_FAOR_Line": 1,
        "Default_FLOT_Line": 1,
        "Default_MEZ_THRTS_Level": 1,
        "mirror_MEZ_THRTS": False,
    }


def _sa_settings() -> dict[str, Any]:
    """The module's stock SA sensor/declutter settings (everything shown)."""
    dcltr = {
        "Bullseye_TDC_Info": True,
        "Waypoint_Info": True,
        "Compase_Rose": True,
        "Ground_Speed": True,
        "Countermeasure_Inventory": True,
        "SEQ": True,
        "CAP": True,
        "CORR": True,
        "FAOR": True,
        "FLOT": True,
        "MEZ_Names": True,
        "MEZ_Rings": True,
    }
    return {
        "SENSORS_SETTINGS": {
            "RWR_Symbols": 1,
            "FRIEND_Symbols": 3,
            "PPLI_tracks": True,
            "FF_tracks": True,
            "SURV_tracks": True,
            "UNK_tracks": True,
        },
        "DCLTR_SETTINGS": {"MREJ1": dict(dcltr), "MREJ2": dict(dcltr)},
    }


def build_hornet_cartridge(
    flight: FlightData, mission_data: MissionData, game: Game, name: str
) -> DtcCartridge:
    terrain = game.theater.terrain.name
    options = flight.dtc_options
    data: dict[str, Any] = {
        "TCN": _build_tcn(flight, mission_data, game) if options.nav_aids else [],
        "type": HORNET_UNIT_TYPE,
        "name": name,
        "terrain": terrain,
    }
    # A section the planner turned off is omitted entirely so the jet's own
    # defaults stand (the §74 Edit Flight DTC tab).
    if options.comms:
        data["COMM"] = _build_comm(flight, mission_data)
    if options.route or options.nav_aids:
        carrier = _find_carrier(flight, mission_data)
        data["WYPT"] = _build_wypt(flight, game, carrier)
    if (
        options.flot_and_zones
        or options.friendly_orbits
        or options.threat_rings
        or saved_orbits(flight)
        or player_shapes(flight, orbits_as_boxes=False)
    ):
        data["SA"] = _build_sa(flight, mission_data, game)
    return DtcCartridge(
        name=name, unit_type=HORNET_UNIT_TYPE, terrain=terrain, data=data
    )
