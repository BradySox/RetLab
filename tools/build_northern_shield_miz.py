"""Build ``resources/campaigns/northern_shield_1988.miz``: Germany - Northern Shield 1988.

Red Tide's war seen from the north. In July 1988 the Soviet drive took Hamburg and
the Baltic coast but never crossed the straits. NATO holds Zealand, Bornholm and,
with Sweden in the war, Skane; the 16th Air Army, the Baltic Fleet and the East
German air force hold Mecklenburg and the Uckermark. There is no land front until
NATO takes a coastal field from the air.

Design note: docs/dev/design/retlab-northern-shield-1988-campaign-notes.md

What it writes, starting from ``red_tide.miz`` for the map and its scenery targets:

1.  **Ownership.** Three NATO fields across the water, four Warsaw Pact fields on
    the coast and south of it; every other field is neutral with dynamic spawn off.
2.  **Invert Sides.** Every red control point carries the invert flag.
3.  **Scenery.** Red Tide's scenery target sets inside the sector; its markers,
    influence zones and every group are dropped.
4.  **The SAM sites.** Eighteen Hawk, SA-2, SA-3, SA-5 and S-60 sites from Carsten's
    Cold War Germany Framework, unit by unit, as FIXED groups.
5.  **The land.** Base defenses, garrisons, depots, factories and the Soviet IADS
    nodes (HQs, comms towers, power) on real places. Barth's garrison stands inside
    its capture zone, so it has to be cleared before an air assault can take it.
6.  **The water.** Four HandyWind sea lanes: NATO's own ferries, and the two
    crossings that supply the first captured coastal fields.
7.  **The roads and the rail.** One M-113 route group per road, traced from real
    town lat/lon, Off Road at the ends and On Road between; one Train rail line.

Run from the repo root::

    python tools/build_northern_shield_miz.py <CG_Cold_War_Germany_Framework_1_1.miz>

Once the DM edits the laydown in the Mission Editor, his save is the source and this
tool is deleted, as Fulda Gap 1985's was.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Iterable, Union

from dcs.countries import CombinedJointTaskForcesBlue
from dcs.mapping import LatLng, Point
from dcs.mission import Mission
from dcs.point import PointAction
from dcs.ships import USS_Arleigh_Burke_IIa
from dcs.statics import Fortification, Warehouse
from dcs.terrain.terrain import Airport
from dcs.triggers import TriggerZone
from dcs.vehicles import AirDefence, Armor, vehicle_map

_REPO_ROOT = Path(__file__).resolve().parents[1]
for _path in (_REPO_ROOT, _REPO_ROOT / "tools"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from game.campaignloader.mizcampaignloader import MizCampaignLoader  # noqa: E402
from game.theater.airfieldclearance import (  # noqa: E402
    RUNWAY_HALF_LENGTH_M,
    RUNWAY_STRIP_HALF_WIDTH_M,
)

SOURCE = _REPO_ROOT / "resources/campaigns/red_tide.miz"
SOURCE_YAML = _REPO_ROOT / "resources/campaigns/red_tide.yaml"
DEST = _REPO_ROOT / "resources/campaigns/northern_shield_1988.miz"

BLUE_AIRFIELDS = ("Kastrup", "Sturup", "Bornholm")
RED_AIRFIELDS = ("Barth", "Peenemunde", "Neubrandenburg", "Templin")

#: The sector: Red Tide scenery sets outside it are dropped.
SECTOR_LAT = (52.75, 55.9)
SECTOR_LON = (11.9, 15.2)

# --- Marker vocabulary (must match MizCampaignLoader's *_UNIT_TYPE(S)) ---------
EWR = AirDefence.x_1L13_EWR
MEDIUM_SAM = AirDefence.S_75M_Volhov
SHORAD = AirDefence.Strela_1_9P31
AAA = AirDefence.ZSU_23_4_Shilka
ARMOR = Armor.M_1_Abrams
NAVAL = USS_Arleigh_Burke_IIa

RED_BLOCK = "red"
BLUE_BLOCK = "blue"

Anchor = Union[str, tuple[float, float]]

# (name, anchor, marker type, country block, placement). An anchor is an airfield
# name or a (lat, lon). Placement: "ring" 3-15 km out, "near" within 6 km first,
# "inner" 1.5-2.7 km out (inside the 3 km capture zone), "at" on the spot or as
# close as clear land allows. The yaml's ground_forces pins each mobile SAM's type.
ADDED_MARKERS: tuple[tuple[str, Anchor, Any, str, str], ...] = (
    # Denmark: the Stevns radar. The Hawks are template sites (FRAMEWORK_SITES).
    ("NS88-Stevns-EWR", (55.325, 12.440), EWR, RED_BLOCK, "at"),
    # Each NATO field keeps a garrison on it, or a red air assault takes it unopposed.
    ("NS88-Kastrup-Garrison", "Kastrup", ARMOR, BLUE_BLOCK, "inner"),
    ("NS88-Sturup-Garrison", "Sturup", ARMOR, BLUE_BLOCK, "inner"),
    ("NS88-Bornholm-Garrison", "Bornholm", ARMOR, BLUE_BLOCK, "inner"),
    ("NS88-Kastrup-SHORAD", "Kastrup", SHORAD, RED_BLOCK, "near"),
    ("NS88-Kastrup-AAA-1", "Kastrup", AAA, RED_BLOCK, "near"),
    ("NS88-Kastrup-AAA-2", "Kastrup", AAA, RED_BLOCK, "near"),
    # Sweden: an RBS 77 (Hawk) battery over Sturup.
    ("NS88-Hawk-Sturup", "Sturup", MEDIUM_SAM, RED_BLOCK, "ring"),
    ("NS88-Sturup-SHORAD", "Sturup", SHORAD, RED_BLOCK, "near"),
    ("NS88-Sturup-AAA", "Sturup", AAA, RED_BLOCK, "near"),
    # Bornholm: the Almindingen radar and the island's own guns.
    ("NS88-Almindingen-EWR", (55.115, 14.890), EWR, RED_BLOCK, "at"),
    ("NS88-Bornholm-SHORAD", "Bornholm", SHORAD, RED_BLOCK, "near"),
    ("NS88-Bornholm-AAA", "Bornholm", AAA, RED_BLOCK, "near"),
    # Barth: lightly held. Its guns and one tank company stand on the field.
    ("NS88-Barth-Garrison", "Barth", ARMOR, RED_BLOCK, "inner"),
    ("NS88-Barth-AAA", "Barth", AAA, RED_BLOCK, "inner"),
    ("NS88-Barth-SHORAD", "Barth", SHORAD, RED_BLOCK, "near"),
    # Peenemunde: the coast's fighter field.
    ("NS88-Peenemunde-SA6", "Peenemunde", MEDIUM_SAM, RED_BLOCK, "ring"),
    ("NS88-Peenemunde-SHORAD", "Peenemunde", SHORAD, RED_BLOCK, "near"),
    ("NS88-Peenemunde-AAA-1", "Peenemunde", AAA, RED_BLOCK, "near"),
    ("NS88-Peenemunde-AAA-2", "Peenemunde", AAA, RED_BLOCK, "near"),
    ("NS88-Peenemunde-EWR", "Peenemunde", EWR, RED_BLOCK, "ring"),
    ("NS88-Peenemunde-Armor-1", "Peenemunde", ARMOR, RED_BLOCK, "near"),
    ("NS88-Peenemunde-Armor-2", "Peenemunde", ARMOR, RED_BLOCK, "near"),
    # Neubrandenburg: the 3rd Air Defense Division at Trollenhagen.
    ("NS88-Neubrandenburg-SA11", "Neubrandenburg", MEDIUM_SAM, RED_BLOCK, "ring"),
    ("NS88-Neubrandenburg-SHORAD", "Neubrandenburg", SHORAD, RED_BLOCK, "near"),
    ("NS88-Neubrandenburg-AAA-1", "Neubrandenburg", AAA, RED_BLOCK, "near"),
    ("NS88-Neubrandenburg-AAA-2", "Neubrandenburg", AAA, RED_BLOCK, "near"),
    ("NS88-Neubrandenburg-EWR", "Neubrandenburg", EWR, RED_BLOCK, "ring"),
    ("NS88-Neubrandenburg-Armor-1", "Neubrandenburg", ARMOR, RED_BLOCK, "near"),
    ("NS88-Neubrandenburg-Armor-2", "Neubrandenburg", ARMOR, RED_BLOCK, "near"),
    # Templin: the rear.
    ("NS88-Templin-SHORAD", "Templin", SHORAD, RED_BLOCK, "near"),
    ("NS88-Templin-AAA", "Templin", AAA, RED_BLOCK, "near"),
    ("NS88-Templin-EWR", "Templin", EWR, RED_BLOCK, "ring"),
    ("NS88-Templin-Armor-1", "Templin", ARMOR, RED_BLOCK, "near"),
    ("NS88-Templin-Armor-2", "Templin", ARMOR, RED_BLOCK, "near"),
)

#: The fixed SAM sites, copied unit by unit from Carsten's Cold War Germany
#: Framework (a free Mission Editor template) as FIXED groups (features doc §122).
#: Rostock's SA-5 is left out: the S-200 stands in the rear, not on the coast (the
#: DM's call), and the campaign fields no SA-10 because the template has none.
FRAMEWORK_SITES: tuple[tuple[str, str], ...] = (
    ("DEN AD HAWK Kastrup", "FIXED Hawk Kastrup"),
    ("DEN AD HAWK Rolskilde", "FIXED Hawk Roskilde"),
    ("DEN AD HAWK Rodvig", "FIXED Hawk Rodvig"),
    ("DEN AD HAWK Rodvig South", "FIXED Hawk Rodvig South"),
    ("GDR AD SA3 Dranske", "FIXED SA-3 Dranske"),
    ("GDR AD SA3 Barhöft", "FIXED SA-3 Barhoft"),
    ("GDR AD SA2 Franzburg", "FIXED SA-2 Franzburg"),
    ("GDR AD SA2 Ueckermünde", "FIXED SA-2 Ueckermunde"),
    ("GDR AD SA2 Neubrandenburg", "FIXED SA-2 Neubrandenburg"),
    ("GDR AD S-60 Prenzlau", "FIXED S-60 Prenzlau"),
    ("GDR AD SA3 Templin", "FIXED SA-3 Templin"),
    ("GDR AD SA5 Badingen", "FIXED SA-5 Badingen"),
    ("GDR AD SA3 Velten", "FIXED SA-3 Velten"),
    ("GDR AD SA3 Fehrbellin", "FIXED SA-3 Fehrbellin"),
    ("GDR AD SA2 Werneuchen", "FIXED SA-2 Werneuchen"),
    ("POL AD SA3 Swinoujscie", "FIXED SA-3 Swinoujscie"),
    ("POL AD SA2 Szczecin", "FIXED SA-2 Szczecin"),
    ("POL AD SA3 Chojna", "FIXED SA-3 Chojna"),
)

#: The Baltic Fleet's surface group, in the Pomeranian Bay.
NAVAL_GROUPS = (("NS88-Baltic-Fleet", (54.550, 14.050)),)

#: (name, anchor, static type, block, placement). Ownership follows the nearest
#: control point.
ADDED_STATICS: tuple[tuple[str, Anchor, Any, str, str], ...] = (
    ("NS88-Kastrup-Ammo", "Kastrup", Warehouse._Ammunition_depot, BLUE_BLOCK, "near"),
    ("NS88-Kastrup-Factory", "Kastrup", Fortification.Workshop_A, BLUE_BLOCK, "ring"),
    ("NS88-Sturup-Ammo", "Sturup", Warehouse._Ammunition_depot, BLUE_BLOCK, "near"),
    (
        "NS88-Bornholm-Ammo",
        "Bornholm",
        Warehouse._Ammunition_depot,
        BLUE_BLOCK,
        "near",
    ),
    (
        "NS88-Peenemunde-Ammo",
        "Peenemunde",
        Warehouse._Ammunition_depot,
        RED_BLOCK,
        "near",
    ),
    (
        "NS88-Neubrandenburg-Ammo",
        "Neubrandenburg",
        Warehouse._Ammunition_depot,
        RED_BLOCK,
        "near",
    ),
    (
        "NS88-Neubrandenburg-Works",
        (53.545, 13.285),
        Fortification.Workshop_A,
        RED_BLOCK,
        "at",
    ),
    (
        "NS88-Neubrandenburg-Motorpool",
        "Neubrandenburg",
        Fortification.Garage_A,
        RED_BLOCK,
        "near",
    ),
    ("NS88-Templin-Ammo", "Templin", Warehouse._Ammunition_depot, RED_BLOCK, "near"),
    ("NS88-Templin-Motorpool", "Templin", Fortification.Garage_A, RED_BLOCK, "near"),
    ("NS88-Schwedt-Works", (53.090, 14.250), Fortification.Workshop_A, RED_BLOCK, "at"),
)

#: The Soviet IADS (Skynet's advanced mode, wired by range): HQs, comms and power.
COMMAND_CENTER = Fortification._Command_Center
COMMS = Fortification.Comms_tower_M
POWER = Fortification.GeneratorF
IADS_NODES: tuple[tuple[str, Any, float, float], ...] = (
    ("NS88-IADS-HQ-Neubrandenburg-3LVD", COMMAND_CENTER, 53.556, 13.240),
    ("NS88-IADS-HQ-Eberswalde-20GA", COMMAND_CENTER, 52.835, 13.820),
    ("NS88-IADS-Comms-Stralsund", COMMS, 54.300, 13.075),
    ("NS88-IADS-Comms-Greifswald", COMMS, 54.090, 13.380),
    ("NS88-IADS-Comms-Demmin", COMMS, 53.905, 13.045),
    ("NS88-IADS-Comms-Anklam", COMMS, 53.855, 13.690),
    ("NS88-IADS-Comms-Neustrelitz", COMMS, 53.365, 13.065),
    ("NS88-IADS-Comms-Prenzlau", COMMS, 53.315, 13.860),
    ("NS88-IADS-Comms-Templin", COMMS, 53.120, 13.500),
    ("NS88-IADS-Comms-Zehdenick", COMMS, 52.980, 13.335),
    ("NS88-IADS-Power-Lubmin", POWER, 54.140, 13.665),
    ("NS88-IADS-Power-Neubrandenburg", POWER, 53.570, 13.230),
    ("NS88-IADS-Power-Templin", POWER, 53.110, 13.470),
)

#: (route name, start control point, corridor towns as (lat, lon), end control
#: point). Only the end points bind a route to its control points.
ROADS: tuple[tuple[str, str, tuple[tuple[float, float], ...], str], ...] = (
    (
        "NS88 Road Barth - Peenemunde (Stralsund, Greifswald)",
        "Barth",
        ((54.317, 12.790), (54.298, 13.060), (54.093, 13.385), (54.053, 13.773)),
        "Peenemunde",
    ),
    (
        "NS88 Road Barth - Neubrandenburg (Grimmen, Demmin)",
        "Barth",
        ((54.202, 12.889), (54.110, 13.042), (53.905, 13.045), (53.692, 13.257)),
        "Neubrandenburg",
    ),
    (
        "NS88 Road Peenemunde - Neubrandenburg (Anklam)",
        "Peenemunde",
        ((54.053, 13.773), (53.856, 13.690), (53.664, 13.545)),
        "Neubrandenburg",
    ),
    (
        "NS88 Road Neubrandenburg - Templin (Neustrelitz)",
        "Neubrandenburg",
        ((53.470, 13.180), (53.365, 13.063), (53.213, 13.312)),
        "Templin",
    ),
)

#: The Nordbahn and its Barth branch: real stations; DCS paths the track between.
RAIL: tuple[tuple[str, tuple[tuple[float, float], ...]], ...] = (
    (
        "Barth-Neubrandenburg Rail",
        (
            (54.3632, 12.7200),  # Barth
            (54.2804, 12.8086),  # Velgast
            (54.3080, 13.0775),  # Stralsund
            (54.1128, 13.0393),  # Grimmen
            (53.9090, 13.0350),  # Demmin
            (53.5583, 13.2629),  # Neubrandenburg
        ),
    ),
)

#: (name, sea waypoints as (lat, lon)). The first and last bind the lane to the
#: nearest control point.
LANES: tuple[tuple[str, tuple[tuple[float, float], ...]], ...] = (
    (
        "NS88 Lane Kastrup - Sturup (Trelleborg)",
        ((55.600, 12.720), (55.450, 12.800), (55.330, 12.950), (55.360, 13.140)),
    ),
    (
        "NS88 Lane Kastrup - Bornholm (Ronne)",
        (
            (55.600, 12.720),
            (55.450, 12.800),
            (55.300, 12.950),
            (55.250, 13.600),
            (55.120, 14.400),
            (55.095, 14.680),
        ),
    ),
    (
        "NS88 Lane Kastrup - Barth (Zingst)",
        (
            (55.600, 12.720),
            (55.450, 12.800),
            (55.300, 12.900),
            (54.800, 12.800),
            (54.470, 12.700),
        ),
    ),
    (
        "NS88 Lane Bornholm - Peenemunde",
        ((55.080, 14.650), (54.700, 14.200), (54.300, 13.950), (54.215, 13.880)),
    ),
)

# --- Placement tolerances ------------------------------------------------------
#: Clear of the 3,000 m capture zone with margin, so a marker's units are too.
MIN_OFFSET_M = 3400.0
MAX_OFFSET_M = 15000.0
STEP_M = 500.0
BEARING_STEP_DEG = 15
MIN_SEPARATION_M = 900.0
NEAR_OFFSET_M = 6000.0
#: Inside the 3,000 m capture zone, clear of the runway band.
INNER_OFFSETS_M = (1500.0, 2700.0)
INNER_SEPARATION_M = 400.0
#: A marker placed "at" a named spot may move this far to find clear land.
AT_SEARCH_M = 3000.0
AT_STEP_M = 250.0
#: Clear of the 3,000 m capture zone, with margin.
MOTORPOOL_MIN_OFFSET_M = 3500.0

Segment = tuple[Point, Point]


def _theater() -> Any:
    """The GermanyCW theatre, loaded only for its landmap."""
    from game import persistency
    from game.campaignloader.campaign import Campaign

    persistency.setup(str(Path.home() / "Saved Games" / "DCS"), False, 0)
    return Campaign.from_file(SOURCE_YAML).load_theater(advanced_iads=False)


def _xy(terrain: Any, lat: float, lon: float) -> Point:
    return Point.from_latlng(LatLng(lat, lon), terrain)


def _in_sector(position: Point) -> bool:
    ll = position.latlng()
    return (
        SECTOR_LAT[0] <= ll.lat <= SECTOR_LAT[1]
        and SECTOR_LON[0] <= ll.lng <= SECTOR_LON[1]
    )


def _segment_distance(p: Point, a: Point, b: Point) -> float:
    dx, dy = b.x - a.x, b.y - a.y
    length_sq = dx * dx + dy * dy
    t = 0.0 if length_sq == 0 else ((p.x - a.x) * dx + (p.y - a.y) * dy) / length_sq
    t = max(0.0, min(1.0, t))
    cx, cy = a.x + t * dx, a.y + t * dy
    return float(((p.x - cx) ** 2 + (p.y - cy) ** 2) ** 0.5)


def _runway_segments(airport: Airport) -> list[Segment]:
    segments = []
    for runway in airport.runways:
        heading = float(runway.heading)
        start = airport.position.point_from_heading(heading, RUNWAY_HALF_LENGTH_M)
        end = airport.position.point_from_heading(heading + 180.0, RUNWAY_HALF_LENGTH_M)
        segments.append((start, end))
    return segments


class Placer:
    """Finds clear land for an added marker, deterministically.

    "Clear" is the landmap's own answer: inside an inclusion zone and outside
    every exclusion zone, and off every runway strip. Where no clear point is in
    reach the marker falls back to inclusion-only ground, and the report names it.
    """

    def __init__(self, theater: Any, taken: list[Point], runways: list[Segment]):
        self.theater = theater
        self.taken = taken
        self.runways = runways
        self.relaxed: list[str] = []

    def _free(self, candidate: Point, separation: float) -> bool:
        return all(
            candidate.distance_to_point(other) >= separation for other in self.taken
        )

    def _off_runways(self, candidate: Point) -> bool:
        return all(
            _segment_distance(candidate, a, b) >= RUNWAY_STRIP_HALF_WIDTH_M
            for a, b in self.runways
        )

    def _pick(
        self,
        name: str,
        passes: Iterable[tuple[list[Point], bool]],
        separation: float = MIN_SEPARATION_M,
    ) -> Point:
        for candidates, relaxed in passes:
            for candidate in candidates:
                if not self.theater.is_on_land(candidate, ignore_exclusion=relaxed):
                    continue
                if not self._off_runways(candidate):
                    continue
                if self._free(candidate, separation):
                    if relaxed:
                        self.relaxed.append(name)
                    self.taken.append(candidate)
                    return candidate
        raise RuntimeError(f"no land for {name} within reach of its anchor")

    @staticmethod
    def _rings(
        origin: Point, start: float, stop: float = MAX_OFFSET_M, step: float = STEP_M
    ) -> list[Point]:
        found = []
        radius = start
        while radius <= stop:
            for bearing in range(0, 360, BEARING_STEP_DEG):
                found.append(origin.point_from_heading(bearing, radius))
            radius += step
        return found

    def ring(self, name: str, origin: Point, start: float = MIN_OFFSET_M) -> Point:
        rings = self._rings(origin, start)
        return self._pick(name, ((rings, False), (rings, True)))

    def near(self, name: str, origin: Point, start: float = MIN_OFFSET_M) -> Point:
        close = self._rings(origin, start, NEAR_OFFSET_M)
        far = self._rings(origin, NEAR_OFFSET_M + STEP_M)
        return self._pick(
            name, ((close, False), (close, True), (far, False), (far, True))
        )

    def inner(self, name: str, origin: Point) -> Point:
        low, high = INNER_OFFSETS_M
        rings = self._rings(origin, low, high, 300.0)
        return self._pick(name, ((rings, False), (rings, True)), INNER_SEPARATION_M)

    def at(self, name: str, spot: Point) -> Point:
        candidates = [spot] + self._rings(spot, AT_STEP_M, AT_SEARCH_M, AT_STEP_M)
        return self._pick(name, ((candidates, False), (candidates, True)))


def _country(mission: Mission, block: str) -> Any:
    country = mission.country(
        MizCampaignLoader.BLUE_COUNTRY.name
        if block == BLUE_BLOCK
        else MizCampaignLoader.RED_COUNTRY.name
    )
    assert country is not None
    return country


def _is_white(zone: TriggerZone) -> bool:
    return zone.color[1] == 1 and zone.color[2] == 1 and zone.color[3] == 1


def _is_blue(zone: TriggerZone) -> bool:
    return zone.color[1] == 0 and zone.color[2] == 0 and zone.color[3] == 1


def _contains(parent: TriggerZone, point: Point) -> bool:
    radius = getattr(parent, "radius", 0.0)
    return parent.position.distance_to_point(point) < radius


def _strip(mission: Mission) -> None:
    """Keep the map, its settings and the sector's scenery sets; drop the rest."""
    for coalition in mission.coalition.values():
        for country in coalition.countries.values():
            for groups in (
                country.vehicle_group,
                country.ship_group,
                country.plane_group,
                country.helicopter_group,
                country.static_group,
            ):
                groups.clear()
    zones = mission.triggers._zones
    parents = [z for z in zones if _is_blue(z) and _in_sector(z.position)]
    kept: list[TriggerZone] = list(parents)
    for zone in zones:
        if _is_white(zone) and any(_contains(p, zone.position) for p in parents):
            kept.append(zone)
    mission.triggers._zones = kept
    print(f"scenery: kept {len(parents)} target sets, {len(kept) - len(parents)} parts")
    # pydcs reads the source's bare 'theatre' entry as a resource and writes it twice.
    mission.map_resource.binary_files = [
        f for f in mission.map_resource.binary_files if f["respath"] != "theatre"
    ]


def _set_ownership(mission: Mission) -> None:
    print("airfield ownership:")
    for airport in mission.terrain.airport_list():
        airport.unlimited_aircrafts = False
        if airport.name in BLUE_AIRFIELDS:
            airport.set_blue()
        elif airport.name in RED_AIRFIELDS:
            airport.set_red()
            # The invert flag: an inverted game hands this field to the player.
            airport.unlimited_aircrafts = True
        else:
            airport.set_neutral()
            # Neutral WITH dynamic spawn reads as a red control point here.
            airport.dynamic_spawn = False
    for name in BLUE_AIRFIELDS + RED_AIRFIELDS:
        if name not in mission.terrain.airports:
            raise RuntimeError(f"{name} is not an airfield on this terrain")
        side = "BLUE" if name in BLUE_AIRFIELDS else "RED"
        print(f"  {name:<28} {side}")


def _add_vehicle(
    mission: Mission, block: str, name: str, position: Point, unit_type: Any
) -> Any:
    group = mission.vehicle_group(
        country=_country(mission, block), name=name, _type=unit_type, position=position
    )
    # Markers are read for their type and position only; they are never driven.
    for point in group.points:
        point.action = PointAction.OffRoad
        point.speed = 0
    return group


def _report(name: str, position: Point, anchor: str = "") -> None:
    ll = position.latlng()
    print(f"  {name:<40} ({ll.lat:7.3f}, {ll.lng:7.3f})  {anchor}")


def _origin(mission: Mission, anchor: Anchor) -> Point:
    if isinstance(anchor, str):
        return mission.terrain.airports[anchor].position
    return _xy(mission.terrain, *anchor)


def _place(
    mission: Mission, placer: Placer, name: str, anchor: Anchor, how: str, start: float
) -> Point:
    origin = _origin(mission, anchor)
    if how == "at":
        return placer.at(name, origin)
    if how == "inner":
        return placer.inner(name, origin)
    if how == "near":
        return placer.near(name, origin, start)
    return placer.ring(name, origin, start)


def _author_land(mission: Mission, placer: Placer) -> None:
    print("\nadded markers:")
    for name, anchor, unit_type, block, how in ADDED_MARKERS:
        position = _place(mission, placer, name, anchor, how, MIN_OFFSET_M)
        _add_vehicle(mission, block, name, position, unit_type)
        _report(name, position, str(anchor))

    print("\nnavy:")
    for name, (lat, lon) in NAVAL_GROUPS:
        position = _xy(mission.terrain, lat, lon)
        if placer.theater.is_on_land(position, ignore_exclusion=True):
            raise RuntimeError(f"{name} is on land")
        mission.ship_group(
            country=_country(mission, RED_BLOCK),
            name=name,
            _type=NAVAL,
            position=position,
        )
        _report(name, position)

    print("\neconomy:")
    for name, anchor, static_type, block, how in ADDED_STATICS:
        start = MIN_OFFSET_M
        if static_type is Fortification.Garage_A:
            # A motorpool's parked armor inside a capture zone blocks the capture.
            start = MOTORPOOL_MIN_OFFSET_M
        position = _place(mission, placer, name, anchor, how, start)
        mission.static_group(
            country=_country(mission, block),
            name=name,
            _type=static_type,
            position=position,
        )
        _report(name, position, str(anchor))

    print("\nSoviet IADS:")
    for name, static_type, lat, lon in IADS_NODES:
        position = placer.at(name, _xy(mission.terrain, lat, lon))
        mission.static_group(
            country=_country(mission, RED_BLOCK),
            name=name,
            _type=static_type,
            position=position,
        )
        _report(name, position)


def _author_framework_sites(mission: Mission, framework: Path) -> None:
    """Copy each template site's units (type, position, heading) as one FIXED group."""
    source = Mission()
    source.load_file(str(framework))
    by_name = {
        group.name: group
        for coalition in source.coalition.values()
        for country in coalition.countries.values()
        for group in country.vehicle_group
    }
    print("\nframework sites:")
    for source_name, name in FRAMEWORK_SITES:
        group = by_name[source_name]
        first = group.units[0]
        copy = mission.vehicle_group(
            country=_country(mission, RED_BLOCK),
            name=name,
            _type=vehicle_map[first.type],
            position=first.position,
            heading=first.heading,
        )
        for unit in group.units[1:]:
            added = mission.vehicle(
                f"{name} {len(copy.units) + 1}", vehicle_map[unit.type]
            )
            added.position = unit.position
            added.heading = unit.heading
            copy.add_unit(added)
        for point in copy.points:
            point.action = PointAction.OffRoad
            point.speed = 0
        _report(f"{name} ({len(copy.units)})", first.position)


def _author_routes(mission: Mission, theater: Any) -> None:
    from campaign_routes import draw

    # MizCampaignLoader reads route groups from this one country only.
    country = mission.country(CombinedJointTaskForcesBlue.name)
    print("\nroads:")
    for name, start, corridor, end in ROADS:
        first = _origin(mission, start)
        points = [(first.x, first.y)]
        for lat, lon in corridor:
            p = _xy(mission.terrain, lat, lon)
            points.append((p.x, p.y))
        last = _origin(mission, end)
        points.append((last.x, last.y))
        draw(mission, country, "route", name, points)
        group = country.vehicle_group[-1]
        # An On Road first leg the editor cannot path from a runway crashes it.
        group.points[0].action = PointAction.OffRoad
        group.points[-1].action = PointAction.OffRoad
        print(f"  {name} ({len(points)} waypoints)")

    print("\nrail:")
    for name, stations in RAIL:
        points = []
        for lat, lon in stations:
            p = _xy(mission.terrain, lat, lon)
            points.append((p.x, p.y))
        draw(mission, country, "rail", name, points)
        print(f"  {name} ({len(points)} stations)")

    print("\nsea lanes:")
    for name, waypoints in LANES:
        points = []
        for lat, lon in waypoints:
            p = _xy(mission.terrain, lat, lon)
            if theater.is_on_land(p, ignore_exclusion=True):
                raise RuntimeError(f"{name}: ({lat}, {lon}) is on land")
            points.append((p.x, p.y))
        draw(mission, country, "lane", name, points)
        print(f"  {name} ({len(points)} waypoints)")


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"missing source miz: {SOURCE}")
    if len(sys.argv) != 2:
        raise SystemExit("usage: build_northern_shield_miz.py <framework .miz>")
    framework = Path(sys.argv[1])

    mission = Mission()
    mission.load_file(str(SOURCE))
    print(f"loaded {SOURCE.name} ({mission.terrain.name})\n")
    theater = _theater()

    _strip(mission)
    _set_ownership(mission)
    fields = [mission.terrain.airports[n] for n in BLUE_AIRFIELDS + RED_AIRFIELDS]
    taken = [airport.position for airport in fields]
    runways = [segment for airport in fields for segment in _runway_segments(airport)]
    placer = Placer(theater, taken, runways)
    _author_land(mission, placer)
    _author_framework_sites(mission, framework)
    _author_routes(mission, theater)

    if placer.relaxed:
        print("\nplaced on inclusion-only ground (no fully clear point in reach):")
        for name in placer.relaxed:
            print(f"  {name}")

    mission.save(str(DEST))
    print(f"\nwrote {DEST.relative_to(_REPO_ROOT)}")


if __name__ == "__main__":
    main()
