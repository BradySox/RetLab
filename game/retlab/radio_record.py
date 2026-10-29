"""Record radios for Tacview (§127): SkyEye records the voice bots' frequencies.

With the setting on, the ``radiorecord`` plugin asks SkyEye over its mission link to
record the AWACS, STRIKE, Vacuum and each player field's Ground, Tower and Approach, plus each
player flight's own frequency. SkyEye writes one WAV per frequency next to the Tacview
recordings, named with the mission time it starts at, so Tacview plays it with the
replay. A flight's own frequency is record-only: SkyEye never answers there (user
call, 2026-10-29). docs/dev/retlab-features.md §127.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from game.retlab.package_control import SKYEYE_LINK_HOST, SKYEYE_LINK_PORT
from game.retlab.voice_atc import frequency_text, station_name, voice_atc_plan

if TYPE_CHECKING:
    from game import Game
    from game.missiongenerator.luagenerator import LuaData
    from game.missiongenerator.missiondata import MissionData
    from game.radio.radios import RadioFrequency


@dataclass(frozen=True)
class RecordedFrequency:
    frequency: RadioFrequency
    label: str
    record_only: bool = False


def recorded_frequencies(
    game: Game, mission_data: MissionData
) -> list[RecordedFrequency]:
    """The frequencies to record, each once: the bots first, then the player flights."""
    if not game.settings.record_radios_for_tacview:
        return []
    found: list[RecordedFrequency] = []

    def add(frequency: RadioFrequency | None, label: str, record_only: bool) -> None:
        if frequency is None or any(f.frequency == frequency for f in found):
            return
        found.append(RecordedFrequency(frequency, label, record_only))

    add(mission_data.skyeye_frequency, "AWACS", False)
    add(mission_data.strike_frequency, "STRIKE", False)
    add(mission_data.vacuum_frequency, "Vacuum", False)
    if (plan := voice_atc_plan(game, mission_data)) is not None:
        for atc_field in plan.fields.values():
            add(atc_field.ground, station_name(atc_field.name, "Ground"), False)
            add(atc_field.tower, station_name(atc_field.name, "Tower"), False)
            add(atc_field.approach, station_name(atc_field.name, "Approach"), False)
    for flight in mission_data.flights:
        if flight.client_units and flight.friendly.is_blue:
            add(flight.intra_flight_channel, flight.callsign, True)
    return found


def populate_radio_record_lua(
    root: LuaData, game: Game, mission_data: MissionData
) -> None:
    """Build ``dcsRetribution.radioRecord``."""
    frequencies = recorded_frequencies(game, mission_data)
    if not frequencies:
        return
    node = root.add_item("radioRecord")
    node.add_key_value("linkHost", SKYEYE_LINK_HOST)
    node.add_key_value("linkPort", str(SKYEYE_LINK_PORT))
    items = node.add_item("frequencies")
    for recorded in frequencies:
        item = items.add_item()
        item.add_key_value("frequency", frequency_text(recorded.frequency))
        item.add_key_value("label", recorded.label)
        item.add_key_value("recordOnly", "true" if recorded.record_only else "")
