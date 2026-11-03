from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from dcs.terrain import GermanyColdWar, MarianaIslands

from game.radio.radios import MHz
from game.runways import RunwayData, ils_label
from game.utils import Heading

GERMANY = GermanyColdWar()
MARIANAS = MarianaIslands()


def _runway(terrain: Any, airfield: str, end: str) -> RunwayData:
    theater: Any = SimpleNamespace(terrain=terrain)
    airport = next(a for a in terrain.airports.values() if a.name == airfield)
    return next(
        rw
        for rw in RunwayData.for_pydcs_airport(theater, airport)
        if rw.runway_name == end
    )


@pytest.mark.parametrize("end, label", [("23", "108.10 ISPA"), ("05", "109.15 ISPE")])
def test_spangdahlem_ils_comes_from_the_localizer(end: str, label: str) -> None:
    assert ils_label(_runway(GERMANY, "Spangdahlem", end)) == label


@pytest.mark.parametrize(
    "airfield, end, label",
    [
        ("Saipan Intl", "07", "109.90 IGSN"),
        ("Antonio B. Won Pat Intl", "06L", "110.90 IAWD"),
        ("Antonio B. Won Pat Intl", "06R", "110.30 IGUM"),
        ("Antonio B. Won Pat Intl", "24L", ""),
    ],
)
def test_marianas_untied_localizers_find_their_runway(
    airfield: str, end: str, label: str
) -> None:
    assert ils_label(_runway(MARIANAS, airfield, end)) == label


def test_icls_shows_the_channel() -> None:
    runway = RunwayData("CVN", Heading.from_degrees(0), "", icls=11)
    assert ils_label(runway) == "11"


def test_ils_without_an_ident_shows_the_frequency() -> None:
    runway = RunwayData("Field", Heading.from_degrees(0), "09", ils=MHz(108, 100))
    assert ils_label(runway) == "108.10"
