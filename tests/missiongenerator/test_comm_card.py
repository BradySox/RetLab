"""The comm card (2026-10-21): presets split like a squadron card, every one named."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

from game.missiongenerator.aircraft.flightdata import ChannelAssignment
from game.missiongenerator.kneeboard.commcard import CommCardPage, preset_rows
from game.missiongenerator.missiondata import MissionData
from game.radio.channels import CommonRadioChannelAllocator
from game.radio.radios import MHz


class _Flight:
    def __init__(self, radio: Any = None) -> None:
        self.callsign = "Colt 1"
        self.intra_flight_channel = MHz(140)
        self.frequency_to_channel_map: dict[Any, list[ChannelAssignment]] = {}
        self.departure = SimpleNamespace(airfield_name="Kobuleti", atc=MHz(262))
        self.arrival = self.departure
        self.divert = None
        self.package = SimpleNamespace(frequency=MHz(264))
        self.friendly = SimpleNamespace(is_blue=True)
        self.client_units = [SimpleNamespace(set_radio_channel_preset=lambda *a: None)]
        self.squadron = SimpleNamespace(radio_presets={})
        self.aircraft_type = SimpleNamespace(
            intra_flight_radio=radio, can_refuel_from=lambda _: True
        )

    def assign_channel(self, radio_id: int, channel: int, freq: Any) -> None:
        self.frequency_to_channel_map.setdefault(freq, []).append(
            ChannelAssignment(radio_id, channel)
        )

    def num_radio_channels(self, radio_id: int) -> int:
        return 20


def _channels(flight: _Flight, radio: int) -> list[Any]:
    return [
        f
        for f, a in sorted(
            ((f, a) for f, v in flight.frequency_to_channel_map.items() for a in v),
            key=lambda fa: fa[1].channel,
        )
        if a.radio_id == radio
    ]


def _data() -> MissionData:
    data = MissionData()
    data.skyeye_frequency = MHz(251)
    data.vacuum_frequency = MHz(270)
    data.atc_frequencies = {"Kobuleti": (MHz(255), MHz(256))}
    return data


def test_support_on_comm1_flight_and_atc_on_comm2() -> None:
    flight = _Flight()
    CommonRadioChannelAllocator(1, 2).assign_channels_for_flight(flight, _data())  # type: ignore[arg-type]
    assert _channels(flight, 1) == [MHz(140), MHz(251), MHz(270), MHz(264)]
    assert _channels(flight, 2) == [MHz(140), MHz(255), MHz(256)]


def test_a_vhf_comm2_keeps_uhf_towers_on_comm1() -> None:
    vhf = SimpleNamespace(ranges=[SimpleNamespace(minimum=MHz(116), maximum=MHz(156))])
    flight = _Flight(vhf)
    CommonRadioChannelAllocator(1, 2).assign_channels_for_flight(flight, _data())  # type: ignore[arg-type]
    assert _channels(flight, 2) == [MHz(140)]
    assert _channels(flight, 1)[-2:] == [MHz(255), MHz(256)]


def test_the_card_names_every_preset(tmp_path: Path) -> None:
    flight = _Flight()
    CommonRadioChannelAllocator(1, 2).assign_channels_for_flight(flight, _data())  # type: ignore[arg-type]
    labels = {MHz(251): "Chainsaw", MHz(255): "Kobuleti Ground", MHz(140): "Colt 1"}
    rows = preset_rows(flight, labels)  # type: ignore[arg-type]
    # Ch 1 on both radios is the flight's own frequency.
    assert rows[0] == ["Colt 1\nVHF 140.000", "1", "Colt 1\nVHF 140.000"]
    assert rows[1][0] == "Chainsaw\nUHF 251.000"
    assert rows[1][2] == "Kobuleti Ground\nUHF 255.000"
    CommCardPage(flight, labels, False).write(tmp_path / "card.png")  # type: ignore[arg-type]
    assert (tmp_path / "card.png").exists()


def test_a_uhf_only_comm1_cannot_carry_a_vhf_flight_frequency() -> None:
    flight = _Flight()
    uhf = SimpleNamespace(ranges=[SimpleNamespace(minimum=MHz(225), maximum=MHz(400))])
    flight.aircraft_type.inter_flight_radio = uhf
    CommonRadioChannelAllocator(1, 2).assign_channels_for_flight(flight, _data())  # type: ignore[arg-type]
    assert _channels(flight, 1)[0] == MHz(251)


def test_running_out_of_presets_is_logged(caplog: Any) -> None:
    flight = _Flight()
    flight.num_radio_channels = lambda radio_id: 2  # type: ignore[method-assign]
    with caplog.at_level("WARNING"):
        CommonRadioChannelAllocator(1, 2).assign_channels_for_flight(flight, _data())  # type: ignore[arg-type]
    assert "out of presets" in caplog.text


def test_unused_presets_repeat_channel_1_instead_of_module_fillers() -> None:
    set_calls: list[tuple[int, int, float]] = []
    flight = _Flight()
    flight.client_units = [
        SimpleNamespace(
            set_radio_channel_preset=lambda r, c, f: set_calls.append((r, c, f))
        )
    ]
    flight.num_radio_channels = lambda radio_id: 6  # type: ignore[method-assign]
    CommonRadioChannelAllocator(1, 2).assign_channels_for_flight(flight, _data())  # type: ignore[arg-type]
    comm2_fill = sorted(c for r, c, f in set_calls if r == 2 and f == 140.0 and c > 3)
    assert comm2_fill == [4, 5, 6]
    # Fillers are not assignments, so the comm card leaves them blank.
    assert _channels(flight, 2) == [MHz(140), MHz(255), MHz(256)]
