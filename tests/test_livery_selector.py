"""The payload tab's livery choice survives closing and reopening the flight.

The tab used to open on the squadron's livery whatever the member had picked,
so a changed livery looked lost.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Iterator

import pytest

from game.ato.flightmember import FlightMember
from game.ato.loadouts import Loadout

LIVERIES = ["vfa-47 cag", "vfa-91 line", "vfa-192 line"]


@dataclass(frozen=True, order=True)
class _Livery:
    id: str
    name: str
    countries: None = None


@pytest.fixture(scope="module")
def qapp() -> Iterator[Any]:
    from PySide6.QtWidgets import QApplication

    yield QApplication.instance() or QApplication([])


def _squadron(
    livery: str | None = "vfa-47 cag", livery_set: list[str] | None = None
) -> Any:
    dcs_type = SimpleNamespace(
        iter_liveries=lambda: [_Livery(x, x.upper()) for x in LIVERIES]
    )
    faction = SimpleNamespace(
        country=SimpleNamespace(shortname="USA"),
        liveries_overrides=SimpleNamespace(get=lambda _type, default: default),
    )
    return SimpleNamespace(
        aircraft=SimpleNamespace(dcs_unit_type=dcs_type, default_livery=None),
        coalition=SimpleNamespace(faction=faction),
        livery=livery,
        livery_set=livery_set or [],
    )


def _selector(squadron: Any) -> Any:
    from qt_ui.widgets.combos.QSquadronLiverySelector import SquadronLiverySelector

    return SquadronLiverySelector(squadron, update_squadron=False)


def _member(livery: str | None, use_livery_set: bool = False) -> FlightMember:
    member = FlightMember(None, Loadout.empty_loadout())
    member.livery = livery
    member.use_livery_set = use_livery_set
    return member


def _show(selector: Any, member: FlightMember) -> None:
    from qt_ui.windows.mission.flight.payload.QFlightPayloadTab import (
        QFlightPayloadTab,
    )

    tab = SimpleNamespace(
        member_selector=SimpleNamespace(selected_member=member),
        livery_selector=selector,
    )
    QFlightPayloadTab.sync_livery_selector(tab)  # type: ignore[arg-type]


def test_reopening_shows_the_members_livery_not_the_squadrons(qapp: Any) -> None:
    selector = _selector(_squadron())
    assert selector.currentData() == "vfa-47 cag"
    _show(selector, _member("vfa-192 line"))
    assert selector.currentData() == "vfa-192 line"


def test_showing_a_livery_never_writes_one_back(qapp: Any) -> None:
    selector = _selector(_squadron())
    writes: list[int] = []
    selector.currentIndexChanged.connect(writes.append)
    _show(selector, _member("vfa-91 line"))
    assert writes == []


def test_the_match_ignores_case(qapp: Any) -> None:
    selector = _selector(_squadron())
    _show(selector, _member("VFA-91 Line"))
    assert selector.currentData() == "vfa-91 line"


def test_a_member_with_no_livery_shows_the_squadron_default(qapp: Any) -> None:
    selector = _selector(_squadron())
    _show(selector, _member("vfa-91 line"))
    _show(selector, _member(None))
    assert selector.currentData() == "vfa-47 cag"


def test_a_member_on_the_livery_set_shows_the_set(qapp: Any) -> None:
    from qt_ui.widgets.combos.QSquadronLiverySelector import LIVERY_SET_TEXT

    selector = _selector(_squadron(livery=None, livery_set=["vfa-91 line"]))
    _show(selector, _member("vfa-91 line"))
    _show(selector, _member(None, use_livery_set=True))
    assert selector.currentText() == LIVERY_SET_TEXT


def test_the_chosen_livery_reaches_the_mission() -> None:
    from game.missiongenerator.aircraft.aircraftpainter import AircraftPainter

    members = [_member("VFA-192 LINE"), _member("VFA-192 LINE")]
    flight = SimpleNamespace(
        squadron=SimpleNamespace(
            livery="vfa-47 cag", livery_set=[], use_livery_set=False
        ),
        unit_type=SimpleNamespace(
            default_livery=None, dcs_unit_type=SimpleNamespace(id="FA-18C_hornet")
        ),
        coalition=SimpleNamespace(faction=SimpleNamespace(liveries_overrides={})),
        iter_members=lambda: iter(members),
    )
    units = [SimpleNamespace(onboard_num="", livery_id=None) for _ in members]
    group = SimpleNamespace(units=units)
    AircraftPainter(flight, group).apply_livery()  # type: ignore[arg-type]
    assert [u.livery_id for u in units] == ["vfa-192 line", "vfa-192 line"]


def test_same_livery_for_all_copies_the_set_choice_too() -> None:
    from game.ato.flightmembers import FlightMembers

    lead = _member(None, use_livery_set=True)
    wing = _member("vfa-91 line", use_livery_set=False)
    roster = SimpleNamespace(members=[lead, wing])
    FlightMembers.use_same_livery_for_all_members(roster)  # type: ignore[arg-type]
    assert (wing.livery, wing.use_livery_set) == (None, True)
