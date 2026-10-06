from typing import Callable

import pytest

from dcs.task import Modulation

from game.radio.radios import MHz, RadioFrequency, kHz


@pytest.mark.parametrize("units,factory", [("kHz", kHz), ("MHz", MHz)])
def test_radio_parsing(units: str, factory: Callable[..., RadioFrequency]) -> None:
    assert RadioFrequency.parse(f"0 {units}") == factory(0)
    assert RadioFrequency.parse(f"0.0 {units}") == factory(0)
    assert RadioFrequency.parse(f"255 {units}") == factory(255)
    assert RadioFrequency.parse(f"255.5 {units}") == factory(255, 500)
    assert RadioFrequency.parse(f"255.500 {units}") == factory(255, 500)
    assert RadioFrequency.parse(f"255.050 {units}") == factory(255, 50)
    assert RadioFrequency.parse(f"255.005 {units}") == factory(255, 5)
    assert RadioFrequency.parse(f"255.0 {units}") == factory(255)

    with pytest.raises(ValueError):
        RadioFrequency.parse("")
    with pytest.raises(ValueError):
        RadioFrequency.parse("255")
    with pytest.raises(ValueError):
        RadioFrequency.parse(f" 255 {units}")
    with pytest.raises(ValueError):
        RadioFrequency.parse(f"255 {units} ")
    with pytest.raises(ValueError):
        RadioFrequency.parse(f"255 {units.lower()}")
    with pytest.raises(ValueError):
        RadioFrequency.parse(f"255. {units}")
    with pytest.raises(ValueError):
        RadioFrequency.parse(f".0 {units}")
    with pytest.raises(ValueError):
        RadioFrequency.parse(f"0. {units}")
    with pytest.raises(ValueError):
        RadioFrequency.parse(f"255.5555 {units}")


def test_radio_str_keeps_trailing_zeros() -> None:
    # Whole-MHz/kHz frequencies must still render three decimal places so the
    # kneeboard frequency columns line up (e.g. ATIS 131.000 vs 131.500).
    assert str(MHz(131)) == "VHF 131.000"
    assert str(MHz(255, 500)) == "UHF 255.500"
    assert str(MHz(251)) == "UHF 251.000"
    assert str(kHz(255)) == "255.000 kHz AM"


def test_radio_str_names_the_band() -> None:
    assert str(MHz(239)) == "UHF 239.000"
    assert str(MHz(225)) == "UHF 225.000"
    assert str(MHz(224, 975)) == "VHF 224.975"
    assert str(MHz(30, 0, Modulation.FM)) == "VHF 30.000 FM"
    assert str(MHz(8)) == "HF 8.000"
