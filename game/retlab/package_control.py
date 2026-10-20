"""Airborne package control (§117): a C-130J-30 runs the player packages.

A ABCCC flight (an EC-130 ABCCC role) orbits behind the front. While it is
alive and airborne the ``pkgcontrol`` plugin runs every blue package with a player
seat on STRIKE (common), one frequency for every package: the check-in reply, the
push call, a hold or abort before the push, and the egress call. The AWACS joins
STRIKE as the second voice for the picture and intercepts. SkyEye speaks for both
over a local UDP link, in opposite voices; every call is also text. With no
controller airborne there is no package control, and the AWACS never stands in. This module builds ``dcsRetribution.packageControl``.
docs/dev/retlab-features.md §117.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from game.ato.flighttype import FlightType
from game.ato.flightwaypointtype import FlightWaypointType

if TYPE_CHECKING:
    from game import Game
    from game.ato.airtaaskingorder import AirTaskingOrder
    from game.missiongenerator.aircraft.flightdata import FlightData
    from game.missiongenerator.luagenerator import LuaData
    from game.missiongenerator.missiondata import MissionData

#: SkyEye's mission-link-address. The plugin sends to it from an ephemeral port.
SKYEYE_LINK_HOST = "127.0.0.1"
SKYEYE_LINK_PORT = 42690

#: SkyEye's two voices. The AWACS takes one at random each mission and the package
#: controller the other, so the two are never the same voice (user call, 2026-10-20).
VOICES = ("feminine", "masculine")


def other_voice(voice: str) -> str:
    return VOICES[1] if voice == VOICES[0] else VOICES[0]


def has_package_control(ato: AirTaskingOrder) -> bool:
    """Whether the ATO fields a ABCCC flight."""
    return any(
        flight.flight_type is FlightType.ABCCC
        for package in ato.packages
        for flight in package.flights
    )


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


def _hold(flight: FlightData) -> Optional[tuple[float, float, int, int]]:
    """The HOLD point, its angels, and its 1-based DCS route index."""
    for index, waypoint in enumerate(flight.waypoints):
        if waypoint.waypoint_type is FlightWaypointType.LOITER:
            angels = int(round(waypoint.alt.feet / 1000))
            return waypoint.x, waypoint.y, angels, index + 1
    return None


def player_packages(mission_data: MissionData) -> list[list[FlightData]]:
    """Blue packages with at least one player seat, flights in package order."""
    return [
        flights
        for flights in mission_data.packages.values()
        if flights
        and flights[0].friendly.is_blue
        and any(f.client_units for f in flights)
        and not any(f.flight_type is FlightType.ABCCC for f in flights)
    ]


def abccc_callsign(mission_data: MissionData) -> str:
    """The first blue ABCCC's spoken callsign."""
    controllers = package_controllers(mission_data)
    return spoken_callsign(controllers[0].callsign) if controllers else "ABCCC"


def strike_comm_name(mission_data: MissionData) -> Optional[str]:
    """The kneeboard comm line for STRIKE (common), or None without a controller."""
    controllers = package_controllers(mission_data)
    if mission_data.strike_frequency is None or not controllers:
        return None
    return f"STRIKE ({spoken_callsign(controllers[0].callsign)})"


def package_controllers(mission_data: MissionData) -> list[FlightData]:
    """The blue ABCCC flights."""
    return [
        f
        for f in mission_data.flights
        if f.flight_type is FlightType.ABCCC and f.friendly.is_blue
    ]


def populate_package_control_lua(
    root: LuaData, game: Game, mission_data: MissionData
) -> None:
    """Build ``dcsRetribution.packageControl``; nothing without a controller."""
    controllers = package_controllers(mission_data)
    packages = player_packages(mission_data)
    strike = mission_data.strike_frequency
    if not controllers or not packages or strike is None:
        return

    start = mission_data.flights[0].mission_start if mission_data.flights else None
    start = start or game.conditions.start_time
    node = root.add_item("packageControl")
    node.add_key_value(
        "startSeconds", str(start.hour * 3600 + start.minute * 60 + start.second)
    )
    node.add_key_value("linkHost", SKYEYE_LINK_HOST)
    node.add_key_value("linkPort", str(SKYEYE_LINK_PORT))
    node.add_key_value("strikeFreq", f"{strike.mhz:.3f}")
    node.add_key_value("strikeModulation", strike.modulation.name)
    node.add_key_value("awacsVoice", mission_data.awacs_voice)
    node.add_key_value("controllerVoice", other_voice(mission_data.awacs_voice))

    controllers_node = node.add_item("controllers")
    for controller in controllers:
        item = controllers_node.add_item()
        item.add_key_value("group", controller.group_name)
        item.add_key_value("callsign", spoken_callsign(controller.callsign))

    packages_node = node.add_item("packages")
    for flights in packages:
        package = flights[0].package
        clock = _Clock(start)
        lead = next(f for f in flights if f.client_units)
        item = packages_node.add_item()
        item.add_key_value("name", spoken_callsign(lead.callsign))
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
                record.add_key_value("holdIndex", str(hold[3]))
            record.add_key_value("home", flight.arrival.airfield_name)
            if role == "strike":
                targets.extend(n for n in _target_units(flight) if n not in targets)
        item.add_data_array("targetUnits", targets)
