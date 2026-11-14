"""Re-lay ``resources/campaigns/1968_Yankee_Station.miz`` at about 1.5x scale (2026-11-13).

The old layout squeezed South Vietnam into 14 NM behind a DMZ at the Psou. This moves
the DMZ up the coast to Tuapse and keeps the north as it was:

* North Vietnam: Hanoi Kutaisi, Kep Senaki, Haiphong Kobuleti, Thanh Hoa Sukhumi,
  Vinh Gudauta, Dong Hoi Sochi-Adler, the DMZ at FOB Vinh Linh (Tuapse).
* South Vietnam: FOB Dong Ha (Novomikhaylovsky), Khe Sanh at the foot of the M4
  (Route 9) by Dzhubga, Phu Bai/Chu Lai Gelendzhik, Da Nang Novorossiysk, Cam Ranh Krymsk, Anapa.
* The Trail: Tuapse over the Shaumyan pass to Mu Gia, Ban Karai (Khadyzhensk),
  Ban Laboy and Tchepone (Goryachy Klyuch), the bottom of Route 9.
* Thailand: Maykop and Mineralnye Vody, unchanged. China: Tbilisi, unchanged.

The base is the pre-rework .miz, read from git at ``BASE_COMMIT``, so the 280 scenery
strike targets and the northern laydown carry over. Roads are real highway points
(OpenStreetMap routing, 2026-11-13). New units are placed by job on ground DCS has read:
the first run writes a check mission; run it in DCS, then run this again.

Running it again discards any Mission Editor change made to the .miz since.
Design note: docs/dev/design/retlab-vietnam-retribution-notes.md

    python tools/build_yankee_station_miz.py
"""

from __future__ import annotations

import math
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dcs import ships
from dcs.mapping import LatLng, Point
from dcs.mission import Mission
from dcs.point import PointAction
from dcs.statics import Fortification, Heliport, Warehouse
from dcs.terrain.terrain import Airport
from dcs.vehicles import AirDefence, Armor, Unarmed

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

#: The last commit with the old (Psou DMZ) layout.
BASE_COMMIT = "0c28ad4c2"
MIZ_PATH = "resources/campaigns/1968_Yankee_Station.miz"
YAML = _REPO_ROOT / "resources/campaigns/1968_Yankee_Station.yaml"
DEST = _REPO_ROOT / MIZ_PATH
REVIEW_MAP = _REPO_ROOT / "tmp/yankee_station_placement.html"

BLUE_AIRFIELDS = (
    "Novorossiysk",
    "Gelendzhik",
    "Krymsk",
    "Anapa-Vityazevo",
    "Maykop-Khanskaya",
    "Mineralnye Vody",
)
RED_AIRFIELDS = (
    "Kutaisi",
    "Senaki-Kolkhi",
    "Kobuleti",
    "Sukhumi-Babushara",
    "Gudauta",
    "Sochi-Adler",
    "Tbilisi-Lochini",
)

# --- Marker vocabulary (MizCampaignLoader's *_UNIT_TYPE(S)) ---------------------
MERAD = AirDefence.Hawk_ln
RED_AAA = AirDefence.ZSU_23_4_Shilka
BLUE_AAA = AirDefence.Vulcan
EWR = AirDefence.x_1L13_EWR
ARMOR = Armor.M_1_Abrams
FOB = Unarmed.SKP_11
HELIPAD = Heliport.Invisible_FARP
ROAD = Armor.M_113
FACTORY = Fortification.Workshop_A
AMMO = Warehouse._Ammunition_depot

RED_BLOCK = "red"
BLUE_BLOCK = "blue"

#: FOBs: (name, block, lat, lon).
FOBS = (
    ("FOB Dong Ha", BLUE_BLOCK, 44.255, 38.86),
    # At the M4 junction by Dzhubga: the landmap excludes the hills up the pass (DM call
    # 2026-11-14 to keep the Route 9 front; its tanks fight on the open ground at the wire).
    ("FOB Khe Sanh", BLUE_BLOCK, 44.325, 38.72),
    ("FOB Vinh Linh", RED_BLOCK, 44.10, 39.08),
    ("FOB Mu Gia", RED_BLOCK, 44.357, 39.292),
    ("FOB Ban Karai", RED_BLOCK, 44.42, 39.53),
    ("FOB Ban Laboy", RED_BLOCK, 44.544, 39.267),
    ("FOB Tchepone", RED_BLOCK, 44.632, 39.13),
)

#: Named spots (lat, lon) for SAMs and economy targets.
PLACES = {
    "Tuapse refinery": (44.095, 39.095),
    "Tuapse hills": (44.1208, 39.1445),
    "Khadyzhensk works": (44.425, 39.535),
    "Goryachy Klyuch depot": (44.63, 39.14),
}


@dataclass(frozen=True)
class Item:
    name: str
    job: Job
    anchor: str
    unit_type: Any
    block: str


def _items(anchor: str, block: str, short: str, **counts: int) -> list[Item]:
    """Per-anchor marker set. Counts: pads, garrison, aaa, sam, ammo, ewr, factory."""
    aaa = BLUE_AAA if block == BLUE_BLOCK else RED_AAA
    kinds = (
        ("pads", Job.DEPOT, HELIPAD, "Pad"),
        ("garrison", Job.GARRISON, ARMOR, "Garrison"),
        ("aaa", Job.AIR_DEFENSE, aaa, "AAA"),
        ("sam", Job.AIR_DEFENSE, MERAD, "SAM"),
        ("ammo", Job.DEPOT, AMMO, "Ammo"),
        ("ewr", Job.EWR, EWR, "EWR"),
        ("factory", Job.DEPOT, FACTORY, "Works"),
    )
    out = []
    for key, job, unit_type, label in kinds:
        for i in range(1, counts.get(key, 0) + 1):
            out.append(Item(f"YS-{short}-{label}-{i}", job, anchor, unit_type, block))
    return out


ITEMS: tuple[Item, ...] = tuple(
    # South Vietnam.
    _items("Novorossiysk", BLUE_BLOCK, "DaNang", aaa=2, garrison=2, ammo=1)
    + _items("Gelendzhik", BLUE_BLOCK, "ChuLai", aaa=1, garrison=1)
    + _items("Krymsk", BLUE_BLOCK, "CamRanh", aaa=1)
    + _items("Anapa-Vityazevo", BLUE_BLOCK, "Anapa", aaa=1)
    + _items("FOB Dong Ha", BLUE_BLOCK, "DongHa", pads=4, garrison=2, aaa=1, ammo=1)
    + _items("FOB Khe Sanh", BLUE_BLOCK, "KheSanh", pads=6, garrison=2, aaa=2, ammo=1)
    # North Vietnam: the two fields that change hands or role.
    + _items("Sochi-Adler", RED_BLOCK, "DongHoi", garrison=2, aaa=2, ammo=1)
    + _items("Kobuleti", RED_BLOCK, "Haiphong", sam=2, aaa=2, garrison=1, ewr=1)
    # The DMZ.
    + _items(
        "FOB Vinh Linh", RED_BLOCK, "VinhLinh", pads=2, garrison=2, aaa=2, ammo=1, ewr=1
    )
    + [
        Item("YS-VinhLinh-Hills-SAM", Job.SPOT, "Tuapse hills", MERAD, RED_BLOCK),
        # Factories are read from either country block (MizCampaignLoader.factories).
        Item("YS-Tuapse-Refinery", Job.TOWN, "Tuapse refinery", FACTORY, RED_BLOCK),
    ]
    # The Trail.
    + _items("FOB Mu Gia", RED_BLOCK, "MuGia", pads=2, garrison=1, aaa=2, ammo=1)
    + _items("FOB Ban Karai", RED_BLOCK, "BanKarai", pads=2, garrison=1, aaa=2, ammo=1)
    + [Item("YS-BanKarai-Works", Job.SPOT, "Khadyzhensk works", FACTORY, RED_BLOCK)]
    + _items("FOB Ban Laboy", RED_BLOCK, "BanLaboy", pads=2, garrison=1, aaa=2, ammo=1)
    + _items("FOB Tchepone", RED_BLOCK, "Tchepone", pads=4, garrison=2, aaa=2)
    + [Item("YS-Tchepone-Depot", Job.SPOT, "Goryachy Klyuch depot", AMMO, RED_BLOCK)]
)

#: Roads: (from, real highway points (lat, lon), to). OpenStreetMap routing
#: 2026-11-13; the Senaki-Sukhumi-Gudauta-Sochi legs are Black Sea Coast 1985's.
ROADS = (
    (
        "Kutaisi",
        ((42.1503, 42.3499), (42.1877, 42.237), (42.2579, 42.1224)),
        "Senaki-Kolkhi",
    ),
    (
        "Kobuleti",
        (
            (41.9893, 41.7741),
            (42.1152, 41.6965),
            (42.2154, 41.7645),
            (42.2491, 41.9524),
        ),
        "Senaki-Kolkhi",
    ),
    (
        "Senaki-Kolkhi",
        (
            (42.3331, 41.8754),
            (42.4204, 41.794),
            (42.53, 41.80),
            (42.712, 41.47),
            (42.83, 41.18),
        ),
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
        (
            (43.5846, 39.7653),
            (43.6679, 39.6155),
            (43.7984, 39.4574),
            (43.9117, 39.3262),
            (44.0163, 39.1751),
        ),
        "FOB Vinh Linh",
    ),
    # The DMZ front.
    (
        "FOB Vinh Linh",
        ((44.1418, 39.0449), (44.1736, 38.9701), (44.2101, 38.8923)),
        "FOB Dong Ha",
    ),
    # Route 9: Dong Ha to Khe Sanh, then the Khe Sanh front down to Tchepone.
    (
        "FOB Dong Ha",
        ((44.2783, 38.7959), (44.2901, 38.7581), (44.301, 38.7197)),
        "FOB Khe Sanh",
    ),
    (
        "FOB Khe Sanh",
        ((44.3543, 38.7054), (44.4709, 38.8351), (44.5198, 38.928), (44.5999, 39.0222)),
        "FOB Tchepone",
    ),
    # The Trail, over the Shaumyan pass and down the north slope.
    (
        "FOB Vinh Linh",
        ((44.1406, 39.1686), (44.1993, 39.2423), (44.2843, 39.28)),
        "FOB Mu Gia",
    ),
    (
        "FOB Mu Gia",
        ((44.3747, 39.3611), (44.3982, 39.4051), (44.4358, 39.4747)),
        "FOB Ban Karai",
    ),
    (
        "FOB Ban Karai",
        ((44.4557, 39.4864), (44.4874, 39.4125), (44.5149, 39.3256)),
        "FOB Ban Laboy",
    ),
    (
        "FOB Ban Laboy",
        ((44.5686, 39.2273), (44.6004, 39.1898), (44.6358, 39.1789)),
        "FOB Tchepone",
    ),
    # South Vietnam's coast road.
    (
        "FOB Dong Ha",
        (
            (44.3191, 38.6972),
            (44.3711, 38.5776),
            (44.4618, 38.4451),
            (44.5175, 38.3121),
            (44.5509, 38.1337),
        ),
        "Gelendzhik",
    ),
    (
        "Gelendzhik",
        ((44.6399, 37.9838), (44.6963, 37.8681), (44.7363, 37.7847)),
        "Novorossiysk",
    ),
    (
        "Novorossiysk",
        ((44.7677, 37.7059), (44.8494, 37.7229), (44.8732, 37.9133)),
        "Krymsk",
    ),
    (
        "Novorossiysk",
        ((44.7718, 37.6961), (44.8951, 37.6013), (44.9139, 37.4003)),
        "Anapa-Vityazevo",
    ),
)

#: Ships: (group name, block, unit type, lat, lon). Naval-1/Naval-2 keep their names
#: (the yaml's carrier squadrons key on them). "Gun Line" is pinned to a battleship and
#: a destroyer by the yaml's ground_forces; it sits inside 10 NM of the DMZ coast.
SHIPS = (
    ("Naval-1", BLUE_BLOCK, ships.Stennis, 43.00, 39.30),
    ("Naval-2", BLUE_BLOCK, ships.Stennis, 42.75, 39.75),
    ("Gun Line", BLUE_BLOCK, ships.USS_Arleigh_Burke_IIa, 44.02, 39.02),
    ("Naval-3", RED_BLOCK, ships.USS_Arleigh_Burke_IIa, 41.98, 41.70),
    ("Naval-4", RED_BLOCK, ships.USS_Arleigh_Burke_IIa, 43.40, 39.80),
    ("Naval-5", RED_BLOCK, ships.USS_Arleigh_Burke_IIa, 43.90, 39.25),
)

#: CTLD pickup zones the loader binds by CP name ("<CP> CTLD").
CTLD_ZONE_RADIUS_M = 304.8
CTLD_FOBS = (
    "FOB Dong Ha",
    "FOB Khe Sanh",
    "FOB Vinh Linh",
    "FOB Mu Gia",
    "FOB Tchepone",
)

# --- What the old layout carried that the new one drops -------------------------
#: Old Trail FOBs (inland of Sukhumi and Gudauta) and old Khe Sanh, by old miz XY.
#: Every group, static and CTLD zone within OLD_SITE_RADIUS_M of one is removed.
OLD_SITES = {
    "Ban Dong": (-241200, 614779),
    "Ban Karai": (-244991, 628366),
    "Ban Laboy": (-265650, 623737),
    "Ban Raving": (-216623, 609932),
    "Ky Son": (-236513, 595430),
    "Mu Gia": (-228987, 642317),
    "Tchepone": (-199745, 578429),
    "Thanh Hoa": (-291758, 619468),
    "Khe Sanh": (-170000, 474000),
}
OLD_SITE_RADIUS_M = 5000.0
#: The old blue Da Nang markers that now sit in North Vietnam, by group-name prefix.
OLD_BLUE_PREFIXES = ("AAA - Da Nang", "AAA - Keh Shan", "USA Armor")
#: Old route groups, convoy spawn chains and the empty Guam off-map spawn.
OLD_DROP_TYPES = (
    ROAD.id,
    MizCampaignLoader.CP_CONVOY_SPAWN_TYPE,
    MizCampaignLoader.OFF_MAP_UNIT_TYPE,
)
#: Old scenery zones inside OLD_SITES are kept: they are real DCS buildings and
#: bridges, now inside North Vietnam; only the CTLD zones at old FOBs go.


def _base_mission() -> Mission:
    data = subprocess.run(
        ["git", "show", f"{BASE_COMMIT}:{MIZ_PATH}"],
        cwd=_REPO_ROOT,
        check=True,
        capture_output=True,
    ).stdout
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "base.miz"
        path.write_bytes(data)
        mission = Mission()
        mission.load_file(str(path))
    return mission


def _theater() -> Any:
    from game import persistency
    from game.campaignloader.campaign import Campaign

    persistency.setup(str(Path.home() / "Saved Games" / "DCS"), False, 0)
    return Campaign.from_file(YAML).load_theater(advanced_iads=False)


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


def _near_old_site(x: float, y: float) -> bool:
    return any(
        math.hypot(x - sx, y - sy) <= OLD_SITE_RADIUS_M for sx, sy in OLD_SITES.values()
    )


def _strip_old(mission: Mission) -> int:
    removed = 0
    for coalition_name, coalition in mission.coalition.items():
        for country in coalition.countries.values():
            groups_by_kind: tuple[list[Any], ...] = (
                country.vehicle_group,
                country.plane_group,
                country.static_group,
            )
            for groups in groups_by_kind:
                keep: list[Any] = []
                for group in groups:
                    unit = group.units[0]
                    drop = (
                        unit.type in OLD_DROP_TYPES
                        or _near_old_site(group.position.x, group.position.y)
                        or (
                            coalition_name == "blue"
                            and group.name.startswith(OLD_BLUE_PREFIXES)
                        )
                    )
                    if drop:
                        removed += 1
                    else:
                        keep.append(group)
                groups[:] = keep
            # Ships are re-authored below.
            removed += len(country.ship_group)
            country.ship_group.clear()
    zones = mission.triggers._zones
    zones[:] = [
        z
        for z in zones
        if not (z.name.endswith(" CTLD") and _near_old_site(z.position.x, z.position.y))
    ]
    return removed


def _set_ownership(mission: Mission) -> None:
    for airport in mission.terrain.airport_list():
        if airport.name in BLUE_AIRFIELDS:
            airport.set_blue()
        elif airport.name in RED_AIRFIELDS:
            airport.set_red()
        else:
            airport.set_neutral()
            airport.dynamic_spawn = False
    for name in BLUE_AIRFIELDS + RED_AIRFIELDS:
        if name not in mission.terrain.airports:
            raise RuntimeError(f"{name} is not an airfield on this terrain")


def _anchors(mission: Mission) -> dict[str, Point]:
    terrain = mission.terrain
    anchors = {
        name: terrain.airports[name].position for name in BLUE_AIRFIELDS + RED_AIRFIELDS
    }
    for name, _, lat, lon in FOBS:
        anchors[name] = _xy(terrain, lat, lon)
    for name, (lat, lon) in PLACES.items():
        anchors[name] = _xy(terrain, lat, lon)
    return anchors


def _place(mission: Mission, theater: Any, anchors: dict[str, Point]) -> Placer:
    terrain = mission.terrain
    placer = Placer(
        terrain,
        "yankee_station",
        on_land=lambda x, y: bool(theater.is_on_land(Point(x, y, terrain))),
    )
    output = probe_output_path(placer.name)
    if output.exists():
        _, readings = parse_probe_output(output)
        placer.cache.add(readings)
        placer.cache.save()
    for name, _, _, _ in FOBS:
        placer.request(name, Job.SPOT, anchors[name].x, anchors[name].y)
    for item in ITEMS:
        origin = anchors[item.anchor]
        airport: Airport | None = terrain.airports.get(item.anchor)
        placer.request(item.name, item.job, origin.x, origin.y, airport=airport)
    try:
        placer.resolve()
    except NeedsCheck as check:
        raise SystemExit(str(check))
    return placer


def _report(name: str, position: Point, note: str = "") -> None:
    ll = position.latlng()
    print(f"  {name:<28} ({ll.lat:8.4f}, {ll.lng:8.4f})  {note}")


def _write_unit(mission: Mission, item: Item, position: Point) -> None:
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
        for point in group.points:
            point.action = PointAction.OffRoad
            point.speed = 0


def _author(mission: Mission, placer: Placer, anchors: dict[str, Point]) -> list[str]:
    terrain = mission.terrain
    unplaced = []
    print("\nFOBs:")
    for name, block, _, _ in FOBS:
        pick = placer.placements[name]
        if pick.x is None or pick.y is None:
            unplaced.append(name)
            continue
        position = Point(pick.x, pick.y, terrain)
        anchors[name] = position
        mission.vehicle_group(
            country=_country(mission, block), name=name, _type=FOB, position=position
        )
        if name in CTLD_FOBS:
            mission.triggers.add_triggerzone(
                position, CTLD_ZONE_RADIUS_M, name=f"CP_{name} CTLD"
            )
        _report(name, position, block)
    print("\nmarkers:")
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
    print("\nroads:")
    for index, (start, corridor, end) in enumerate(ROADS, start=1):
        points = (
            [anchors[start]]
            + [_xy(mission.terrain, lat, lon) for lat, lon in corridor]
            + [anchors[end]]
        )
        group = mission.vehicle_group(
            country=_country(mission, BLUE_BLOCK),
            name=f"YS-Road-{index} {start} - {end}",
            _type=ROAD,
            position=points[0],
        )
        # Off-road ends: an On Road end the ME cannot route to crashes it on load
        # (Black Sea Coast 1985, 2026-11-08).
        group.points[0].action = PointAction.OffRoad
        for point in points[1:-1]:
            group.add_waypoint(point, PointAction.OnRoad)
        group.add_waypoint(points[-1], PointAction.OffRoad)
        print(f"  {group.name} ({len(points)} waypoints)")


def _author_sea(mission: Mission, theater: Any) -> None:
    print("\nships:")
    for name, block, unit_type, lat, lon in SHIPS:
        position = _xy(mission.terrain, lat, lon)
        if theater.is_on_land(position, ignore_exclusion=True):
            raise RuntimeError(f"{name} would be placed on land at {lat}, {lon}")
        mission.ship_group(_country(mission, block), name, unit_type, position)
        _report(name, position, block)


def main() -> None:
    mission = _base_mission()
    print(f"loaded {BASE_COMMIT}:{MIZ_PATH} ({mission.terrain.name})")
    theater = _theater()

    anchors = _anchors(mission)
    placer = _place(mission, theater, anchors)

    print(f"removed {_strip_old(mission)} old groups")
    _set_ownership(mission)
    unplaced = _author(mission, placer, anchors)
    _author_roads(mission, anchors)
    _author_sea(mission, theater)

    write_review_map(
        REVIEW_MAP,
        "1968 Yankee Station placement",
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
