"""Shared extraction helpers for the DTC cartridge builders (§74).

Everything a cartridge wants already exists at generation time; these helpers
pull it into airframe-neutral shapes the per-jet builders (:mod:`.hornet`,
:mod:`.viper`) format. Fog discipline: anything intel-flavored (the threat
rings) is read through the same viewer leaves the kneeboard uses
(``known_for(flight.friendly)``), so the cartridge never knows more than the
player's map -- and ``map_hidden`` objects (§50 ambush teams) are never
emitted anywhere.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone as tz
from typing import TYPE_CHECKING, Any, Optional

from dcs import Point

from game.ato.flighttype import FlightType
from game.ato.flightwaypointtype import FlightWaypointType

if TYPE_CHECKING:
    from game import Game
    from game.ato.flightwaypoint import FlightWaypoint
    from game.missiongenerator.aircraft.flightdata import FlightData
    from game.missiongenerator.missiondata import MissionData
    from game.radio.radios import RadioFrequency
    from game.theater.player import Player

#: Route-sequence default speed the ME uses when a leg speed is unknown (km/h).
DEFAULT_LEG_SPEED_KMH = 463.0

#: Sanity clamp for computed leg ground speeds (km/h).
MIN_LEG_SPEED_KMH = 150.0
MAX_LEG_SPEED_KMH = 2200.0

#: Waypoint types that are reference marks, not flown route members.
NON_ROUTE_WAYPOINTS = (
    FlightWaypointType.DIVERT,
    FlightWaypointType.BULLSEYE,
)


def waypoint_display_name(label: str, max_len: int = 24) -> str:
    """ASCII-fold a waypoint name for cockpit displays.

    Retribution waypoint names carry em-dashes and other punctuation the DDI/
    DED fonts may not render; fold dashes, drop the rest of non-ASCII, and cap
    the length.
    """
    folded = label.replace("—", "-").replace("–", "-")
    cleaned = folded.encode("ascii", "ignore").decode("ascii")
    return " ".join(cleaned.split())[:max_len]


def sanitize_short_name(label: str, max_len: int = 5) -> str:
    """Uppercase alphanumeric truncation -- the DTC channel-name filter.

    The ME import clamps channel names to 5 uppercase letters/digits
    (``custom_input_filter_*`` in the FA-18C descriptor); emitting names that
    already satisfy the filter keeps what the jet shows identical to what we
    wrote.
    """
    cleaned = re.sub(r"[^A-Z0-9]", "", label.upper())
    return cleaned[:max_len]


def short_callsign(callsign: str) -> str:
    """First word of a callsign, sanitized ("Arco 1-1" -> "ARCO")."""
    first = callsign.split()[0] if callsign.split() else callsign
    return sanitize_short_name(first)


def seconds_of_day(
    game: Game, when: Optional[datetime], mission_start: Optional[datetime] = None
) -> int:
    """Seconds since Zulu midnight of the mission day -- the cartridge's clock.

    DCS mission time is theater-local, but cartridge times are Zulu. The ME's
    own DTC manager bases them on ``mission.start_time - SummerTimeDelta*3600``
    (``me_managerDTC.lua``), and both jets read them against a Zulu system
    clock: the Hornet's TOT is entered in Zulu (FA-18C guide p123) and the
    Viper's CRUS TOS page sits beside a System Time that is "based on Zulu time
    (UTC)" (F-16C guide p103, p107). Emitting local put every ETA out by the
    map's UTC offset -- +4 h on Caucasus, -8 h on Nevada.

    The base stays the mission day's midnight rather than the wall clock's, so
    ETAs across a Zulu midnight keep increasing (the editor's TOS field carries
    a days component for exactly that).
    """
    if when is None:
        return 0
    # The mission can begin before the turn clock (§104), across midnight.
    start = mission_start or game.conditions.start_time
    start_zulu = start.replace(tzinfo=game.theater.timezone).astimezone(tz.utc)
    midnight = start_zulu.replace(hour=0, minute=0, second=0, microsecond=0)
    when_zulu = when.replace(tzinfo=game.theater.timezone).astimezone(tz.utc)
    return max(0, int((when_zulu - midnight).total_seconds()))


def leg_speed_kmh(prev: Optional[FlightWaypoint], current: FlightWaypoint) -> float:
    """Ground speed for the leg into ``current`` in km/h (the DTC speed unit)."""
    if (
        prev is None
        or prev.tot is None
        and prev.departure_time is None
        or current.tot is None
    ):
        return DEFAULT_LEG_SPEED_KMH
    depart = prev.departure_time or prev.tot
    assert depart is not None
    elapsed = (current.tot - depart).total_seconds()
    if elapsed <= 0:
        return DEFAULT_LEG_SPEED_KMH
    meters = prev.position.distance_to_point(current.position)
    speed = meters / elapsed * 3.6
    return max(MIN_LEG_SPEED_KMH, min(MAX_LEG_SPEED_KMH, speed))


def bearing_degrees(start: Point, end: Point) -> float:
    """Map bearing from start to end (0 = north), DCS x=north / y=east."""
    return math.degrees(math.atan2(end.y - start.y, end.x - start.x)) % 360.0


def is_route_waypoint(waypoint: FlightWaypoint) -> bool:
    return waypoint.waypoint_type not in NON_ROUTE_WAYPOINTS


def is_target_waypoint(waypoint: FlightWaypoint) -> bool:
    """A point the flight attacks, by type -- never by the attached target list.

    Retribution hangs that list on the ingress point too, so the task can be
    built; reading it put the target symbol on the IP (the Viper's HSD
    triangle, the Hornet's route flag) in a generated miz on 2026-08-22.
    """
    return "TARGET" in waypoint.waypoint_type.name


def nearest_field_elevation(game: Game, x: float, y: float) -> float:
    """The elevation of the nearest airfield with a known one, metres AMSL.

    The only height data the campaign carries. Exact on a flat map, within the
    field's valley elsewhere, and closer than 0 everywhere (DM call,
    2026-08-22). Boats and FOBs have no record and never answer, so a coastal
    target is not pulled to sea level by the carrier. A DCS-side
    ``Terrain.GetHeight`` dump is the exact route if this ever proves short.
    """
    from game.missiongenerator.kneeboard_recon.airport_imagery import (
        field_elevation_for_airport,
    )

    best: Optional[float] = None
    best_distance = math.inf
    for cp in game.theater.controlpoints:
        airport = getattr(cp, "airport", None)
        if airport is None:
            continue
        elevation = field_elevation_for_airport(game.theater.terrain, airport)
        if elevation is None:
            continue
        distance = math.hypot(cp.position.x - x, cp.position.y - y)
        if distance < best_distance:
            best, best_distance = elevation, distance
    return best if best is not None else 0.0


def ground_elevation(game: Game, x: float, y: float) -> float:
    """The ground at a point, metres AMSL: DCS's own height where a grid ships.

    Terrains without a ``resources/terrain_heights`` grid keep the nearest
    field's elevation.
    """
    from game.theater.terrainheights import terrain_height

    height = terrain_height(game.theater.terrain.name, x, y)
    if height is not None:
        return height
    return nearest_field_elevation(game, x, y)


def steerpoint_altitude(waypoint: FlightWaypoint, game: Game) -> float:
    """The steerpoint's altitude in metres MSL: what the .miz route gives the jet.

    Both jets carry two altitude fields, the point's ``alt`` and the route
    leg's (``routeAltitude`` / ``NAV_ROUTE[].alt``), and the cockpit shows the
    first: a Viper flown 2026-09-13 with ``alt`` 131 ft and ``routeAltitude``
    22,000 ft read ELEV 131 on the DED. Without a cartridge the jet takes ELEV
    from the mission-editor waypoint altitude, so the mirror carries the same
    number: the planned altitude on an en-route point, the ground under a
    ground-marked one (the .miz puts those at 0 AGL for a client flight).
    Nothing honours an AGL tag on the point, so an AGL plan is converted with
    the same ground height. Design note: retlab-dtc-cartridge-notes.md.
    """
    if waypoint.marks_ground_for_player:
        return ground_elevation(game, waypoint.position.x, waypoint.position.y)
    if waypoint.alt_type == "RADIO":
        return waypoint.alt.meters + ground_elevation(
            game, waypoint.position.x, waypoint.position.y
        )
    return waypoint.alt.meters


def leg_altitude(waypoint: FlightWaypoint, game: Game) -> tuple[float, int]:
    """``steerpoint_altitude`` with the DTC ``altitudeType``, always 1 (MSL)."""
    return steerpoint_altitude(waypoint, game), 1


def _altitude_msl(waypoint: FlightWaypoint) -> float:
    return waypoint.alt.meters if waypoint.alt_type == "BARO" else 0.0


@dataclass(frozen=True)
class SupportTrack:
    """One friendly racetrack: a CAP station or a tanker/AEW&C orbit."""

    callsign: str
    kind: str  # "CAP" | "TKR" | "AWACS" | "HOLD"
    start: Point
    end: Point
    #: The orbiting flight's AircraftType, so a tanker box can be offered only
    #: to jets that can take gas from it. None on a stand-in.
    aircraft_type: Any = None
    #: The orbit's planned altitude, metres MSL (0 when the plan is AGL).
    altitude_m: float = 0.0
    #: A tanker box's corners, in route order; None on a racetrack.
    box: Optional[tuple[tuple[float, float], ...]] = None
    #: How far the drawn box reaches either side of the flown track. None means
    #: :data:`SUPPORT_ORBIT_DIAMETER_M` / 2.
    half_width_m: Optional[float] = None

    @property
    def center(self) -> tuple[float, float]:
        return ((self.start.x + self.end.x) / 2, (self.start.y + self.end.y) / 2)

    @property
    def course(self) -> float:
        if self.start.distance_to_point(self.end) < 1.0:
            return 0.0
        return bearing_degrees(self.start, self.end)

    @property
    def length_m(self) -> float:
        # Floor at 2 NM so a degenerate/point orbit still draws a readable
        # racetrack on the SA page.
        return max(3704.0, self.start.distance_to_point(self.end))


def racetrack_ends(
    flight: FlightData,
) -> tuple[Optional[Point], Optional[Point]]:
    """The PATROL_TRACK -> PATROL waypoint pair (same rule as the §45 F10
    orbit drawings).

    A tanker box ends back on its start, so its pair is the front leg instead:
    BOX 1 -> BOX 2, where receivers meet it.
    """
    start: Optional[Point] = None
    end: Optional[Point] = None
    for waypoint in flight.waypoints:
        if waypoint.waypoint_type == FlightWaypointType.PATROL_TRACK:
            start = waypoint.position
        elif waypoint.waypoint_type == FlightWaypointType.PATROL:
            end = waypoint.position
    corners = box_corners(flight)
    if corners is not None:
        return corners[0], corners[1]
    return start, end


def box_corners(flight: FlightData) -> Optional[list[Point]]:
    """A tanker box's corners (PATROL_TRACK through the last one before PATROL),
    or None for a two-point racetrack."""
    corners: list[Point] = []
    for waypoint in flight.waypoints:
        if waypoint.waypoint_type == FlightWaypointType.PATROL_TRACK:
            corners = [waypoint.position]
        elif waypoint.waypoint_type == FlightWaypointType.PATROL:
            break
        elif corners:
            corners.append(waypoint.position)
    return corners if len(corners) >= 3 else None


def _support_half_width(flight: FlightData) -> Optional[float]:
    """The F10 marker's half-width, from the flight's own orbit speed, so the
    cockpit box and the map box are the same size. None without a speed."""
    from game.missiongenerator.drawingsgenerator import DrawingsGenerator

    if getattr(flight, "patrol_speed", None) is None:
        return None
    return DrawingsGenerator._support_orbit_radius(flight)


_CAP_FLIGHT_TYPES = (FlightType.BARCAP, FlightType.TARCAP)
_SUPPORT_FLIGHT_TYPES = (FlightType.REFUELING, FlightType.AEWC)

#: Two CAP racetracks whose centers sit within this distance on near-parallel
#: courses are the same patrol *station*: the §6 BARCAP wave relief flies each
#: station as several flights with jittered tracks, and the SA page wants the
#: station once, not once per wave (a 3-station/3-wave ATO otherwise burns all
#: nine Hornet CAP_PTS slots on duplicates and squeezes the tankers out).
STATION_MERGE_DISTANCE_M = 15_000.0
STATION_MERGE_COURSE_DEG = 25.0


def dedupe_stations(tracks: list[SupportTrack]) -> list[SupportTrack]:
    """Collapse wave-relief duplicates of the same patrol station.

    Greedy first-kept clustering: a track merges into an already-kept one when
    their centers are within :data:`STATION_MERGE_DISTANCE_M` and their courses
    within :data:`STATION_MERGE_COURSE_DEG` (either direction of the leg). The
    earliest wave's track represents the station.
    """
    kept: list[SupportTrack] = []
    for track in tracks:
        for existing in kept:
            dx = track.center[0] - existing.center[0]
            dy = track.center[1] - existing.center[1]
            if math.hypot(dx, dy) > STATION_MERGE_DISTANCE_M:
                continue
            delta = abs(track.course - existing.course) % 360.0
            delta = min(delta, 360.0 - delta)
            # A relief wave may fly the same leg in either direction.
            if min(delta, abs(delta - 180.0)) <= STATION_MERGE_COURSE_DEG:
                break
        else:
            kept.append(track)
    return kept


def _tracks_of_types(
    mission_data: MissionData,
    types: tuple[FlightType, ...],
    kind_by_type: dict[FlightType, str],
) -> list[SupportTrack]:
    tracks = []
    for flight in mission_data.flights:
        if flight.flight_type not in types:
            continue
        if not flight.friendly.is_blue:
            continue
        start, end = racetrack_ends(flight)
        if start is None or end is None:
            continue
        corners = box_corners(flight)
        tracks.append(
            SupportTrack(
                callsign=short_callsign(flight.callsign),
                kind=kind_by_type[flight.flight_type],
                start=start,
                end=end,
                aircraft_type=flight.aircraft_type,
                altitude_m=_orbit_altitude(flight),
                box=(
                    tuple((p.x, p.y) for p in corners) if corners is not None else None
                ),
                half_width_m=_support_half_width(flight),
            )
        )
    return tracks


#: Waypoint types that anchor a non-orbiting flight's own-track stand-in, in
#: preference order: the hold point is where the flight actually orbits while
#: it waits, the join point is the next best fix.
_HOLD_WAYPOINTS = (FlightWaypointType.LOITER, FlightWaypointType.JOIN)


def _orbit_altitude(flight: FlightData) -> float:
    for waypoint in flight.waypoints:
        if waypoint.waypoint_type == FlightWaypointType.PATROL_TRACK:
            return _altitude_msl(waypoint)
    return 0.0


def own_orbit_track(flight: FlightData) -> Optional[SupportTrack]:
    """The flight's own racetrack, or a stand-in at its hold point.

    A flight that flies a real racetrack (BARCAP, TARCAP, tanker, AEW&C) gets
    that track. Everyone else orbits somewhere too -- the hold -- so rather
    than no track at all, a degenerate one at the hold (or join) point draws as
    the minimum-length racetrack. None only when the plan has neither.
    """
    start, end = racetrack_ends(flight)
    callsign = short_callsign(flight.callsign)
    if start is not None and end is not None:
        return SupportTrack(
            callsign=callsign,
            kind="CAP",
            start=start,
            end=end,
            altitude_m=_orbit_altitude(flight),
        )
    for waypoint_type in _HOLD_WAYPOINTS:
        for waypoint in flight.waypoints:
            if waypoint.waypoint_type == waypoint_type:
                position = waypoint.position
                return SupportTrack(
                    callsign=callsign,
                    kind="HOLD",
                    start=position,
                    end=position,
                    altitude_m=_altitude_msl(waypoint),
                )
    return None


def raw_cap_tracks(mission_data: MissionData) -> list[SupportTrack]:
    """Every blue CAP orbit *flight* (each §6 wave separately)."""
    return _tracks_of_types(
        mission_data,
        _CAP_FLIGHT_TYPES,
        {FlightType.BARCAP: "CAP", FlightType.TARCAP: "CAP"},
    )


def support_tracks(mission_data: MissionData) -> list[SupportTrack]:
    """Every blue tanker + AEW&C orbit (the §45 F10-drawing set)."""
    return _tracks_of_types(
        mission_data,
        _SUPPORT_FLIGHT_TYPES,
        {FlightType.REFUELING: "TKR", FlightType.AEWC: "AWACS"},
    )


def flot_segments(game: Game) -> list[tuple[str, list[tuple[float, float]]]]:
    """Each active front line as (name, its trace left to right).

    `bounds.polyline` is the geometry the F10 drawing and the web map already
    read, so a salient the player planned against is the salient in the cockpit.
    The hand-rebuilt chord this replaced stayed straight even with rung E bowing
    the front.
    """
    from game.missiongenerator.frontlineconflictdescription import (
        FrontLineConflictDescription,
    )

    segments = []
    for front_line in game.theater.conflicts():
        bounds = FrontLineConflictDescription.frontline_bounds(front_line, game.theater)
        segments.append(
            (front_line.name, [(point.x, point.y) for point in bounds.polyline])
        )
    return segments


#: A support orbit's turn diameter when the flight's orbit speed is unknown;
#: otherwise the box takes the F10 marker's half-width. The box is the
#: racetrack's footprint: the straight legs plus the room the turns need.
SUPPORT_ORBIT_DIAMETER_M = 5 * 1852.0

#: Corners plus the repeat that closes the figure. No display auto-closes a
#: line -- the Hornet's FAOR and the Viper's GEO sets both draw segments
#: between consecutive points and stop.
SUPPORT_BOX_POINTS = 5


def _reference_point(flight: FlightData) -> Optional[Point]:
    """The flight's target, else its last waypoint -- what "nearest" is measured from."""
    for waypoint in flight.waypoints:
        if is_target_waypoint(waypoint):
            return waypoint.position
    return flight.waypoints[-1].position if flight.waypoints else None


def usable_tanker_tracks(
    flight: FlightData, mission_data: MissionData
) -> list[SupportTrack]:
    """The tankers this flight can take gas from, nearest to its target first.

    Flown 2026-09-13: the Hornet's SA page draws ONE FAOR line -- the selected
    one, like its CAP point -- and it was the AWACS. So line 1 has to be the
    tanker that matters: a boom jet has no use for a probe tanker's box, and no
    jet has a use for the AWACS's.
    """
    tankers = []
    for track in support_tracks(mission_data):
        if track.kind != "TKR":
            continue
        if (
            track.aircraft_type is not None
            and not flight.aircraft_type.can_refuel_from(track.aircraft_type)
        ):
            continue
        tankers.append(track)
    reference = _reference_point(flight)
    if reference is not None:
        tankers.sort(key=lambda t: math.dist(t.center, (reference.x, reference.y)))
    return tankers


def support_boxes(
    mission_data: MissionData, max_boxes: int, flight: Optional[FlightData] = None
) -> list[tuple[str, list[tuple[float, float]]]]:
    """Each usable tanker orbit as a closed box, (callsign, 5 points).

    The orbits already ride the jets as points, but a point is not an area: on
    the Hornet's SA page only the SELECTED CAP point draws its racetrack, so the
    gas is invisible until you go looking for it. With ``flight`` given the
    boxes are :func:`usable_tanker_tracks`; without it, every support orbit.
    """
    boxes: list[tuple[str, list[tuple[float, float]]]] = []
    tracks = (
        usable_tanker_tracks(flight, mission_data)
        if flight is not None
        else support_tracks(mission_data)
    )
    for track in tracks[:max_boxes]:
        half_width = (
            track.half_width_m
            if track.half_width_m is not None
            else SUPPORT_ORBIT_DIAMETER_M / 2
        )
        if track.box is not None and len(track.box) == SUPPORT_BOX_POINTS - 1:
            corners = _grown_box(track.box, half_width)
            boxes.append((track.callsign, corners + [corners[0]]))
            continue
        half_length = track.length_m / 2 + half_width
        course = math.radians(track.course)
        # Along the orbit's own course, and across it. DCS x is north, y east,
        # and `bearing_degrees` is a compass bearing, so north is +x.
        along = (math.cos(course), math.sin(course))
        across = (-math.sin(course), math.cos(course))
        centre_x, centre_y = track.center
        corners = [
            (
                centre_x + along[0] * length + across[0] * width,
                centre_y + along[1] * length + across[1] * width,
            )
            for length, width in (
                (half_length, half_width),
                (half_length, -half_width),
                (-half_length, -half_width),
                (-half_length, half_width),
            )
        ]
        boxes.append((track.callsign, corners + [corners[0]]))
    return boxes


def _grown_box(
    corners: tuple[tuple[float, float], ...], margin: float
) -> list[tuple[float, float]]:
    """A tanker box's four corners, each pushed out by ``margin`` along both of
    its edges (square corners), so the turns at each corner stay inside it."""
    grown = []
    for index, (x, y) in enumerate(corners):
        offset_x = offset_y = 0.0
        for neighbour in (corners[index - 1], corners[(index + 1) % len(corners)]):
            edge = math.dist((x, y), neighbour)
            if edge < 1.0:
                continue
            offset_x += (x - neighbour[0]) / edge * margin
            offset_y += (y - neighbour[1]) / edge * margin
        grown.append((x + offset_x, y + offset_y))
    return grown


def _chain_bars(bars: list[list[tuple[float, float]]]) -> list[tuple[float, float]]:
    """Order and orient the front bars into one continuous trace.

    A front is a bar at most `max_frontline_width` wide centred on the supply
    crossing the two sides contest, so a theater's fronts are separated stubs
    with uncontested border between them. The gaps are joined straight: nothing
    in the campaign model says where an unopposed border runs, and a straight
    join is the one approximation that cannot invent a salient.
    """
    if not bars:
        return []
    remaining = list(bars)
    # Start from the endpoint farthest from the set's centroid, so the chain
    # runs across the theater instead of outward from its middle.
    ends = [point for bar in remaining for point in (bar[0], bar[-1])]
    centroid = (
        sum(x for x, _ in ends) / len(ends),
        sum(y for _, y in ends) / len(ends),
    )
    first = max(
        remaining,
        key=lambda bar: max(math.dist(bar[0], centroid), math.dist(bar[-1], centroid)),
    )
    remaining.remove(first)
    if math.dist(first[-1], centroid) > math.dist(first[0], centroid):
        first = first[::-1]
    chain = list(first)
    while remaining:
        tail = chain[-1]
        best = min(
            remaining,
            key=lambda bar: min(math.dist(tail, bar[0]), math.dist(tail, bar[-1])),
        )
        remaining.remove(best)
        if math.dist(tail, best[-1]) < math.dist(tail, best[0]):
            best = best[::-1]
        chain.extend(best)
    return chain


def decimate_open(
    points: list[tuple[float, float]], max_points: int
) -> list[tuple[float, float]]:
    """Thin an open polyline to `max_points`, keeping both ends."""
    if max_points < 2 or len(points) <= max_points:
        return points
    step = (len(points) - 1) / (max_points - 1)
    kept = [points[round(index * step)] for index in range(max_points)]
    kept[-1] = points[-1]
    return kept


def red_land_boundary(
    game: Game, max_lines: int, max_points_per_line: int
) -> list[tuple[str, list[tuple[float, float]]]]:
    """The land boundary with red, as runs fitting the display's line budget.

    One continuous trace, not a front per line: the pilot needs to read which
    side of the line is hostile, and a set of disconnected stubs cannot say it.
    Consecutive runs repeat the vertex they meet on, so the display draws them
    as one line.
    """
    bars = [points for _, points in flot_segments(game) if len(points) >= 2]
    chain = _chain_bars(bars)
    if len(chain) < 2:
        return []
    # Consecutive runs repeat their meeting vertex, which is what makes them
    # read as one line, so the repeats come out of the budget.
    budget = max_lines * max_points_per_line - (max_lines - 1)
    chain = decimate_open(chain, budget)
    runs: list[list[tuple[float, float]]] = []
    index = 0
    while index < len(chain) - 1 and len(runs) < max_lines:
        runs.append(chain[index : index + max_points_per_line])
        index += max_points_per_line - 1
    if len(runs) == 1:
        return [("FLOT", runs[0])]
    return [(f"FLOT {n}", points) for n, points in enumerate(runs, start=1)]


@dataclass(frozen=True)
class ThreatSite:
    """One enemy air-defense site the blue player's map already shows exact."""

    label: str
    #: The site's full map name; the Apache's TGT notes want it where the
    #: F-16 SA page wants the 3-char label.
    name: str
    x: float
    y: float
    range_m: float


#: NATO shorthand by DCS unit-type id / display-name keywords. Ordered: the
#: specific system names first (DCS ids say "Kub"/"S-300PS", never "SA-6").
_SAM_LABEL_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"S[-_ ]?400", "21"),
    (r"S[-_ ]?300|SA[-_ ]?10|SA[-_ ]?20", "10"),
    (r"S[-_ ]?200|SA[-_ ]?5", "5"),
    (r"S[-_ ]?125|SA[-_ ]?3", "3"),
    (r"S[-_ ]?75|SNR[-_ ]?75|SA[-_ ]?2\b", "2"),
    (r"BUK|SA[-_ ]?11", "11"),
    (r"SA[-_ ]?17", "17"),
    (r"TOR|SA[-_ ]?15", "15"),
    (r"KUB|SA[-_ ]?6", "6"),
    (r"OSA|SA[-_ ]?8", "8"),
    (r"STRELA[-_ ]?10|SA[-_ ]?13", "13"),
    (r"STRELA|SA[-_ ]?9", "9"),
    (r"TUNGUSKA|SA[-_ ]?19", "19"),
    (r"PANTSIR|SA[-_ ]?22", "22"),
    (r"SA[-_ ]?(\d+)", ""),  # any remaining SA-N -> the digits
    (r"PATRIOT", "P"),
    (r"HAWK", "HK"),
    (r"NASAMS", "NS"),
    (r"ROLAND", "RO"),
    (r"RAPIER", "RP"),
    (r"CHAPARRAL", "CH"),
    (r"HQ[-_ ]?7", "7"),
    (r"AVENGER", "AV"),
    (r"GEPARD|VULCAN|ZSU|SHILKA|ZU[-_ ]?23|AAA|FLAK", "A"),
)


def _threat_label(tgo_name: str, unit_names: list[str]) -> str:
    """A <=3-char SA-page label for a SAM site, derived from its unit types."""
    haystack = " ".join([tgo_name, *unit_names]).upper()
    for pattern, replacement in _SAM_LABEL_PATTERNS:
        match = re.search(pattern, haystack)
        if match:
            return replacement if replacement else match.group(1)[:3]
    return sanitize_short_name(tgo_name, 3) or "T"


def known_enemy_threat_sites(game: Game, viewer: Player) -> list[ThreatSite]:
    """Enemy air-defense sites the viewer's map shows exact, longest range
    first.

    The filter mirrors the map: ``known_for(viewer)`` gates intel fog (an
    un-engaged site never leaks a ring) and ``map_hidden`` (§50 ambush teams) is
    never emitted.
    """
    sites = []
    for cp in game.theater.controlpoints:
        if not cp.captured.is_red:
            continue
        for tgo in getattr(cp, "ground_objects", []):
            if getattr(tgo, "category", None) != "aa":
                continue
            if getattr(tgo, "map_hidden", False):
                continue
            if not tgo.known_for(viewer):
                continue
            threat_range = tgo.max_threat_range()
            if not threat_range or threat_range.meters <= 0:
                continue
            unit_names = []
            for group in getattr(tgo, "groups", []):
                for unit in getattr(group, "units", []):
                    unit_type = getattr(unit, "type", None)
                    # TheaterUnit.type is a pydcs class; its .id is the DCS
                    # type string ("Kub 1S91 str") the label patterns key on.
                    unit_names.append(
                        str(getattr(unit_type, "id", None) or unit_type or "")
                    )
            sites.append(
                ThreatSite(
                    label=_threat_label(tgo.name, unit_names),
                    name=str(tgo.name),
                    x=tgo.position.x,
                    y=tgo.position.y,
                    range_m=threat_range.meters,
                )
            )
    sites.sort(key=lambda site: site.range_m, reverse=True)
    return sites


def _distance_to_route(x: float, y: float, route: list[tuple[float, float]]) -> float:
    """Metres from a point to the nearest leg of the route polyline."""
    if len(route) == 1:
        return math.hypot(x - route[0][0], y - route[0][1])
    best = math.inf
    for (ax, ay), (bx, by) in zip(route, route[1:]):
        dx, dy = bx - ax, by - ay
        length_sq = dx * dx + dy * dy
        t = 0.0 if length_sq == 0 else ((x - ax) * dx + (y - ay) * dy) / length_sq
        t = max(0.0, min(1.0, t))
        best = min(best, math.hypot(x - (ax + t * dx), y - (ay + t * dy)))
    return best


def _segment_distance(
    a: tuple[float, float],
    b: tuple[float, float],
    route: list[tuple[float, float]],
) -> float:
    """Metres between segment a-b and the route polyline."""
    best = min(_distance_to_route(a[0], a[1], route), _distance_to_route(*b, route))
    for c, d in zip(route, route[1:]):
        best = min(best, _distance_to_route(c[0], c[1], [a, b]))
        best = min(best, _distance_to_route(d[0], d[1], [a, b]))
        if _segments_cross(a, b, c, d):
            return 0.0
    return best


def _segments_cross(
    a: tuple[float, float],
    b: tuple[float, float],
    c: tuple[float, float],
    d: tuple[float, float],
) -> bool:
    def side(
        p: tuple[float, float], q: tuple[float, float], r: tuple[float, float]
    ) -> float:
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    return side(a, b, c) * side(a, b, d) < 0 and side(c, d, a) * side(c, d, b) < 0


def land_border_runs(
    game: Game, route: list[tuple[float, float]], corridor_m: float
) -> list[tuple[str, list[tuple[float, float]]]]:
    """Each land border that comes within ``corridor_m`` of the route, as one
    continuous line, nearest first.

    A frontier is an edge two countries share: the §98 terrain files are one
    shared coverage, so neighbours agree vertex for vertex. An edge only one
    country has is coast or the map's clip edge, and is not drawn. A border
    that leaves the strip and comes back is drawn through the gap (DM
    2026-09-29): two pieces of one border read as two borders.
    """
    zones = getattr(game.theater, "neutral_border_zones", None) or []
    rings = [
        (zone.country, [(float(x), float(y)) for x, y in zone.border])
        for zone in zones
        if len(zone.border) >= 3
    ]
    owners: dict[frozenset[tuple[float, float]], frozenset[str]] = {}
    for country, ring in rings:
        for a, b in zip(ring, ring[1:] + ring[:1]):
            key = frozenset((a, b))
            owners[key] = owners.get(key, frozenset()) | {country}
    emitted: set[frozenset[tuple[float, float]]] = set()
    # Each stretch of frontier between one pair of countries, walked once.
    chains: list[tuple[frozenset[str], list[tuple[float, float]]]] = []
    for _country, ring in rings:
        edges = list(zip(ring, ring[1:] + ring[:1]))
        pairs = [
            (
                owners[frozenset(edge)]
                if len(owners[frozenset(edge)]) >= 2 and frozenset(edge) not in emitted
                else None
            )
            for edge in edges
        ]
        if not any(pairs):
            continue
        # Start where the neighbour changes so no chain is cut at the ring's seam.
        first = next((i for i in range(len(edges)) if pairs[i] != pairs[i - 1]), 0)
        chain: list[tuple[float, float]] = []
        chain_pair: Optional[frozenset[str]] = None
        for offset in range(len(edges)):
            index = (first + offset) % len(edges)
            edge, pair = edges[index], pairs[index]
            if chain and pair != chain_pair:
                chains.append((chain_pair, chain))  # type: ignore[arg-type]
                chain = []
            if pair is None:
                continue
            if not chain:
                chain, chain_pair = [edge[0]], pair
            chain.append(edge[1])
            emitted.add(frozenset(edge))
        if chain:
            chains.append((chain_pair, chain))  # type: ignore[arg-type]
    if not route:
        return []
    nearest: dict[frozenset[str], tuple[float, list[tuple[float, float]]]] = {}
    for pair, chain in chains:
        near = [
            index
            for index, (a, b) in enumerate(zip(chain, chain[1:]))
            if _segment_distance(a, b, route) <= corridor_m
        ]
        if not near:
            continue
        line = chain[near[0] : near[-1] + 2]
        distance = min(_distance_to_route(x, y, route) for x, y in line)
        if pair not in nearest or distance < nearest[pair][0]:
            nearest[pair] = (distance, line)
    ordered = sorted(nearest.items(), key=lambda item: item[1][0])
    return [("-".join(sorted(pair)), line) for pair, (_d, line) in ordered]


def country_at(game: Game, x: float, y: float) -> Optional[str]:
    """The §98 country whose border contains this point, if any."""
    for zone in getattr(game.theater, "neutral_border_zones", None) or []:
        ring = zone.border
        inside = False
        for (ax, ay), (bx, by) in zip(ring, ring[1:] + ring[:1]):
            if (ay > y) != (by > y) and x < ax + (y - ay) * (bx - ax) / (by - ay):
                inside = not inside
        if inside:
            return str(zone.country)
    return None


def country_code(country: str) -> str:
    """The country's 3-letter code (SYR, IRQ), from pydcs where it knows one."""
    from dcs import countries

    try:
        return str(countries.get_by_name(country).shortname)
    except Exception:
        return "".join(c for c in country.upper() if c.isalpha())[:3]


def threat_sites_for(game: Game, flight: FlightData) -> list[ThreatSite]:
    """The known sites this flight's cartridge draws: every one, or only those
    whose ring comes within the DTC tab's distance of the route (§102)."""
    sites = known_enemy_threat_sites(game, flight.friendly)
    radius_nm = flight.dtc_options.threat_ring_radius_nm
    route = [(w.position.x, w.position.y) for w in flight.waypoints]
    if radius_nm is None or not route:
        return sites
    limit = radius_nm * 1852.0
    return [
        site
        for site in sites
        if _distance_to_route(site.x, site.y, route) - site.range_m <= limit
    ]


def frequency_labels(
    flight: FlightData, mission_data: MissionData
) -> dict[RadioFrequency, str]:
    """A short name for every mission frequency the channel allocator may have
    preset: the one thing the Hornet's COMM section adds over the miz."""
    labels: dict[RadioFrequency, str] = {}

    def put(freq: Optional[RadioFrequency], label: str) -> None:
        if freq is not None and freq not in labels:
            labels[freq] = sanitize_short_name(label)

    put(flight.intra_flight_channel, short_callsign(flight.callsign))
    for awacs in mission_data.awacs:
        put(awacs.freq, short_callsign(awacs.callsign))
    for tanker in mission_data.tankers:
        put(tanker.freq, short_callsign(tanker.callsign))
    for jtac in mission_data.jtacs:
        put(jtac.freq, "JTAC")
    put(flight.package.frequency, "PKG")
    put(flight.departure.atc, "DEP")
    if flight.arrival != flight.departure:
        put(flight.arrival.atc, "ARR")
    if flight.divert is not None:
        put(flight.divert.atc, "DVT")
    return labels
