"""Civilian air traffic: a steady stream of real civil aircraft, clear of the war.

Rebuilt 2026-11-09 to the DM's picks; ``docs/dev/design/retlab-civil-traffic-notes.md``
has the design. Python plans every flight of the mission here. The ones flying at
mission start are spawned live; the rest wait switched off (late activation), and the
``civtraffic`` plugin switches them on one by one to hold the airborne count at the
setting's level. Not RAT: RAT crashed the sim resolving heliport ids.

Constraints learned from flown tests:
- pydcs speed arguments are km/h; passing m/s air-started the old fleet below stall.
- A transit needs a waypoint at its cruise level, or DCS flies a shallow V and never
  climbs (2026-08-08).
- Fixed-wing traffic never uses a field without a runway (test 59: Syria's helipads).
- No heavy ground-starts from a high field (test 40: an IL-76 out of Bamyan).
"""

from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterable, Optional, Sequence, Type

from dcs.mapping import Point
from dcs.mission import StartType
from dcs.task import OptROE, SetInvisibleCommand
from dcs.unittype import ShipType
from shapely.geometry import LineString
from shapely.geometry import Point as ShapelyPoint
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from pydcs_extensions.vietnamwarvessels.vietnamwarvessels import (
    vwv_junk,
    vwv_sampan_canopy,
    vwv_sampan_covered,
    vwv_sampan_covered_ak47,
    vwv_sampan_open,
    vwv_sampan_open_box,
)

from game.settings.enums import CivilAirTraffic
from game.utils import mps

from .civilianfleet import CivilRegion, CivilType, region_for

if TYPE_CHECKING:
    from dcs.country import Country
    from dcs.mission import Mission
    from game.factions.faction import Faction
    from game.game import Game
    from .missiondata import MissionData

NM = 1_852.0

# ── Traffic levels ────────────────────────────────────────────────────────────
#: Aircraft flying at once, per setting: (airways, local hops).
TARGETS: dict[CivilAirTraffic, tuple[int, int]] = {
    CivilAirTraffic.OFF: (0, 0),
    CivilAirTraffic.LIGHT: (4, 1),
    CivilAirTraffic.NORMAL: (6, 3),
    CivilAirTraffic.BUSY: (10, 4),
}
#: The queue covers this long a mission at the target level.
COVER_S = 4 * 3_600
#: Upper bound on planned flights per layer, so a busy setting cannot bloat the miz.
MAX_FLIGHTS_PER_LAYER = 60

# ── Where civil traffic may fly ───────────────────────────────────────────────
FRONT_KEEPOUT_M = 40 * NM
#: Margin added outside each known SAM ring.
SAM_MARGIN_M = 5 * NM
#: An airway has to cross something to read as a transit rather than a hop.
MIN_TRANSIT_M = 80 * NM
HOP_MIN_M = 10 * NM
HOP_MAX_M = 70 * NM
#: Map-edge entry and exit points per side of the airfield box.
GATES_PER_SIDE = 6

# ── How a flight is flown ─────────────────────────────────────────────────────
#: Where along a field departure the cruise level is reached, and where a field
#: arrival leaves it.
CRUISE_ENTRY_FRAC = 0.25
CRUISE_EXIT_FRAC = 0.9
#: Where along its route an airliner flying at mission start is placed.
LIVE_FRAC_RANGE = (0.1, 0.8)
#: Allowance for the climb out of and the approach into a field.
FIELD_END_ALLOWANCE_S = 600
#: Fixed-wing ground starts are not planned from fields above this; they fly in from
#: the map edge instead.
HIGH_FIELD_M = 2_000

AIRWAY = "airway"
HOP = "hop"


@dataclass(frozen=True)
class CivilField:
    """An airfield neither side uses, clear of the war."""

    name: str
    point: Point
    has_runway: bool = True
    elevation_m: Optional[float] = None


@dataclass(frozen=True)
class CivilFlight:
    """One planned civil flight.

    ``origin``/``destination`` of None mean the map edge: the flight enters at
    ``start`` already at cruise, or leaves the map at ``end``.
    """

    civil_type: CivilType
    layer: str
    origin: Optional[CivilField]
    destination: Optional[CivilField]
    start: Point
    end: Point
    #: Flying at mission start rather than waiting to be switched on.
    live: bool
    #: Set when the flight starts in the air: a map-edge entry, or a live airliner
    #: placed partway along its route.
    air_start_point: Optional[Point]
    callsign: str
    livery: str
    duration_s: int

    @property
    def air_start(self) -> bool:
        return self.air_start_point is not None


@dataclass(frozen=True)
class CivilTrafficLuaFlight:
    """What the ``civtraffic`` plugin needs about one spawned flight."""

    group: str
    layer: str
    queued: bool
    #: Set when the flight leaves at the map edge: the plugin removes it there.
    exit_point: Optional[tuple[float, float]]
    #: The departure field, so two take-offs from one runway are spaced.
    field: Optional[str]
    max_age_s: int


@dataclass
class CivilTrafficLua:
    targets: dict[str, int]
    flights: list[CivilTrafficLuaFlight] = field(default_factory=list)


def _neutral_country(mission: "Mission") -> "Optional[Country]":
    countries = list(mission.coalition["neutrals"].countries.values())
    return countries[0] if countries else None


def _dist(a: Point, b: Point) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def along(a: Point, b: Point, frac: float) -> Point:
    """The point ``frac`` of the way from ``a`` to ``b``."""
    return Point(a.x + (b.x - a.x) * frac, a.y + (b.y - a.y) * frac, a._terrain)


def war_airspace(
    fronts: Iterable[Point], sam_rings: Iterable[BaseGeometry]
) -> BaseGeometry:
    """Everywhere civil traffic stays out of: the fronts and every known SAM ring."""
    shapes: list[BaseGeometry] = [
        ShapelyPoint(f.x, f.y).buffer(FRONT_KEEPOUT_M) for f in fronts
    ]
    shapes.extend(ring.buffer(SAM_MARGIN_M) for ring in sam_rings if not ring.is_empty)
    return unary_union(shapes)


def clear_of(a: Point, b: Point, war: BaseGeometry) -> bool:
    """Whether the straight leg from ``a`` to ``b`` stays out of the war."""
    if war.is_empty:
        return True
    return not LineString([(a.x, a.y), (b.x, b.y)]).intersects(war)


def edge_gates(points: Sequence[Point], per_side: int = GATES_PER_SIDE) -> list[Point]:
    """Entry and exit points spaced along the box around every airfield on the map.

    The airfield box, not ``Terrain.bounds``: the bounds leave out real airfields and
    run upside down on three maps.
    """
    if len(points) < 2:
        return []
    terrain = points[0]._terrain
    xs = [p.x for p in points]
    ys = [p.y for p in points]
    lo_x, hi_x, lo_y, hi_y = min(xs), max(xs), min(ys), max(ys)
    gates: list[Point] = []
    for i in range(per_side):
        f = (i + 0.5) / per_side
        x = lo_x + (hi_x - lo_x) * f
        y = lo_y + (hi_y - lo_y) * f
        gates.append(Point(hi_x, y, terrain))  # north
        gates.append(Point(lo_x, y, terrain))  # south
        gates.append(Point(x, hi_y, terrain))  # east
        gates.append(Point(x, lo_y, terrain))  # west
    return gates


def _same_side(a: Point, b: Point) -> bool:
    return math.isclose(a.x, b.x) or math.isclose(a.y, b.y)


#: An airway end: a field, or a map-edge gate (None).
_End = tuple[Optional[CivilField], Point]


def airway_routes(
    fields: Sequence[CivilField], gates: Sequence[Point], war: BaseGeometry
) -> list[tuple[_End, _End]]:
    """Every long, war-free leg between two ends, in both directions."""
    ends: list[_End] = [(f, f.point) for f in fields if f.has_runway]
    ends.extend((None, g) for g in gates)
    routes: list[tuple[_End, _End]] = []
    for i, a in enumerate(ends):
        for b in ends[i + 1 :]:
            if a[0] is None and b[0] is None and _same_side(a[1], b[1]):
                continue
            if _dist(a[1], b[1]) < MIN_TRANSIT_M or not clear_of(a[1], b[1], war):
                continue
            routes.append((a, b))
            routes.append((b, a))
    return routes


def hop_routes(
    fields: Sequence[CivilField], war: BaseGeometry
) -> list[tuple[CivilField, CivilField]]:
    """Every short, war-free hop between two nearby fields, in both directions."""
    routes: list[tuple[CivilField, CivilField]] = []
    for i, a in enumerate(fields):
        for b in fields[i + 1 :]:
            d = _dist(a.point, b.point)
            if HOP_MIN_M <= d <= HOP_MAX_M and clear_of(a.point, b.point, war):
                routes.append((a, b))
                routes.append((b, a))
    return routes


def _callsign(region: CivilRegion, rng: random.Random) -> str:
    operator = rng.choice(region.operators) if region.operators else "CIVIL"
    return f"{operator} {rng.randint(100, 999)}"


def _duration(
    civil_type: CivilType,
    start: Point,
    end: Point,
    origin: Optional[CivilField],
    destination: Optional[CivilField],
    air_start: bool,
) -> int:
    seconds = _dist(start, end) / civil_type.speed_ms
    if origin is not None and not air_start:
        seconds += FIELD_END_ALLOWANCE_S
    if destination is not None:
        seconds += FIELD_END_ALLOWANCE_S
    return int(seconds)


def _high_field(origin: Optional[CivilField]) -> bool:
    return (
        origin is not None
        and origin.elevation_m is not None
        and origin.elevation_m > HIGH_FIELD_M
    )


def plan_airways(
    routes: Sequence[tuple[_End, _End]],
    region: CivilRegion,
    target: int,
    rng: random.Random,
    cover_s: int = COVER_S,
) -> list[CivilFlight]:
    """The airliners: ``target`` flying at mission start, then a queue to replace
    them as they land or leave the map."""
    if target <= 0 or not routes or not region.airliners:
        return []
    usable = [r for r in routes if not _high_field(r[0][0])]
    if not usable:
        return []
    flights: list[CivilFlight] = []
    queued_s = 0
    while len(flights) < target + MAX_FLIGHTS_PER_LAYER:
        live = len(flights) < target
        if not live and queued_s >= target * cover_s:
            break
        civil_type = rng.choice(region.airliners)
        (origin, start), (destination, end) = rng.choice(usable)
        air_point: Optional[Point]
        if live:
            air_point = along(start, end, rng.uniform(*LIVE_FRAC_RANGE))
        elif origin is None:
            air_point = start
        else:
            air_point = None
        duration = _duration(
            civil_type,
            air_point or start,
            end,
            origin,
            destination,
            air_point is not None,
        )
        flights.append(
            CivilFlight(
                civil_type=civil_type,
                layer=AIRWAY,
                origin=origin,
                destination=destination,
                start=start,
                end=end,
                live=live,
                air_start_point=air_point,
                callsign=_callsign(region, rng),
                livery=rng.choice(civil_type.liveries),
                duration_s=duration,
            )
        )
        if not live:
            queued_s += duration
    return flights


def plan_hops(
    routes: Sequence[tuple[CivilField, CivilField]],
    region: CivilRegion,
    target: int,
    rng: random.Random,
    cover_s: int = COVER_S,
) -> list[CivilFlight]:
    """Light planes and helicopters: short low hops between nearby civil fields."""
    if target <= 0 or not routes or not region.local:
        return []
    flights: list[CivilFlight] = []
    queued_s = 0
    used_origins: set[str] = set()
    while len(flights) < target + MAX_FLIGHTS_PER_LAYER:
        live = len(flights) < target
        if not live and queued_s >= target * cover_s:
            break
        civil_type = rng.choice(region.local)
        options = [
            r
            for r in routes
            if civil_type.is_helicopter or (r[0].has_runway and r[1].has_runway)
        ]
        if live:
            # Flights that start together leave from different fields.
            fresh = [r for r in options if r[0].name not in used_origins]
            options = fresh or options
        if not options:
            break
        origin, destination = rng.choice(options)
        used_origins.add(origin.name)
        duration = _duration(
            civil_type, origin.point, destination.point, origin, destination, False
        )
        flights.append(
            CivilFlight(
                civil_type=civil_type,
                layer=HOP,
                origin=origin,
                destination=destination,
                start=origin.point,
                end=destination.point,
                live=live,
                air_start_point=None,
                callsign=_callsign(region, rng),
                livery=rng.choice(civil_type.liveries),
                duration_s=duration,
            )
        )
        if not live:
            queued_s += duration
    return flights


def cruise_points(flight: CivilFlight) -> list[Point]:
    """The waypoints between the start and the end that hold the cruise level.

    A field departure climbs to level by ``CRUISE_ENTRY_FRAC``; a field arrival
    leaves it at ``CRUISE_EXIT_FRAC``. A flight placed partway along takes only the
    points still ahead of it.
    """
    if flight.layer == HOP:
        return [along(flight.start, flight.end, 0.5)]
    fracs: list[float] = []
    if flight.origin is not None:
        fracs.append(CRUISE_ENTRY_FRAC)
    if flight.destination is not None:
        fracs.append(CRUISE_EXIT_FRAC)
    done = 0.0
    if flight.air_start_point is not None:
        total = _dist(flight.start, flight.end)
        done = _dist(flight.start, flight.air_start_point) / total if total else 0.0
    return [along(flight.start, flight.end, f) for f in fracs if f > done]


def max_age_s(flight: CivilFlight) -> int:
    """How long the plugin lets a flight live before removing it as stuck."""
    return int(flight.duration_s * 1.5) + 1_200


class CivilianTrafficGenerator:
    """Plans and spawns the civil air traffic, and hands the plugin its schedule."""

    def __init__(
        self,
        mission: Mission,
        game: Game,
        mission_data: Optional[MissionData] = None,
        rng: Optional[random.Random] = None,
    ) -> None:
        self.mission = mission
        self.game = game
        self.mission_data = mission_data
        self.rng = rng or random.Random()

    def region(self) -> CivilRegion:
        region = region_for(getattr(self.mission.terrain, "name", ""))
        return region.for_year(self.game.date.year)

    def war(self) -> BaseGeometry:
        """The fronts and every SAM ring blue knows of, both sides.

        Blue's view, not the truth: a gap in the traffic over an unfound red site
        would give the site away.
        """
        from game.theater.fogofwar import fog_intact
        from game.theater.player import Player
        from game.threatzones import ThreatZones

        fronts = [front.position for front in self.game.theater.conflicts()]
        rings: list[BaseGeometry] = []
        with fog_intact():
            for side in (Player.BLUE, Player.RED):
                zones = ThreatZones.for_faction(self.game, side, viewer=Player.BLUE)
                rings.append(zones.air_defenses)
        return war_airspace(fronts, rings)

    def civil_fields(self, war: BaseGeometry) -> list[CivilField]:
        """Airfields neither side uses, outside the war."""
        from game.missiongenerator.kneeboard_recon.airport_imagery import (
            field_elevation_for_airport,
        )

        controlled = {
            cp.dcs_airport.name
            for cp in self.game.theater.controlpoints
            if cp.dcs_airport is not None
        }
        fields: list[CivilField] = []
        for name, airport in self.mission.terrain.airports.items():
            if name in controlled:
                continue
            point = airport.position
            if not war.is_empty and war.contains(ShapelyPoint(point.x, point.y)):
                continue
            fields.append(
                CivilField(
                    name=name,
                    point=point,
                    has_runway=bool(airport.runways),
                    elevation_m=field_elevation_for_airport(
                        self.mission.terrain, airport
                    ),
                )
            )
        return fields

    def plan(self) -> list[CivilFlight]:
        level = self.game.settings.civil_air_traffic
        airway_target, hop_target = TARGETS[level]
        region = self.region()
        if not region.airliners and not region.local:
            return []
        war = self.war()
        fields = self.civil_fields(war)
        gates = edge_gates([a.position for a in self.mission.terrain.airports.values()])
        return plan_airways(
            airway_routes(fields, gates, war), region, airway_target, self.rng
        ) + plan_hops(hop_routes(fields, war), region, hop_target, self.rng)

    def generate(self) -> None:
        level = self.game.settings.civil_air_traffic
        if level is CivilAirTraffic.OFF:
            logging.info("Civilian air traffic off by settings")
            return
        country = _neutral_country(self.mission)
        if country is None:
            logging.warning("No neutral country available; skipping civilian traffic")
            return
        flights = self.plan()
        airway_target, hop_target = TARGETS[level]
        lua = CivilTrafficLua(targets={AIRWAY: airway_target, HOP: hop_target})
        for idx, flight in enumerate(flights):
            name = self._spawn(country, idx, flight)
            if name is None:
                continue
            exit_point = (
                (flight.end.x, flight.end.y) if flight.destination is None else None
            )
            departs = flight.origin if not flight.air_start else None
            lua.flights.append(
                CivilTrafficLuaFlight(
                    group=name,
                    layer=flight.layer,
                    queued=not flight.live,
                    exit_point=exit_point,
                    field=departs.name if departs is not None else None,
                    max_age_s=max_age_s(flight),
                )
            )
        if self.mission_data is not None and lua.flights:
            self.mission_data.civil_traffic = lua
        logging.info(
            "Civilian traffic (%s): %d flights planned, %d airway and %d hop at once",
            level.value,
            len(lua.flights),
            airway_target,
            hop_target,
        )

    def _spawn(
        self, country: "Country", idx: int, flight: CivilFlight
    ) -> Optional[str]:
        # The callsign is what the F10 map shows; the index keeps names unique.
        name = f"{flight.callsign} [{idx}]"
        civil_type = flight.civil_type
        speed_kph = mps(civil_type.speed_ms).kph
        try:
            if flight.air_start_point is not None:
                group = self.mission.flight_group_inflight(
                    country=country,
                    name=name,
                    aircraft_type=civil_type.aircraft,
                    position=flight.air_start_point,
                    altitude=civil_type.altitude_m,
                    speed=speed_kph,
                    group_size=1,
                )
            else:
                assert flight.origin is not None
                departure = self.mission.terrain.airports.get(flight.origin.name)
                if departure is None:
                    return None
                group = self.mission.flight_group_from_airport(
                    country=country,
                    name=name,
                    aircraft_type=civil_type.aircraft,
                    airport=departure,
                    start_type=StartType.Runway,
                    group_size=1,
                )
            for unit in group.units:
                unit.livery_id = flight.livery.lower()

            for point in cruise_points(flight):
                waypoint = group.add_waypoint(point, civil_type.altitude_m, speed_kph)
                if civil_type.agl:
                    waypoint.alt_type = "RADIO"

            if flight.destination is None:
                group.add_waypoint(flight.end, civil_type.altitude_m, speed_kph)
            else:
                destination = self.mission.terrain.airports.get(flight.destination.name)
                if destination is not None:
                    group.land_at(destination)

            group.late_activation = not flight.live
            group.points[0].tasks.append(OptROE(OptROE.Values.WeaponHold))
            group.points[0].tasks.append(SetInvisibleCommand(True))
        except Exception:  # pragma: no cover - defensive; never block generation
            logging.exception("Failed to spawn civilian flight %s", name)
            return None
        return name


def loiter_chain(
    anchor: Point, radius_m: float, n_legs: int, rng: random.Random
) -> tuple[Point, ...]:
    """A small, irregular loop of points around ``anchor``, each leg within
    ``radius_m``, for slow ambient traffic that never strays far from its anchor."""
    base_angle = rng.uniform(0, 2 * math.pi)
    points = []
    for i in range(n_legs):
        angle = base_angle + i * (2 * math.pi / n_legs) + rng.uniform(-0.3, 0.3)
        r = radius_m * rng.uniform(0.4, 1.0)
        points.append(
            Point(
                anchor.x + r * math.cos(angle),
                anchor.y + r * math.sin(angle),
                anchor._terrain,
            )
        )
    return tuple(points)


# ── Naval civilian traffic (Sampans/Junks) ──────────────────────────────────────
# Only spawned when the campaign's faction requirements call for Vietnam War Vessels
# (see _faction_requires_vwv) -- these hulls don't exist outside that mod. Real-world
# top speed for both hull families is ~1-2 m/s, so unlike the air transits these never
# leave the immediate vicinity of their anchor; a tight loiter near a known-water point
# (a carrier/LHA control point) is realistic and avoids needing real water pathfinding.
NAVAL_TYPES: tuple[Type[ShipType], ...] = (
    vwv_junk,
    vwv_sampan_open,
    vwv_sampan_canopy,
    vwv_sampan_covered,
    vwv_sampan_covered_ak47,
    vwv_sampan_open_box,
)
NAVAL_SPEED_MS = 1.5  # matches the mod's own ~1-2 m/s hull speeds
NAVAL_LOITER_RADIUS_M = 1_500  # tight loiter around the anchor
NAVAL_LOITER_LEGS = 3  # waypoints in the loiter chain, excluding the anchor itself
NAVAL_PER_ANCHOR = (1, 2)  # min/max boats spawned per coastal anchor


def _faction_requires_vwv(faction: "Faction") -> bool:
    return any("vietnam war vessels" in key.lower() for key in faction.requirements)


@dataclass(frozen=True)
class NavalRoute:
    """One planned ambient boat: a slow loiter loop around a coastal anchor."""

    ship_type: Type[ShipType]
    chain: tuple[Point, ...]


class NavalCivilianTrafficGenerator:
    """Plans and spawns ambient Sampans/Junks near coastal control points.

    Only runs when a faction's requirements call for Vietnam War Vessels -- these hulls
    are mod-only and otherwise unavailable. See ``CivilianTrafficGenerator`` for the air
    traffic layer this complements.
    """

    def __init__(
        self, mission: Mission, game: Game, rng: Optional[random.Random] = None
    ) -> None:
        self.mission = mission
        self.game = game
        self.rng = rng or random.Random()

    def _vwv_available(self) -> bool:
        return _faction_requires_vwv(self.game.blue.faction) or _faction_requires_vwv(
            self.game.red.faction
        )

    def coastal_anchors(self) -> list[Point]:
        """Carrier/LHA control points: the only theater positions guaranteed to be
        navigable water, so no separate water-pathfinding is needed."""
        return [
            cp.position
            for cp in self.game.theater.controlpoints
            if cp.is_carrier or cp.is_lha
        ]

    def generate(self) -> None:
        if not self._vwv_available():
            return

        country = _neutral_country(self.mission)
        if country is None:
            logging.warning(
                "No neutral country available — skipping naval civilian traffic"
            )
            return

        anchors = self.coastal_anchors()
        routes: list[NavalRoute] = []
        for anchor in anchors:
            count = self.rng.randint(*NAVAL_PER_ANCHOR)
            for _ in range(count):
                ship_type = self.rng.choice(NAVAL_TYPES)
                chain = loiter_chain(
                    anchor, NAVAL_LOITER_RADIUS_M, NAVAL_LOITER_LEGS, self.rng
                )
                routes.append(NavalRoute(ship_type=ship_type, chain=chain))

        spawned = sum(
            1 for idx, route in enumerate(routes) if self._spawn(country, idx, route)
        )
        logging.info(
            "Naval civilian traffic: %d boats near %d coastal anchor(s)",
            spawned,
            len(anchors),
        )

    def _spawn(self, country: "Country", idx: int, route: NavalRoute) -> bool:
        name = f"CIV_{route.ship_type.id}_{idx}"
        try:
            group = self.mission.ship_group(
                country=country,
                name=name,
                _type=route.ship_type,
                position=route.chain[0],
                group_size=1,
            )
            for point in route.chain[1:]:
                # km/h, as above -- the raw m/s value crawled the hulls at ~0.8 kt.
                group.add_waypoint(point, mps(NAVAL_SPEED_MS).kph)

            group.points[0].tasks.append(OptROE(OptROE.Values.WeaponHold))
            group.points[0].tasks.append(SetInvisibleCommand(True))
        except Exception:  # pragma: no cover - defensive; never block generation
            logging.exception("Failed to spawn naval civilian traffic %s", name)
            return False
        return True
