"""Build ``resources/campaigns/black_sea_coast_1985.miz``: Caucasus - Black Sea Coast 1985.

A fictional 1985 war: NATO holds Georgia (Senaki, Kutaisi, Lochini, Vaziani) with a
carrier offshore and drives up the Black Sea coast through Gali, Sukhumi, Gudauta and
Sochi, then up to Tuapse and over the hills to Krasnodar, with branches to Maykop and
Krymsk. The tool takes only the map, coalitions and weather from
``northern_russia.miz`` and strips every group and zone it carries.

Design note: docs/dev/design/retlab-black-sea-coast-1985-campaign-notes.md

Run from the repo root::

    python tools/build_black_sea_coast_1985_miz.py

The first build writes a check mission to run once in DCS; the next build places
every unit on ground DCS has read. Never hand-edit the .miz while this tool owns it.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dcs import ships
from dcs.mapping import LatLng, Point
from dcs.mission import Mission
from dcs.point import PointAction
from dcs.statics import Fortification, Heliport, Warehouse
from dcs.vehicles import AirDefence, Armor, MissilesSS, Unarmed

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from game.campaignloader.mizcampaignloader import MizCampaignLoader  # noqa: E402
from tools.campaign_placement import (  # noqa: E402
    Job,
    NeedsCheck,
    Placer,
    parse_probe_output,
    placement_markers,
    probe_output_path,
    write_review_map,
)

SOURCE = _REPO_ROOT / "resources/campaigns/northern_russia.miz"
SOURCE_YAML = _REPO_ROOT / "resources/campaigns/northern_russia.yaml"
DEST = _REPO_ROOT / "resources/campaigns/black_sea_coast_1985.miz"
REVIEW_MAP = _REPO_ROOT / "tmp/black_sea_coast_1985_placement.html"

BLUE_AIRFIELDS = ("Senaki-Kolkhi", "Kutaisi", "Tbilisi-Lochini", "Vaziani")
RED_AIRFIELDS = (
    "Sukhumi-Babushara",
    "Gudauta",
    "Sochi-Adler",
    "Maykop-Khanskaya",
    "Krasnodar-Center",
    "Krasnodar-Pashkovsky",
    "Krymsk",
)

# --- Marker vocabulary (must match MizCampaignLoader's *_UNIT_TYPE(S)) ---------
#: Medium-range only: the faction fills SA-2, SA-3, SA-6 or SA-11. No LORAD
#: marker, so no SA-5 or SA-10 (the DM's period call, 2026-11-08).
MERAD = AirDefence.Hawk_ln
SHORAD = AirDefence.x_2S6_Tunguska
AAA = AirDefence.ZSU_23_4_Shilka
EWR = AirDefence.x_1L13_EWR
ARMOR = Armor.M_1_Abrams
MISSILE = MissilesSS.Scud_B
BLUE_SHORAD = AirDefence.M1097_Avenger
FOB = Unarmed.SKP_11
#: A FOB's helicopter pad (FARP_HELIPADS_TYPE); without one a FOB parks nothing.
HELIPAD = Heliport.Invisible_FARP
ROAD = Armor.M_113

RED_BLOCK = "red"
BLUE_BLOCK = "blue"

#: Red FOBs on the coast road (name, lat, lon). Tuapse is the spot Black Sea
#: already uses (its "FOB Sochi").
FOBS = (
    ("FOB Gali", 42.6091, 41.7367),
    ("FOB Lazarevskoye", 43.91, 39.33),
    ("FOB Tuapse", 44.079, 39.134),
    ("FOB Goryachy Klyuch", 44.63, 39.13),
)

#: Real places (lat, lon) for command posts, power, comms, factories (Job.TOWN)
#: and named spots for SAMs, radars, missile hides and motor pools (Job.SPOT).
#: Town anchors sit on the edge of the landmap's town exclusions (2026-11-08).
#: Motor pools sit about 4 km out, outside the 3 km capture zone. The rail
#: stations and the Adagum works are where Abchazian Blitz and Black Sea put theirs.
PLACES = {
    "Sukhumi town": (43.0194, 41.0273),
    "Psyrtsha rail station": (43.085, 40.842),
    "Gudauta town": (43.1251, 40.6275),
    "Bzyb rail station": (43.229, 40.347),
    "Sochi town": (43.60, 39.74),
    "Sochi hills": (43.62, 39.82),
    "Akhun tower": (43.548, 39.845),
    "Adler motor pool": (43.475, 39.975),
    "Tuapse refinery": (44.095, 39.095),
    "Tuapse hills": (44.1208, 39.1445),
    "Goryachy Klyuch hills": (44.6183, 39.0857),
    "Maykop town": (44.61, 40.10),
    "Krasnodar command": (45.0744, 38.9301),
    "Krasnodar refinery": (44.9756, 39.0833),
    "Krasnodar power": (45.05, 39.13),
    "Krasnodar north": (45.15, 38.95),
    "Krasnodar motor pool": (45.122, 38.94),
    "Krymsk town": (44.9351, 38.0243),
    "Krymsk hills": (44.90, 37.90),
    "Adagum works": (45.106, 37.716),
    "Novorossiysk port": (44.7424, 37.7919),
}


@dataclass(frozen=True)
class Item:
    """One unit to place: its name, job, anchor, type and country block."""

    name: str
    job: Job
    anchor: str
    unit_type: Any
    block: str = RED_BLOCK


def _red_field(field: str, short: str, town: str) -> list[Item]:
    return [
        Item(f"BSC-{short}-SHORAD", Job.AIR_DEFENSE, field, SHORAD),
        Item(f"BSC-{short}-AAA-1", Job.AIR_DEFENSE, field, AAA),
        Item(f"BSC-{short}-AAA-2", Job.AIR_DEFENSE, field, AAA),
        Item(f"BSC-{short}-Garrison-1", Job.GARRISON, field, ARMOR),
        Item(f"BSC-{short}-Garrison-2", Job.GARRISON, field, ARMOR),
        Item(f"BSC-{short}-Ammo", Job.DEPOT, field, Warehouse._Ammunition_depot),
        Item(f"BSC-{short}-Command", Job.TOWN, town, Fortification._Command_Center),
        Item(f"BSC-{short}-EWR", Job.EWR, field, EWR),
    ]


def _red_fob(fob: str, short: str, pads: int = 0) -> list[Item]:
    return [
        Item(f"BSC-{short}-Pad-{i}", Job.DEPOT, fob, HELIPAD)
        for i in range(1, pads + 1)
    ] + [
        Item(f"BSC-{short}-Garrison-1", Job.GARRISON, fob, ARMOR),
        Item(f"BSC-{short}-Garrison-2", Job.GARRISON, fob, ARMOR),
        Item(f"BSC-{short}-Ammo", Job.DEPOT, fob, Warehouse._Ammunition_depot),
        Item(f"BSC-{short}-AAA", Job.AIR_DEFENSE, fob, AAA),
    ]


def _blue_field(field: str, short: str) -> list[Item]:
    return [
        Item(f"BSC-{short}-SHORAD", Job.AIR_DEFENSE, field, BLUE_SHORAD, BLUE_BLOCK),
        Item(f"BSC-{short}-Hawk", Job.AIR_DEFENSE, field, MERAD, BLUE_BLOCK),
        Item(f"BSC-{short}-Garrison-1", Job.GARRISON, field, ARMOR, BLUE_BLOCK),
        Item(f"BSC-{short}-Garrison-2", Job.GARRISON, field, ARMOR, BLUE_BLOCK),
        Item(
            f"BSC-{short}-Ammo",
            Job.DEPOT,
            field,
            Warehouse._Ammunition_depot,
            BLUE_BLOCK,
        ),
    ]


ITEMS: tuple[Item, ...] = tuple(
    # Sukhumi and Gudauta: the Abkhaz coast.
    _red_field("Sukhumi-Babushara", "Sukhumi", "Sukhumi town")
    + [
        Item("BSC-Sukhumi-SAM", Job.AIR_DEFENSE, "Sukhumi-Babushara", MERAD),
        Item(
            "BSC-Psyrtsha-Depot",
            Job.SPOT,
            "Psyrtsha rail station",
            Warehouse._Ammunition_depot,
        ),
    ]
    + _red_field("Gudauta", "Gudauta", "Gudauta town")
    + [
        Item("BSC-Gudauta-SAM", Job.AIR_DEFENSE, "Gudauta", MERAD),
        Item("BSC-Bzyb-Depot", Job.SPOT, "Bzyb rail station", Fortification.Workshop_A),
    ]
    # Sochi: the coast's main base, under the Akhun tower.
    + _red_field("Sochi-Adler", "Sochi", "Sochi town")
    + [
        Item("BSC-Adler-SAM", Job.AIR_DEFENSE, "Sochi-Adler", MERAD),
        Item("BSC-Sochi-Hills-SAM", Job.SPOT, "Sochi hills", MERAD),
        Item("BSC-Akhun-Tower", Job.SPOT, "Akhun tower", Fortification.Comms_tower_M),
        Item(
            "BSC-Adler-Motorpool", Job.SPOT, "Adler motor pool", Fortification.Garage_A
        ),
    ]
    # The coast road north.
    + _red_fob("FOB Gali", "Gali")
    + _red_fob("FOB Lazarevskoye", "Lazarevskoye")
    + [Item("BSC-Lazarevskoye-SHORAD", Job.AIR_DEFENSE, "FOB Lazarevskoye", SHORAD)]
    + _red_fob("FOB Tuapse", "Tuapse", pads=2)
    + [
        Item("BSC-Tuapse-SAM", Job.SPOT, "Tuapse hills", MERAD),
        Item(
            "BSC-Tuapse-Refinery",
            Job.TOWN,
            "Tuapse refinery",
            Fortification.Tech_combine,
        ),
        Item("BSC-Tuapse-EWR", Job.EWR, "FOB Tuapse", EWR),
    ]
    + _red_fob("FOB Goryachy Klyuch", "GoryachyKlyuch", pads=2)
    + [Item("BSC-GoryachyKlyuch-Missiles", Job.SPOT, "Goryachy Klyuch hills", MISSILE)]
    # Maykop.
    + _red_field("Maykop-Khanskaya", "Maykop", "Maykop town")
    + [Item("BSC-Maykop-SAM", Job.AIR_DEFENSE, "Maykop-Khanskaya", MERAD)]
    # Krasnodar: the front HQ, its refinery and SAM ring.
    + _red_field("Krasnodar-Center", "Krasnodar", "Krasnodar command")
    + [
        Item("BSC-Krasnodar-SAM", Job.AIR_DEFENSE, "Krasnodar-Center", MERAD),
        Item("BSC-Krasnodar-North-SAM", Job.SPOT, "Krasnodar north", MERAD),
        Item(
            "BSC-Krasnodar-Refinery",
            Job.TOWN,
            "Krasnodar refinery",
            Fortification.Tech_combine,
        ),
        Item(
            "BSC-Krasnodar-Power", Job.TOWN, "Krasnodar power", Fortification.GeneratorF
        ),
        Item(
            "BSC-Krasnodar-Tower",
            Job.TOWN,
            "Krasnodar command",
            Fortification.Comms_tower_M,
        ),
        Item(
            "BSC-Krasnodar-Motorpool",
            Job.SPOT,
            "Krasnodar motor pool",
            Fortification.Garage_A,
        ),
    ]
    + [
        Item("BSC-Pashkovsky-SAM", Job.AIR_DEFENSE, "Krasnodar-Pashkovsky", MERAD),
        Item("BSC-Pashkovsky-SHORAD", Job.AIR_DEFENSE, "Krasnodar-Pashkovsky", SHORAD),
        Item("BSC-Pashkovsky-AAA", Job.AIR_DEFENSE, "Krasnodar-Pashkovsky", AAA),
        Item("BSC-Pashkovsky-Garrison-1", Job.GARRISON, "Krasnodar-Pashkovsky", ARMOR),
        Item("BSC-Pashkovsky-Garrison-2", Job.GARRISON, "Krasnodar-Pashkovsky", ARMOR),
    ]
    # Krymsk: the rear, with the Adagum works and the Novorossiysk port.
    + _red_field("Krymsk", "Krymsk", "Krymsk town")
    + [
        Item("BSC-Krymsk-SAM", Job.AIR_DEFENSE, "Krymsk", MERAD),
        Item("BSC-Krymsk-Missiles", Job.SPOT, "Krymsk hills", MISSILE),
        Item("BSC-Adagum-Works", Job.SPOT, "Adagum works", Fortification.Workshop_A),
        Item(
            "BSC-Novorossiysk-Port",
            Job.TOWN,
            "Novorossiysk port",
            Warehouse._Ammunition_depot,
        ),
    ]
    # Blue: Georgia.
    + _blue_field("Senaki-Kolkhi", "Senaki")
    + _blue_field("Kutaisi", "Kutaisi")
    + _blue_field("Tbilisi-Lochini", "Lochini")
    + _blue_field("Vaziani", "Vaziani")
)

#: The roads: (from, real highway points as (lat, lon), to). Traced from OpenStreetMap
#: routing (2026-11-08); Senaki to Sukhumi by hand through Zugdidi, Gali and
#: Ochamchire, since today's router will not cross the Enguri.
ROADS = (
    (
        "Kutaisi",
        ((42.1503, 42.3499), (42.1877, 42.237), (42.2579, 42.1224)),
        "Senaki-Kolkhi",
    ),
    (
        "Tbilisi-Lochini",
        (
            (41.8875, 44.7167),
            (42.0244, 44.2562),
            (42.0301, 43.7804),
            (42.1112, 43.3283),
            (42.195, 42.8892),
        ),
        "Kutaisi",
    ),
    (
        "Tbilisi-Lochini",
        ((41.6926, 44.9731), (41.6919, 45.0344), (41.6597, 45.0568)),
        "Vaziani",
    ),
    (
        "Senaki-Kolkhi",
        ((42.3331, 41.8754), (42.4204, 41.794), (42.53, 41.80)),
        "FOB Gali",
    ),
    (
        "FOB Gali",
        ((42.712, 41.47), (42.78, 41.30), (42.83, 41.18)),
        "Sukhumi-Babushara",
    ),
    (
        "Sukhumi-Babushara",
        ((42.9722, 41.0661), (43.0637, 40.9669), (43.0885, 40.7722)),
        "Gudauta",
    ),
    (
        "Gudauta",
        ((43.2165, 40.481), (43.2314, 40.3178), (43.3281, 40.2156), (43.3866, 40.0595)),
        "Sochi-Adler",
    ),
    (
        "Sochi-Adler",
        ((43.551, 39.8011), (43.6558, 39.6921), (43.7287, 39.5635), (43.8211, 39.4384)),
        "FOB Lazarevskoye",
    ),
    (
        "FOB Lazarevskoye",
        ((43.9615, 39.2713), (44.0047, 39.1923), (44.0415, 39.1509)),
        "FOB Tuapse",
    ),
    (
        "FOB Tuapse",
        (
            (44.1772, 38.9761),
            (44.2687, 38.8143),
            (44.4172, 38.7457),
            (44.5304, 38.9408),
        ),
        "FOB Goryachy Klyuch",
    ),
    (
        "FOB Goryachy Klyuch",
        ((44.7315, 39.2189), (44.849, 39.2046), (44.9595, 39.1198)),
        "Krasnodar-Pashkovsky",
    ),
    (
        "Krasnodar-Pashkovsky",
        ((45.0431, 39.1071), (45.034, 39.022), (45.0783, 38.9744)),
        "Krasnodar-Center",
    ),
    (
        "FOB Tuapse",
        (
            (44.1833, 39.2403),
            (44.3617, 39.3008),
            (44.4346, 39.5166),
            (44.4432, 39.7648),
            (44.5342, 39.9889),
        ),
        "Maykop-Khanskaya",
    ),
    (
        "Krasnodar-Center",
        ((45.064, 38.7418), (45.1781, 38.5235), (45.2063, 38.2888), (45.1413, 38.0947)),
        "Krymsk",
    ),
)

# --- The sea, by lat/lon -------------------------------------------------------
CARRIER = ("BSC-CV", 42.85, 40.25)
LHA = ("BSC-LHA", 42.65, 40.95)
#: Ship markers (Arleigh Burke hull; the faction fills the real ships).
SHIP_MARKERS = (
    ("BSC-NATO-Escort", BLUE_BLOCK, 42.75, 40.55),
    ("BSC-Soviet-Tuapse", RED_BLOCK, 44.00, 38.85),
    ("BSC-Soviet-Novorossiysk", RED_BLOCK, 44.55, 37.85),
)


def _theater() -> Any:
    """The Caucasus theatre, loaded only for its landmap."""
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


def _report(name: str, position: Point, anchor: str = "") -> None:
    ll = position.latlng()
    print(f"  {name:<28} ({ll.lat:8.4f}, {ll.lng:8.4f})  {anchor}")


def _anchors(mission: Mission) -> dict[str, Point]:
    terrain = mission.terrain
    anchors = {
        name: terrain.airports[name].position for name in BLUE_AIRFIELDS + RED_AIRFIELDS
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
        "black_sea_coast_1985",
        on_land=lambda x, y: bool(theater.is_on_land(Point(x, y, terrain))),
    )
    # Take in the last check mission's readings, if DCS has written them.
    output = probe_output_path(placer.name)
    if output.exists():
        _, readings = parse_probe_output(output)
        placer.cache.add(readings)
        placer.cache.save()
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


def _write_unit(mission: Mission, item: Item, position: Point) -> None:
    """A static for buildings and depots, a one-unit vehicle marker otherwise."""
    from dcs.unittype import StaticType

    country = _country(mission, item.block)
    if item.unit_type is HELIPAD:
        mission.farp(country, item.name, position, farp_type="Invisible FARP")
    elif isinstance(item.unit_type, type) and issubclass(item.unit_type, StaticType):
        mission.static_group(
            country=country, name=item.name, _type=item.unit_type, position=position
        )
    else:
        group = mission.vehicle_group(
            country=country, name=item.name, _type=item.unit_type, position=position
        )
        # Markers are read for their type and position only; they are never driven.
        for point in group.points:
            point.action = PointAction.OffRoad
            point.speed = 0


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
            country=_country(mission, RED_BLOCK),
            name=name,
            _type=FOB,
            position=position,
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


def _author_roads(mission: Mission, anchors: dict[str, Point]) -> None:
    """One M-113 group per road, the highway points On Road (the .miz route standard)."""
    print("\nroads:")
    for index, (start, corridor, end) in enumerate(ROADS, start=1):
        points = (
            [anchors[start]]
            + [_xy(mission.terrain, lat, lon) for lat, lon in corridor]
            + [anchors[end]]
        )
        group = mission.vehicle_group(
            country=_country(mission, BLUE_BLOCK),
            name=f"BSC-Road-{index} {start} - {end}",
            _type=ROAD,
            position=points[0],
        )
        # The ends sit on base and FOB centres, off the road net: an On Road end the
        # ME cannot route to crashed it on load (me_mission.lua calc_route_length,
        # 2026-11-08), so only the highway points between are On Road.
        group.points[0].action = PointAction.OffRoad
        for point in points[1:-1]:
            group.add_waypoint(point, PointAction.OnRoad)
        group.add_waypoint(points[-1], PointAction.OffRoad)
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

    anchors = _anchors(mission)
    placer = _place(mission, theater, anchors)

    _strip(mission)
    _set_ownership(mission)
    unplaced = _author(mission, placer, anchors)
    _author_roads(mission, anchors)
    _author_sea(mission, theater)

    write_review_map(
        REVIEW_MAP,
        "Black Sea Coast 1985 placement",
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
