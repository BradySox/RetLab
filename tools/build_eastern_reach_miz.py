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
3.  **The land.** Every marker is placed by its job with ``tools/campaign_placement.py``
    on ground DCS has read. The first build writes a check mission to run once.
4.  **UAE batteries.** Four sites from the freeware Arabian SAM Template at Al Dhafra,
    Al Minhad and Fujairah, copied as drawn as FIXED groups.
5.  **The sea.** A carrier, an LHA and an escort in the Gulf of Oman, and two IRGCN
    boat groups off the Sirik coast.

Run from the repo root::

    python tools/build_eastern_reach_miz.py [--template <Arabian_SAM_Template.miz>]

Never hand-edit ``eastern_reach_2025.miz``.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from dcs import ships
from dcs.mapping import LatLng, Point
from dcs.mission import Mission
from dcs.point import PointAction
from dcs.statics import Fortification, Warehouse
from dcs.unitgroup import VehicleGroup
from dcs.vehicles import AirDefence, Armor, MissilesSS, Unarmed

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from game.campaignloader.mizcampaignloader import MizCampaignLoader  # noqa: E402
from tools.campaign_placement import (  # noqa: E402
    Job,
    NeedsCheck,
    Placer,
    placement_markers,
    write_review_map,
)

SOURCE = _REPO_ROOT / "resources/campaigns/operation_noisy_cricket.miz"
SOURCE_YAML = _REPO_ROOT / "resources/campaigns/operation_noisy_cricket.yaml"
DEST = _REPO_ROOT / "resources/campaigns/eastern_reach_2025.miz"
REVIEW_MAP = _REPO_ROOT / "tmp/eastern_reach_placement.html"

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
BLUE_SHORAD = AirDefence.M1097_Avenger
FOB = Unarmed.SKP_11
ROAD = Armor.M_113

RED_BLOCK = "red"
BLUE_BLOCK = "blue"

#: Red FOBs beside the real highway (name, lat, lon), each just outside its town.
FOBS = (
    ("FOB Sirik", 26.5292, 57.1391),
    ("FOB Minab", 27.1501, 57.0880),
    ("FOB Kahnuj", 27.9506, 57.7074),
    ("FOB Jebal Barez", 29.2902, 57.9948),
)

#: Real towns (centre lat, lon) for command posts, power and comms (Job.TOWN),
#: and named spots for the missile hides, the Silkworm coast and the pass (Job.SPOT).
PLACES = {
    "Kerman town": (30.2839, 57.0834),
    "Jiroft town": (28.6751, 57.7380),
    "Minab town": (27.1467, 57.0801),
    "Kahnuj town": (27.9473, 57.7003),
    "Kerman east hills": (30.20, 57.30),
    "Kerman south ridge": (30.03, 56.88),
    "Jiroft west range": (28.74, 57.50),
    "Sardu hills": (29.18, 57.86),
    "Minab hills": (27.30, 57.30),
    "Bashagard hills": (26.55, 57.50),
    "Sirik coast north": (26.76, 57.05),
    "Sirik coast south": (26.36, 57.12),
    "Jebal Barez pass": (29.2887, 57.9934),
}

TEMPLATE_DEFAULT = _REPO_ROOT / "Arabian_SAM_Template.miz"
#: The freeware Arabian SAM Template's UAE sites kept (Brady's call: just the
#: batteries at the three fields blue flies from). Copied unit for unit.
TEMPLATE_SITES = {
    "BSAM-Patriot-UAE-2": "FIXED Al Dhafra Patriot",
    "BSAM-Hawk-UAE-13": "FIXED Al Dhafra Hawk",
    "BSAM-Patriot-UAE-4": "FIXED Al Minhad Patriot",
    "BEW-AN117-DN37": "FIXED Fujairah EWR",
}


@dataclass(frozen=True)
class Item:
    """One unit to place: its name, job, anchor, type and country block."""

    name: str
    job: Job
    anchor: str
    unit_type: Any
    block: str = RED_BLOCK


def _red_field(field: str, short: str, town: str, ewr: bool = True) -> list[Item]:
    items = [
        Item(f"ER-{short}-SHORAD-1", Job.AIR_DEFENSE, field, SHORAD),
        Item(f"ER-{short}-SHORAD-2", Job.AIR_DEFENSE, field, SHORAD),
        Item(f"ER-{short}-AAA-1", Job.AIR_DEFENSE, field, AAA),
        Item(f"ER-{short}-AAA-2", Job.AIR_DEFENSE, field, AAA),
        Item(f"ER-{short}-Garrison-1", Job.GARRISON, field, ARMOR),
        Item(f"ER-{short}-Garrison-2", Job.GARRISON, field, ARMOR),
        Item(f"ER-{short}-Ammo", Job.DEPOT, field, Warehouse._Ammunition_depot),
        Item(f"ER-{short}-Command", Job.TOWN, town, Fortification._Command_Center),
    ]
    if ewr:
        items.append(Item(f"ER-{short}-EWR", Job.EWR, field, EWR))
    return items


def _red_fob(fob: str, short: str, guns: int = 1) -> list[Item]:
    items = [
        Item(f"ER-{short}-Garrison-1", Job.GARRISON, fob, ARMOR),
        Item(f"ER-{short}-Garrison-2", Job.GARRISON, fob, ARMOR),
        Item(f"ER-{short}-Ammo", Job.DEPOT, fob, Warehouse._Ammunition_depot),
    ]
    items += [
        Item(f"ER-{short}-AAA-{i}", Job.AIR_DEFENSE, fob, AAA)
        for i in range(1, guns + 1)
    ]
    return items


ITEMS: tuple[Item, ...] = tuple(
    # Kerman: the long-range belt, the regional HQ and the missile works.
    _red_field("Kerman", "Kerman", "Kerman town")
    + [
        Item("ER-Kerman-LORAD-1", Job.AIR_DEFENSE, "Kerman", LORAD),
        Item("ER-Kerman-LORAD-2", Job.SPOT, "Kerman east hills", LORAD),
        Item("ER-Kerman-MERAD", Job.SPOT, "Kerman south ridge", MERAD),
        Item("ER-Kerman-EWR-South", Job.EWR, "Kerman south ridge", EWR),
        Item("ER-Kerman-Power", Job.TOWN, "Kerman town", Fortification.GeneratorF),
        Item("ER-Kerman-Comms", Job.TOWN, "Kerman town", Fortification.Comms_tower_M),
        Item("ER-Kerman-Factory-1", Job.DEPOT, "Kerman", Fortification.Workshop_A),
        Item("ER-Kerman-Factory-2", Job.DEPOT, "Kerman", Fortification.Workshop_A),
        Item("ER-Kerman-Missile-Works", Job.DEPOT, "Kerman", Fortification.Tech_combine),
        Item("ER-Kerman-Motorpool", Job.DEPOT, "Kerman", Fortification.Garage_A),
        Item("ER-Kerman-Missiles-1", Job.SPOT, "Kerman east hills", MISSILE),
        Item("ER-Kerman-Missiles-2", Job.SPOT, "Kerman south ridge", MISSILE),
    ]
    # Jiroft: the valley's air base and the IRGC's forward HQ.
    + _red_field("Jiroft", "Jiroft", "Jiroft town")
    + [
        Item("ER-Jiroft-LORAD", Job.AIR_DEFENSE, "Jiroft", LORAD),
        Item("ER-Jiroft-MERAD", Job.SPOT, "Jiroft west range", MERAD),
        Item("ER-Jiroft-Missiles", Job.SPOT, "Jiroft west range", MISSILE),
    ]
    # The Jebal Barez pass.
    + _red_fob("FOB Jebal Barez", "JebalBarez")
    + [
        Item("ER-JebalBarez-MERAD", Job.SPOT, "Sardu hills", MERAD),
        Item("ER-JebalBarez-Comms", Job.SPOT, "Jebal Barez pass", Fortification.Comms_tower_M),
    ]
    # Kahnuj.
    + _red_fob("FOB Kahnuj", "Kahnuj")
    + [
        Item("ER-Kahnuj-SHORAD", Job.AIR_DEFENSE, "FOB Kahnuj", SHORAD),
        Item("ER-Kahnuj-Power", Job.TOWN, "Kahnuj town", Fortification.GeneratorF),
    ]
    # Minab: the gate to the valley.
    + _red_fob("FOB Minab", "Minab")
    + [
        Item("ER-Minab-SHORAD", Job.AIR_DEFENSE, "FOB Minab", SHORAD),
        Item("ER-Minab-MERAD", Job.SPOT, "Minab hills", MERAD),
        Item("ER-Minab-EWR", Job.EWR, "FOB Minab", EWR),
        Item("ER-Minab-Comms", Job.TOWN, "Minab town", Fortification.Comms_tower_M),
    ]
    # Sirik: the coast facing the landing.
    + _red_fob("FOB Sirik", "Sirik", guns=2)
    + [
        Item("ER-Sirik-SHORAD", Job.AIR_DEFENSE, "FOB Sirik", SHORAD),
        Item("ER-Sirik-Silkworm-1", Job.SPOT, "Sirik coast north", COASTAL),
        Item("ER-Sirik-Silkworm-2", Job.SPOT, "Sirik coast south", COASTAL),
        Item("ER-Bashagard-Missiles", Job.SPOT, "Bashagard hills", MISSILE),
    ]
    # Lar: the Tomcat base across the mountains.
    + [
        Item("ER-Lar-MERAD", Job.AIR_DEFENSE, "Lar", MERAD),
        Item("ER-Lar-SHORAD", Job.AIR_DEFENSE, "Lar", SHORAD),
        Item("ER-Lar-AAA", Job.AIR_DEFENSE, "Lar", AAA),
        Item("ER-Lar-EWR", Job.EWR, "Lar", EWR),
    ]
    # Blue: the beachhead and the rear.
    + [
        Item("ER-Jask-SHORAD", Job.AIR_DEFENSE, "Bandar-e-Jask", BLUE_SHORAD, BLUE_BLOCK),
        Item("ER-Jask-Garrison-1", Job.GARRISON, "Bandar-e-Jask", ARMOR, BLUE_BLOCK),
        Item("ER-Jask-Garrison-2", Job.GARRISON, "Bandar-e-Jask", ARMOR, BLUE_BLOCK),
        Item("ER-Jask-Ammo", Job.DEPOT, "Bandar-e-Jask", Warehouse._Ammunition_depot, BLUE_BLOCK),
        Item("ER-Fujairah-SHORAD", Job.AIR_DEFENSE, "Fujairah Intl", BLUE_SHORAD, BLUE_BLOCK),
        Item("ER-Fujairah-Ammo", Job.DEPOT, "Fujairah Intl", Warehouse._Ammunition_depot, BLUE_BLOCK),
        Item("ER-Dhafra-Factory", Job.DEPOT, "Al Dhafra AFB", Fortification.Workshop_A, BLUE_BLOCK),
    ]
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


def _theater() -> Any:
    """The Persian Gulf theatre, loaded only for its landmap."""
    from game import persistency
    from game.campaignloader.campaign import Campaign

    persistency.setup(str(Path.home() / "Saved Games" / "DCS"), False, 0)
    return Campaign.from_file(SOURCE_YAML).load_theater(advanced_iads=False)


def _xy(terrain: Any, lat: float, lon: float) -> Point:
    return Point.from_latlng(LatLng(lat, lon), terrain)


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
    for name, (lat, lon) in PLACES.items():
        anchors[name] = _xy(terrain, lat, lon)
    return anchors


def _place(mission: Mission, theater: Any, anchors: dict[str, Point]) -> Placer:
    """Request every FOB and marker by job; resolve against DCS's own ground."""
    terrain = mission.terrain
    placer = Placer(
        terrain,
        "eastern_reach",
        on_land=lambda x, y: bool(theater.is_on_land(Point(x, y, terrain))),
    )
    for name, _, _ in FOBS:
        placer.request(name, Job.SPOT, anchors[name].x, anchors[name].y)
    for item in ITEMS:
        origin = anchors[item.anchor]
        airport = terrain.airports.get(item.anchor)
        placer.request(item.name, item.job, origin.x, origin.y, airport=airport)
    try:
        placer.resolve()
    except NeedsCheck as check:
        raise SystemExit(str(check))
    return placer


def _author(mission: Mission, placer: Placer, anchors: dict[str, Point]) -> list[str]:
    """Write every pick; return the names that found no good ground."""
    terrain = mission.terrain
    unplaced = []
    print("\nFOBs:")
    for name, _, _ in FOBS:
        pick = placer.placements[name]
        if pick.x is None or pick.y is None:
            unplaced.append(name)
            continue
        position = Point(pick.x, pick.y, terrain)
        # The roads end on the FOB's final spot.
        anchors[name] = position
        mission.vehicle_group(
            country=_country(mission, RED_BLOCK), name=name, _type=FOB, position=position
        )
        _report(name, position)

    print("\nmarkers, economy and command:")
    for item in ITEMS:
        pick = placer.placements[item.name]
        if pick.x is None or pick.y is None:
            unplaced.append(item.name)
            continue
        position = Point(pick.x, pick.y, terrain)
        _write_unit(mission, item, position)
        _report(item.name, position, item.anchor)
    return unplaced


def _write_unit(mission: Mission, item: Item, position: Point) -> None:
    """A static for buildings and depots, a one-unit vehicle marker otherwise."""
    from dcs.unittype import StaticType

    if isinstance(item.unit_type, type) and issubclass(item.unit_type, StaticType):
        mission.static_group(
            country=_country(mission, item.block),
            name=item.name,
            _type=item.unit_type,
            position=position,
        )
    else:
        _add_vehicle(mission, item.block, item.name, position, item.unit_type)


def _copy_template_sites(mission: Mission, template: Optional[Path]) -> None:
    """Copy the kept UAE sites as drawn, renamed FIXED so New Game keeps them."""
    if template is None or not template.exists():
        raise SystemExit(
            f"missing the Arabian SAM Template at {template}; pass --template <path>"
        )
    source = Mission()
    source.load_file(str(template))
    found: dict[str, VehicleGroup] = {}
    for coalition in source.coalition.values():
        for country in coalition.countries.values():
            for group in country.vehicle_group:
                if group.name in TEMPLATE_SITES:
                    found[group.name] = group
    missing = set(TEMPLATE_SITES) - set(found)
    if missing:
        raise SystemExit(f"template has no group(s) {sorted(missing)}")
    print("\ntemplate sites:")
    blue = _country(mission, BLUE_BLOCK)
    for source_name, new_name in TEMPLATE_SITES.items():
        group = found[source_name]
        units = list(group.units)
        copy = mission.vehicle_group(
            country=blue,
            name=new_name,
            _type=_vehicle_type(units[0].type),
            position=units[0].position,
            heading=units[0].heading,
            group_size=1,
        )
        copy.points[0].action = PointAction.OffRoad
        copy.points[0].speed = 0
        for unit in units[1:]:
            added = mission.vehicle(f"{new_name} {len(copy.units) + 1}", _vehicle_type(unit.type))
            added.position = Point(unit.position.x, unit.position.y, mission.terrain)
            added.heading = unit.heading
            copy.add_unit(added)
        _report(f"{new_name} ({len(copy.units)})", copy.units[0].position)


def _vehicle_type(type_id: str) -> Any:
    from dcs.vehicles import vehicle_map

    return vehicle_map[type_id]


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
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", type=Path, default=TEMPLATE_DEFAULT)
    args = parser.parse_args()
    if not SOURCE.exists():
        raise SystemExit(f"missing source miz: {SOURCE}")

    mission = Mission()
    mission.load_file(str(SOURCE))
    print(f"loaded {SOURCE.name} ({mission.terrain.name})\n")
    theater = _theater()

    anchors = _anchors(mission)
    placer = _place(mission, theater, anchors)

    _strip(mission)
    _set_ownership(mission)
    unplaced = _author(mission, placer, anchors)
    _copy_template_sites(mission, args.template)
    _author_roads(mission, anchors)
    _author_sea(mission, theater)

    write_review_map(
        REVIEW_MAP,
        "Eastern Reach placement",
        f"{len(placer.placements)} picks, {len(unplaced)} with no good ground",
        placement_markers(mission.terrain, placer),
    )
    print(f"\nreview map: {REVIEW_MAP.relative_to(_REPO_ROOT)}")
    if unplaced:
        print("\nno good ground in reach (left out):")
        for name in unplaced:
            print(f"  {name}")

    mission.save(str(DEST))
    print(f"\nwrote {DEST.relative_to(_REPO_ROOT)}")


if __name__ == "__main__":
    main()
