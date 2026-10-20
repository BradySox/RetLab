"""The ABCCC and SkyEye AWACS cheat-sheet kneeboard pages (§116, §117) render."""

from __future__ import annotations

from pathlib import Path

from game.missiongenerator.kneeboard.voicepages import AbcccPage, SkyEyeAwacsPage
from game.radio.radios import MHz


def test_abccc_page_writes_with_the_mission_names(tmp_path: Path) -> None:
    out = tmp_path / "abccc.png"
    page = AbcccPage("Bookshelf", MHz(264, 500), "Chainsaw", "Colt 1-1", False)
    page.write(out)
    assert out.stat().st_size > 0


def test_abccc_page_without_an_awacs(tmp_path: Path) -> None:
    out = tmp_path / "abccc.png"
    AbcccPage("Anvil", MHz(264, 500), None, "Colt 1-1", True).write(out)
    assert out.stat().st_size > 0


def test_awacs_page_writes_with_and_without_strike(tmp_path: Path) -> None:
    for strike in (MHz(264, 500), None):
        out = tmp_path / f"awacs-{strike is None}.png"
        SkyEyeAwacsPage("Chainsaw", MHz(251), strike, "Colt 1-1", False).write(out)
        assert out.stat().st_size > 0
