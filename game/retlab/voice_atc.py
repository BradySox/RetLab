"""Voice ATC (§119): Ground and Tower for player flights, through SkyEye.

Every airfield a player flight takes off from or lands at gets new Ground and Tower
frequencies, never the field's DCS tower frequency: DCS's own ATC on it keeps telling a
player who taxis without its permission to hold position (user call, 2026-10-20). Each
player flight gets a squawk code.
The ``voiceatc`` plugin decides every reply in the mission; SkyEye hears the calls and
speaks the replies over its mission link. AI-only fields keep DCS's own ATC.
docs/dev/retlab-features.md §119.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterator, Optional

from game.retlab.package_control import SKYEYE_LINK_HOST, SKYEYE_LINK_PORT
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
    """VHF AM Ground and Tower frequencies for each player airfield, reserved like STRIKE.

    A field keeps its pair for the whole campaign (``Game.voice_atc_frequencies``), so a
    pilot can learn it. Every pinned pair is reserved first, used this turn or not, so a
    new field never takes another field's frequency.
    """
    if not game.settings.voice_atc:
        return
    pinned = game.voice_atc_frequencies
    for name, pair in pinned.items():
        for frequency in pair:
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
            pinned[name] = (registry.alloc_vhf(), registry.alloc_vhf())
            registry.atc_pinned.update(pinned[name])
        mission_data.atc_frequencies[name] = pinned[name]


def squawk_codes() -> Iterator[str]:
    """Four-digit transponder codes, digits 0 to 7 only: 4101, 4102 ... 4177, 4201 ..."""
    for n in range(0o4101, 0o7400):
        code = f"{n:o}"
        if not code.endswith("00"):
            yield code


def frequency_text(frequency: RadioFrequency) -> str:
    """``262.000AM``: the string SkyEye prints a frequency as."""
    return f"{frequency.mhz:.3f}{frequency.modulation.name}"


def lead_callsign(flight: FlightData) -> str:
    """``"Viper 1"`` -> ``"Viper 1-1"``: the lead's callsign, which ATC answers to."""
    if re.fullmatch(r"\D+ \d+", flight.callsign):
        return f"{flight.callsign}-1"
    return flight.callsign


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
    """The Ground and Tower lines an airfield's ATC box shows under Voice ATC."""
    return (
        f"GND {_preset(flight, atc_field.ground)}\n"
        f"TWR {_preset(flight, atc_field.tower)}"
    )


@dataclass
class AtcField:
    name: str
    runway: str
    tower: RadioFrequency
    ground: RadioFrequency
    ground_voice: str = ""
    tower_voice: str = ""


@dataclass
class AtcFlight:
    group: str
    callsign: str
    squawk: str
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
    codes = squawk_codes()
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
                AtcField(runway.airfield_name, runway.runway_name, tower, ground),
            )
        if not any(names):
            continue
        plan.flights.append(
            AtcFlight(
                flight.group_name,
                lead_callsign(flight),
                next(codes),
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
    mission_data.voice_atc = plan
    return plan


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
        item.add_key_value("altimeter", f"{altimeter:.2f}")
        item.add_key_value("ground", frequency_text(atc_field.ground))
        item.add_key_value("tower", frequency_text(atc_field.tower))
        item.add_key_value("groundVoice", atc_field.ground_voice)
        item.add_key_value("towerVoice", atc_field.tower_voice)
    flights_node = node.add_item("flights")
    for flight in plan.flights:
        item = flights_node.add_item()
        item.add_key_value("group", flight.group)
        item.add_key_value("callsign", flight.callsign)
        item.add_key_value("squawk", flight.squawk)
        item.add_key_value("departure", flight.departure or "")
        item.add_key_value("arrival", flight.arrival or "")
        item.add_key_value("divert", flight.divert or "")
