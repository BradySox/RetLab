"""AWACS package controller (§117): the blue AWACS talks to player packages on SRS.

The ``pkgcontrol`` plugin speaks the calls at runtime through SRS's External Audio
program (MOOSE MSRS, Windows voice): a check-in reply from the F10 menu, the push
call, a hold or abort before the push, and the egress call. This module builds its
data, ``dcsRetribution.packageControl``. docs/dev/retlab-features.md §117.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from game.ato.flighttype import FlightType
from game.ato.flightwaypointtype import FlightWaypointType

if TYPE_CHECKING:
    from game import Game
    from game.missiongenerator.aircraft.flightdata import FlightData
    from game.missiongenerator.luagenerator import LuaData
    from game.missiongenerator.missiondata import MissionData

SRS_PORT = 5002
#: User call (2026-10-20): a male US voice, unlike SkyEye's female one.
VOICE_GENDER = "male"
VOICE_CULTURE = "en-US"

SEAD_TASKS = frozenset({FlightType.SEAD, FlightType.SEAD_ESCORT, FlightType.SEAD_SWEEP})
ESCORT_TASKS = frozenset({FlightType.ESCORT, FlightType.TARCAP, FlightType.SWEEP})
TARGET_WAYPOINTS = frozenset(
    {FlightWaypointType.TARGET_POINT, FlightWaypointType.TARGET_GROUP_LOC}
)


def role_for(flight_type: FlightType) -> str:
    if flight_type in SEAD_TASKS:
        return "sead"
    if flight_type in ESCORT_TASKS:
        return "escort"
    return "strike"


def spoken_callsign(callsign: str) -> str:
    """``"Darkstar1-1"`` or ``"Darkstar 1"`` -> ``"Darkstar"``: what a controller says."""
    word = callsign.split()[0] if callsign.split() else callsign
    return word.rstrip("0123456789-") or callsign


@dataclass(frozen=True)
class _Clock:
    start: datetime

    def seconds(self, when: Optional[datetime]) -> Optional[int]:
        if when is None:
            return None
        return max(0, int((when - self.start).total_seconds()))


def _target_units(flight: FlightData) -> list[str]:
    names: list[str] = []
    for waypoint in flight.waypoints:
        if waypoint.waypoint_type in TARGET_WAYPOINTS:
            names.extend(u.unit_name for u in waypoint.targets if u.alive)
    return names


def _hold(flight: FlightData) -> Optional[tuple[float, float, int]]:
    for waypoint in flight.waypoints:
        if waypoint.waypoint_type is FlightWaypointType.LOITER:
            return waypoint.x, waypoint.y, int(round(waypoint.alt.feet / 1000))
    return None


def player_packages(mission_data: MissionData) -> list[list[FlightData]]:
    """Blue packages with at least one player seat, flights in package order."""
    return [
        flights
        for flights in mission_data.packages.values()
        if flights
        and flights[0].friendly.is_blue
        and any(f.client_units for f in flights)
    ]


def populate_package_control_lua(
    root: LuaData, game: Game, mission_data: MissionData
) -> None:
    """Build ``dcsRetribution.packageControl``; nothing when off or no player package."""
    if not game.settings.package_controller:
        return
    awacs = [a for a in mission_data.awacs if a.blue.is_blue]
    packages = player_packages(mission_data)
    if not awacs or not packages:
        return

    start = mission_data.flights[0].mission_start if mission_data.flights else None
    start = start or game.conditions.start_time
    node = root.add_item("packageControl")
    node.add_key_value(
        "startSeconds", str(start.hour * 3600 + start.minute * 60 + start.second)
    )
    node.add_key_value("srsPath", game.settings.package_controller_srs_path)
    node.add_key_value("port", str(SRS_PORT))
    node.add_key_value("gender", VOICE_GENDER)
    node.add_key_value("culture", VOICE_CULTURE)

    awacs_node = node.add_item("awacs")
    for info in awacs:
        item = awacs_node.add_item()
        item.add_key_value("group", info.group_name)
        item.add_key_value("callsign", spoken_callsign(info.callsign))

    packages_node = node.add_item("packages")
    for flights in packages:
        package = flights[0].package
        if package.frequency is None:
            continue
        clock = _Clock(start)
        lead = next(f for f in flights if f.client_units)
        item = packages_node.add_item()
        item.add_key_value("name", spoken_callsign(lead.callsign))
        item.add_key_value("freq", f"{package.frequency.mhz:.3f}")
        item.add_key_value("modulation", package.frequency.modulation.name)
        tot = clock.seconds(package.time_over_target)
        item.add_key_value("totAfter", str(tot if tot is not None else ""))
        item.add_key_value("targetName", package.target.name)
        item.add_key_value("targetX", str(package.target.position.x))
        item.add_key_value("targetY", str(package.target.position.y))
        targets: list[str] = []
        flights_node = item.add_item("flights")
        for flight in flights:
            role = role_for(flight.flight_type)
            record = flights_node.add_item()
            record.add_key_value("group", flight.group_name)
            record.add_key_value("callsign", flight.callsign)
            record.add_key_value("role", role)
            record.add_key_value("client", "true" if flight.client_units else "")
            push = clock.seconds(flight.push_time)
            record.add_key_value("pushAfter", str(push if push is not None else ""))
            if (hold := _hold(flight)) is not None:
                record.add_key_value("holdX", str(hold[0]))
                record.add_key_value("holdY", str(hold[1]))
                record.add_key_value("holdAngels", str(hold[2]))
            if role == "strike":
                targets.extend(n for n in _target_units(flight) if n not in targets)
        item.add_data_array("targetUnits", targets)
