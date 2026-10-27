"""Vacuum ELINT (§118): an orbit that calls radiating red radars by bullseye.

A KC-135 (any era), or a C-130J-30 when none is free, holds the AWACS station one slot back. While it is
airborne the ``vacuum`` plugin calls each red ground radar once each time it comes on,
on Vacuum's own frequency, and on STRIKE only when the radar covers a player package's
route or target. SkyEye speaks the calls over its mission link and works out the
bullseye itself. It speaks of SAMs only: an early warning or search radar is heard
and fixed, never called. Players call it through SkyEye (check in, emitters, target status, mud,
say again) and the plugin answers. It never jams, lases or designates.
docs/dev/retlab-features.md §118.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Iterable, Optional

from game.ato.flight import Flight
from game.ato.flighttype import FlightType
from game.data.units import UnitClass
from game.theater.fogofwar import fog_intact
from game.theater.player import Player
from game.theater.theatergroundobject import NavalGroundObject, SamGroundObject
from game.retlab.package_control import (
    SKYEYE_LINK_HOST,
    SKYEYE_LINK_PORT,
    _country,
    lead_callsign,
    player_packages,
)
from game.retlab.skyeye_voices import pick_another_voice

if TYPE_CHECKING:
    from game import Game
    from game.ato.airtaaskingorder import AirTaskingOrder
    from game.ato.package import Package
    from game.coalition import Coalition
    from game.missiongenerator.aircraft.flightdata import FlightData
    from game.missiongenerator.luagenerator import LuaData
    from game.missiongenerator.missiondata import MissionData
    from game.theater.theatergroundobject import TheaterGroundObject
    from game.theater.theatergroup import TheaterGroup, TheaterUnit

#: Turns with this many SEAD, SEAD Escort or DEAD flights get a Vacuum (user call,
#: 2026-10-20; lowered from 2, 2026-10-22).
SEAD_FLIGHTS_FOR_VACUUM = 1
SEAD_TYPES = frozenset(
    {
        FlightType.SEAD,
        FlightType.SEAD_ESCORT,
        FlightType.SEAD_SWEEP,
        FlightType.DEAD,
    }
)

#: Unit classes that carry a radar. Radar-laid guns (AAA_RADAR) are left out: a
#: Shilka on every road would drown the calls that matter.
RADAR_CLASSES = frozenset(
    {
        UnitClass.EARLY_WARNING_RADAR,
        UnitClass.SEARCH_RADAR,
        UnitClass.SEARCH_TRACK_RADAR,
        UnitClass.TRACK_RADAR,
        UnitClass.SPECIALIZED_RADAR,
        UnitClass.TELAR,
    }
)

#: How far Vacuum hears a radar, about an RC-135's horizon at altitude.
VACUUM_RANGE_NM = 250

CALLSIGN = "Vacuum"

_NATO = re.compile(r"\b((?:SA|HQ)-\d+[A-Z]?)\b(/)?")
_SITE_SUFFIX = {
    "TR",
    "SR",
    "STR",
    "LN",
    "CP",
    "CWAR",
    "PCP",
    "RADAR",
    "EWR",
    "TEL",
    "TELAR",
    "ECS",
    "CR",
}

#: Words DCS puts in front of a system's name: "SAM Hawk", "AShM Silkworm".
_TYPE_PREFIX = {"SAM", "ASHM"}

#: Search radars that serve no one SAM: the Dog Ear is a SHORAD battery's command-post radar.
_SHARED_SEARCH_RADAR = re.compile(r"Sborka|Dog Ear", re.IGNORECASE)

#: Which radar names a site: its fire-control radar before a search radar, a search radar
#: before an early-warning one. A P-19 "(SA-2/3)" out-ranges an SA-6 Kub's own radar, and
#: picking by range alone called Kub sites "SA-2" (Test 63, 2026-10-21).
_LABEL_RANK = {
    UnitClass.TRACK_RADAR: 3,
    UnitClass.SEARCH_TRACK_RADAR: 3,
    UnitClass.TELAR: 3,
    UnitClass.SEARCH_RADAR: 2,
    UnitClass.SPECIALIZED_RADAR: 2,
    UnitClass.EARLY_WARNING_RADAR: 1,
}


def plan_vacuum(coalition: Coalition) -> Optional[Flight]:
    """Add a Vacuum to the AWACS package on a turn with SEAD or DEAD, when the setting is on."""
    game = coalition.game
    if not coalition.player.is_blue or not game.settings.vacuum_elint:
        return None
    ato = coalition.ato
    if _flights(ato, {FlightType.ELINT}):
        return None
    if len(_flights(ato, SEAD_TYPES)) < SEAD_FLIGHTS_FOR_VACUUM:
        return None
    package = _awacs_package(ato)
    if package is None or package.primary_flight is None:
        return None
    squadron = coalition.air_wing.best_squadron_for(
        package.primary_flight.departure,
        FlightType.ELINT,
        1,
        False,
        this_turn=True,
    )
    if squadron is None:
        logging.info("Vacuum: no C-130J-30 or KC-135 free this turn")
        return None
    start_type = squadron.location.required_aircraft_start_type
    if start_type is None:
        start_type = game.settings.start_type_for(FlightType.ELINT, has_players=False)
        if game.settings.support_air_start:
            from game.ato.starttype import StartType

            start_type = StartType.IN_FLIGHT
    flight = Flight(package, squadron, 1, FlightType.ELINT, start_type, divert=None)
    package.add_flight(flight)
    flight.recreate_flight_plan()
    logging.info("Vacuum: %s joins %s", squadron.aircraft.display_name, package)
    return flight


def has_vacuum(ato: AirTaskingOrder) -> bool:
    """Whether the ATO fields a Vacuum flight."""
    return bool(_flights(ato, {FlightType.ELINT}))


def vacuum_comm_name() -> str:
    return f"{CALLSIGN.upper()} (ELINT)"


def _flights(ato: AirTaskingOrder, types: Iterable[FlightType]) -> list[Flight]:
    wanted = set(types)
    return [f for p in ato.packages for f in p.flights if f.flight_type in wanted]


def _awacs_package(ato: AirTaskingOrder) -> Optional[Package]:
    """The land AWACS package: Vacuum orbits like the AWACS, never over a boat."""
    for package in ato.packages:
        if package.primary_task is not FlightType.AEWC:
            continue
        target = package.target
        if getattr(target, "is_carrier", False) or getattr(target, "is_fleet", False):
            continue
        return package
    return None


def emitter_label(unit: TheaterUnit) -> str:
    """What Vacuum calls a radar: its NATO name, else the system's own name."""
    unit_type = unit.unit_type
    name = unit_type.display_name if unit_type is not None else unit.type.id
    if (nato := _NATO.search(name)) is not None:
        # "SA-2/3" is a search radar shared by several systems, not one SAM.
        return "search radar" if nato.group(2) else nato.group(1)
    if unit_type is not None and unit_type.unit_class is UnitClass.EARLY_WARNING_RADAR:
        return "early warning radar"
    if _SHARED_SEARCH_RADAR.search(name):
        return "search radar"
    name = re.sub(r'"[^"]*"|\([^)]*\)|\[[^\]]*\]', "", name)
    words = [w for w in name.split() if w.upper() not in _TYPE_PREFIX]
    # The system's name ends at the first component word: "NASAMS SR MPQ64F1" is NASAMS.
    for i, word in enumerate(words[1:], start=1):
        if word.upper() in _SITE_SUFFIX:
            words = words[:i]
            break
    return " ".join(words) or "radar"


#: A fix this close is "tight" (the Lua plugin's TIGHT_METERS).
TIGHT_FIX_M = 1852.0


def known_fix(tgo: TheaterGroundObject) -> tuple[str, Optional[float]]:
    """How well Vacuum knows a site before it hears it, and the fix error (m) an earlier
    Vacuum left on it: a fixed SAM's spot is known before the war ("tight"), another known
    site is "tight" or "loose" by its old fix, anything else not at all.
    """
    with fog_intact():
        if not tgo.known_for(Player.BLUE):
            return "", None
    if tgo.is_fixed_sam_site:
        return "tight", None
    error = tgo.vacuum_fix_m
    if error is not None and error <= TIGHT_FIX_M:
        return "tight", error
    return "loose", error


#: Labels that name no SAM: Vacuum hears these radars but never speaks of them.
NON_SAM_LABELS = frozenset({"early warning radar", "search radar", "radar"})


def speaks_of(tgo: TheaterGroundObject, main: TheaterUnit, label: str) -> bool:
    """Whether Vacuum speaks of a site: a SAM only, never an early warning or search radar
    (Brady's call, 2026-10-26). A SAM site whose tracker is dead still counts by its name.
    """
    if label in NON_SAM_LABELS:
        return False
    rank = _LABEL_RANK.get(main.unit_type.unit_class, 0) if main.unit_type else 0
    return rank >= 3 or isinstance(tgo, SamGroundObject)


def site_radar(radars: list[TheaterUnit]) -> TheaterUnit:
    """The radar that names a site: the fire-control one, the longest-ranged on a tie."""
    return max(
        radars,
        key=lambda u: (
            _LABEL_RANK.get(u.unit_type.unit_class, 0) if u.unit_type else 0,
            u.detection_range().meters,
        ),
    )


def _radar_units(group: TheaterGroup) -> list[TheaterUnit]:
    return [
        u
        for u in group.units
        if u.alive
        and not u.is_static
        and u.unit_type is not None
        and u.unit_type.unit_class in RADAR_CLASSES
    ]


Route = list[tuple[float, float]]


def _segment_distance(
    p: tuple[float, float], a: tuple[float, float], b: tuple[float, float]
) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = dx * dx + dy * dy
    t = 0.0
    if length > 0:
        t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / length))
    cx, cy = a[0] + t * dx, a[1] + t * dy
    return float(((p[0] - cx) ** 2 + (p[1] - cy) ** 2) ** 0.5)


def covers_route(
    position: tuple[float, float], reach_m: float, routes: list[Route]
) -> bool:
    """Whether a radar's threat ring touches any leg (or lone point) of a route."""
    for route in routes:
        legs = list(zip(route, route[1:])) or [(route[0], route[0])]
        if any(_segment_distance(position, a, b) <= reach_m for a, b in legs):
            return True
    return False


def player_routes(mission_data: MissionData) -> list[Route]:
    """Every player-package flight's route, and each package's target."""
    routes: list[Route] = []
    for flights in player_packages(mission_data):
        for flight in flights:
            route = [(w.x, w.y) for w in flight.waypoints]
            if route:
                routes.append(route)
        target = flights[0].package.target.position
        routes.append([(target.x, target.y)])
    return routes


def vacuum_flights(mission_data: MissionData) -> list[FlightData]:
    return [
        f
        for f in mission_data.flights
        if f.flight_type is FlightType.ELINT and f.friendly.is_blue
    ]


def populate_vacuum_lua(root: LuaData, game: Game, mission_data: MissionData) -> None:
    """Build ``dcsRetribution.vacuum``: Vacuum's groups, its frequency and the radars."""
    flights = vacuum_flights(mission_data)
    frequency = mission_data.vacuum_frequency
    if not flights or frequency is None:
        return
    node = root.add_item("vacuum")
    node.add_key_value("callsign", CALLSIGN)
    node.add_key_value("frequency", f"{frequency.mhz:.3f}{frequency.modulation.name}")
    if (strike := mission_data.strike_frequency) is not None:
        node.add_key_value("strike", f"{strike.mhz:.3f}{strike.modulation.name}")
    node.add_key_value(
        "voice",
        pick_another_voice(_country(flights[0]), mission_data.skyeye_voices),
    )
    node.add_key_value("linkHost", SKYEYE_LINK_HOST)
    node.add_key_value("linkPort", str(SKYEYE_LINK_PORT))
    node.add_key_value("rangeMeters", str(int(VACUUM_RANGE_NM * 1852)))
    node.add_data_array("groups", [f.group_name for f in flights])

    # The player flights that may call Vacuum, with their package's target.
    callers = node.add_item("flights")
    for package_flights in player_packages(mission_data):
        target = package_flights[0].package.target.position
        for flight in package_flights:
            if not flight.client_units:
                continue
            record = callers.add_item()
            record.add_key_value("group", flight.group_name)
            record.add_key_value("callsign", lead_callsign(flight))
            record.add_key_value("targetX", str(target.x))
            record.add_key_value("targetY", str(target.y))

    routes = player_routes(mission_data)
    emitters = node.add_item("emitters")
    for control_point in game.theater.controlpoints:
        if not control_point.captured.is_red:
            continue
        for tgo in control_point.ground_objects:
            if isinstance(tgo, NavalGroundObject):
                continue
            known, known_error = known_fix(tgo)
            for group in tgo.groups:
                radars = _radar_units(group)
                if not radars:
                    continue
                main = site_radar(radars)
                reach = group.max_threat_range().meters
                label = emitter_label(main)
                item = emitters.add_item()
                item.add_key_value("label", label)
                # Every radar is listened to (its fix reveals the site), only SAMs spoken of.
                item.add_key_value("sam", "true" if speaks_of(tgo, main, label) else "")
                item.add_data_array("units", [u.unit_name for u in radars])
                position = (group.position.x, group.position.y)
                covers = reach > 0 and covers_route(position, reach, routes)
                item.add_key_value("strike", "true" if covers else "")
                item.add_key_value("reach", str(int(reach)))
                item.add_key_value("known", known)
                if known_error is not None:
                    item.add_key_value("knownError", str(int(known_error)))
