"""Build ``resources/campaigns/northern_flank_1985.miz`` from Starfire's Able Archer miz.

"Kola - Northern Flank 1985" forks the laydown of ``exercise_able_archer.miz``
rather than re-authoring the Kola map: that miz carries hand-placed air defence,
garrisons, motor pools and scenery strike targets around Bodo, Andoya, Banak,
Kirkenes and the Murmansk complex, and every unit in it is vanilla, so pydcs
round-trips it losslessly. Able Archer itself ships unchanged.

Design note: docs/dev/design/retlab-northern-flank-campaign-notes.md

The edits, none of which the source miz can express by itself:

1.  **Sweden and Finland hold nothing.** Able Archer fights across both. Here
    every field outside Norway and the USSR is neutral, and every inherited
    marker or strike zone standing on Swedish or Finnish soil is dropped, so §98
    reads both countries as uninvolved and stands their border SAMs.
2.  **One road front.** Blue holds Bodo, Evenes, Andoya and Bardufoss; red holds
    Alta, Banak and Kirkenes (captured) and Koshka Yavr, Severomorsk-1, Olenya
    and Monchegorsk. Severomorsk-3 and Murmansk International go neutral, and their
    inherited defences bind to Severomorsk-1 -- the Murmansk ring.
3.  **The routes move to the yaml.** The M-113 path groups, the convoy-spawn
    markers and the shipping lanes are dropped; ``supply_routes:`` and
    ``shipping_lanes:`` in the campaign yaml replace them.
4.  **The sea is re-seated.** One carrier group north-west of Andoya, a blue
    escort group, and two Northern Fleet groups in the Barents. The LHA is gone.
5.  **Four fields are furnished** -- Evenes, Bardufoss and Alta had no laydown
    and Koshka Yavr two launchers -- and the Murmansk ring gets its long-range batteries, three C2
    cells, the factories and the ammunition depots Able Archer never placed.

Every added land marker is validated against the real landmap (inside an
inclusion zone, outside every exclusion zone), kept outside the runway strip the
airfield-clearance check uses, and kept apart from every other added marker.
SAM markers are searched along the runway's extended centreline first: with no
elevation data offline, the valley floor a runway is built along is the best
available stand-in for flat ground. Every sea position is checked to be off land.

Run from the repo root::

    python tools/build_northern_flank_miz.py

The tool is the source of truth for the edits; the laydown it inherits belongs
to ``exercise_able_archer.miz``. Never hand-edit ``northern_flank_1985.miz``.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any, Iterable, Optional

import yaml
from dcs import ships
from dcs.mapping import LatLng, Point
from dcs.mission import Mission
from dcs.point import PointAction
from dcs.statics import Fortification, Warehouse
from dcs.terrain.terrain import Airport
from dcs.unittype import VehicleType
from dcs.vehicles import AirDefence, Armor, MissilesSS, Unarmed
from shapely.geometry import Point as ShapelyPoint
from shapely.geometry import Polygon

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from game.campaignloader.mizcampaignloader import MizCampaignLoader  # noqa: E402
from game.controlpoint_influenceradius import (  # noqa: E402
    ControlPointInfluenceRadius,
)

SOURCE = _REPO_ROOT / "resources/campaigns/exercise_able_archer.miz"
SOURCE_YAML = _REPO_ROOT / "resources/campaigns/exercise_able_archer.yaml"
DEST = _REPO_ROOT / "resources/campaigns/northern_flank_1985.miz"
BORDERS = _REPO_ROOT / "resources/borders/kola.yaml"

BLUE_AIRFIELDS = ("Bodo", "Evenes", "Andoya", "Bardufoss")
RED_AIRFIELDS = (
    "Alta",
    "Banak",
    "Kirkenes",
    "Koshka Yavr",
    "Severomorsk-1",
    "Olenya",
    "Monchegorsk",
)

#: The two countries that are not in this war. Nothing may stand on their soil.
NEUTRAL_COUNTRIES = {"Sweden", "Finland"}

#: An inherited marker further than this from every campaign airfield belonged to
#: a base this campaign does not use.
KEEP_RADIUS_M = 100_000.0
#: Markers this close to a dropped neutral FOB were that FOB's own garrison.
FOB_GARRISON_M = 5_000.0

# --- Marker vocabulary (must match MizCampaignLoader's *_UNIT_TYPE(S)) ---------
EWR_MARKER: type[VehicleType] = getattr(AirDefence, "x_1L13_EWR", None) or getattr(
    AirDefence, "X_1L13_EWR"
)
LORAD = AirDefence.S_300PS_5P85C_ln
MERAD = AirDefence.Hawk_ln
SHORAD = AirDefence.rapier_fsa_launcher
AAA = AirDefence.Vulcan
ARMOR = Armor.M_1_Abrams
COASTAL = MissilesSS.hy_launcher

#: Inherited marker types this campaign replaces rather than keeps.
DROPPED_VEHICLE_TYPES = {
    Armor.M_113.id,  # front-line path groups -> yaml supply_routes
    Armor.M1043_HMMWV_Armament.id,  # convoy spawn chains traced for those paths
    Unarmed.KrAZ6322.id,  # the two neutral FOBs, both off the campaign's axis
    AirDefence.Patriot_ln.id,  # Bodo's long-range slot: re-banded, see BODO_HAWK
}
DROPPED_STATIC_TYPES = {"Invisible FARP"}  # the pads of the two dropped FOBs

#: Bodo's inherited marker is long-range, and nothing NATO fielded in north
#: Norway in 1985 fills that band. A marker the faction cannot fill never
#: populates, so it is re-authored one band down at the same hand-placed spot.
BODO_HAWK = ("NF-Bodo-Hawk", -62864, -345947)

# --- Added land markers --------------------------------------------------------
# (name, anchor airfield, marker type, country block, placement)
#   placement "axis": along the runway's extended centreline, SAM sites.
#   placement "ring": first clear land point on rings round the field.
#   placement "near": within NEAR_OFFSET_M if any land allows it (guns, point
#                     defence, garrisons -- nothing that levels a launcher).
# SAM, EWR and coastal markers go in the red block (the loader's coalition-
# agnostic default; they bind to the nearest control point of either side).
RED_BLOCK = "red"
BLUE_BLOCK = "blue"
ADDED_MARKERS: tuple[tuple[str, str, Any, str, str], ...] = (
    # Evenes -- the Narvik gate. Unfurnished in the source miz.
    ("NF-Evenes-Hawk", "Evenes", MERAD, RED_BLOCK, "axis"),
    ("NF-Evenes-SHORAD", "Evenes", SHORAD, RED_BLOCK, "near"),
    ("NF-Evenes-AAA", "Evenes", AAA, BLUE_BLOCK, "near"),
    ("NF-Evenes-Garrison", "Evenes", ARMOR, BLUE_BLOCK, "near"),
    # Bardufoss -- the front field behind the Lyngen position.
    ("NF-Bardufoss-Hawk", "Bardufoss", MERAD, RED_BLOCK, "axis"),
    ("NF-Bardufoss-SHORAD", "Bardufoss", SHORAD, RED_BLOCK, "near"),
    ("NF-Bardufoss-AAA-1", "Bardufoss", AAA, BLUE_BLOCK, "near"),
    ("NF-Bardufoss-AAA-2", "Bardufoss", AAA, BLUE_BLOCK, "near"),
    ("NF-Bardufoss-Garrison-1", "Bardufoss", ARMOR, BLUE_BLOCK, "near"),
    ("NF-Bardufoss-Garrison-2", "Bardufoss", ARMOR, BLUE_BLOCK, "near"),
    ("NF-Bardufoss-EWR", "Bardufoss", EWR_MARKER, RED_BLOCK, "ring"),
    # Alta -- the Soviet spearhead's field. Mobile air defence only.
    ("NF-Alta-SA6", "Alta", MERAD, RED_BLOCK, "axis"),
    ("NF-Alta-SHORAD", "Alta", SHORAD, RED_BLOCK, "near"),
    ("NF-Alta-AAA-1", "Alta", AAA, RED_BLOCK, "near"),
    ("NF-Alta-AAA-2", "Alta", AAA, RED_BLOCK, "near"),
    ("NF-Alta-Garrison-1", "Alta", ARMOR, RED_BLOCK, "near"),
    ("NF-Alta-Garrison-2", "Alta", ARMOR, RED_BLOCK, "near"),
    # Banak and Kirkenes inherit their point defence; they gain a medium battery
    # and the forward radar picket.
    ("NF-Banak-SA6", "Banak", MERAD, RED_BLOCK, "axis"),
    ("NF-Banak-EWR", "Banak", EWR_MARKER, RED_BLOCK, "ring"),
    ("NF-Kirkenes-SA3", "Kirkenes", MERAD, RED_BLOCK, "axis"),
    ("NF-Kirkenes-EWR", "Kirkenes", EWR_MARKER, RED_BLOCK, "ring"),
    # Koshka Yavr -- the Pechenga fighter-bomber field, the invasion's home base.
    # (Luostari, 10 NM away, has helicopter pads only: no jet can park there.)
    # The source gives it two point-defence launchers; it gains the rest.
    ("NF-Koshka-SA3", "Koshka Yavr", MERAD, RED_BLOCK, "axis"),
    ("NF-Koshka-AAA", "Koshka Yavr", AAA, RED_BLOCK, "near"),
    ("NF-Koshka-Garrison", "Koshka Yavr", ARMOR, RED_BLOCK, "near"),
    # The Murmansk ring's long-range batteries. The source places one, east of
    # the city; these give Severomorsk and the Olenya bomber base their own.
    ("NF-Severomorsk-SA10", "Severomorsk-1", LORAD, RED_BLOCK, "axis"),
    ("NF-Olenya-SA5", "Olenya", LORAD, RED_BLOCK, "axis"),
    ("NF-Olenya-EWR", "Olenya", EWR_MARKER, RED_BLOCK, "ring"),
    ("NF-Monchegorsk-SA2", "Monchegorsk", MERAD, RED_BLOCK, "axis"),
)

#: Coastal anti-ship batteries, anchored on a real headland by lat/lon and then
#: nudged to the nearest clear land point. (name, lat, lon)
COASTAL_SITES = (
    ("NF-Coastal-Liinakhamari", 69.640, 31.370),  # the Pechenga fjord mouth
    ("NF-Coastal-Kola-Bay", 69.205, 33.350),  # Polyarny, the Kola Bay mouth
)

#: Advanced-IADS C2 cells: command centre + comms + power, co-located so range
#: mode wires the nearby batteries to them. One per echelon.
C2_CELLS = ("Severomorsk-1", "Olenya", "Banak")

#: (name, anchor airfield, static type, block). Factories are always blue-block
#: by the loader's convention; ownership follows the nearest control point.
ADDED_STATICS: tuple[tuple[str, str, Any, str], ...] = (
    ("NF-Bodo-Factory", "Bodo", Fortification.Workshop_A, BLUE_BLOCK),
    ("NF-Evenes-Factory", "Evenes", Fortification.Workshop_A, BLUE_BLOCK),
    ("NF-Severomorsk-Factory", "Severomorsk-1", Fortification.Workshop_A, BLUE_BLOCK),
    ("NF-Monchegorsk-Factory", "Monchegorsk", Fortification.Workshop_A, BLUE_BLOCK),
    ("NF-Evenes-Ammo", "Evenes", Warehouse._Ammunition_depot, BLUE_BLOCK),
    ("NF-Bardufoss-Ammo", "Bardufoss", Warehouse._Ammunition_depot, BLUE_BLOCK),
    ("NF-Alta-Ammo", "Alta", Warehouse._Ammunition_depot, RED_BLOCK),
    ("NF-Banak-Ammo", "Banak", Warehouse._Ammunition_depot, RED_BLOCK),
    ("NF-Kirkenes-Ammo", "Kirkenes", Warehouse._Ammunition_depot, RED_BLOCK),
    ("NF-Koshka-Ammo", "Koshka Yavr", Warehouse._Ammunition_depot, RED_BLOCK),
    ("NF-Olenya-Ammo", "Olenya", Warehouse._Ammunition_depot, RED_BLOCK),
)

# --- The sea, by lat/lon -------------------------------------------------------
#: The carrier control point. The yaml's carrier air wing and ``carriers:`` block
#: key on this group name.
CARRIER_NAME = "Blue-CV"
CARRIER_AT = (69.85, 14.80)  # 30 NM north-west of Andenes; ~390 NM to Severomorsk
#: Ship markers (Arleigh Burke hull; the faction fills the real ships). A marker
#: binds to the nearest control point, so each sits unambiguously on its own side.
SHIP_MARKERS = (
    ("NF-Blue-SAG", BLUE_BLOCK, 69.55, 15.30),  # the carrier's surface screen
    ("NF-Red-SAG", RED_BLOCK, 70.75, 32.20),  # Northern Fleet group, off Vardo
    ("NF-Red-Landing-Group", RED_BLOCK, 70.05, 32.60),  # east of Varanger
)

# --- Placement tolerances ------------------------------------------------------
#: Clear of the 1.6 km x 300 m strip `game/theater/airfieldclearance.py` warns on,
#: and of the dispersals a northern-flank field spreads well beyond its runway.
MIN_OFFSET_M = 3000.0
MAX_OFFSET_M = 15000.0
STEP_M = 500.0
BEARING_STEP_DEG = 15
LATERAL_OFFSETS_M = (0.0, 500.0, -500.0, 1000.0, -1000.0)
MIN_SEPARATION_M = 900.0
#: How far out a gun, a point-defence launcher or a building may sit.
NEAR_OFFSET_M = 6000.0


def _theater() -> Any:
    """The Kola theatre, loaded only for its landmap."""
    from game import persistency
    from game.campaignloader.campaign import Campaign

    persistency.setup(str(Path.home() / "Saved Games" / "DCS"), False, 0)
    return Campaign.from_file(SOURCE_YAML).load_theater(advanced_iads=False)


def _neutral_soil() -> list[Polygon]:
    data = yaml.safe_load(BORDERS.read_text(encoding="utf-8"))
    return [
        Polygon(zone["border"])
        for zone in data["zones"]
        if zone["country"] in NEUTRAL_COUNTRIES
    ]


def _xy(terrain: Any, lat: float, lon: float) -> Point:
    return Point.from_latlng(LatLng(lat, lon), terrain)


class Placer:
    """Finds clear land for an added marker, deterministically.

    "Clear" is the landmap's own answer: inside an inclusion zone and outside
    every exclusion zone, which is the ground the map's author judged a vehicle
    can stand on. The Kola landmap is coarse on the Norwegian coast -- Bodo,
    Andoya, Alta, Banak and Kirkenes all sit in what it calls sea -- so a field
    with no clear point in reach falls back to inclusion-only ground, and the
    report says so for every marker that needed it.
    """

    def __init__(self, theater: Any, neutral: list[Polygon], taken: list[Point]):
        self.theater = theater
        self.neutral = neutral
        self.taken = taken
        self.relaxed: list[str] = []

    def _free(self, candidate: Point) -> bool:
        spot = ShapelyPoint(candidate.x, candidate.y)
        if any(zone.contains(spot) for zone in self.neutral):
            return False
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

    def near(self, name: str, origin: Point) -> Point:
        """Close to the field before clear: guns, point defence and buildings.

        None of them levels a launcher, and a gun 14 km out defends nothing, so
        inclusion-only ground inside NEAR_OFFSET_M beats clear ground beyond it.
        """
        close = self._rings(origin, MIN_OFFSET_M, NEAR_OFFSET_M)
        far = self._rings(origin, NEAR_OFFSET_M + STEP_M)
        return self._pick(
            name, ((close, False), (close, True), (far, False), (far, True))
        )

    def axis(self, name: str, airport: Airport) -> Point:
        """Along the extended runway centreline first: the valley floor."""
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


def _set_ownership(mission: Mission) -> None:
    print("airfield ownership:")
    for airport in mission.terrain.airport_list():
        if airport.name in BLUE_AIRFIELDS:
            airport.set_blue()
        elif airport.name in RED_AIRFIELDS:
            airport.set_red()
        else:
            airport.set_neutral()
            # The source marks Koshka Yavr neutral WITH dynamic spawn, which
            # pydcs reports as is_neutral() and this fork's loader then reads as
            # a red control point. A field outside the campaign must be neither.
            airport.dynamic_spawn = False
    for name in BLUE_AIRFIELDS + RED_AIRFIELDS:
        if name not in mission.terrain.airports:
            raise RuntimeError(f"{name} is not an airfield on this terrain")
        side = "BLUE" if name in BLUE_AIRFIELDS else "RED"
        print(f"  {name:<20} {side}")


def _campaign_fields(mission: Mission) -> list[Airport]:
    return [mission.terrain.airports[n] for n in BLUE_AIRFIELDS + RED_AIRFIELDS]


def _belongs(
    position: Point,
    fields: Iterable[Airport],
    neutral: list[Polygon],
    dropped_fobs: Iterable[Point] = (),
) -> bool:
    spot = ShapelyPoint(position.x, position.y)
    if any(zone.contains(spot) for zone in neutral):
        return False
    # The garrison of a FOB this campaign drops goes with it, even on Soviet soil.
    if any(position.distance_to_point(fob) <= FOB_GARRISON_M for fob in dropped_fobs):
        return False
    nearest = min(position.distance_to_point(f.position) for f in fields)
    return nearest <= KEEP_RADIUS_M


def _filter_inherited(mission: Mission, neutral: list[Polygon]) -> None:
    """Keep the source laydown that stands on this campaign's ground."""
    fields = _campaign_fields(mission)
    kept: dict[str, int] = {}
    dropped: dict[str, int] = {}
    fobs = [
        vehicle.position
        for coalition in mission.coalition.values()
        for country in coalition.countries.values()
        for vehicle in country.vehicle_group
        if vehicle.units[0].type == Unarmed.KrAZ6322.id
    ]
    for coalition in mission.coalition.values():
        for country in coalition.countries.values():
            # Every ship group is re-authored: the carrier moves, the LHA and the
            # shipping lanes go, and the red markers sat in blue water.
            for ship in list(country.ship_group):
                country.ship_group.remove(ship)
                dropped[ship.units[0].type] = dropped.get(ship.units[0].type, 0) + 1
            for vehicle in list(country.vehicle_group):
                kind = vehicle.units[0].type
                if kind not in DROPPED_VEHICLE_TYPES and _belongs(
                    vehicle.position, fields, neutral, fobs
                ):
                    kept[kind] = kept.get(kind, 0) + 1
                    continue
                country.vehicle_group.remove(vehicle)
                dropped[kind] = dropped.get(kind, 0) + 1
            for static in list(country.static_group):
                kind = static.units[0].type
                if kind not in DROPPED_STATIC_TYPES and _belongs(
                    static.position, fields, neutral, fobs
                ):
                    kept[kind] = kept.get(kind, 0) + 1
                    continue
                country.static_group.remove(static)
                dropped[kind] = dropped.get(kind, 0) + 1
    print("\ninherited from Able Archer (kept / dropped):")
    for kind in sorted(set(kept) | set(dropped)):
        print(f"  {kind:<28} {kept.get(kind, 0):>3} / {dropped.get(kind, 0):>3}")

    # Trigger zones: the CTLD zones of fields this campaign does not hold would
    # dangle, and a scenery strike target on neutral soil would be bombable.
    names = set(BLUE_AIRFIELDS + RED_AIRFIELDS)
    zones = mission.triggers._zones
    before = len(zones)
    for zone in list(zones):
        if " CTLD" in zone.name:
            if zone.name.split(" CTLD")[0] not in names:
                zones.remove(zone)
        elif ControlPointInfluenceRadius.is_red(zone):
            # An influence zone names its control point; the loader raises on a
            # name that is no longer one.
            if zone.properties[1].get("value") not in names:
                zones.remove(zone)
        elif not _belongs(zone.position, fields, neutral):
            zones.remove(zone)
    print(f"  trigger zones                {len(zones):>3} / {before - len(zones):>3}")


def _add_vehicle(
    mission: Mission, block: str, name: str, position: Point, unit_type: Any
) -> None:
    country = mission.country(
        MizCampaignLoader.BLUE_COUNTRY.name
        if block == BLUE_BLOCK
        else MizCampaignLoader.RED_COUNTRY.name
    )
    assert country is not None
    group = mission.vehicle_group(
        country=country, name=name, _type=unit_type, position=position
    )
    # Markers are read for their type and position only; they are never driven.
    for point in group.points:
        point.action = PointAction.OffRoad
        point.speed = 0


def _add_static(
    mission: Mission, block: str, name: str, position: Point, static_type: Any
) -> None:
    country = mission.country(
        MizCampaignLoader.BLUE_COUNTRY.name
        if block == BLUE_BLOCK
        else MizCampaignLoader.RED_COUNTRY.name
    )
    assert country is not None
    mission.static_group(
        country=country, name=name, _type=static_type, position=position
    )


def _report(name: str, position: Point, anchor: Optional[Airport]) -> None:
    where = ""
    if anchor is not None:
        km = position.distance_to_point(anchor.position) / 1000
        where = f"  {km:4.1f} km from {anchor.name}"
    print(f"  {name:<28} ({position.x:8.0f}, {position.y:8.0f}){where}")


def _author_land(mission: Mission, placer: Placer) -> None:
    airports = mission.terrain.airports

    print("\nre-banded:")
    name, x, y = BODO_HAWK
    position = Point(x, y, mission.terrain)
    placer.taken.append(position)
    _add_vehicle(mission, RED_BLOCK, name, position, MERAD)
    _report(name, position, airports["Bodo"])

    print("\nadded markers:")
    for name, anchor_name, unit_type, block, placement in ADDED_MARKERS:
        anchor = airports[anchor_name]
        position = (
            placer.axis(name, anchor)
            if placement == "axis"
            else (
                placer.near(name, anchor.position)
                if placement == "near"
                else placer.ring(name, anchor.position)
            )
        )
        _add_vehicle(mission, block, name, position, unit_type)
        _report(name, position, anchor)

    print("\ncoastal batteries:")
    for name, lat, lon in COASTAL_SITES:
        position = placer.ring(name, _xy(mission.terrain, lat, lon), start=0.0)
        _add_vehicle(mission, RED_BLOCK, name, position, COASTAL)
        _report(name, position, None)

    print("\nC2 cells:")
    for anchor_name in C2_CELLS:
        anchor = airports[anchor_name]
        short = anchor_name.split("-")[0].split(" ")[0]
        for label, static_type in (
            ("CC", Fortification._Command_Center),
            ("Comms", Fortification.Comms_tower_M),
            ("Power", Fortification.GeneratorF),
        ):
            name = f"NF-{short}-{label}"
            position = placer.near(name, anchor.position)
            _add_static(mission, RED_BLOCK, name, position, static_type)
            _report(name, position, anchor)

    print("\neconomy:")
    for name, anchor_name, static_type, block in ADDED_STATICS:
        anchor = airports[anchor_name]
        position = placer.near(name, anchor.position)
        _add_static(mission, block, name, position, static_type)
        _report(name, position, anchor)


def _author_sea(mission: Mission, theater: Any) -> None:
    blue = mission.country(MizCampaignLoader.BLUE_COUNTRY.name)
    red = mission.country(MizCampaignLoader.RED_COUNTRY.name)
    assert blue is not None and red is not None

    def at_sea(name: str, lat: float, lon: float) -> Point:
        position = _xy(mission.terrain, lat, lon)
        if theater.is_on_land(position, ignore_exclusion=True):
            raise RuntimeError(f"{name} would be placed on land at {lat}, {lon}")
        return position

    print("\nships:")
    position = at_sea(CARRIER_NAME, *CARRIER_AT)
    mission.ship_group(blue, CARRIER_NAME, ships.Stennis, position)
    _report(CARRIER_NAME, position, None)
    for name, block, lat, lon in SHIP_MARKERS:
        position = at_sea(name, lat, lon)
        mission.ship_group(
            blue if block == BLUE_BLOCK else red,
            name,
            ships.USS_Arleigh_Burke_IIa,
            position,
        )
        _report(name, position, None)


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"missing source miz: {SOURCE}")

    mission = Mission()
    mission.load_file(str(SOURCE))
    print(f"loaded {SOURCE.name} ({mission.terrain.name})\n")

    theater = _theater()
    neutral = _neutral_soil()

    _set_ownership(mission)
    _filter_inherited(mission, neutral)

    # Added markers keep clear of each other and of everything inherited.
    taken: list[Point] = []
    for coalition in mission.coalition.values():
        for country in coalition.countries.values():
            for group in list(country.vehicle_group) + list(country.static_group):
                taken.append(group.position)
    placer = Placer(theater, neutral, taken)

    _author_land(mission, placer)
    _author_sea(mission, theater)

    if placer.relaxed:
        print()
        print("placed on inclusion-only ground (no fully clear point in reach):")
        for name in placer.relaxed:
            print(f"  {name}")

    mission.save(str(DEST))
    print(f"\nwrote {DEST.relative_to(_REPO_ROOT)}")


if __name__ == "__main__":
    main()
