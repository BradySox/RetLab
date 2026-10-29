"""Voice ATC (§119): Ground and Tower for player flights, through SkyEye.

Every airfield a player flight takes off from or lands at gets new Ground and Tower
frequencies, never the field's DCS tower frequency: DCS's own ATC on it keeps telling a
player who taxis without its permission to hold position (user call, 2026-10-20). No
squawk codes: ATC never gives or checks one (user call, 2026-10-22).
The ``voiceatc`` plugin decides every reply in the mission; SkyEye hears the calls and
speaks the replies over its mission link. AI-only fields keep DCS's own ATC.
docs/dev/retlab-features.md §119.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from game.retlab.atc_routes import FieldRoutes, chart_routes, point_lines
from game.retlab.package_control import (
    SKYEYE_LINK_HOST,
    SKYEYE_LINK_PORT,
    lead_callsign,
)
from game.retlab.skyeye_voices import pick_another_voice
from game.theater.controlpoint import Airfield

if TYPE_CHECKING:
    from game import Game
    from game.ato.airtaaskingorder import AirTaskingOrder
    from game.missiongenerator.aircraft.flightdata import FlightData
    from game.missiongenerator.luagenerator import LuaData
    from game.missiongenerator.missiondata import MissionData
    from game.radio.radios import RadioFrequency, RadioRegistry


def player_airfields(ato: AirTaskingOrder) -> list[Airfield]:
    """Airfields a player flight takes off from, lands at or diverts to, in ATO order."""
    fields: list[Airfield] = []
    for package in ato.packages:
        for flight in package.flights:
            if not flight.client_count:
                continue
            for cp in (flight.departure, flight.arrival, flight.divert):
                if isinstance(cp, Airfield) and cp not in fields:
                    fields.append(cp)
    return fields


def allocate_atc_frequencies(
    game: Game, registry: RadioRegistry, mission_data: MissionData
) -> None:
    """UHF Ground, Tower and Approach frequencies for each player airfield, reserved
    like STRIKE. Approach also works departures (user call, 2026-10-29).

    UHF because the F-4E, the F-5E and a Tomcat pilot without a RIO have no VHF
    radio (user call, 2026-10-21). A field keeps its pair for the whole campaign
    (``Game.voice_atc_frequencies``), so a pilot can learn it. Every pinned pair is
    reserved first, used this turn or not, so a new field never takes another
    field's frequency.
    """
    if not game.settings.voice_atc:
        return
    pinned = game.voice_atc_frequencies
    # A pair pinned while Ground and Tower were VHF AM (#1340) is picked again.
    for name in [n for n, pair in pinned.items() if not all(is_uhf(f) for f in pair)]:
        del pinned[name]
    approaches = game.voice_atc_approach_frequencies
    for name in [n for n, f in approaches.items() if not is_uhf(f)]:
        del approaches[name]
    for name, pair in pinned.items():
        frequencies = list(pair)
        if name in approaches:
            frequencies.append(approaches[name])
        for frequency in frequencies:
            if frequency in registry.allocated_channels:
                logging.warning(
                    "Voice ATC: %s's pinned %s is also a map frequency; keeping it",
                    name,
                    frequency,
                )
            else:
                registry.reserve(frequency)
            registry.atc_pinned.add(frequency)
    for airfield in player_airfields(game.blue.ato):
        name = airfield.airport.name
        if name not in pinned:
            pinned[name] = (registry.alloc_uhf(), registry.alloc_uhf())
            registry.atc_pinned.update(pinned[name])
        if name not in approaches:
            approaches[name] = registry.alloc_uhf()
            registry.atc_pinned.add(approaches[name])
        mission_data.atc_frequencies[name] = pinned[name]
        mission_data.approach_frequencies[name] = approaches[name]


def is_uhf(frequency: RadioFrequency) -> bool:
    return frequency.band == "UHF"


def frequency_text(frequency: RadioFrequency) -> str:
    """``262.000AM``: the string SkyEye prints a frequency as."""
    return f"{frequency.mhz:.3f}{frequency.modulation.name}"


def station_name(field_name: str, position: str) -> str:
    """``Tel Nof Ground``: a field position as the comm card, the ATC card and ATC say it."""
    return f"{field_name} {position.capitalize()}"


def approach_name(field_name: str) -> str:
    """``Kobuleti Approach/Departure``: one frequency works both (user call, 2026-10-29)."""
    return f"{field_name} Approach/Departure"


def preset_name(flight: FlightData, frequency: RadioFrequency) -> Optional[str]:
    """``COMM2 Ch 2``: the preset a frequency sits on in this flight's jets, if any."""
    channels = flight.channels_for(frequency)
    if not channels:
        return None
    first = channels[0]
    return flight.aircraft_type.channel_name(first.radio_id, first.channel)


def _preset(flight: FlightData, frequency: RadioFrequency) -> str:
    """``124.300 (COMM2 Ch 2)``: a frequency and the preset it sits on, if any."""
    label = f"{frequency.mhz:.3f}"
    name = preset_name(flight, frequency)
    return f"{label} ({name})" if name else label


def atc_lines(flight: FlightData, atc_field: AtcField) -> str:
    """The Ground, Tower and Approach lines an airfield's ATC box shows under Voice ATC."""
    lines = (
        f"GND {_preset(flight, atc_field.ground)}\n"
        f"TWR {_preset(flight, atc_field.tower)}"
    )
    if atc_field.approach is not None:
        lines += f"\nAPP/DEP {_preset(flight, atc_field.approach)}"
    return lines


def runway_ends(game: Game, airfield_name: str) -> list[str]:
    """``["10R", "28L", "10L", "28R"]``: each runway's two ends, in pairs."""
    terrain = getattr(getattr(game, "theater", None), "terrain", None)
    airport = getattr(terrain, "airports", {}).get(airfield_name) if terrain else None
    ends: list[str] = []
    for runway in getattr(airport, "runways", []):
        ends.extend([runway.main.name, runway.opposite.name])
    return ends


@dataclass
class AtcField:
    name: str
    runway: str
    tower: RadioFrequency
    ground: RadioFrequency
    #: Approach, which also works departures (step 2); None on a save from before it.
    approach: Optional[RadioFrequency] = None
    ground_voice: str = ""
    tower_voice: str = ""
    approach_voice: str = ""
    #: The chart's entry and exit points; None where the map has no chart, and the
    #: plugin generates the route.
    routes: Optional[FieldRoutes] = None
    #: The ATC card's row for each chart point.
    route_lines: list[str] = field(default_factory=list)
    #: Every runway end at the field, in pairs ("10R", "28L", ...), for the plugin to
    #: switch to the one DCS's AI is using.
    runways: list[str] = field(default_factory=list)


@dataclass
class AtcFlight:
    group: str
    callsign: str
    departure: Optional[str]
    arrival: Optional[str]
    divert: Optional[str] = None


@dataclass
class VoiceAtcPlan:
    fields: dict[str, AtcField] = field(default_factory=dict)
    flights: list[AtcFlight] = field(default_factory=list)

    def flight(self, group: str) -> Optional[AtcFlight]:
        return next((f for f in self.flights if f.group == group), None)


def voice_atc_plan(game: Game, mission_data: MissionData) -> Optional[VoiceAtcPlan]:
    """The fields and player flights ATC runs, built once per mission."""
    if not game.settings.voice_atc or not mission_data.atc_frequencies:
        return None
    if mission_data.voice_atc is not None:
        return mission_data.voice_atc
    plan = VoiceAtcPlan()
    for flight in mission_data.flights:
        if not (flight.client_units and flight.friendly.is_blue):
            continue
        names: list[Optional[str]] = []
        for runway in (flight.departure, flight.arrival, flight.divert):
            if runway is None:
                names.append(None)
                continue
            frequencies = mission_data.atc_frequencies.get(runway.airfield_name)
            if frequencies is None:
                names.append(None)
                continue
            ground, tower = frequencies
            names.append(runway.airfield_name)
            plan.fields.setdefault(
                runway.airfield_name,
                AtcField(
                    runway.airfield_name,
                    runway.runway_name,
                    tower,
                    ground,
                    approach=mission_data.approach_frequencies.get(
                        runway.airfield_name
                    ),
                    runways=runway_ends(game, runway.airfield_name),
                    routes=_routes(game, runway.airfield_name),
                ),
            )
        if not any(names):
            continue
        plan.flights.append(
            AtcFlight(
                flight.group_name,
                lead_callsign(flight),
                names[0],
                names[1],
                names[2],
            )
        )
    country = game.blue.faction.country.name
    taken = list(mission_data.skyeye_voices)
    for atc_field in plan.fields.values():
        atc_field.ground_voice = pick_another_voice(country, taken)
        taken.append(atc_field.ground_voice)
        atc_field.tower_voice = pick_another_voice(country, taken)
        taken.append(atc_field.tower_voice)
        if atc_field.approach is not None:
            atc_field.approach_voice = pick_another_voice(country, taken)
            taken.append(atc_field.approach_voice)
        atc_field.route_lines = _route_lines(game, atc_field)
    mission_data.voice_atc = plan
    return plan


def _routes(game: Game, airfield_name: str) -> Optional[FieldRoutes]:
    terrain = getattr(getattr(game, "theater", None), "terrain", None)
    return chart_routes(terrain, airfield_name) if terrain is not None else None


def _route_lines(game: Game, atc_field: AtcField) -> list[str]:
    terrain = getattr(getattr(game, "theater", None), "terrain", None)
    airport = getattr(terrain, "airports", {}).get(atc_field.name) if terrain else None
    if atc_field.routes is None or airport is None:
        return []
    return point_lines(atc_field.routes, airport.position)


def populate_voice_atc_lua(
    root: LuaData, game: Game, mission_data: MissionData
) -> None:
    """Build ``dcsRetribution.voiceAtc``."""
    plan = voice_atc_plan(game, mission_data)
    if plan is None or not plan.flights:
        return
    node = root.add_item("voiceAtc")
    node.add_key_value("linkHost", SKYEYE_LINK_HOST)
    node.add_key_value("linkPort", str(SKYEYE_LINK_PORT))
    altimeter = game.conditions.weather.atmospheric.qnh.inches_hg
    fields_node = node.add_item("fields")
    for atc_field in plan.fields.values():
        item = fields_node.add_item()
        item.add_key_value("name", atc_field.name)
        item.add_key_value("airbase", atc_field.name)
        item.add_key_value("runway", atc_field.runway)
        item.add_key_value("runways", ",".join(atc_field.runways))
        item.add_key_value("altimeter", f"{altimeter:.2f}")
        item.add_key_value("ground", frequency_text(atc_field.ground))
        item.add_key_value("tower", frequency_text(atc_field.tower))
        item.add_key_value("groundVoice", atc_field.ground_voice)
        item.add_key_value("towerVoice", atc_field.tower_voice)
        if atc_field.approach is not None:
            item.add_key_value("approach", frequency_text(atc_field.approach))
            item.add_key_value("approachVoice", atc_field.approach_voice)
        if (routes := atc_field.routes) is not None:
            item.add_key_value("chart", routes.chart)
            item.add_key_value("maxAltitude", str(routes.max_altitude_ft))
            item.add_key_value("patternAltitude", str(routes.pattern_ft))
            points_node = item.add_item("points")
            for point in routes.points:
                record = points_node.add_item()
                record.add_key_value("name", point.name)
                record.add_key_value("x", str(round(point.position.x)))
                record.add_key_value("z", str(round(point.position.y)))
                record.add_key_value("entry", ",".join(point.entry_runways))
                record.add_key_value("exit", "true" if point.exit else "")
    flights_node = node.add_item("flights")
    for flight in plan.flights:
        item = flights_node.add_item()
        item.add_key_value("group", flight.group)
        item.add_key_value("callsign", flight.callsign)
        item.add_key_value("departure", flight.departure or "")
        item.add_key_value("arrival", flight.arrival or "")
        item.add_key_value("divert", flight.divert or "")
