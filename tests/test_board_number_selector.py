"""The payload tab's board-number control (§62).

A pinned number is the lead's; the wingmen follow in order. A number another
flight of the coalition holds is refused, so no two packages share a modex.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from types import SimpleNamespace
from typing import Any, Iterator

import pytest


@pytest.fixture(scope="module")
def qapp() -> Iterator[Any]:
    from PySide6.QtWidgets import QApplication

    yield QApplication.instance() or QApplication([])


def _flight(ato: Any, count: int, board_number: int | None = None) -> Any:
    flight = SimpleNamespace(
        count=count,
        board_number=board_number,
        squadron=SimpleNamespace(
            coalition=SimpleNamespace(ato=ato),
            aircraft=SimpleNamespace(dcs_unit_type=SimpleNamespace(id="FA-18C_hornet")),
        ),
        unit_type=SimpleNamespace(dcs_unit_type=SimpleNamespace(id="FA-18C_hornet")),
        package=SimpleNamespace(
            package_description="Strike", target=SimpleNamespace(name="Bridge")
        ),
    )
    return flight


def _ato(*flights: Any) -> Any:
    ato = SimpleNamespace(packages=[])
    ato.packages.append(SimpleNamespace(flights=list(flights)))
    return ato


def _selector(flight: Any) -> Any:
    from qt_ui.windows.mission.flight.payload.QFlightPayloadTab import (
        BoardNumberSelector,
    )

    return BoardNumberSelector(flight)


def test_setting_a_number_pins_the_whole_flight(qapp: Any) -> None:
    ato = _ato()
    flight = _flight(ato, 4)
    ato.packages[0].flights.append(flight)
    selector = _selector(flight)

    selector.enabled.setChecked(True)
    selector.number.setValue(105)

    assert flight.board_number == 105
    assert "105, 106, 107, 108" in selector.summary.text()


def test_a_number_held_by_another_package_is_refused(qapp: Any) -> None:
    ato = _ato()
    holder = _flight(ato, 2, 106)
    flight = _flight(ato, 4)
    ato.packages[0].flights.extend([holder, flight])
    selector = _selector(flight)

    selector.enabled.setChecked(True)
    selector.number.setValue(105)

    # Ticking the box applied the default 100-103; 105-108 overlaps 106.
    assert flight.board_number == 100
    assert "Not applied: 106 belongs to" in selector.summary.text()
    assert "Keeping 100" in selector.summary.text()


def test_unticking_returns_the_flight_to_automatic(qapp: Any) -> None:
    ato = _ato()
    flight = _flight(ato, 2, 210)
    ato.packages[0].flights.append(flight)
    selector = _selector(flight)

    assert selector.enabled.isChecked()
    selector.enabled.setChecked(False)

    assert flight.board_number is None
