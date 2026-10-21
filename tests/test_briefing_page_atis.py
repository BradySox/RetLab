from __future__ import annotations

from unittest.mock import MagicMock

from game.missiongenerator.kneeboard import BriefingPage
from game.radio.radios import MHz, RadioFrequency


def _page(atis_by_name: dict[str, RadioFrequency]) -> BriefingPage:
    page = BriefingPage.__new__(BriefingPage)
    page.flight = MagicMock()
    page.flight.channel_for.return_value = None  # bare freq, no preset
    page.atis_by_name = atis_by_name
    page.atc_fields = {}
    return page


def test_airfield_info_row_includes_atis_when_known() -> None:
    runway = MagicMock()
    runway.airfield_name = "Batumi"
    runway.atc = None
    runway.tacan = None
    runway.ils = None
    runway.icls = None
    runway.runway_name = "13"
    row = _page({"Batumi": MHz(131)})._row_with_atis("Departure", runway)
    assert "131" in row[-1]


def test_airfield_info_row_blank_atis_when_unknown() -> None:
    runway = MagicMock()
    runway.airfield_name = "Nowhere"
    runway.atc = runway.tacan = runway.ils = runway.icls = None
    runway.runway_name = "09"
    row = _page({})._row_with_atis("Arrival", runway)
    assert row[-1] == ""


def test_none_runway_row_has_empty_atis_cell() -> None:
    row = _page({})._row_with_atis("Divert", None)
    assert len(row) == 7
    assert row[-1] == ""


def test_voice_atc_ground_and_tower_replace_the_dcs_tower() -> None:
    from game.radio.radios import MHz
    from game.retlab.voice_atc import AtcField

    page = _page({})
    page.flight.channels_for.return_value = []  # type: ignore[attr-defined]
    page.atc_fields = {"Batumi": AtcField("Batumi", "13", MHz(126, 500), MHz(124, 300))}
    runway = MagicMock()
    runway.airfield_name = "Batumi"
    runway.atc = MHz(260)
    runway.atc_vhf = None
    runway.tacan = None
    runway.ils = None
    runway.icls = None
    row = page.airfield_info_row("Departure", runway)
    assert row[2] == "GND 124.300\nTWR 126.500"
