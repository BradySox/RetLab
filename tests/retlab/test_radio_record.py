"""Record radios for Tacview (§127): which frequencies SkyEye is asked to record."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from game.missiongenerator.missiondata import MissionData
from game.radio.radios import MHz
from game.retlab.radio_record import recorded_frequencies


def _game(on: bool = True) -> Any:
    return SimpleNamespace(
        settings=SimpleNamespace(record_radios_for_tacview=on, voice_atc=False)
    )


def _flight(callsign: str, mhz: int, client: bool = True, blue: bool = True) -> Any:
    return SimpleNamespace(
        callsign=callsign,
        intra_flight_channel=MHz(mhz),
        client_units=[object()] if client else [],
        friendly=SimpleNamespace(is_blue=blue),
    )


def test_off_records_nothing() -> None:
    data = MissionData()
    data.skyeye_frequency = MHz(251)
    assert recorded_frequencies(_game(on=False), data) == []


def test_bots_then_player_flights_each_frequency_once() -> None:
    data = MissionData()
    data.skyeye_frequency = MHz(251)
    data.strike_frequency = MHz(264)
    data.flights = [
        _flight("Enfield 4", 130),
        _flight("Colt 1", 131, client=False),
        _flight("Uzi 2", 132, blue=False),
        _flight("Ford 9", 264),
    ]
    found = recorded_frequencies(_game(), data)
    assert [(f.label, f.frequency, f.record_only) for f in found] == [
        ("AWACS", MHz(251), False),
        ("STRIKE", MHz(264), False),
        ("Enfield 4", MHz(130), True),
    ]
