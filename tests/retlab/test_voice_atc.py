"""Voice ATC (§119): squawk codes, the lead callsign and which flights and fields get ATC."""

from __future__ import annotations

from itertools import islice
from types import SimpleNamespace
from typing import Any

from game.missiongenerator.missiondata import MissionData
from game.radio.radios import MHz
from game.retlab.voice_atc import (
    frequency_text,
    lead_callsign,
    squawk_codes,
    voice_atc_plan,
)


def test_squawk_codes_use_only_digits_0_to_7_and_never_repeat() -> None:
    codes = list(squawk_codes())
    assert codes[:3] == ["4101", "4102", "4103"]
    assert "4110" in codes and "4200" not in codes
    assert all(set(c) <= set("01234567") and len(c) == 4 for c in codes)
    assert len(set(codes)) == len(codes)
    assert not {"7500", "7600", "7700"} & set(codes)


def test_the_lead_answers_to_ship_one() -> None:
    viper: Any = SimpleNamespace(callsign="Viper 1")
    assert lead_callsign(viper) == "Viper 1-1"


def test_frequencies_print_as_skyeye_prints_them() -> None:
    assert frequency_text(MHz(262)) == "262.000AM"


def _runway(name: str) -> Any:
    return SimpleNamespace(airfield_name=name, runway_name="25")


def _flight(
    group: str,
    client: bool,
    field: str = "Kobuleti",
    blue: bool = True,
    divert: Any = None,
) -> Any:
    return SimpleNamespace(
        group_name=group,
        callsign=group + " 1",
        client_units=[object()] if client else [],
        friendly=SimpleNamespace(is_blue=blue),
        departure=_runway(field),
        arrival=_runway(field),
        divert=_runway(divert) if divert else None,
    )


def _game(on: bool = True) -> Any:
    return SimpleNamespace(
        settings=SimpleNamespace(voice_atc=on),
        blue=SimpleNamespace(
            faction=SimpleNamespace(country=SimpleNamespace(name="USA"))
        ),
    )


def test_only_blue_player_flights_at_atc_fields_get_atc() -> None:
    data = MissionData()
    data.atc_frequencies = {"Kobuleti": (MHz(260), MHz(264))}
    data.skyeye_voices = ["en_US-ryan-medium", "en_US-amy-medium"]
    data.flights = [
        _flight("Viper", True),
        _flight("Colt", False),
        _flight("Enfield", True, field="Batumi"),
        _flight("Red", True, blue=False),
        _flight("Uzi", True),
    ]
    plan = voice_atc_plan(_game(), data)
    assert plan is not None
    assert [(f.group, f.callsign, f.squawk) for f in plan.flights] == [
        ("Viper", "Viper 1-1", "4101"),
        ("Uzi", "Uzi 1-1", "4102"),
    ]
    field = plan.fields["Kobuleti"]
    assert (field.runway, field.ground, field.tower) == ("25", MHz(260), MHz(264))
    voices = {field.ground_voice, field.tower_voice}
    assert len(voices) == 2 and not voices & set(data.skyeye_voices)
    # Built once: the kneeboard sees the same squawks as the mission.
    assert voice_atc_plan(_game(), data) is plan


def test_a_divert_field_gets_its_own_ground_and_tower() -> None:
    data = MissionData()
    data.atc_frequencies = {
        "Kobuleti": (MHz(124), MHz(125)),
        "Batumi": (MHz(126), MHz(127)),
    }
    data.flights = [_flight("Viper", True, divert="Batumi")]
    plan = voice_atc_plan(_game(), data)
    assert plan is not None
    assert plan.flights[0].divert == "Batumi"
    assert (plan.fields["Batumi"].ground, plan.fields["Batumi"].tower) == (
        MHz(126),
        MHz(127),
    )


def test_player_airfields_include_the_divert() -> None:
    from game.retlab.voice_atc import player_airfields
    from game.theater.controlpoint import Airfield

    home: Any = Airfield.__new__(Airfield)
    divert: Any = Airfield.__new__(Airfield)
    flight = SimpleNamespace(
        client_count=1, departure=home, arrival=home, divert=divert
    )
    ato: Any = SimpleNamespace(packages=[SimpleNamespace(flights=[flight])])
    assert player_airfields(ato) == [home, divert]


def test_nothing_with_the_setting_off() -> None:
    data = MissionData()
    data.atc_frequencies = {"Kobuleti": (MHz(260), MHz(264))}
    data.flights = [_flight("Viper", True)]
    assert voice_atc_plan(_game(on=False), data) is None


def test_codes_run_past_the_first_block() -> None:
    assert list(islice(squawk_codes(), 62, 64)) == ["4177", "4201"]


def _preset_flight(departure: str, arrival: str) -> Any:
    return SimpleNamespace(
        departure=SimpleNamespace(airfield_name=departure, atc=MHz(250)),
        arrival=SimpleNamespace(
            airfield_name=arrival, atc=MHz(250 if arrival == departure else 251)
        ),
        divert=None,
        package=SimpleNamespace(frequency=None),
        aircraft_type=SimpleNamespace(can_refuel_from=lambda _: True),
    )


def test_voice_atc_fields_preset_ground_and_tower_instead_of_dcs_tower() -> None:
    from game.radio.channels import CommonRadioChannelAllocator

    data = MissionData()
    data.atc_frequencies = {
        "Kobuleti": (MHz(260), MHz(264)),
        "Batumi": (MHz(266), MHz(268)),
    }
    presets = CommonRadioChannelAllocator._inter_flight_frequencies
    assert presets(_preset_flight("Kobuleti", "Batumi"), data) == [
        MHz(260),
        MHz(264),
        MHz(266),
        MHz(268),
    ]
    # A field without voice ATC keeps its DCS tower.
    assert presets(_preset_flight("Senaki", "Kobuleti"), data) == [
        MHz(250),
        MHz(260),
        MHz(264),
    ]
    assert presets(_preset_flight("Senaki", "Senaki"), MissionData()) == [MHz(250)]


def test_ground_and_tower_are_vhf_am_airband() -> None:
    from game.radio.radios import RadioRegistry

    registry = RadioRegistry()
    pair = [registry.alloc_vhf() for _ in range(40)]
    assert all(118 <= f.mhz < 136 for f in pair)
    assert all(f.modulation.name == "AM" for f in pair)
    assert len(set(pair)) == len(pair)


def test_atc_lines_name_the_preset_channels() -> None:
    from game.missiongenerator.aircraft.flightdata import ChannelAssignment
    from game.retlab.voice_atc import AtcField, atc_lines

    channels = {MHz(124, 300): [ChannelAssignment(2, 2)]}
    flight: Any = SimpleNamespace(
        channels_for=lambda f: channels.get(f, []),
        aircraft_type=SimpleNamespace(
            channel_name=lambda radio, channel: f"COMM{radio} Ch {channel}"
        ),
    )
    field = AtcField("Kobuleti", "25", MHz(126, 500), MHz(124, 300))
    assert atc_lines(flight, field) == ("GND 124.300 (COMM2 Ch 2)\nTWR 126.500")


def _pin_game(*names: str) -> Any:
    from game.theater.controlpoint import Airfield

    fields = []
    for name in names:
        field: Any = Airfield.__new__(Airfield)
        field.airport = SimpleNamespace(name=name)
        fields.append(field)
    flights = [
        SimpleNamespace(client_count=1, departure=f, arrival=f, divert=None)
        for f in fields
    ]
    return SimpleNamespace(
        settings=SimpleNamespace(voice_atc=True),
        blue=SimpleNamespace(
            ato=SimpleNamespace(packages=[SimpleNamespace(flights=flights)])
        ),
        voice_atc_frequencies={},
    )


def test_a_field_keeps_its_ground_and_tower_every_turn() -> None:
    import pickle

    from game.radio.radios import RadioRegistry
    from game.retlab.voice_atc import allocate_atc_frequencies

    game = _pin_game("Hatzerim", "Akrotiri")
    first = MissionData()
    allocate_atc_frequencies(game, RadioRegistry(), first)
    # Next turn: a fresh registry, and the pairs survive a save and load.
    game.voice_atc_frequencies = pickle.loads(pickle.dumps(game.voice_atc_frequencies))
    second = MissionData()
    allocate_atc_frequencies(game, RadioRegistry(), second)
    assert second.atc_frequencies == first.atc_frequencies
    used = [f for pair in second.atc_frequencies.values() for f in pair]
    assert len(set(used)) == 4


def test_a_new_field_never_takes_a_pinned_frequency() -> None:
    from game.radio.radios import RadioRegistry
    from game.retlab.voice_atc import allocate_atc_frequencies

    game = _pin_game("Hatzerim")
    allocate_atc_frequencies(game, RadioRegistry(), MissionData())
    hatzerim = game.voice_atc_frequencies["Hatzerim"]
    # A later turn flies only from Akrotiri: Hatzerim's pair stays reserved.
    later = _pin_game("Akrotiri")
    later.voice_atc_frequencies = game.voice_atc_frequencies
    registry = RadioRegistry()
    allocate_atc_frequencies(later, registry, MissionData())
    assert set(later.voice_atc_frequencies["Akrotiri"]).isdisjoint(hatzerim)
    assert set(hatzerim) <= registry.allocated_channels
    assert set(hatzerim) <= registry.atc_pinned


def test_old_saves_get_an_empty_pin_table() -> None:
    from game.game import Game

    game: Any = Game.__new__(Game)
    state = {"settings": SimpleNamespace(), "hq_requests": object()}
    try:
        game.__setstate__(state)
    except Exception:
        pass
    assert state["voice_atc_frequencies"] == {}
