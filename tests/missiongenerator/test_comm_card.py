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
            intra_flight_radio=radio,
            can_refuel_from=lambda _: True,
            channel_name=lambda r, c: f"COM{r} Ch {c}",
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


def _uhf() -> Any:
    return SimpleNamespace(ranges=[SimpleNamespace(minimum=MHz(225), maximum=MHz(400))])


def test_only_own_side_tankers_and_jtacs_are_preset() -> None:
    from game.theater.player import Player

    flight = _Flight()
    flight.friendly = Player.BLUE  # type: ignore[assignment]
    data = _data()
    data.tankers = [
        SimpleNamespace(freq=MHz(247), blue=Player.RED, aircraft_type=None),  # type: ignore[list-item]
        SimpleNamespace(freq=MHz(248), blue=Player.BLUE, aircraft_type=None),  # type: ignore[list-item]
    ]
    data.jtacs = [
        SimpleNamespace(freq=MHz(31), blue=Player.RED),  # type: ignore[list-item]
        SimpleNamespace(freq=MHz(32), blue=Player.BLUE),  # type: ignore[list-item]
    ]
    CommonRadioChannelAllocator(1, 2).assign_channels_for_flight(flight, data)  # type: ignore[arg-type]
    comm1 = _channels(flight, 1)
    assert MHz(248) in comm1 and MHz(32) in comm1
    assert MHz(247) not in comm1 and MHz(31) not in comm1


def test_strike_is_the_package_preset_without_being_saved_on_the_package() -> None:
    flight = _Flight()
    data = _data()
    data.strike_frequency = MHz(266)
    data.strike_packages = {id(flight.package)}
    CommonRadioChannelAllocator(1, 2).assign_channels_for_flight(flight, data)  # type: ignore[arg-type]
    assert MHz(266) in _channels(flight, 1)
    assert MHz(264) not in _channels(flight, 1)
    assert flight.package.frequency == MHz(264)


def test_no_preset_a_radio_cannot_tune() -> None:
    # One UHF set (F-4E, F-5E): a VHF tower is never preset on it.
    flight = _Flight()
    flight.aircraft_type.inter_flight_radio = _uhf()
    flight.departure = SimpleNamespace(airfield_name="Senaki", atc=MHz(132))
    flight.arrival = flight.departure
    CommonRadioChannelAllocator(1, 1).assign_channels_for_flight(flight, _data())  # type: ignore[arg-type]
    assert MHz(132) not in _channels(flight, 1)
    assert MHz(251) in _channels(flight, 1)
    # Two sets: a tower COMM2 cannot take moves to COMM1 only if COMM1 tunes it.
    two = _Flight(_uhf())
    two.aircraft_type.inter_flight_radio = _uhf()
    two.departure = SimpleNamespace(airfield_name="Senaki", atc=MHz(132))
    two.arrival = two.departure
    CommonRadioChannelAllocator(1, 2).assign_channels_for_flight(two, _data())  # type: ignore[arg-type]
    assert MHz(132) not in _channels(two, 1) + _channels(two, 2)


def test_f15e_comm1_is_support_and_comm2_is_flight_and_atc(tmp_path: Path) -> None:
    from dcs.planes import F_15ESE

    from game import persistency
    from game.dcs.aircrafttype import AircraftType

    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16888)
    f15e = next(AircraftType.for_dcs_type(F_15ESE))
    assert f15e.inter_flight_radio is not None
    assert f15e.inter_flight_radio.name == "AN/ARC-164"
    assert f15e.intra_flight_radio is not None
    assert f15e.intra_flight_radio.name == "AN/ARC-210"
    allocator = f15e.channel_allocator
    assert isinstance(allocator, CommonRadioChannelAllocator)
    assert (allocator.inter_flight_radio_index, allocator.intra_flight_radio_index) == (
        1,
        2,
    )
    # Its flight frequency is UHF, so Ch 1 on COMM1 is the flight too.
    assert f15e.intra_flight_radio.ranges[0].minimum == MHz(225)


def test_a_long_name_is_cut_to_its_column() -> None:
    from game.missiongenerator.kneeboard.commcard import fit

    text = fit("CVN-71 Theodore Roosevelt Tower 72X", 10, len)
    assert len(text) <= 10 and text.endswith("...")
    assert fit("Ford 2-1", 10, len) == "Ford 2-1"


def test_the_card_heads_each_radio_as_the_other_pages_name_it() -> None:
    from game.missiongenerator.kneeboard.commcard import radio_name

    flight = _Flight()
    assert radio_name(flight, 1) == "COM1"  # type: ignore[arg-type]
    flight.aircraft_type.channel_name = lambda r, c: f"Button {c}"
    assert radio_name(flight, 2) == "COMM 2"  # type: ignore[arg-type]


def test_ground_and_tower_sit_where_each_jet_can_tune_them(tmp_path: Path) -> None:
    from dcs.planes import F_14B, F_16C_50, F_4E_45MC

    from game import persistency
    from game.dcs.aircrafttype import AircraftType

    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16888)
    atc = [MHz(255), MHz(256)]
    for dcs_type, radio in ((F_14B, 2), (F_16C_50, 1), (F_4E_45MC, 1)):
        aircraft = next(AircraftType.for_dcs_type(dcs_type))
        flight = _Flight()
        flight.aircraft_type = aircraft  # type: ignore[assignment]
        assert aircraft.channel_allocator is not None
        aircraft.channel_allocator.assign_channels_for_flight(flight, _data())  # type: ignore[arg-type]
        assert set(atc) <= set(_channels(flight, radio)), dcs_type.id
