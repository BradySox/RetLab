"""The ABCCC, SkyEye AWACS and ATC kneeboard pages (§116, §117, §119) render."""

from __future__ import annotations

from pathlib import Path

from game.missiongenerator.kneeboard.voicepages import (
    AbcccPage,
    AtcPage,
    SkyEyeAwacsPage,
)
from game.radio.radios import MHz
from game.retlab.voice_atc import AtcField, station_name


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


def test_atc_card_lists_home_arrival_and_divert_with_presets(tmp_path: Path) -> None:
    home = AtcField("Hatzerim", "28L", MHz(125, 100), MHz(130, 600))
    arrival = AtcField("Ramat David", "33", MHz(127), MHz(128))
    divert = AtcField("Akrotiri", "28", MHz(129, 300), MHz(133, 700))
    presets = {MHz(130, 600): "COMM2 Ch 2", MHz(125, 100): "COMM2 Ch 3"}
    page = AtcPage(
        "Ford 5-1",
        "4101",
        home,
        arrival,
        False,
        divert=divert,
        preset=presets.get,
    )
    assert [(role, f.name) for role, f in page._fields()] == [
        ("home", "Hatzerim"),
        ("arrival", "Ramat David"),
        ("divert", "Akrotiri"),
    ]
    assert (
        page._station("Hatzerim Ground", home.ground)
        == "  Hatzerim Ground: COMM2 Ch 2, 130.600 AM"
    )
    assert page._station("Akrotiri Ground", divert.ground) == (
        "  Akrotiri Ground: 133.700 AM"
    )
    out = tmp_path / "atc-full.png"
    page.write(out)
    assert out.stat().st_size > 0


def test_atc_card_lists_a_field_once() -> None:
    home = AtcField("Hatzerim", "28L", MHz(125, 100), MHz(130, 600))
    page = AtcPage("Ford 5-1", "4101", home, home, False, divert=home)
    assert [role for role, _ in page._fields()] == ["home"]


def test_the_comm_card_and_the_atc_card_name_a_station_alike() -> None:
    # The comm ladder, the ATC card and the in-mission text all read "Tel Nof Ground".
    assert station_name("Tel Nof", "ground") == "Tel Nof Ground"
    assert station_name("Tel Nof", "tower") == "Tel Nof Tower"
