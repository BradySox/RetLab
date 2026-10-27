from __future__ import annotations

import pytest

from game.runways import LIGHT_WIND_MPS, opposite_runway_name, runway_label


@pytest.mark.parametrize(
    "name, opposite",
    [
        ("28L", "10R"),
        ("10R", "28L"),
        ("05", "23"),
        ("18", "36"),
        ("36", "18"),
        ("01C", "19C"),
        ("17R", "35L"),
    ],
)
def test_opposite_runway_name(name: str, opposite: str) -> None:
    assert opposite_runway_name(name) == opposite


@pytest.mark.parametrize("name", ["", "045", "00", "37", "H1"])
def test_names_that_are_not_runway_ends_have_no_opposite(name: str) -> None:
    assert opposite_runway_name(name) is None


def test_light_wind_shows_both_ends() -> None:
    assert runway_label("28L", 3.0) == "28L / 10R"


def test_twelve_knots_and_up_shows_the_into_wind_end_only() -> None:
    assert runway_label("28L", LIGHT_WIND_MPS) == "28L"


def test_a_carrier_brc_is_never_doubled() -> None:
    assert runway_label("045", 1.0) == "045"
