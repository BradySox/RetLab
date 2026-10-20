"""Build ``resources/campaigns/red_bear_1985.miz``: Afghanistan - Red Bear 1985.

A fictional winter war across the top of the Afghanistan map. A USAF expeditionary
wing holds Herat and Shindand; the Soviet 40th Army holds the north and Kabul. Two
axes: north along the ring road through Qala i Naw, Maymana, Mazar-i-Sharif and the
Salang to Bagram, and central along the Hari Rud road through Chaghcharan and Bamyan
to Kabul. The miz is authored here from the bare map; nothing is taken from
``graveyard_of_empires.miz`` but the terrain and its mission settings.

Design note: docs/dev/design/retlab-red-bear-1985-campaign-notes.md

What it writes:

1.  **Ownership.** Blue holds Herat and Shindand, and Camp Bastion as a rear base for the
    heavies with no road to the war; red holds the seven northern and eastern fields.
    Every other field is neutral, so the south stays out of the fighting.
2.  **Invert Sides.** Every red control point carries the invert flag.
3.  **The land.** Red FOBs at Mazar-i-Sharif and Pul-i-Khumri, base defences,
    garrisons, depots and factories placed by the landmap, a Scud site near Kabul,
    and an off-map red rear at Termez across the Soviet border.
4.  **The roads.** One M-113 route group per road, every waypoint On Road, traced
    from real town lat/lon (``tools/supply_route_geo.py`` explains the method).

Run from the repo root::

    python tools/build_red_bear_1985_miz.py

Never hand-edit ``red_bear_1985.miz``.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Iterable

from dcs.countries import CombinedJointTaskForcesBlue
from dcs.mapping import LatLng, Point
from dcs.mission import Mission
from dcs.planes import F_15C
from dcs.point import PointAction
from dcs.statics import Fortification, Warehouse
from dcs.terrain.terrain import Airport
from dcs.vehicles import AirDefence, Armor, MissilesSS, Unarmed

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from game.campaignloader.mizcampaignloader import MizCampaignLoader  # noqa: E402

SOURCE = _REPO_ROOT / "resources/campaigns/graveyard_of_empires.miz"
SOURCE_YAML = _REPO_ROOT / "resources/campaigns/graveyard_of_empires.yaml"
DEST = _REPO_ROOT / "resources/campaigns/red_bear_1985.miz"

MAYMANA = "Maymana Zahiraddin Faryabi"
#: Camp Bastion is blue's rear, with stands for the heavies (the DM's pick). No
#: road joins it to the war, so no front opens in the south.
BLUE_AIRFIELDS = ("Herat", "Shindand", "Camp Bastion")
RED_AIRFIELDS = (
    "Qala i Naw",
    MAYMANA,
    "Chaghcharan",
    "Bamyan",
    "Bagram",
    "Kabul",
    "Jalalabad",
)

# --- Marker vocabulary (must match MizCampaignLoader's *_UNIT_TYPE(S)) ---------
EWR = AirDefence.x_1L13_EWR
MEDIUM_SAM = AirDefence.S_75M_Volhov
SHORAD = AirDefence.Strela_1_9P31
AAA = AirDefence.ZSU_23_4_Shilka
ARMOR = Armor.M_1_Abrams

RED_BLOCK = "red"
BLUE_BLOCK = "blue"

#: Red's FOBs on the northern ring road: Marmal airbase outside Mazar-i-Sharif,
#: and Pul-i-Khumri at the north end of the Salang road.
FOBS = (
    ("Mazar-i-Sharif", 36.706, 67.209),
    ("Pul-i-Khumri", 35.944, 68.712),
)
#: The Soviet rear across the Amu Darya; it is beyond the playable map.
OFF_MAP = (("Termez", RED_BLOCK, 37.29, 67.31),)
#: The 40th Army's Scud battery on the Shomali plain north of Kabul.
SCUD_SITE = ("RB85-Kabul-Scud", "Kabul")

# (name, anchor, marker type, country block, placement). An anchor is an airfield
# or FOB name. Placement as in build_corporate_1982_miz.py. SAM and EWR markers go
# in the red block, the loader's side-agnostic default.
ADDED_MARKERS: tuple[tuple[str, str, Any, str, str], ...] = (
    # Herat, Shindand and Camp Bastion: the wing's Hawk batteries, radars and guns.
    ("RB85-Herat-EWR", "Herat", EWR, RED_BLOCK, "ring"),
    ("RB85-Herat-Hawk", "Herat", MEDIUM_SAM, RED_BLOCK, "axis"),
    ("RB85-Herat-AAA-1", "Herat", AAA, RED_BLOCK, "near"),
    ("RB85-Herat-AAA-2", "Herat", AAA, RED_BLOCK, "near"),
    ("RB85-Herat-Garrison", "Herat", ARMOR, BLUE_BLOCK, "near"),
    ("RB85-Shindand-EWR", "Shindand", EWR, RED_BLOCK, "ring"),
    ("RB85-Shindand-Hawk", "Shindand", MEDIUM_SAM, RED_BLOCK, "axis"),
    ("RB85-Shindand-AAA-1", "Shindand", AAA, RED_BLOCK, "near"),
    ("RB85-Shindand-AAA-2", "Shindand", AAA, RED_BLOCK, "near"),
    ("RB85-Bastion-Hawk", "Camp Bastion", MEDIUM_SAM, RED_BLOCK, "axis"),
    ("RB85-Bastion-AAA", "Camp Bastion", AAA, RED_BLOCK, "near"),
    # The northern axis: Qala i Naw, Maymana and the two FOBs.
    ("RB85-QalaiNaw-SHORAD", "Qala i Naw", SHORAD, RED_BLOCK, "near"),
    ("RB85-QalaiNaw-AAA", "Qala i Naw", AAA, RED_BLOCK, "near"),
    ("RB85-QalaiNaw-Garrison-1", "Qala i Naw", ARMOR, RED_BLOCK, "near"),
    ("RB85-QalaiNaw-Garrison-2", "Qala i Naw", ARMOR, RED_BLOCK, "near"),
    ("RB85-Maymana-SHORAD", MAYMANA, SHORAD, RED_BLOCK, "near"),
    ("RB85-Maymana-AAA", MAYMANA, AAA, RED_BLOCK, "near"),
    ("RB85-Maymana-Garrison", MAYMANA, ARMOR, RED_BLOCK, "near"),
    ("RB85-Mazar-EWR", "Mazar-i-Sharif", EWR, RED_BLOCK, "ring"),
    ("RB85-Mazar-SAM", "Mazar-i-Sharif", MEDIUM_SAM, RED_BLOCK, "ring"),
    ("RB85-Mazar-AAA", "Mazar-i-Sharif", AAA, RED_BLOCK, "near"),
    ("RB85-Mazar-Garrison-1", "Mazar-i-Sharif", ARMOR, RED_BLOCK, "near"),
    ("RB85-Mazar-Garrison-2", "Mazar-i-Sharif", ARMOR, RED_BLOCK, "near"),
    ("RB85-PuliKhumri-SHORAD", "Pul-i-Khumri", SHORAD, RED_BLOCK, "near"),
    ("RB85-PuliKhumri-AAA", "Pul-i-Khumri", AAA, RED_BLOCK, "near"),
    ("RB85-PuliKhumri-Garrison", "Pul-i-Khumri", ARMOR, RED_BLOCK, "near"),
    # The central axis: Chaghcharan and Bamyan.
    ("RB85-Chaghcharan-SHORAD", "Chaghcharan", SHORAD, RED_BLOCK, "near"),
    ("RB85-Chaghcharan-AAA", "Chaghcharan", AAA, RED_BLOCK, "near"),
    ("RB85-Chaghcharan-Garrison-1", "Chaghcharan", ARMOR, RED_BLOCK, "near"),
    ("RB85-Chaghcharan-Garrison-2", "Chaghcharan", ARMOR, RED_BLOCK, "near"),
    ("RB85-Bamyan-SAM", "Bamyan", MEDIUM_SAM, RED_BLOCK, "ring"),
    ("RB85-Bamyan-AAA", "Bamyan", AAA, RED_BLOCK, "near"),
    ("RB85-Bamyan-Garrison", "Bamyan", ARMOR, RED_BLOCK, "near"),
    # The deep bases: SA-2 and SA-3 rings around Bagram and Kabul.
    ("RB85-Bagram-EWR", "Bagram", EWR, RED_BLOCK, "ring"),
    ("RB85-Bagram-SAM-1", "Bagram", MEDIUM_SAM, RED_BLOCK, "ring"),
    ("RB85-Bagram-SAM-2", "Bagram", MEDIUM_SAM, RED_BLOCK, "axis"),
    ("RB85-Bagram-SHORAD", "Bagram", SHORAD, RED_BLOCK, "near"),
    ("RB85-Bagram-AAA-1", "Bagram", AAA, RED_BLOCK, "near"),
    ("RB85-Bagram-AAA-2", "Bagram", AAA, RED_BLOCK, "near"),
    ("RB85-Kabul-EWR", "Kabul", EWR, RED_BLOCK, "ring"),
    ("RB85-Kabul-SAM-1", "Kabul", MEDIUM_SAM, RED_BLOCK, "ring"),
    ("RB85-Kabul-SAM-2", "Kabul", MEDIUM_SAM, RED_BLOCK, "axis"),
    ("RB85-Kabul-SHORAD", "Kabul", SHORAD, RED_BLOCK, "near"),
    ("RB85-Kabul-AAA-1", "Kabul", AAA, RED_BLOCK, "near"),
    ("RB85-Kabul-AAA-2", "Kabul", AAA, RED_BLOCK, "near"),
    ("RB85-Jalalabad-SHORAD", "Jalalabad", SHORAD, RED_BLOCK, "near"),
    ("RB85-Jalalabad-AAA", "Jalalabad", AAA, RED_BLOCK, "near"),
)

#: (name, anchor, static type, block). Ownership follows the nearest control point.
ADDED_STATICS: tuple[tuple[str, str, Any, str], ...] = (
    ("RB85-Herat-Factory", "Herat", Fortification.Workshop_A, BLUE_BLOCK),
    ("RB85-Herat-Ammo", "Herat", Warehouse._Ammunition_depot, BLUE_BLOCK),
    ("RB85-Herat-Motorpool", "Herat", Fortification.Garage_A, BLUE_BLOCK),
    ("RB85-Shindand-Ammo", "Shindand", Warehouse._Ammunition_depot, BLUE_BLOCK),
    ("RB85-Mazar-Factory", "Mazar-i-Sharif", Fortification.Workshop_A, RED_BLOCK),
    ("RB85-Mazar-Ammo", "Mazar-i-Sharif", Warehouse._Ammunition_depot, RED_BLOCK),
    ("RB85-Mazar-Motorpool", "Mazar-i-Sharif", Fortification.Garage_A, RED_BLOCK),
    ("RB85-Chaghcharan-Ammo", "Chaghcharan", Warehouse._Ammunition_depot, RED_BLOCK),
    ("RB85-Kabul-Factory", "Kabul", Fortification.Workshop_A, RED_BLOCK),
    ("RB85-Kabul-Ammo", "Kabul", Warehouse._Ammunition_depot, RED_BLOCK),
    ("RB85-Bagram-Ammo", "Bagram", Warehouse._Ammunition_depot, RED_BLOCK),
    ("RB85-Bagram-Motorpool", "Bagram", Fortification.Garage_A, RED_BLOCK),
)

#: (route name, start control point, corridor towns as (lat, lon), end control
#: point). Only the end points bind a route to its control points.
ROADS: tuple[tuple[str, str, tuple[tuple[float, float], ...], str], ...] = (
    (
        "RB85 Road Shindand - Herat",
        "Shindand",
        ((33.64, 62.27), (33.92, 62.18)),
        "Herat",
    ),
    (
        "RB85 Road Herat - Qala i Naw",
        "Herat",
        ((34.35, 62.20), (34.48, 62.59), (34.72, 62.93)),
        "Qala i Naw",
    ),
    (
        "RB85 Road Qala i Naw - Maymana",
        "Qala i Naw",
        ((35.58, 63.33), (35.73, 63.78), (35.68, 64.30), (35.84, 64.53)),
        MAYMANA,
    ),
    (
        "RB85 Road Maymana - Mazar-i-Sharif",
        MAYMANA,
        ((36.43, 64.92), (36.95, 65.12), (36.67, 65.75), (36.76, 66.90)),
        "Mazar-i-Sharif",
    ),
    (
        "RB85 Road Mazar-i-Sharif - Pul-i-Khumri",
        "Mazar-i-Sharif",
        ((36.70, 67.70), (36.26, 68.02)),
        "Pul-i-Khumri",
    ),
    (
        "RB85 Road Pul-i-Khumri - Bagram (Salang)",
        "Pul-i-Khumri",
        ((35.62, 68.68), (35.32, 69.03), (35.12, 69.24), (35.01, 69.17)),
        "Bagram",
    ),
    (
        "RB85 Road Herat - Chaghcharan (Hari Rud)",
        "Herat",
        ((34.35, 62.40), (34.37, 63.17), (34.35, 63.73), (34.10, 64.30)),
        "Chaghcharan",
    ),
    (
        "RB85 Road Chaghcharan - Bamyan",
        "Chaghcharan",
        ((34.52, 66.30), (34.38, 67.02), (34.82, 67.82)),
        "Bamyan",
    ),
    (
        "RB85 Road Bamyan - Kabul",
        "Bamyan",
        ((34.65, 68.10), (34.47, 68.33), (34.47, 68.65), (34.40, 68.87)),
        "Kabul",
    ),
    (
        "RB85 Road Kabul - Bagram",
        "Kabul",
        ((34.85, 69.17),),
        "Bagram",
    ),
    (
        "RB85 Road Kabul - Jalalabad",
        "Kabul",
        ((34.59, 69.76), (34.45, 70.15)),
        "Jalalabad",
    ),
)

# --- Placement tolerances ------------------------------------------------------
MIN_OFFSET_M = 3000.0
MAX_OFFSET_M = 15000.0
STEP_M = 500.0
BEARING_STEP_DEG = 15
LATERAL_OFFSETS_M = (0.0, 500.0, -500.0, 1000.0, -1000.0)
MIN_SEPARATION_M = 900.0
NEAR_OFFSET_M = 6000.0
#: A FOB has no runway strip to keep clear of.
FOB_MIN_OFFSET_M = 800.0
#: Clear of the 3,000 m capture zone, with margin.
MOTORPOOL_MIN_OFFSET_M = 3500.0


def _theater() -> Any:
    """The Afghanistan theatre, loaded only for its landmap."""
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
    """Keep the map and its settings; drop every group and zone the source placed."""
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
    print(f"  {name:<30} ({ll.lat:7.3f}, {ll.lng:7.3f})  {anchor}")


def _author_land(mission: Mission, placer: Placer) -> dict[str, Point]:
    """Place the FOBs and every marker; return each control point's position."""
    airports = mission.terrain.airports
    anchors = {name: airports[name].position for name in BLUE_AIRFIELDS}
    anchors.update({name: airports[name].position for name in RED_AIRFIELDS})

    print("\nforward operating bases:")
    for name, lat, lon in FOBS:
        position = _xy(mission.terrain, lat, lon)
        if not placer.theater.is_on_land(position):
            raise RuntimeError(f"{name} is not on clear land")
        placer.taken.append(position)
        group = _add_vehicle(mission, RED_BLOCK, name, position, Unarmed.SKP_11)
        group.late_activation = True  # the invert flag
        anchors[name] = position
        _report(name, position)

    def start_of(name: str) -> float:
        return MIN_OFFSET_M if name in airports else FOB_MIN_OFFSET_M

    print("\nadded markers:")
    for name, anchor_name, unit_type, block, placement in ADDED_MARKERS:
        origin = anchors[anchor_name]
        if placement == "axis":
            position = placer.axis(name, airports[anchor_name])
        elif placement == "near":
            position = placer.near(name, origin, start_of(anchor_name))
        else:
            position = placer.ring(name, origin, start_of(anchor_name))
        _add_vehicle(mission, block, name, position, unit_type)
        _report(name, position, anchor_name)

    name, anchor_name = SCUD_SITE
    position = placer.ring(name, anchors[anchor_name], 10_000.0)
    _add_vehicle(mission, RED_BLOCK, name, position, MissilesSS.Scud_B)
    _report(name, position, anchor_name)

    print("\neconomy:")
    for name, anchor_name, static_type, block in ADDED_STATICS:
        origin = anchors[anchor_name]
        start = start_of(anchor_name)
        if static_type is Fortification.Garage_A:
            # A motorpool's parked armor inside a capture zone blocks the capture.
            start = max(start, MOTORPOOL_MIN_OFFSET_M)
        position = placer.near(name, origin, start)
        mission.static_group(
            country=_country(mission, block),
            name=name,
            _type=static_type,
            position=position,
        )
        _report(name, position, anchor_name)

    print("\noff-map:")
    for name, block, lat, lon in OFF_MAP:
        position = _xy(mission.terrain, lat, lon)
        group = mission.flight_group_inflight(
            country=_country(mission, block),
            name=name,
            aircraft_type=F_15C,
            position=position,
            altitude=6000,
        )
        # The invert flag, on red's rear only.
        group.late_activation = block == RED_BLOCK
        _report(name, position)
    return anchors


def _author_roads(mission: Mission, anchors: dict[str, Point]) -> None:
    from campaign_routes import draw

    # MizCampaignLoader reads route groups from this one country only.
    country = mission.country(CombinedJointTaskForcesBlue.name)
    print("\nroads:")
    for name, start, corridor, end in ROADS:
        points = [(anchors[start].x, anchors[start].y)]
        for lat, lon in corridor:
            p = _xy(mission.terrain, lat, lon)
            points.append((p.x, p.y))
        points.append((anchors[end].x, anchors[end].y))
        draw(mission, country, "route", name, points)
        # The end points sit on runways, off any road. An On Road leg the editor
        # cannot path leaves a hole in its spans; a hole in the first leg crashes it.
        group = mission.find_group(name)
        group.points[0].action = PointAction.OffRoad
        group.points[-1].action = PointAction.OffRoad
        print(f"  {name} ({len(points)} waypoints)")


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
    anchors = _author_land(mission, placer)
    _author_roads(mission, anchors)

    if placer.relaxed:
        print("\nplaced on inclusion-only ground (no fully clear point in reach):")
        for name in placer.relaxed:
            print(f"  {name}")

    # Routes are authored in the .miz; keep any drawn there by hand.
    if DEST.exists():
        from campaign_routes import carry_route_groups

        carry_route_groups(mission, DEST)
    mission.save(str(DEST))
    print(f"\nwrote {DEST.relative_to(_REPO_ROOT)}")


if __name__ == "__main__":
    main()
