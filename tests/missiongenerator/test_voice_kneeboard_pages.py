"""The ABCCC, SkyEye AWACS and ATC kneeboard pages (§116, §117, §119) render."""

from __future__ import annotations

from pathlib import Path

from game.missiongenerator.kneeboard.voicepages import (
    AbcccPage,
    AtcPage,
    SkyEyeAwacsPage,
)
from game.radio.radios import MHz
from game.retlab.voice_atc import AtcField


def test_abccc_page_writes_with_the_mission_names(tmp_path: Path) -> None:
    out = tmp_path / "abccc.png"
    page = AbcccPage("Anvil", MHz(264, 500), "Chainsaw", "Colt 1-1", False)
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


def test_atc_page_writes_for_one_field_and_for_two(tmp_path: Path) -> None:
    kobuleti = AtcField("Kobuleti", "25", MHz(262), MHz(260))
    batumi = AtcField("Batumi", "13", MHz(266), MHz(268))
    for name, arrival in (("same", kobuleti), ("other", batumi), ("none", None)):
        out = tmp_path / f"atc-{name}.png"
        AtcPage("Viper 1-1", "4101", kobuleti, arrival, False).write(out)
        assert out.stat().st_size > 0
