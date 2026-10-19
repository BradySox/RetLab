"""Tests for the per-mission briefing card and the briefing text (§107)."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from PIL import Image

from game.missiongenerator.briefinggenerator import BriefingGenerator
from game.retlab.briefing_card import (
    HEIGHT,
    WIDTH,
    BriefingCard,
    CardFlight,
    render_briefing_card,
)


def _flight(n: int) -> CardFlight:
    return CardFlight(f"Enfield {n}", "F/A-18C Hornet", "SEAD", "WILDCAT", "0509")


def test_card_is_a_1600_by_1067_png(tmp_path: Path) -> None:
    card = BriefingCard("Red Tide", "TURN 1", ["CAVOK"], [_flight(1)])
    path = render_briefing_card(card, tmp_path / "card.png")
    with Image.open(path) as image:
        assert image.format == "PNG"
        assert image.size == (WIDTH, HEIGHT)


def test_card_draws_with_no_flights_and_with_many(tmp_path: Path) -> None:
    empty = BriefingCard("A very long campaign name " * 4, "TURN 1", [], [])
    render_briefing_card(empty, tmp_path / "empty.png")
    full = BriefingCard(
        "Red Tide", "TURN 1", ["CAVOK"], [_flight(n) for n in range(20)]
    )
    render_briefing_card(full, tmp_path / "full.png")


def _ally(callsign: str, delay_minutes: int) -> Any:
    return SimpleNamespace(
        callsign=callsign,
        flight_type="AEW&C",
        aircraft_type=SimpleNamespace(display_name="E-2C Hawkeye"),
        size=1,
        departure_delay=timedelta(minutes=delay_minutes),
        package=SimpleNamespace(
            target=SimpleNamespace(name="CVN-71"), time_over_target="0510"
        ),
        client_units=[],
        friendly=SimpleNamespace(is_blue=True),
        departure=SimpleNamespace(airfield_name="Tel Nof"),
    )


def _briefing_text(flights: list[Any]) -> str:
    generator = BriefingGenerator(None, None)  # type: ignore[arg-type]
    generator.flights = flights
    generator.generate_allied_flights_by_departure()
    return generator.template.render(
        game=SimpleNamespace(turn=1),
        allied_flights_by_departure=generator.allied_flights_by_departure,
    )


def test_briefing_text_is_not_html_escaped() -> None:
    text = _briefing_text([_ally("Magic 5", 0)])
    assert "AEW&C" in text
    assert "&amp;" not in text


def test_ally_line_names_callsign_aircraft_and_target() -> None:
    text = _briefing_text([_ally("Magic 5", 0)])
    assert "Magic 5: AEW&C E-2C Hawkeye x 1" in text
    assert "target: CVN-71" in text


def test_ally_flights_are_in_departure_order() -> None:
    text = _briefing_text([_ally("Late 1", 30), _ally("Early 1", 0)])
    assert text.index("Early 1") < text.index("Late 1")
