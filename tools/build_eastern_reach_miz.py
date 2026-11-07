"""Build ``resources/campaigns/eastern_reach_2025.miz``: Persian Gulf - Eastern Reach 2025.

A fictional 2025 war: US Marines hold Bandar-e-Jask and drive north up the
Minab-Kahnuj-Jiroft highway to Kerman. Bandar Abbas and the Hormuz coast are out
of the war; Lar is a red fighter base with no road to the front. The tool takes
only the map, coalitions and weather from ``operation_noisy_cricket.miz`` and
strips every group and zone it carries.

Design note: docs/dev/design/retlab-eastern-reach-campaign-notes.md

What it writes:

1.  **Ownership.** Blue holds Al Dhafra, Al Minhad, Al Ain, Fujairah and Jask; red
    holds Jiroft, Kerman and Lar. Every other field is neutral.
2.  **The valley.** Four red FOBs on the highway (Sirik, Minab, Kahnuj, the Jebal
    Barez pass) and six roads drawn on the real highway, every waypoint On Road.
3.  **The sea.** A carrier, an LHA and an escort in the Gulf of Oman, Silkworm sites
    on the Sirik coast and two IRGCN boat groups off it.
4.  **The land.** SAM, EWR, AAA and garrison markers per base; command posts at
    Jiroft and Kerman; missile sites in the hills; depots, factories and power.

Every land marker is inside a landmap inclusion zone and outside every exclusion
zone, at least 3.4 km from an airfield's centre, and apart from every other
marker. Every sea position is checked to be off land.

Run from the repo root::

    python tools/build_eastern_reach_miz.py

Never hand-edit ``eastern_reach_2025.miz``.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Iterable

from dcs import ships
from dcs.mapping import LatLng, Point
from dcs.mission import Mission
from dcs.point import PointAction
from dcs.statics import Fortification, Warehouse
from dcs.vehicles import AirDefence, Armor, MissilesSS, Unarmed

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from game.campaignloader.mizcampaignloader import MizCampaignLoader  # noqa: E402

SOURCE = _REPO_ROOT / "resources/campaigns/operation_noisy_cricket.miz"
SOURCE_YAML = _REPO_ROOT / "resources/campaigns/operation_noisy_cricket.yaml"
DEST = _REPO_ROOT / "resources/campaigns/eastern_reach_2025.miz"

BLUE_AIRFIELDS = (
    "Al Dhafra AFB",
    "Al Minhad AFB",
    "Al Ain Intl",
    "Fujairah Intl",
    "Bandar-e-Jask",
)
RED_AIRFIELDS = ("Jiroft", "Kerman", "Lar")

# --- Marker vocabulary (must match MizCampaignLoader's *_UNIT_TYPE(S)) ---------
LORAD = AirDefence.S_300PS_5P85C_ln
MERAD = AirDefence.Hawk_ln
SHORAD = AirDefence.x_2S6_Tunguska
AAA = AirDefence.ZSU_23_4_Shilka
EWR = AirDefence.x_1L13_EWR
ARMOR = Armor.M_1_Abrams
MISSILE = MissilesSS.Scud_B
COASTAL = MissilesSS.hy_launcher
BLUE_LORAD = AirDefence.Patriot_ln
BLUE_SHORAD = AirDefence.M1097_Avenger
FOB = Unarmed.SKP_11
ROAD = Armor.M_113

RED_BLOCK = "red"
BLUE_BLOCK = "blue"

#: Red FOBs on the highway (name, lat, lon): each sits beside the real road,
#: on clear land just outside its town.
FOBS = (
    ("FOB Sirik", 26.5292, 57.1391),
    ("FOB Minab", 27.1501, 57.0880),
    ("FOB Kahnuj", 27.9506, 57.7074),
    ("FOB Jebal Barez", 29.2902, 57.9948),
)

#: Named spots off the bases (name, lat, lon): radar heads on high ground,
#: the missile hides in the hills and the Silkworm coast.
SPOTS = {
    "Kerman south ridge": (30.02, 56.88),
    "Kerman east hills": (30.20, 57.30),
    "Jiroft west range": (28.70, 57.42),
    "Sardu hills": (29.15, 57.80),
    "Minab hills": (27.30, 57.30),
    "Sirik coast north": (26.75, 57.02),
    "Sirik coast south": (26.36, 57.12),
    "Bashagard hills": (26.55, 57.50),
    "Lar ridge": (27.55, 54.30),
}

# (name, anchor, marker type, country block, placement). An anchor is an
# airfield, a FOB or a named spot. "axis" puts a marker off the runway's ends,
# "near" within 6 km, "ring" at the first clear spot outward.
ADDED_MARKERS: tuple[tuple[str, str, Any, str, str], ...] = (
    # Kerman: the long-range belt, the A-50's base, the regional HQ.
    ("ER-Kerman-LORAD-1", "Kerman", LORAD, RED_BLOCK, "axis"),
    ("ER-Kerman-LORAD-2", "Kerman east hills", LORAD, RED_BLOCK, "ring"),
    ("ER-Kerman-MERAD", "Kerman south ridge", MERAD, RED_BLOCK, "ring"),
    ("ER-Kerman-SHORAD-1", "Kerman", SHORAD, RED_BLOCK, "near"),
    ("ER-Kerman-SHORAD-2", "Kerman", SHORAD, RED_BLOCK, "near"),
    ("ER-Kerman-AAA-1", "Kerman", AAA, RED_BLOCK, "near"),
    ("ER-Kerman-AAA-2", "Kerman", AAA, RED_BLOCK, "near"),
    ("ER-Kerman-EWR", "Kerman south ridge", EWR, RED_BLOCK, "ring"),
    ("ER-Kerman-Garrison-1", "Kerman", ARMOR, RED_BLOCK, "near"),
    ("ER-Kerman-Garrison-2", "Kerman", ARMOR, RED_BLOCK, "near"),
    ("ER-Kerman-Missiles-1", "Kerman east hills", MISSILE, RED_BLOCK, "ring"),
    ("ER-Kerman-Missiles-2", "Kerman south ridge", MISSILE, RED_BLOCK, "ring"),
    # Jiroft: the valley's air base and the IRGC's forward HQ.
    ("ER-Jiroft-LORAD", "Jiroft", LORAD, RED_BLOCK, "axis"),
    ("ER-Jiroft-MERAD", "Jiroft west range", MERAD, RED_BLOCK, "ring"),
    ("ER-Jiroft-SHORAD-1", "Jiroft", SHORAD, RED_BLOCK, "near"),
    ("ER-Jiroft-SHORAD-2", "Jiroft", SHORAD, RED_BLOCK, "near"),
    ("ER-Jiroft-AAA-1", "Jiroft", AAA, RED_BLOCK, "near"),
    ("ER-Jiroft-AAA-2", "Jiroft", AAA, RED_BLOCK, "near"),
    ("ER-Jiroft-EWR", "Jiroft west range", EWR, RED_BLOCK, "ring"),
    ("ER-Jiroft-Garrison-1", "Jiroft", ARMOR, RED_BLOCK, "near"),
    ("ER-Jiroft-Garrison-2", "Jiroft", ARMOR, RED_BLOCK, "near"),
    ("ER-Jiroft-Missiles", "Jiroft west range", MISSILE, RED_BLOCK, "ring"),
    # The Jebal Barez pass.
    ("ER-JebalBarez-MERAD", "Sardu hills", MERAD, RED_BLOCK, "ring"),
    ("ER-JebalBarez-AAA", "FOB Jebal Barez", AAA, RED_BLOCK, "near"),
    ("ER-JebalBarez-Garrison-1", "FOB Jebal Barez", ARMOR, RED_BLOCK, "near"),
    ("ER-JebalBarez-Garrison-2", "FOB Jebal Barez", ARMOR, RED_BLOCK, "near"),
    # Kahnuj.
    ("ER-Kahnuj-SHORAD", "FOB Kahnuj", SHORAD, RED_BLOCK, "near"),
    ("ER-Kahnuj-AAA", "FOB Kahnuj", AAA, RED_BLOCK, "near"),
    ("ER-Kahnuj-Garrison-1", "FOB Kahnuj", ARMOR, RED_BLOCK, "near"),
    ("ER-Kahnuj-Garrison-2", "FOB Kahnuj", ARMOR, RED_BLOCK, "near"),
    # Minab: the gate to the valley.
    ("ER-Minab-MERAD", "Minab hills", MERAD, RED_BLOCK, "ring"),
    ("ER-Minab-SHORAD", "FOB Minab", SHORAD, RED_BLOCK, "near"),
    ("ER-Minab-EWR", "Minab hills", EWR, RED_BLOCK, "ring"),
    ("ER-Minab-Garrison-1", "FOB Minab", ARMOR, RED_BLOCK, "near"),
    ("ER-Minab-Garrison-2", "FOB Minab", ARMOR, RED_BLOCK, "near"),
    # Sirik: the coast facing the landing.
    ("ER-Sirik-SHORAD", "FOB Sirik", SHORAD, RED_BLOCK, "near"),
    ("ER-Sirik-AAA-1", "FOB Sirik", AAA, RED_BLOCK, "near"),
    ("ER-Sirik-AAA-2", "FOB Sirik", AAA, RED_BLOCK, "near"),
    ("ER-Sirik-Garrison-1", "FOB Sirik", ARMOR, RED_BLOCK, "near"),
    ("ER-Sirik-Garrison-2", "FOB Sirik", ARMOR, RED_BLOCK, "near"),
    ("ER-Sirik-Silkworm-1", "Sirik coast north", COASTAL, RED_BLOCK, "ring"),
    ("ER-Sirik-Silkworm-2", "Sirik coast south", COASTAL, RED_BLOCK, "ring"),
    ("ER-Bashagard-Missiles", "Bashagard hills", MISSILE, RED_BLOCK, "ring"),
    # Lar: the F-14 base across the mountains.
    ("ER-Lar-MERAD", "Lar ridge", MERAD, RED_BLOCK, "ring"),
    ("ER-Lar-SHORAD", "Lar", SHORAD, RED_BLOCK, "near"),
    ("ER-Lar-AAA", "Lar", AAA, RED_BLOCK, "near"),
    ("ER-Lar-EWR", "Lar ridge", EWR, RED_BLOCK, "ring"),
    # Blue: the beachhead and the rear.
    ("ER-Jask-SHORAD", "Bandar-e-Jask", BLUE_SHORAD, BLUE_BLOCK, "near"),
    ("ER-Jask-Garrison-1", "Bandar-e-Jask", ARMOR, BLUE_BLOCK, "near"),
    ("ER-Jask-Garrison-2", "Bandar-e-Jask", ARMOR, BLUE_BLOCK, "near"),
    ("ER-Fujairah-SHORAD", "Fujairah Intl", BLUE_SHORAD, BLUE_BLOCK, "near"),
    ("ER-Dhafra-Patriot", "Al Dhafra AFB", BLUE_LORAD, BLUE_BLOCK, "axis"),
)

#: (name, anchor, static type, block). Ownership follows the nearest control point.
ADDED_STATICS: tuple[tuple[str, str, Any, str], ...] = (
    ("ER-Kerman-Command", "Kerman", Fortification._Command_Center, RED_BLOCK),
    ("ER-Kerman-Power", "Kerman", Fortification.GeneratorF, RED_BLOCK),
    ("ER-Kerman-Comms", "Kerman east hills", Fortification.Comms_tower_M, RED_BLOCK),
    ("ER-Kerman-Factory-1", "Kerman", Fortification.Workshop_A, RED_BLOCK),
    ("ER-Kerman-Factory-2", "Kerman", Fortification.Workshop_A, RED_BLOCK),
    ("ER-Kerman-Missile-Works", "Kerman", Fortification.Tech_combine, RED_BLOCK),
    ("ER-Kerman-Ammo", "Kerman", Warehouse._Ammunition_depot, RED_BLOCK),
    ("ER-Kerman-Motorpool", "Kerman", Fortification.Garage_A, RED_BLOCK),
    ("ER-Jiroft-Command", "Jiroft", Fortification._Command_Center, RED_BLOCK),
    ("ER-Jiroft-Ammo", "Jiroft", Warehouse._Ammunition_depot, RED_BLOCK),
    ("ER-JebalBarez-Comms", "FOB Jebal Barez", Fortification.Comms_tower_M, RED_BLOCK),
    ("ER-Kahnuj-Ammo", "FOB Kahnuj", Warehouse._Ammunition_depot, RED_BLOCK),
    ("ER-Minab-Comms", "Minab hills", Fortification.Comms_tower_M, RED_BLOCK),
    ("ER-Minab-Ammo", "FOB Minab", Warehouse._Ammunition_depot, RED_BLOCK),
    ("ER-Sirik-Ammo", "FOB Sirik", Warehouse._Ammunition_depot, RED_BLOCK),
    ("ER-Jask-Ammo", "Bandar-e-Jask", Warehouse._Ammunition_depot, BLUE_BLOCK),
    ("ER-Fujairah-Ammo", "Fujairah Intl", Warehouse._Ammunition_depot, BLUE_BLOCK),
    ("ER-Dhafra-Factory", "Al Dhafra AFB", Fortification.Workshop_A, BLUE_BLOCK),
)

#: The roads: (from, real highway junctions as (lat, lon), to). Traced from the
#: real Jask-Minab-Jiroft-Kerman highway (OpenStreetMap routing, 2026-11-07).
ROADS = (
    (
        "Bandar-e-Jask",
        ((25.7916, 57.7749), (25.8437, 57.6132), (25.8516, 57.3780), (26.3263, 57.2452)),
        "FOB Sirik",
    ),
    (
        "FOB Sirik",
        ((26.7628, 57.0573), (26.9895, 57.0993), (27.1111, 57.0894)),
        "FOB Minab",
    ),
    (
        "FOB Minab",
        ((27.2209, 57.0557), (27.4311, 57.0350), (27.4982, 57.4047), (27.6632, 57.6593)),
        "FOB Kahnuj",
    ),
    (
        "FOB Kahnuj",
        ((28.0881, 57.8189), (28.3635, 57.9153), (28.6401, 57.7744)),
        "Jiroft",
    ),
    (
        "Jiroft",
        ((28.8191, 57.8178), (28.9064, 57.8818), (29.0611, 57.9165)),
        "FOB Jebal Barez",
    ),
    (
        "FOB Jebal Barez",
        ((29.5329, 57.7989), (29.7631, 57.5848), (30.0335, 57.2935), (30.1091, 57.1839)),
        "Kerman",
    ),
)

# --- The sea, by lat/lon -------------------------------------------------------
CARRIER = ("ER-CVN", 25.15, 57.55)
LHA = ("ER-LHA", 25.40, 58.05)
#: Ship markers (Arleigh Burke hull; the faction fills the real ships).
SHIP_MARKERS = (
    ("ER-US-Escort", BLUE_BLOCK, 25.30, 57.80),
    ("ER-IRGCN-Sirik", RED_BLOCK, 26.45, 56.90),
    ("ER-IRGCN-Kuh-e-Mobarak", RED_BLOCK, 25.70, 57.25),
)

# --- Placement tolerances ------------------------------------------------------
MIN_OFFSET_M = 3400.0
MAX_OFFSET_M = 15000.0
STEP_M = 500.0
BEARING_STEP_DEG = 15
LATERAL_OFFSETS_M = (0.0, 500.0, -500.0, 1000.0, -1000.0)
MIN_SEPARATION_M = 900.0
NEAR_OFFSET_M = 6000.0
#: Garrisons stand inside a FOB's 3 km capture zone.
FOB_NEAR_START_M = 1500.0


def _theater() -> Any:
    """The Persian Gulf theatre, loaded only for its landmap."""
    from game import persistency
    from game.campaignloader.campaign import Campaign

    persistency.setup(str(Path.home() / "Saved Games" / "DCS"), False, 0)
    return Campaign.from_file(SOURCE_YAML).load_theater(advanced_iads=False)


def _xy(terrain: Any, lat: float, lon: float) -> Point:
    return Point.from_latlng(LatLng(lat, lon), terrain)


class Placer:
    """Finds clear land for an added marker, deterministically.

    "Clear" is the landmap's own answer: inside an inclusion zone, outside every
    exclusion zone, and at least MIN_OFFSET_M from every airfield's centre.
    """

    def __init__(self, theater: Any, taken: list[Point], airfields: list[Point]):
        self.theater = theater
        self.taken = taken
        self.airfields = airfields
        self.relaxed: list[str] = []

    def _free(self, candidate: Point) -> bool:
        return all(
            candidate.distance_to_point(other) >= MIN_SEPARATION_M
            for other in self.taken
        ) and all(
            candidate.distance_to_point(field) >= MIN_OFFSET_M
            for field in self.airfields
        )

    def _pick(self, name: str, passes: Iterable[tuple[list[Point], bool]]) -> Point:
        for candidates, relaxed in passes:
            for candidate in candidates:
                if not self.theater.is_on_land(candidate, ignore_exclusion=relaxed):
                    continue
                if self._free(candidate):
                    if relaxed:
                        self.relaxed.append(name)
                    self.taken.append(candidate)
                    return candidate
        raise RuntimeError(f"no land for {name} within {MAX_OFFSET_M} m of its anchor")

    @staticmethod
    def _rings(origin: Point, start: float, stop: float = MAX_OFFSET_M) -> list[Point]:
        found = []
        radius = start
        while radius <= stop:
            for bearing in range(0, 360, BEARING_STEP_DEG):
                found.append(origin.point_from_heading(bearing, radius))
            radius += STEP_M
        return found

    def ring(self, name: str, origin: Point, start: float) -> Point:
        rings = [origin] + self._rings(origin, max(start, STEP_M))
        return self._pick(name, ((rings, False), (rings, True)))

    def near(self, name: str, origin: Point, start: float) -> Point:
        close = self._rings(origin, start, NEAR_OFFSET_M)
        far = self._rings(origin, NEAR_OFFSET_M + STEP_M)
        return self._pick(
            name, ((close, False), (close, True), (far, False), (far, True))
        )

    def axis(self, name: str, airport: Any) -> Point:
        heading = float(airport.runways[0].heading)
        candidates = []
        distance = MIN_OFFSET_M + 1000.0
        while distance <= MAX_OFFSET_M:
            for along in (heading, heading + 180.0):
                centre = airport.position.point_from_heading(along, distance)
                for lateral in LATERAL_OFFSETS_M:
                    candidates.append(centre.point_from_heading(along + 90.0, lateral))
            distance += STEP_M
        candidates += self._rings(airport.position, MIN_OFFSET_M)
        return self._pick(name, ((candidates, False), (candidates, True)))


def _country(mission: Mission, block: str) -> Any:
    country = mission.country(
        MizCampaignLoader.BLUE_COUNTRY.name
        if block == BLUE_BLOCK
        else MizCampaignLoader.RED_COUNTRY.name
    )
    assert country is not None
    return country


def _strip(mission: Mission) -> None:
    """Keep the map, coalitions and weather; drop every group and zone."""
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
    mission.triggers._zones.clear()


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
        print(f"  {name:<20} {side}")


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
    print(f"  {name:<28} ({ll.lat:8.4f}, {ll.lng:8.4f})  {anchor}")


def _anchors(mission: Mission) -> dict[str, Point]:
    terrain = mission.terrain
    anchors = {
        name: terrain.airports[name].position
        for name in BLUE_AIRFIELDS + RED_AIRFIELDS
    }
    for name, lat, lon in FOBS:
        anchors[name] = _xy(terrain, lat, lon)
    for name, (lat, lon) in SPOTS.items():
        anchors[name] = _xy(terrain, lat, lon)
    return anchors


def _author_fobs(mission: Mission, anchors: dict[str, Point]) -> None:
    print("\nFOBs:")
    for name, _, _ in FOBS:
        mission.vehicle_group(
            country=_country(mission, RED_BLOCK),
            name=name,
            _type=FOB,
            position=anchors[name],
        )
        _report(name, anchors[name])


def _author_land(
    mission: Mission, placer: Placer, anchors: dict[str, Point]
) -> None:
    airports = mission.terrain.airports
    fob_names = {name for name, _, _ in FOBS}

    def start_of(anchor: str) -> float:
        if anchor in airports:
            return MIN_OFFSET_M
        if anchor in fob_names:
            return FOB_NEAR_START_M
        return 0.0

    print("\nadded markers:")
    for name, anchor, unit_type, block, placement in ADDED_MARKERS:
        origin = anchors[anchor]
        if placement == "axis":
            position = placer.axis(name, airports[anchor])
        elif placement == "near":
            position = placer.near(name, origin, start_of(anchor))
        else:
            position = placer.ring(name, origin, start_of(anchor))
        _add_vehicle(mission, block, name, position, unit_type)
        _report(name, position, anchor)

    print("\neconomy and command:")
    for name, anchor, static_type, block in ADDED_STATICS:
        origin = anchors[anchor]
        position = placer.near(name, origin, max(start_of(anchor), STEP_M))
        mission.static_group(
            country=_country(mission, block),
            name=name,
            _type=static_type,
            position=position,
        )
        _report(name, position, anchor)


def _author_roads(mission: Mission, anchors: dict[str, Point]) -> None:
    """One M-113 group per road, every waypoint On Road (the .miz route standard)."""
    print("\nroads:")
    for index, (start, corridor, end) in enumerate(ROADS, start=1):
        points = (
            [anchors[start]]
            + [_xy(mission.terrain, lat, lon) for lat, lon in corridor]
            + [anchors[end]]
        )
        group = mission.vehicle_group(
            country=_country(mission, BLUE_BLOCK),
            name=f"ER-Road-{index} {start} - {end}",
            _type=ROAD,
            position=points[0],
        )
        group.points[0].action = PointAction.OnRoad
        for point in points[1:]:
            group.add_waypoint(point, PointAction.OnRoad)
        print(f"  {group.name} ({len(points)} waypoints)")


def _author_sea(mission: Mission, theater: Any) -> None:
    def at_sea(name: str, lat: float, lon: float) -> Point:
        position = _xy(mission.terrain, lat, lon)
        if theater.is_on_land(position, ignore_exclusion=True):
            raise RuntimeError(f"{name} would be placed on land at {lat}, {lon}")
        return position

    print("\nships:")
    blue = _country(mission, BLUE_BLOCK)
    name, lat, lon = CARRIER
    mission.ship_group(blue, name, ships.Stennis, at_sea(name, lat, lon))
    _report(name, at_sea(name, lat, lon))
    name, lat, lon = LHA
    mission.ship_group(blue, name, ships.LHA_Tarawa, at_sea(name, lat, lon))
    _report(name, at_sea(name, lat, lon))
    for name, block, lat, lon in SHIP_MARKERS:
        position = at_sea(name, lat, lon)
        mission.ship_group(
            _country(mission, block), name, ships.USS_Arleigh_Burke_IIa, position
        )
        _report(name, position)


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"missing source miz: {SOURCE}")

    mission = Mission()
    mission.load_file(str(SOURCE))
    print(f"loaded {SOURCE.name} ({mission.terrain.name})\n")
    theater = _theater()

    _strip(mission)
    _set_ownership(mission)
    anchors = _anchors(mission)
    airfields = [p.position for p in mission.terrain.airport_list()]
    placer = Placer(theater, [anchors[name] for name, _, _ in FOBS], airfields)
    _author_fobs(mission, anchors)
    _author_land(mission, placer, anchors)
    _author_roads(mission, anchors)
    _author_sea(mission, theater)

    if placer.relaxed:
        print("\nplaced on inclusion-only ground (no fully clear point in reach):")
        for name in placer.relaxed:
            print(f"  {name}")

    mission.save(str(DEST))
    print(f"\nwrote {DEST.relative_to(_REPO_ROOT)}")


if __name__ == "__main__":
    main()
