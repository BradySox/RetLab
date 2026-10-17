"""Build ``resources/campaigns/mount_pleasant_2032.miz``: Falklands - Mount Pleasant 2032.

A fictional war in November 2032: a rearmed Argentina has landed at Goose Green
and San Carlos, and the UK garrison and a US Air Force detachment hold Mount
Pleasant and Stanley. The campaign is defensive and ends when the islands are
clear; the four mainland fields are red rear bases with no road to the islands.
The only thing taken from another campaign is the Stanley scenery (Government
House, the fuel silo and the stores) from ``RetakeTheFalklands.miz``, which ships
unchanged.

Design note: docs/dev/design/retlab-mount-pleasant-2032-campaign-notes.md

What it writes:

1.  **Ownership.** Blue holds Mount Pleasant and Stanley; red holds Goose Green,
    San Carlos and the four mainland fields. Every other field is neutral: Chile
    is not in the war.
2.  **Invert Sides.** Every red control point carries the invert flag, so an
    inverted game hands Argentina to the player.
3.  **The sea.** A Type 45 group east of Stanley, a patrol ship off Mare Harbour,
    and the Argentine escort in Falkland Sound.
4.  **The land.** Sky Sabre and Stormer round Mount Pleasant, the Mount Kent
    radar, HQ-7 and guns at the lodgement, garrisons, depots and factories.

Every added land marker is inside a landmap inclusion zone and outside every
exclusion zone, outside the runway strip the airfield-clearance check uses, and
apart from every other marker. Every sea position is checked to be off land.

Run from the repo root::

    python tools/build_mount_pleasant_2032_miz.py

Never hand-edit ``mount_pleasant_2032.miz``.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Iterable

from dcs import ships
from dcs.mapping import LatLng, Point
from dcs.mission import Mission
from dcs.planes import F_15C
from dcs.point import PointAction
from dcs.statics import Fortification, Warehouse
from dcs.terrain.terrain import Airport
from dcs.vehicles import AirDefence, Armor

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from game.campaignloader.mizcampaignloader import MizCampaignLoader  # noqa: E402

SOURCE = _REPO_ROOT / "resources/campaigns/RetakeTheFalklands.miz"
SOURCE_YAML = _REPO_ROOT / "resources/campaigns/RetakeTheFalklands.yaml"
DEST = _REPO_ROOT / "resources/campaigns/mount_pleasant_2032.miz"

BLUE_AIRFIELDS = ("Mount Pleasant", "Port Stanley")
RED_AIRFIELDS = (
    "Goose Green",
    "San Carlos FOB",
    "Rio Gallegos",
    "Rio Grande",
    "San Julian",
    "Ushuaia",
)

# --- Marker vocabulary (must match MizCampaignLoader's *_UNIT_TYPE(S)) ---------
LORAD = AirDefence.Patriot_ln
EWR = AirDefence.x_1L13_EWR
SHORAD = AirDefence.rapier_fsa_launcher
AAA = AirDefence.Vulcan
ARMOR = Armor.M_1_Abrams

RED_BLOCK = "red"
BLUE_BLOCK = "blue"

#: The Mount Kent remote radar head, anchored by lat/lon rather than a field.
MOUNT_KENT_RADAR = ("Mount Kent radar", -51.672, -58.105)

# (name, anchor, marker type, country block, placement). An anchor is an airfield
# name or the Mount Kent radar. Placement as in build_northern_flank_miz.py.
ADDED_MARKERS: tuple[tuple[str, str, Any, str, str], ...] = (
    # Mount Pleasant: Sky Sabre, Stormer and the garrison.
    ("MP32-MPA-SkySabre", "Mount Pleasant", LORAD, RED_BLOCK, "axis"),
    ("MP32-MPA-Stormer-1", "Mount Pleasant", SHORAD, RED_BLOCK, "near"),
    ("MP32-MPA-Stormer-2", "Mount Pleasant", SHORAD, RED_BLOCK, "near"),
    ("MP32-MPA-Garrison-1", "Mount Pleasant", ARMOR, BLUE_BLOCK, "near"),
    ("MP32-MPA-Garrison-2", "Mount Pleasant", ARMOR, BLUE_BLOCK, "near"),
    ("MP32-MountKent-EWR", "Mount Kent radar", EWR, RED_BLOCK, "ring"),
    # Stanley.
    ("MP32-Stanley-Stormer", "Port Stanley", SHORAD, RED_BLOCK, "near"),
    ("MP32-Stanley-Garrison", "Port Stanley", ARMOR, BLUE_BLOCK, "near"),
    # Goose Green: the lodgement's main base.
    ("MP32-GooseGreen-HQ7", "Goose Green", SHORAD, RED_BLOCK, "ring"),
    ("MP32-GooseGreen-EWR", "Goose Green", EWR, RED_BLOCK, "ring"),
    ("MP32-GooseGreen-AAA-1", "Goose Green", AAA, RED_BLOCK, "near"),
    ("MP32-GooseGreen-AAA-2", "Goose Green", AAA, RED_BLOCK, "near"),
    ("MP32-GooseGreen-Garrison-1", "Goose Green", ARMOR, RED_BLOCK, "near"),
    ("MP32-GooseGreen-Garrison-2", "Goose Green", ARMOR, RED_BLOCK, "near"),
    # San Carlos: the landing beaches.
    ("MP32-SanCarlos-HQ7", "San Carlos FOB", SHORAD, RED_BLOCK, "ring"),
    ("MP32-SanCarlos-AAA-1", "San Carlos FOB", AAA, RED_BLOCK, "near"),
    ("MP32-SanCarlos-AAA-2", "San Carlos FOB", AAA, RED_BLOCK, "near"),
    ("MP32-SanCarlos-Garrison-1", "San Carlos FOB", ARMOR, RED_BLOCK, "near"),
    ("MP32-SanCarlos-Garrison-2", "San Carlos FOB", ARMOR, RED_BLOCK, "near"),
    # The mainland rear.
    ("MP32-RioGallegos-EWR", "Rio Gallegos", EWR, RED_BLOCK, "ring"),
    ("MP32-RioGallegos-AAA", "Rio Gallegos", AAA, RED_BLOCK, "near"),
    ("MP32-RioGrande-AAA", "Rio Grande", AAA, RED_BLOCK, "near"),
    ("MP32-SanJulian-AAA", "San Julian", AAA, RED_BLOCK, "near"),
    ("MP32-Ushuaia-AAA", "Ushuaia", AAA, RED_BLOCK, "near"),
)

#: (name, anchor, static type, block). Ownership follows the nearest control point.
ADDED_STATICS: tuple[tuple[str, str, Any, str], ...] = (
    ("MP32-MPA-Factory", "Mount Pleasant", Fortification.Workshop_A, BLUE_BLOCK),
    ("MP32-GooseGreen-Factory", "Goose Green", Fortification.Workshop_A, BLUE_BLOCK),
    ("MP32-MPA-Ammo", "Mount Pleasant", Warehouse._Ammunition_depot, BLUE_BLOCK),
    ("MP32-Stanley-Ammo", "Port Stanley", Warehouse._Ammunition_depot, BLUE_BLOCK),
    ("MP32-GooseGreen-Ammo", "Goose Green", Warehouse._Ammunition_depot, RED_BLOCK),
    ("MP32-SanCarlos-Ammo", "San Carlos FOB", Warehouse._Ammunition_depot, RED_BLOCK),
)

# --- The sea, by lat/lon -------------------------------------------------------
#: Ship markers (Arleigh Burke hull; the faction fills the real ships).
SHIP_MARKERS = (
    ("MP32-UK-Type45-Group", BLUE_BLOCK, -51.66, -57.40),  # east of Stanley
    ("MP32-UK-Mare-Harbour", BLUE_BLOCK, -51.99, -58.40),  # off Mount Pleasant
    ("MP32-ARA-Falkland-Sound", RED_BLOCK, -51.53, -59.22),  # the landing's escort
)
#: The US detachment's AWACS and tankers fly in from Ascension Island.
OFF_MAP = ("Ascension Island", -50.90, -56.20)

# --- Placement tolerances ------------------------------------------------------
MIN_OFFSET_M = 3000.0
MAX_OFFSET_M = 15000.0
STEP_M = 500.0
BEARING_STEP_DEG = 15
LATERAL_OFFSETS_M = (0.0, 500.0, -500.0, 1000.0, -1000.0)
MIN_SEPARATION_M = 900.0
NEAR_OFFSET_M = 6000.0


def _theater() -> Any:
    """The Falklands theatre, loaded only for its landmap."""
    from game import persistency
    from game.campaignloader.campaign import Campaign

    persistency.setup(str(Path.home() / "Saved Games" / "DCS"), False, 0)
    return Campaign.from_file(SOURCE_YAML).load_theater(advanced_iads=False)


def _xy(terrain: Any, lat: float, lon: float) -> Point:
    return Point.from_latlng(LatLng(lat, lon), terrain)


class Placer:
    """Finds clear land for an added marker, deterministically.

    "Clear" is the landmap's own answer: inside an inclusion zone and outside
    every exclusion zone. Where no clear point is in reach the marker falls back
    to inclusion-only ground, and the report names it.
    """

    def __init__(self, theater: Any, taken: list[Point]):
        self.theater = theater
        self.taken = taken
        self.relaxed: list[str] = []

    def _free(self, candidate: Point) -> bool:
        return all(
            candidate.distance_to_point(other) >= MIN_SEPARATION_M
            for other in self.taken
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

    def ring(self, name: str, origin: Point, start: float = MIN_OFFSET_M) -> Point:
        rings = self._rings(origin, start)
        return self._pick(name, ((rings, False), (rings, True)))

    def near(self, name: str, origin: Point, start: float = MIN_OFFSET_M) -> Point:
        close = self._rings(origin, start, NEAR_OFFSET_M)
        far = self._rings(origin, NEAR_OFFSET_M + STEP_M)
        return self._pick(
            name, ((close, False), (close, True), (far, False), (far, True))
        )

    def axis(self, name: str, airport: Airport) -> Point:
        heading = float(airport.runways[0].heading)
        candidates = []
        distance = MIN_OFFSET_M
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
    """Keep the map and the Stanley scenery; drop every group the source placed."""
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
    stanley = mission.terrain.airports["Port Stanley"].position
    zones = mission.triggers._zones
    for zone in list(zones):
        # The source's scenery is all in Stanley town; nothing else survives.
        if zone.position.distance_to_point(stanley) > 10_000:
            zones.remove(zone)


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
    print(f"  {name:<28} ({ll.lat:8.3f}, {ll.lng:8.3f})  {anchor}")


def _author_land(mission: Mission, placer: Placer) -> None:
    airports = mission.terrain.airports
    radar_name, radar_lat, radar_lon = MOUNT_KENT_RADAR
    radar = _xy(mission.terrain, radar_lat, radar_lon)

    def anchor_of(name: str) -> tuple[Point, float]:
        if name == radar_name:
            return radar, 0.0
        return airports[name].position, MIN_OFFSET_M

    print("\nadded markers:")
    for name, anchor_name, unit_type, block, placement in ADDED_MARKERS:
        origin, start = anchor_of(anchor_name)
        if placement == "axis":
            position = placer.axis(name, airports[anchor_name])
        elif placement == "near":
            position = placer.near(name, origin, start)
        else:
            position = placer.ring(name, origin, start)
        _add_vehicle(mission, block, name, position, unit_type)
        _report(name, position, anchor_name)

    print("\neconomy:")
    for name, anchor_name, static_type, block in ADDED_STATICS:
        origin, start = anchor_of(anchor_name)
        position = placer.near(name, origin, start)
        mission.static_group(
            country=_country(mission, block),
            name=name,
            _type=static_type,
            position=position,
        )
        _report(name, position, anchor_name)


def _author_sea_and_air(mission: Mission, theater: Any) -> None:
    def at_sea(name: str, lat: float, lon: float) -> Point:
        position = _xy(mission.terrain, lat, lon)
        if theater.is_on_land(position, ignore_exclusion=True):
            raise RuntimeError(f"{name} would be placed on land at {lat}, {lon}")
        return position

    print("\nships:")
    for name, block, lat, lon in SHIP_MARKERS:
        position = at_sea(name, lat, lon)
        mission.ship_group(
            _country(mission, block), name, ships.USS_Arleigh_Burke_IIa, position
        )
        _report(name, position)

    print("\noff-map:")
    name, lat, lon = OFF_MAP
    position = at_sea(name, lat, lon)
    mission.flight_group_inflight(
        country=_country(mission, BLUE_BLOCK),
        name=name,
        aircraft_type=F_15C,
        position=position,
        altitude=6000,
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
    placer = Placer(theater, [])
    _author_land(mission, placer)
    _author_sea_and_air(mission, theater)

    if placer.relaxed:
        print("\nplaced on inclusion-only ground (no fully clear point in reach):")
        for name in placer.relaxed:
            print(f"  {name}")

    mission.save(str(DEST))
    print(f"\nwrote {DEST.relative_to(_REPO_ROOT)}")


if __name__ == "__main__":
    main()
