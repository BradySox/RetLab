"""The ABCCC, SkyEye AWACS, Vacuum and ATC kneeboard pages (§116-§119) render."""

from __future__ import annotations

from pathlib import Path

from game.missiongenerator.kneeboard.voicepages import (
    AbcccPage,
    AtcPage,
    SkyEyeAwacsPage,
    VACUUM_TASKS,
    VacuumPage,
)
from game.ato.flighttype import FlightType
from game.radio.radios import MHz
from game.retlab.voice_atc import AtcField, station_name


def test_abccc_page_writes_with_the_mission_names(tmp_path: Path) -> None:
    out = tmp_path / "abccc.png"
    page = AbcccPage("Anvil", MHz(264, 500), "Colt 1-1", False)
    page.write(out)
    assert out.stat().st_size > 0


def test_abccc_page_dark(tmp_path: Path) -> None:
    out = tmp_path / "abccc.png"
    AbcccPage("Anvil", MHz(264, 500), "Colt 1-1", True).write(out)
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
        AtcPage("Viper 1-1", kobuleti, arrival, False).write(out)
        assert out.stat().st_size > 0


def test_atc_card_lists_home_arrival_and_divert_with_presets(tmp_path: Path) -> None:
    home = AtcField("Hatzerim", "28L", MHz(125, 100), MHz(130, 600))
    arrival = AtcField("Ramat David", "33", MHz(127), MHz(128))
    divert = AtcField("Akrotiri", "28", MHz(129, 300), MHz(133, 700))
    presets = {MHz(130, 600): "COMM2 Ch 2", MHz(125, 100): "COMM2 Ch 3"}
    page = AtcPage(
        "Ford 5-1",
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
    page = AtcPage("Ford 5-1", home, home, False, divert=home)
    assert [role for role, _ in page._fields()] == ["home"]


def test_the_comm_card_and_the_atc_card_name_a_station_alike() -> None:
    # The comm ladder, the ATC card and the in-mission text all read "Tel Nof Ground".
    assert station_name("Tel Nof", "ground") == "Tel Nof Ground"
    assert station_name("Tel Nof", "tower") == "Tel Nof Tower"


def test_vacuum_card_is_the_calls_and_the_dark_sam(tmp_path: Path) -> None:
    out = tmp_path / "vacuum.png"
    VacuumPage(MHz(262), MHz(264, 500), "Ford 9-1", False).write(out)
    assert out.stat().st_size > 0
    text = out.with_suffix(".txt").read_text("utf8")
    for expected in (
        "Vacuum: 262.000 AM",
        "Also on STRIKE: 264.500 AM",
        '"Vacuum, Ford 9-1, checking in."',
        '"Vacuum, Ford 9-1, say emitters."',
        '"Vacuum, Ford 9-1, request target status."',
        '"Vacuum, Ford 9-1, mud 270."',
        '"Vacuum, Ford 9-1, say again."',
        '  Vacuum: "SA-6 awake 270, 35, tight; SA-11 asleep 245, 50, loose."',
        "A SAM that keeps its radar off is invisible to Vacuum.",
        '"Blank" does not mean safe.',
    ):
        assert expected in text, expected
    # Calls only (user call, 2026-10-22): no radar table, no explanations.
    for gone in ("early warning radar", "Radar names", "listening plane", "silent"):
        assert gone not in text, gone


def test_vacuum_card_without_strike(tmp_path: Path) -> None:
    out = tmp_path / "vacuum.png"
    VacuumPage(MHz(262), None, "Ford 9-1", True).write(out)
    text = out.with_suffix(".txt").read_text("utf8")
    assert "STRIKE" not in text


def test_only_sead_escort_and_dead_get_the_vacuum_card() -> None:
    assert VACUUM_TASKS == {FlightType.SEAD, FlightType.SEAD_ESCORT, FlightType.DEAD}
