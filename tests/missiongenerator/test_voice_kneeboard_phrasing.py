"""The voice cards list the calls SkyEye recognizes, each with its answer, and nothing else (2026-10-22)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from game.missiongenerator.kneeboard import voicepages
from game.missiongenerator.kneeboard.voicepages import (
    AbcccPage,
    AtcPage,
    SkyEyeAwacsPage,
)
from game.radio.radios import MHz
from game.retlab.voice_atc import AtcField


def _card_lines(page: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    seen: list[str] = []
    real = voicepages._lines

    def capture(writer: Any, lines: list[str]) -> None:
        seen.extend(lines)
        real(writer, lines)

    monkeypatch.setattr(voicepages, "_lines", capture)
    page.write(tmp_path / "card.png")
    return "\n".join(seen)


def _calls(text: str) -> list[str]:
    """The pilot's calls: every line that opens with a quote."""
    return [line for line in text.splitlines() if line.startswith('"')]


def _answers(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.startswith("  ")]


def test_abccc_card_is_calls_and_answers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    page = AbcccPage(
        "Blackjack",
        MHz(264, 500),
        "Ford 9-1",
        False,
        push_time="1432",
        hold_angels=20,
    )
    text = _card_lines(page, tmp_path, monkeypatch)
    assert _calls(text) == [
        '"Blackjack, Ford 9-1, checking in."',
        '"Blackjack, Ford 9-1, ready."',
        '"Blackjack, Ford 9-1, ready to push."',
        '"Blackjack, Ford 9-1, say push time."',
        '"Blackjack, Ford 9-1, off target."',
    ]
    assert len(_answers(text)) == len(_calls(text))
    assert "Push time 1432" in text
    assert "command post" not in text and "Tip" not in text
    assert '"Radar contact. Cleared direct hold, angels 20. Push time 1432."' in text


def test_abccc_card_leaves_out_numbers_it_does_not_have(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    page = AbcccPage("Blackjack", MHz(264, 500), "Ford 9-1", False)
    text = _card_lines(page, tmp_path, monkeypatch)
    assert '  Blackjack: "Radar contact."' in text
    assert '  Blackjack: "Copy ready."' in text
    assert '  Blackjack: "Push time <time>."' in text
    assert "1432" not in text and "angels" not in text


def test_awacs_card_is_calls_and_answers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    page = SkyEyeAwacsPage("Image", MHz(251), None, "Ford 9-1", False)
    text = _card_lines(page, tmp_path, monkeypatch)
    calls = _calls(text)
    assert calls[:3] == [
        '"Image, Ford 9-1, radio check."',
        '"Image, Ford 9-1, picture."',
        '"Image, Ford 9-1, bogey dope."',
    ]
    assert 5 <= len(calls) <= 8
    assert len(_answers(text)) == len(calls)
    # SkyEye answers an AWACS check-in by asking which check was meant.
    assert "checking in" not in text
    assert "Nobody answers" not in text and "player name" not in text
    # Live numbers are placeholders, never figures that read as mission data.
    assert '  Image: "Group BRAA <brg>/<rng>, <alt> thousand, hot, hostile."' in text
    assert '  Image: "Nearest tanker, BRA <brg>/<rng>."' in text
    for figure in ("090/40", "270/25", "180/40", "Texaco"):
        assert figure not in text, figure


def test_awacs_card_names_the_tanker_that_can_refuel_the_jet(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    page = SkyEyeAwacsPage("Image", MHz(251), None, "Ford 9-1", False, tanker="Arco 2")
    text = _card_lines(page, tmp_path, monkeypatch)
    assert '  Image: "Nearest tanker, Arco 2, BRA <brg>/<rng>."' in text


def test_atc_card_after_landing_is_a_pilot_call_with_station_and_callsign(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = AtcField("Hatzerim", "28L", MHz(125, 100), MHz(130, 600))
    page = AtcPage("Ford 9-1", home, home, False)
    text = _card_lines(page, tmp_path, monkeypatch)
    assert (
        '"Hatzerim Tower, Ford 9-1, clear of the runway."\n  ATC: "Taxi to parking."'
    ) in text
    # The takeoff clearance approves the frequency change: no airborne call (2026-10-26).
    assert "airborne" not in text
    # No squawk codes (user call, 2026-10-22): Ground clears taxi, the readback is the runway.
    assert (
        '  ATC: "Runway 28L, altimeter, taxi, hold short runway 28L, contact Tower '
        f'{voicepages._spoken_freq(home.tower)}."'
    ) in text
    assert '  You: "Hold short 28L, Ford 9-1."' in text
    assert "squawk" not in text.lower()
    # Calls only: no explanations of readbacks, discipline or the F10 menu.
    for gone in ("Readback incomplete", "F10", "Nothing stops you", "(or "):
        assert gone not in text, gone
    for call in _calls(text):
        assert "Ford 9-1" in call, call


def test_atc_card_teaches_the_military_pattern(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = AtcField("Hatzerim", "28L", MHz(125, 100), MHz(130, 600))
    page = AtcPage("Ford 9-1", home, home, False)
    text = _card_lines(page, tmp_path, monkeypatch)
    calls = _calls(text)
    for call in (
        '"Hatzerim Ground, Ford 9-1, flight of two, have the numbers, request taxi."',
        '"Hatzerim Tower, Ford 9-1, 10 miles, full stop."',
        '"Hatzerim Tower, Ford 9-1, 10 miles, request straight-in."',
        '"Ford 9-1, initial."',
        '"Ford 9-1, base, gear down, full stop."',
    ):
        assert call in calls, call
    assert '  ATC: "Runway 28L, wind, report initial."' in text
    assert (
        '  ATC: "Runway 28L, wind, cleared for takeoff, frequency change approved."'
        in text
    )
    assert '  ATC: "Runway 28L, wind, cleared to land."' in text
    # Each call has one answer line; only a readback adds a "You:" line.
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith('"'):
            assert lines[i + 1].startswith("  ATC: "), line
    # The landing clearance comes at base, never with the inbound call.
    inbound = lines.index('"Hatzerim Tower, Ford 9-1, 10 miles, full stop."')
    assert "cleared to land" not in lines[inbound + 1]
