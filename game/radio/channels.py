from __future__ import annotations

import logging

from dataclasses import dataclass
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from game.missiongenerator.aircraft.flightdata import FlightData
    from game.missiongenerator.missiondata import MissionData
    from game.radio.radios import RadioFrequency
    from game.runways import RunwayData


def tunable_atc(
    flight: FlightData, runway: Optional[RunwayData]
) -> Optional[RadioFrequency]:
    """The tower frequency the flight's radio can tune, UHF first, else VHF, else None."""
    if runway is None:
        return None
    radio = flight.aircraft_type.intra_flight_radio
    for freq in (runway.atc, runway.atc_vhf):
        if freq is None:
            continue
        if radio is None or any(
            r.minimum.hertz <= freq.hertz < r.maximum.hertz for r in radio.ranges
        ):
            return freq
    return None


def awacs_presets(
    flight: FlightData, mission_data: MissionData
) -> list[RadioFrequency]:
    """The flight's own side's AWACS frequencies worth a preset; the enemy's never
    (they showed as unnamed rows on the comm card). With SkyEye on, the blue AI
    AWACS are silent (§116), so a blue flight gets SkyEye, then Vacuum (§118)."""
    own = [a.freq for a in mission_data.awacs if a.blue == flight.friendly]
    if mission_data.skyeye_frequency is None or not flight.friendly.is_blue:
        return own
    frequencies = [mission_data.skyeye_frequency]
    if mission_data.vacuum_frequency is not None:
        frequencies.append(mission_data.vacuum_frequency)
    return frequencies


def _voice_atc(airfield_name: str, mission_data: MissionData) -> list[RadioFrequency]:
    """A Voice ATC field's Ground, Tower and Approach (§119); empty for any other."""
    pair = mission_data.atc_frequencies.get(airfield_name)
    if pair is None:
        return []
    frequencies = list(pair)
    if (approach := mission_data.approach_frequencies.get(airfield_name)) is not None:
        frequencies.append(approach)
    return frequencies


def _tunable(radio: Any, freq: RadioFrequency) -> bool:
    return radio is None or any(
        r.minimum.hertz <= freq.hertz < r.maximum.hertz for r in radio.ranges
    )


def friendly_jtacs(
    flight: FlightData, mission_data: MissionData
) -> list[RadioFrequency]:
    """The flight's own side's JTACs; a red JTAC was a blue preset (2026-10-21)."""
    return [j.freq for j in mission_data.jtacs if j.blue == flight.friendly]


def friendly_tankers(
    flight: FlightData, mission_data: MissionData
) -> list[RadioFrequency]:
    """Own-side tankers this flight can take fuel from (boom vs probe). A red KC-135
    was COM1 Ch 5 in a blue F-16 (2026-10-21). can_refuel_from is permissive for
    untagged airframes, so one with no refueling method still gets every tanker."""
    return [
        tanker.freq
        for tanker in mission_data.tankers
        if tanker.blue == flight.friendly
        and flight.aircraft_type.can_refuel_from(tanker.aircraft_type)
    ]


def _fill_unused(flight: FlightData, radio_id: int) -> None:
    """Point every preset left over at the radio's Ch 1. The module's own default
    fillers (121, 126, 128 MHz...) landed players on AI chatter (2026-10-20).
    Not recorded as an assignment, so the comm card leaves those rows blank."""
    used: dict[int, RadioFrequency] = {}
    for freq, assignments in flight.frequency_to_channel_map.items():
        for a in assignments:
            if a.radio_id == radio_id:
                used[a.channel] = freq
    if 1 not in used:
        return
    for channel in range(1, flight.num_radio_channels(radio_id) + 1):
        if channel not in used:
            for unit in flight.client_units:
                unit.set_radio_channel_preset(radio_id, channel, used[1].mhz)


class RadioChannelAllocator:
    """Base class for radio channel allocators."""

    def assign_channels_for_flight(
        self, flight: FlightData, mission_data: MissionData
    ) -> None:
        """Assigns mission frequencies to preset channels for the flight."""
        raise NotImplementedError

    @classmethod
    def from_cfg(cls, cfg: dict[str, Any]) -> RadioChannelAllocator:
        return cls()

    @classmethod
    def name(cls) -> str:
        raise NotImplementedError


@dataclass(frozen=True)
class CommonRadioChannelAllocator(RadioChannelAllocator):
    """Radio channel allocator suitable for most aircraft.

    Most of the aircraft with preset channels available have one or more radios
    with 20 or more channels available (typically per-radio, but this is not the
    case for the JF-17).
    """

    #: Index of the radio used for intra-flight communications. Matches the
    #: index of the panel_radio field of the pydcs.dcs.planes object.
    inter_flight_radio_index: Optional[int]

    #: Index of the radio used for intra-flight communications. Matches the
    #: index of the panel_radio field of the pydcs.dcs.planes object.
    intra_flight_radio_index: Optional[int]

    def assign_channels_for_flight(
        self, flight: FlightData, mission_data: MissionData
    ) -> None:
        if flight.client_units and flight.squadron.radio_presets:
            return self.assign_from_squadron_presets(flight)
        self._assign_presets(flight, mission_data)
        for radio_id in {self.inter_flight_radio_index, self.intra_flight_radio_index}:
            if radio_id is not None:
                _fill_unused(flight, radio_id)

    def _assign_presets(self, flight: FlightData, mission_data: MissionData) -> None:
        if flight.client_units and flight.squadron.radio_presets:
            return self.assign_from_squadron_presets(flight)

        if self.intra_flight_radio_index is not None:
            flight.assign_channel(
                self.intra_flight_radio_index, 1, flight.intra_flight_channel
            )

        if self.inter_flight_radio_index is None:
            return
        radio_id = self.inter_flight_radio_index
        intra = self.intra_flight_radio_index

        # A preset the set cannot tune is a dead channel in the cockpit.
        inter_radio = getattr(flight.aircraft_type, "inter_flight_radio", None)
        if intra is None or intra == radio_id:
            # One set of channels (the JF-17 shares its presets across both radios):
            # one list, after the intra-flight channel.
            frequencies = [
                f
                for f in self._inter_flight_frequencies(flight, mission_data)
                if _tunable(inter_radio, f)
            ]
            first_channel = 2 if intra == radio_id else 1
            self._assign_sequential(flight, radio_id, first_channel, frequencies)
            return

        # Two radios, laid out like a squadron comm card (user call, 2026-10-21):
        # COMM1 the support nets, COMM2 the flight then each field's Ground and
        # Tower, where that radio tunes UHF (an F-16's COM2 is VHF only).
        radio = flight.aircraft_type.intra_flight_radio
        atc = self._atc_frequencies(flight, mission_data)
        on_intra = [f for f in atc if _tunable(radio, f)]
        support = self._support_frequencies(flight, mission_data)
        support.extend(f for f in atc if f not in on_intra)
        support = [f for f in support if _tunable(inter_radio, f)]
        # Ch 1 on both radios is the flight's own frequency (user call, 2026-10-21).
        self._assign_sequential(flight, intra, 2, on_intra)
        first = 1
        if _tunable(inter_radio, flight.intra_flight_channel):
            flight.assign_channel(radio_id, 1, flight.intra_flight_channel)
            first = 2
        self._assign_sequential(flight, radio_id, first, support)

    @staticmethod
    def _atc_frequencies(
        flight: FlightData, mission_data: MissionData
    ) -> list[RadioFrequency]:
        """Departure, arrival and divert ATC: Voice ATC's Ground, Tower and Approach
        (§119), else the field's DCS tower."""
        frequencies: list[RadioFrequency] = []
        fields = [flight.departure, flight.arrival]
        if flight.divert is not None:
            fields.append(flight.divert)
        for field in fields:
            candidates: list[Optional[RadioFrequency]] = list(
                _voice_atc(field.airfield_name, mission_data)
            ) or [field.atc]
            for freq in candidates:
                if freq is not None and freq not in frequencies:
                    frequencies.append(freq)
        return frequencies

    @staticmethod
    def _support_frequencies(
        flight: FlightData, mission_data: MissionData
    ) -> list[RadioFrequency]:
        """AWACS (SkyEye and Vacuum when on), the package (STRIKE with an ABCCC),
        JTACs and the tankers this flight can take fuel from."""
        frequencies = awacs_presets(flight, mission_data)
        if (freq := mission_data.package_frequency(flight.package)) is not None:
            frequencies.append(freq)
        frequencies.extend(friendly_jtacs(flight, mission_data))
        frequencies.extend(friendly_tankers(flight, mission_data))
        return frequencies

    @staticmethod
    def _inter_flight_frequencies(
        flight: FlightData, mission_data: MissionData
    ) -> list[RadioFrequency]:
        frequencies: list[RadioFrequency] = []
        # Voice ATC (§119) replaces a field's DCS tower with its Ground, Tower and Approach.
        if departure_atc := _voice_atc(flight.departure.airfield_name, mission_data):
            frequencies.extend(departure_atc)
        elif flight.departure.atc is not None:
            frequencies.append(flight.departure.atc)
        # TODO: If there ever are multiple AWACS, limit to mission relevant.
        frequencies.extend(awacs_presets(flight, mission_data))
        frequencies.extend(friendly_jtacs(flight, mission_data))
        if (freq := mission_data.package_frequency(flight.package)) is not None:
            frequencies.append(freq)
        if flight.arrival != flight.departure:
            if arrival_atc := _voice_atc(flight.arrival.airfield_name, mission_data):
                frequencies.extend(arrival_atc)
            elif flight.arrival.atc is not None:
                frequencies.append(flight.arrival.atc)
        frequencies.extend(friendly_tankers(flight, mission_data))
        if flight.divert is not None and flight.divert.atc is not None:
            frequencies.append(flight.divert.atc)
        return frequencies

    @staticmethod
    def _assign_sequential(
        flight: FlightData,
        radio_id: int,
        first_channel: int,
        frequencies: list[RadioFrequency],
    ) -> None:
        channels = iter(range(first_channel, flight.num_radio_channels(radio_id) + 1))
        for index, frequency in enumerate(frequencies):
            try:
                flight.assign_channel(radio_id, next(channels), frequency)
            except StopIteration:
                # The rest are nice-to-haves, but say so: a dropped ATC or tanker
                # preset is otherwise only noticed in the cockpit.
                logging.warning(
                    "%s: radio %d is out of presets; left off %s",
                    flight.callsign,
                    radio_id,
                    ", ".join(str(f) for f in frequencies[index:]),
                )
                break

    @classmethod
    def from_cfg(cls, cfg: dict[str, Any]) -> CommonRadioChannelAllocator:
        return CommonRadioChannelAllocator(
            inter_flight_radio_index=cfg["inter_flight_radio_index"],
            intra_flight_radio_index=cfg["intra_flight_radio_index"],
        )

    @classmethod
    def name(cls) -> str:
        return "common"

    def assign_from_squadron_presets(self, flight: FlightData) -> None:
        presets = flight.squadron.radio_presets
        for radio in presets:
            radio_id = 1
            if self.intra_flight_radio_index and radio == "intra_flight":
                radio_id = self.intra_flight_radio_index
            elif self.inter_flight_radio_index and radio == "inter_flight":
                radio_id = self.inter_flight_radio_index
            elif type(radio) == int:
                radio_id = radio
            for channel, freq in enumerate(presets[radio], start=1):
                flight.assign_channel(radio_id, channel, freq)


@dataclass(frozen=True)
class NoOpChannelAllocator(RadioChannelAllocator):
    """Channel allocator for aircraft that don't support preset channels."""

    def assign_channels_for_flight(
        self, flight: FlightData, mission_data: MissionData
    ) -> None:
        pass

    @classmethod
    def name(cls) -> str:
        return "noop"


@dataclass(frozen=True)
class FarmerRadioChannelAllocator(RadioChannelAllocator):
    """Preset channel allocator for the MiG-19P."""

    def assign_channels_for_flight(
        self, flight: FlightData, mission_data: MissionData
    ) -> None:
        # The Farmer only has 6 preset channels. It also only has a VHF radio,
        # and currently our ATC data and AWACS are only in the UHF band.
        radio_id = 1
        flight.assign_channel(radio_id, 1, flight.intra_flight_channel)
        # TODO: Assign 4-6 to VHF frequencies of departure, arrival, and divert.
        # TODO: Assign 2 and 3 to AWACS if it is VHF.

    @classmethod
    def name(cls) -> str:
        return "farmer"


@dataclass(frozen=True)
class ViggenRadioChannelAllocator(RadioChannelAllocator):
    """Preset channel allocator for the AJS37."""

    def assign_channels_for_flight(
        self, flight: FlightData, mission_data: MissionData
    ) -> None:
        # The Viggen's preset channels are handled differently from other
        # aircraft. Since 2.7.9 the group channels will not be generated automatically
        # anymore. So we have to set AWACS and JTAC manually. There are also seven
        # special channels we can modify. We'll set the first channel of the main radio
        # to the intra-flight channel, and the first three emergency channels to each
        # of the flight plan's airfields. The fourth emergency channel is always
        # the guard channel.
        radio_id = 1

        # Possible Group Channels (100-139)
        channel_alloc = iter(range(1, 40))

        # Intra-Flight channel on Special 1 and Group 100 (required by module)
        flight.assign_channel(radio_id, 41, flight.intra_flight_channel)  # Special 1
        flight.assign_channel(
            radio_id, next(channel_alloc), flight.intra_flight_channel
        )

        for awacs_freq in awacs_presets(flight, mission_data):
            flight.assign_channel(radio_id, next(channel_alloc), awacs_freq)

        for jtac_freq in friendly_jtacs(flight, mission_data):
            flight.assign_channel(radio_id, next(channel_alloc), jtac_freq)

        if flight.departure.atc is not None:
            flight.assign_channel(radio_id, 44, flight.departure.atc)  # FR24 E
        if flight.arrival.atc is not None:
            flight.assign_channel(radio_id, 45, flight.arrival.atc)  # FR24 F
        if flight.divert is not None and flight.divert.atc is not None:
            flight.assign_channel(radio_id, 46, flight.divert.atc)  # FR24 G

    @classmethod
    def name(cls) -> str:
        return "viggen"


@dataclass(frozen=True)
class SCR522RadioChannelAllocator(RadioChannelAllocator):
    """Preset channel allocator for the SCR522 WW2 radios. (4 channels)"""

    def assign_channels_for_flight(
        self, flight: FlightData, mission_data: MissionData
    ) -> None:
        radio_id = 1
        flight.assign_channel(radio_id, 1, flight.intra_flight_channel)
        # The set tunes 100-156 MHz only (P-51D manual, SCR-522), so the tower's
        # UHF frequency would be a preset it cannot reach.
        if (departure := tunable_atc(flight, flight.departure)) is not None:
            flight.assign_channel(radio_id, 2, departure)
        if (arrival := tunable_atc(flight, flight.arrival)) is not None:
            flight.assign_channel(radio_id, 3, arrival)

        # TODO : Some GCI on Channel 4 ?

    @classmethod
    def name(cls) -> str:
        return "SCR-522"


@dataclass(frozen=True)
class ARC5RadioChannelAllocator(RadioChannelAllocator):
    """Preset channel allocator for the ARC-5 WW2 radios. (4 channels)"""

    def assign_channels_for_flight(
        self, flight: FlightData, mission_data: MissionData
    ) -> None:
        radio_id = 1
        flight.assign_channel(radio_id, 1, flight.intra_flight_channel)
        if flight.departure.atc is not None:
            flight.assign_channel(radio_id, 2, flight.departure.atc)
        if flight.arrival.atc is not None:
            flight.assign_channel(radio_id, 3, flight.arrival.atc)

        # TODO : Some GCI on Channel 4 ?

    @classmethod
    def name(cls) -> str:
        return "ARC-5"


class ChannelNamer:
    """Base class allowing channel name customization per-aircraft.

    Most aircraft will want to customize this behavior, but the default is
    reasonable for any aircraft with numbered radios.
    """

    @staticmethod
    def channel_name(radio_id: int, channel_id: int) -> str:
        """Returns the name of the channel for the given radio and channel."""
        return f"COMM{radio_id} Ch {channel_id}"

    @classmethod
    def name(cls) -> str:
        return "default"


class SingleRadioChannelNamer(ChannelNamer):
    """Channel namer for the aircraft with only a single radio.

    Aircraft like the MiG-19P and the MiG-21bis only have a single radio, so
    it's not necessary for us to name the radio when naming the channel.
    """

    @staticmethod
    def channel_name(radio_id: int, channel_id: int) -> str:
        return f"Ch {channel_id}"

    @classmethod
    def name(cls) -> str:
        return "single"


class HueyChannelNamer(ChannelNamer):
    """Channel namer for the UH-1H."""

    @staticmethod
    def channel_name(radio_id: int, channel_id: int) -> str:
        # Transmit selector 2 is the ARC-51BX UHF; 3 is VHF (UH-1H manual, 7.1).
        return f"UHF Ch {channel_id}"

    @classmethod
    def name(cls) -> str:
        return "huey"


class MirageChannelNamer(ChannelNamer):
    """Channel namer for the M-2000."""

    @staticmethod
    def channel_name(radio_id: int, channel_id: int) -> str:
        radio_name = ["UHF", "V/UHF"][radio_id - 1]
        return f"{radio_name} Ch {channel_id}"

    @classmethod
    def name(cls) -> str:
        return "mirage"


class MirageF1CEChannelNamer(ChannelNamer):
    """Channel namer for the Mirage-F1CE."""

    @staticmethod
    def channel_name(radio_id: int, channel_id: int) -> str:
        radio_name = ["V/UHF", "UHF"][radio_id - 1]
        return f"{radio_name} Ch {channel_id}"

    @classmethod
    def name(cls) -> str:
        return "mirage-f1CE"


class ApacheChannelNamer(ChannelNamer):
    """Channel namer for the AH-64D Apache"""

    @staticmethod
    def channel_name(radio_id: int, channel_id: int) -> str:
        # From the manual: Radio identifier (“VHF” for ARC-186, “UHF” for ARC-164,
        # “FM1” for first ARC-201D, “FM2” for second ARC-201D, or “HF” for ARC-220).
        radio_name = [
            "VHF",  # ARC-186
            "UHF",  # ARC-164
            "FM1",  # first ARC-201D
            "FM2",  # second ARC-201D
            "HF",  # ARC-220
        ][radio_id - 1]
        return f"{radio_name} Ch {channel_id}"

    @classmethod
    def name(cls) -> str:
        return "apache"


class TomcatChannelNamer(ChannelNamer):
    """Channel namer for the F-14."""

    @staticmethod
    def channel_name(radio_id: int, channel_id: int) -> str:
        radio_name = ["UHF", "VHF/UHF"][radio_id - 1]
        return f"{radio_name} Ch {channel_id}"

    @classmethod
    def name(cls) -> str:
        return "tomcat"


class ViggenChannelNamer(ChannelNamer):
    """Channel namer for the AJS37."""

    @staticmethod
    def channel_name(radio_id: int, channel_id: int) -> str:
        special_channels = [
            "FR 22 Special 1",
            "FR 22 Special 2",
            "FR 22 Special 3",
            "FR 24 E",
            "FR 24 F",
            "FR 24 G",
            "FR 24 H",
        ]
        if channel_id >= 41:  # Special channels are 41-47
            return special_channels[channel_id - 41]
        return f"FR 22 Group {99 + channel_id}"

    @classmethod
    def name(cls) -> str:
        return "viggen"


class ViperChannelNamer(ChannelNamer):
    """Channel namer for the F-16."""

    @staticmethod
    def channel_name(radio_id: int, channel_id: int) -> str:
        return f"COM{radio_id} Ch {channel_id}"

    @classmethod
    def name(cls) -> str:
        return "viper"


class SCR522ChannelNamer(ChannelNamer):
    """
    Channel namer for P-51 & P-47D
    """

    @staticmethod
    def channel_name(radio_id: int, channel_id: int) -> str:
        if channel_id > 3:
            return "?"
        else:
            return f"Button " + "ABCD"[channel_id - 1]

    @classmethod
    def name(cls) -> str:
        return "SCR-522"


class ARC5ChannelNamer(ChannelNamer):
    """
    Channel namer for F4U-1D Corsair
    """

    @staticmethod
    def channel_name(radio_id: int, channel_id: int) -> str:
        if channel_id > 3:
            return "?"
        else:
            return f"Channel " + "1234"[channel_id - 1]

    @classmethod
    def name(cls) -> str:
        return "ARC-5"


class LegacyWarthogChannelNamer(ChannelNamer):
    """Channel namer for the legacy A-10C."""

    @staticmethod
    def channel_name(radio_id: int, channel_id: int) -> str:
        radio_name = {
            1: "VHF AM",
            2: "UHF",
            3: "VHF FM",
        }[radio_id]
        return f"{radio_name} Ch {channel_id}"

    @classmethod
    def name(cls) -> str:
        return "a10c-legacy"


class WarthogChannelNamer(ChannelNamer):
    """Channel namer for the legacy A-10C II"""

    @staticmethod
    def channel_name(radio_id: int, channel_id: int) -> str:
        radio_name = {
            1: "COM 1",
            2: "UHF",
            3: "VHF FM",
        }[radio_id]
        return f"{radio_name} Ch {channel_id}"

    @classmethod
    def name(cls) -> str:
        return "a10c-ii"


class PhantomChannelNamer(ChannelNamer):
    """Channel namer for the F-14."""

    @staticmethod
    def channel_name(radio_id: int, channel_id: int) -> str:
        radio_name = ["COMM", "AUX"][radio_id - 1]
        return f"{radio_name} Ch {channel_id}"

    @classmethod
    def name(cls) -> str:
        return "phantom"


class KiowaChannelNamer(ChannelNamer):
    """Channel namer for OH58D Kiowa Warrior"""

    @staticmethod
    def channel_name(radio_id: int, channel_id: int) -> str:
        radio_name = ["UHF AM", "VHF AM", "VHF FM1", "VHF FM2"][radio_id - 1]
        return f"{radio_name} Ch {channel_id}"

    @classmethod
    def name(cls) -> str:
        return "kiowa"


class FulcrumChannelNamer(ChannelNamer):
    """Channel namer for the MiG-29 Fulcrum A"""

    @staticmethod
    def channel_name(radio_id: int, channel_id: int) -> str:
        return f"Ch {channel_id -1}"

    @classmethod
    def name(cls) -> str:
        return "fulcrum"
