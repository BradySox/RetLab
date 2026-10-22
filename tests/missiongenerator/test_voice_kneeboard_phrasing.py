"""The voice cards teach the calls SkyEye now understands, natural form first (2026-10-21)."""

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


def test_abccc_card_teaches_check_in_aliases_and_the_roll_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    page = AbcccPage("Blackjack", MHz(264, 500), "Image", "Ford 9-1", False)
    text = _card_lines(page, tmp_path, monkeypatch)
    assert '"Blackjack, Ford 9-1, checking in."  (or "with you", "on station")' in text
    assert '"... package, check in"' in text
    assert '"Blackjack, Ford 9-1, ready"' in text
    assert "push time 1432" in text
    assert "All players" not in text


def test_awacs_card_no_longer_asks_for_the_callsign_as_player_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    page = SkyEyeAwacsPage("Image", MHz(251), None, "Ford 9-1", False)
    text = _card_lines(page, tmp_path, monkeypatch)
    assert "player name" not in text
    assert '"Image, Ford 9-1, checking in."' in text


def test_atc_card_after_landing_is_a_pilot_call_with_station_and_callsign(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = AtcField("Hatzerim", "28L", MHz(125, 100), MHz(130, 600))
    page = AtcPage("Ford 9-1", "4101", home, home, False)
    text = _card_lines(page, tmp_path, monkeypatch)
    assert (
        'After landing, you: "Tower, Ford 9-1, clear of the runway."  '
        'ATC: "Taxi to parking."'
    ) in text
    assert '"Clear the runway, taxi to parking."' not in text
    assert '"Hatzerim Tower, Ford 9-1, airborne."  (or "outbound")' in text
    assert "your name first works too" in text
