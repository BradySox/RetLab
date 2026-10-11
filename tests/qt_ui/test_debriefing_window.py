"""The Debriefing window's layout.

It used to open at its layout's minimum height: everything but three scroll
boxes was a fixed height, so those three shrank to two rows, and the lost-units
lists kept their own narrow width inside an empty frame.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from types import SimpleNamespace
from typing import Any, Iterator

import pytest

from game.retlab.flight_grades import FlightCard, Grade
from game.theater import Player


@pytest.fixture(scope="module")
def qapp() -> Iterator[Any]:
    from PySide6.QtWidgets import QApplication

    yield QApplication.instance() or QApplication([])


class _Debriefing:
    player_country = "USA"
    enemy_country = "Russia"
    base_captures: list[Any] = []
    damaged_runways: list[Any] = []
    state_data = SimpleNamespace(mission_ended=True)

    def __init__(self, blue_rows: int, red_rows: int, cards: int) -> None:
        self.rows = {True: blue_rows, False: red_rows}
        self.game = SimpleNamespace(
            last_sitrep=None,
            last_flight_cards=[
                FlightCard(
                    name=f"Senaki Strike|{n}|FA-18C_hornet|",
                    task="Strike",
                    aircraft="4 x F/A-18C Hornet (Lot 20)",
                    player=n == 0,
                    grade=Grade.AVERAGE,
                    lines=("On time at the target.", "8 weapons released, 5 hits."),
                    faults=("Lost 1 of 4 aircraft.",),
                    squadron='VFA-103 "Jolly Rogers"',
                    target="Senaki",
                )
                for n in range(cards)
            ],
        )

    def front_line_losses_by_type(self, player: Player) -> dict[str, int]:
        return {f"Unit type {n}": n + 1 for n in range(self.rows[player.is_blue])}

    def _none(self, player: Player) -> dict[Any, int]:
        return {}

    aircraft_losses_by_type = _none
    motorpool_losses_by_type = _none
    convoy_losses_by_type = _none
    cargo_ship_losses_by_type = _none
    airlift_losses_by_type = _none
    ground_object_losses_by_type = _none
    scenery_losses_by_type = _none

    def loss_counts(self, player: Player) -> Any:
        return SimpleNamespace(aircraft=0, front_line=0, ground_objects=0, bases_lost=0)

    def rescued_pilots_for(self, player: Player) -> list[Any]:
        return []


def _window(blue_rows: int = 7, red_rows: int = 30, cards: int = 12) -> Any:
    from qt_ui.windows.QDebriefingWindow import QDebriefingWindow

    window = QDebriefingWindow(_Debriefing(blue_rows, red_rows, cards))  # type: ignore[arg-type]
    window.resize(window.sizeHint())
    # A hidden window is only laid out when it is painted.
    window.grab()
    # The caller must hold this: Qt deletes the children with the window.
    return window


def test_a_short_loss_list_is_shown_whole(qapp: Any) -> None:
    window = _window()
    area = window.player_lost_units.scroll_area
    assert area.viewport().height() >= area.widget().sizeHint().height()


def test_a_long_loss_list_scrolls_past_ten_rows(qapp: Any) -> None:
    from qt_ui.windows.QDebriefingWindow import LOSS_ROWS_BEFORE_SCROLL

    window = _window()
    area = window.enemy_lost_units.scroll_area
    full = area.widget().sizeHint().height()
    assert area.sizeHint().height() == round(full * LOSS_ROWS_BEFORE_SCROLL / 30)
    assert area.viewport().height() >= area.sizeHint().height()


def test_a_loss_list_fills_its_box(qapp: Any) -> None:
    window = _window()
    for box in (window.player_lost_units, window.enemy_lost_units):
        assert box.scroll_area.widget().width() == box.scroll_area.viewport().width()


def test_no_losses_reads_none(qapp: Any) -> None:
    from PySide6.QtWidgets import QLabel

    window = _window(blue_rows=0)
    box = window.player_lost_units
    assert [label.text() for label in box.findChildren(QLabel)] == ["None"]


def test_the_report_cards_do_not_set_the_window_height(qapp: Any) -> None:
    assert _window(cards=40).sizeHint().height() == _window(cards=3).sizeHint().height()


def test_a_debrief_with_no_cards_is_one_column(qapp: Any) -> None:
    assert _window(cards=0).sizeHint().width() < _window(cards=3).sizeHint().width()
