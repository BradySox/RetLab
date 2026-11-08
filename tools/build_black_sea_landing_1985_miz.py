"""Build ``resources/campaigns/black_sea_landing_1985.miz``: Caucasus - Black Sea Landing 1985.

A fictional 1985 war: NATO holds a beachhead at Batumi and Kobuleti with a carrier
offshore and drives up the coast to Poti, then inland along the main highway
through Senaki, Kutaisi, Zestafoni, the Rikoti pass, Khashuri and Gori to Tbilisi.
Sukhumi is a flank base up the Abkhaz coast; Mozdok is the rear bomber base across
the mountains with no road to the front. The tool takes only the map, coalitions
and weather from ``northern_russia.miz`` and strips every group and zone it carries.

Design note: docs/dev/design/retlab-black-sea-landing-1985-campaign-notes.md

Run from the repo root::

    python tools/build_black_sea_landing_1985_miz.py

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
DEST = _REPO_ROOT / "resources/campaigns/black_sea_landing_1985.miz"
REVIEW_MAP = _REPO_ROOT / "tmp/black_sea_landing_1985_placement.html"

BLUE_AIRFIELDS = ("Batumi", "Kobuleti")
RED_AIRFIELDS = (
    "Senaki-Kolkhi",
    "Kutaisi",
    "Sukhumi-Babushara",
    "Tbilisi-Lochini",
    "Vaziani",
    "Mozdok",
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

#: Red FOBs on the highway (name, lat, lon), each just outside its town. Khashuri
#: is the spot Northern Russia and Iron Gate already use.
FOBS = (
    ("FOB Poti", 42.13, 41.70),
    ("FOB Zugdidi", 42.509, 41.871),
    ("FOB Zestafoni", 42.125, 43.06),
    ("FOB Khashuri", 41.993, 43.632),
    ("FOB Gori", 41.965, 44.14),
)

#: Real places (lat, lon) for command posts, power, comms, factories (Job.TOWN)
#: and named spots for SAMs, radars and missile hides (Job.SPOT). The Tbilisi
#: nodes are where WRL Kutaisi to Vaziani puts its own.
PLACES = {
    "Tbilisi command": (41.738, 44.811),
    "Tbilisi tower": (41.742, 44.764),
    "Tbilisi power": (41.698, 44.784),
    "Tbilisi north hills": (41.80, 44.80),
    "Mtskheta": (41.845, 44.715),
    "Rustavi steel works": (41.55, 45.01),
    "Zhinvali dam": (42.13, 44.77),
    "Gori town": (41.984, 44.113),
    "Gori south ridge": (41.666, 44.116),
    "Mukhrani plain": (41.93, 44.57),
    "Surami pass": (42.03, 43.50),
    "Zestafoni works": (42.11, 43.03),
    "Kutaisi town": (42.27, 42.70),
    "Tskaltubo hills": (42.33, 42.60),
    "Jvari": (42.715, 42.05),
    "Poti port": (42.15, 41.67),
    "Sukhumi town": (43.00, 41.02),
    "Mozdok town": (43.74, 44.65),
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
        Item(f"BSL-{short}-SHORAD", Job.AIR_DEFENSE, field, SHORAD),
        Item(f"BSL-{short}-AAA-1", Job.AIR_DEFENSE, field, AAA),
        Item(f"BSL-{short}-AAA-2", Job.AIR_DEFENSE, field, AAA),
        Item(f"BSL-{short}-Garrison-1", Job.GARRISON, field, ARMOR),
        Item(f"BSL-{short}-Garrison-2", Job.GARRISON, field, ARMOR),
        Item(f"BSL-{short}-Ammo", Job.DEPOT, field, Warehouse._Ammunition_depot),
        Item(f"BSL-{short}-Command", Job.TOWN, town, Fortification._Command_Center),
        Item(f"BSL-{short}-EWR", Job.EWR, field, EWR),
    ]


def _red_fob(fob: str, short: str, pads: int = 0) -> list[Item]:
    return [
        Item(f"BSL-{short}-Pad-{i}", Job.DEPOT, fob, HELIPAD)
        for i in range(1, pads + 1)
    ] + [
        Item(f"BSL-{short}-Garrison-1", Job.GARRISON, fob, ARMOR),
        Item(f"BSL-{short}-Garrison-2", Job.GARRISON, fob, ARMOR),
        Item(f"BSL-{short}-Ammo", Job.DEPOT, fob, Warehouse._Ammunition_depot),
        Item(f"BSL-{short}-AAA", Job.AIR_DEFENSE, fob, AAA),
    ]


def _blue_field(field: str, short: str) -> list[Item]:
    return [
        Item(f"BSL-{short}-SHORAD", Job.AIR_DEFENSE, field, BLUE_SHORAD, BLUE_BLOCK),
        Item(f"BSL-{short}-Hawk", Job.AIR_DEFENSE, field, MERAD, BLUE_BLOCK),
        Item(f"BSL-{short}-Garrison-1", Job.GARRISON, field, ARMOR, BLUE_BLOCK),
        Item(f"BSL-{short}-Garrison-2", Job.GARRISON, field, ARMOR, BLUE_BLOCK),
        Item(
            f"BSL-{short}-Ammo",
            Job.DEPOT,
            field,
            Warehouse._Ammunition_depot,
            BLUE_BLOCK,
        ),
    ]


ITEMS: tuple[Item, ...] = tuple(
    # Tbilisi: the Transcaucasus Military District HQ, the capital's SAM ring.
    _red_field("Tbilisi-Lochini", "Lochini", "Tbilisi command")
    + [
        Item("BSL-Lochini-SAM", Job.AIR_DEFENSE, "Tbilisi-Lochini", MERAD),
        Item("BSL-Tbilisi-North-SAM", Job.SPOT, "Tbilisi north hills", MERAD),
        Item("BSL-Mtskheta-SAM", Job.SPOT, "Mtskheta", MERAD),
        Item(
            "BSL-Tbilisi-Tower", Job.TOWN, "Tbilisi tower", Fortification.Comms_tower_M
        ),
        Item("BSL-Tbilisi-Power", Job.TOWN, "Tbilisi power", Fortification.GeneratorF),
        Item(
            "BSL-Tbilisi-Motorpool",
            Job.DEPOT,
            "Tbilisi-Lochini",
            Fortification.Garage_A,
        ),
        Item("BSL-Mukhrani-Missiles", Job.SPOT, "Mukhrani plain", MISSILE),
        Item("BSL-Zhinvali-Power", Job.SPOT, "Zhinvali dam", Fortification.GeneratorF),
    ]
    # Vaziani: the fighter base east of the capital, and Rustavi's steel works.
    + [
        Item("BSL-Vaziani-SAM", Job.AIR_DEFENSE, "Vaziani", MERAD),
        Item("BSL-Vaziani-SHORAD", Job.AIR_DEFENSE, "Vaziani", SHORAD),
        Item("BSL-Vaziani-AAA", Job.AIR_DEFENSE, "Vaziani", AAA),
        Item("BSL-Vaziani-Garrison", Job.GARRISON, "Vaziani", ARMOR),
        Item("BSL-Vaziani-Ammo", Job.DEPOT, "Vaziani", Warehouse._Ammunition_depot),
        Item(
            "BSL-Rustavi-Works-1",
            Job.TOWN,
            "Rustavi steel works",
            Fortification.Tech_combine,
        ),
        Item(
            "BSL-Rustavi-Works-2",
            Job.TOWN,
            "Rustavi steel works",
            Fortification.Workshop_A,
        ),
    ]
    # Gori and the road east.
    + _red_fob("FOB Gori", "Gori", pads=2)
    + [
        Item("BSL-Gori-SAM", Job.SPOT, "Gori town", MERAD),
        Item(
            "BSL-Gori-Tower", Job.SPOT, "Gori south ridge", Fortification.Comms_tower_M
        ),
        Item("BSL-Gori-EWR", Job.EWR, "FOB Gori", EWR),
    ]
    # Khashuri and the Surami pass.
    + _red_fob("FOB Khashuri", "Khashuri")
    + [
        Item("BSL-Surami-SAM", Job.SPOT, "Surami pass", MERAD),
        Item("BSL-Khashuri-Depot", Job.DEPOT, "FOB Khashuri", Fortification.Garage_A),
    ]
    # Zestafoni: the ferroalloy works at the foot of the pass.
    + _red_fob("FOB Zestafoni", "Zestafoni", pads=2)
    + [
        Item(
            "BSL-Zestafoni-Works",
            Job.TOWN,
            "Zestafoni works",
            Fortification.Tech_combine,
        ),
    ]
    # Kutaisi: the western Georgia HQ and its auto works.
    + _red_field("Kutaisi", "Kutaisi", "Kutaisi town")
    + [
        Item("BSL-Kutaisi-SAM", Job.AIR_DEFENSE, "Kutaisi", MERAD),
        Item("BSL-Kutaisi-Factory", Job.TOWN, "Kutaisi town", Fortification.Workshop_A),
        Item("BSL-Tskaltubo-Missiles", Job.SPOT, "Tskaltubo hills", MISSILE),
    ]
    # Senaki: the closest red field to the beachhead.
    + _red_field("Senaki-Kolkhi", "Senaki", "Senaki-Kolkhi")
    + [
        Item("BSL-Senaki-SAM", Job.AIR_DEFENSE, "Senaki-Kolkhi", MERAD),
        Item("BSL-Jvari-Power", Job.TOWN, "Jvari", Fortification.GeneratorF),
    ]
    # Poti: the port on the coast road.
    + _red_fob("FOB Poti", "Poti")
    + [
        Item("BSL-Poti-SHORAD", Job.AIR_DEFENSE, "FOB Poti", SHORAD),
        Item("BSL-Poti-Port", Job.TOWN, "Poti port", Warehouse._Ammunition_depot),
    ]
    # Zugdidi and Sukhumi up the Abkhaz coast.
    + _red_fob("FOB Zugdidi", "Zugdidi")
    + _red_field("Sukhumi-Babushara", "Sukhumi", "Sukhumi town")
    + [Item("BSL-Sukhumi-SAM", Job.AIR_DEFENSE, "Sukhumi-Babushara", MERAD)]
    # Mozdok: the bomber base across the mountains.
    + _red_field("Mozdok", "Mozdok", "Mozdok town")
    + [Item("BSL-Mozdok-SAM", Job.AIR_DEFENSE, "Mozdok", MERAD)]
    # Blue: the beachhead.
    + _blue_field("Kobuleti", "Kobuleti")
    + _blue_field("Batumi", "Batumi")
)

#: The roads: (from, real highway points as (lat, lon), to). Traced from OpenStreetMap
#: routing (2026-11-08); Zugdidi to Sukhumi by hand through Gali and Ochamchire, since
#: today's router will not cross the Enguri.
ROADS = (
    (
        "Batumi",
        ((41.6717, 41.6978), (41.787, 41.7875), (41.9, 41.8108)),
        "Kobuleti",
    ),
    (
        "Kobuleti",
        ((41.9375, 41.8226), (41.986, 41.7747), (42.0626, 41.7243)),
        "FOB Poti",
    ),
    (
        "FOB Poti",
        ((42.2047, 41.7316), (42.2367, 41.8673), (42.2572, 42.0078)),
        "Senaki-Kolkhi",
    ),
    (
        "Senaki-Kolkhi",
        ((42.2548, 42.1302), (42.1838, 42.2446), (42.1514, 42.3527)),
        "Kutaisi",
    ),
    (
        "Kutaisi",
        (
            (42.1675, 42.5349),
            (42.1867, 42.6793),
            (42.2111, 42.8191),
            (42.1612, 42.9465),
        ),
        "FOB Zestafoni",
    ),
    (
        "FOB Zestafoni",
        (
            (42.0927, 43.1263),
            (42.1021, 43.2333),
            (42.1063, 43.355),
            (42.0855, 43.4674),
            (42.0348, 43.5584),
        ),
        "FOB Khashuri",
    ),
    (
        "FOB Khashuri",
        ((42.029, 43.7767), (42.0522, 43.906), (42.01, 44.0408)),
        "FOB Gori",
    ),
    (
        "FOB Gori",
        (
            (42.0234, 44.2776),
            (41.9443, 44.5048),
            (41.8764, 44.7241),
            (41.7212, 44.7834),
        ),
        "Tbilisi-Lochini",
    ),
    (
        "Tbilisi-Lochini",
        ((41.6926, 44.9731), (41.6919, 45.0344), (41.6597, 45.0568)),
        "Vaziani",
    ),
    (
        "Senaki-Kolkhi",
        ((42.2581, 41.991), (42.3331, 41.8754), (42.4204, 41.794)),
        "FOB Zugdidi",
    ),
    (
        "FOB Zugdidi",
        ((42.53, 41.80), (42.627, 41.735), (42.712, 41.47), (42.80, 41.25)),
        "Sukhumi-Babushara",
    ),
)

# --- The sea, by lat/lon -------------------------------------------------------
CARRIER = ("BSL-CV", 41.70, 41.05)
LHA = ("BSL-LHA", 41.90, 41.45)
#: Ship markers (Arleigh Burke hull; the faction fills the real ships).
SHIP_MARKERS = (
    ("BSL-NATO-Escort", BLUE_BLOCK, 41.80, 41.25),
    ("BSL-Soviet-Sukhumi", RED_BLOCK, 42.80, 40.85),
    ("BSL-Soviet-Poti", RED_BLOCK, 42.30, 41.35),
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
        "black_sea_landing_1985",
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
            name=f"BSL-Road-{index} {start} - {end}",
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

    anchors = _anchors(mission)
    placer = _place(mission, theater, anchors)

    _strip(mission)
    _set_ownership(mission)
    unplaced = _author(mission, placer, anchors)
    _author_roads(mission, anchors)
    _author_sea(mission, theater)

    write_review_map(
        REVIEW_MAP,
        "Black Sea Landing 1985 placement",
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
