"""With SkyEye on, its AWACS and Vacuum take the presets the silent AI AWACS had (§116)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from game.missiongenerator.missiondata import MissionData
from game.radio.channels import awacs_presets
from game.radio.radios import MHz


def _awacs(freq: Any, blue: bool) -> Any:
    return SimpleNamespace(freq=freq, blue=SimpleNamespace(is_blue=blue))


def _flight(blue: bool = True) -> Any:
    return SimpleNamespace(friendly=SimpleNamespace(is_blue=blue))


def test_without_skyeye_every_awacs_gets_a_preset() -> None:
    data = MissionData()
    data.awacs = [_awacs(MHz(372), True)]
    assert awacs_presets(_flight(), data) == [MHz(372)]


def test_skyeye_and_vacuum_replace_the_silent_blue_awacs() -> None:
    data = MissionData()
    data.awacs = [_awacs(MHz(372), True), _awacs(MHz(380), False)]
    data.skyeye_frequency = MHz(251)
    data.vacuum_frequency = MHz(262)
    assert awacs_presets(_flight(), data) == [MHz(251), MHz(262), MHz(380)]


def test_red_flights_keep_their_own_awacs() -> None:
    data = MissionData()
    data.awacs = [_awacs(MHz(380), False)]
    data.skyeye_frequency = MHz(251)
    assert awacs_presets(_flight(blue=False), data) == [MHz(380)]
