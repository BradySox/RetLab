"""§131 stage 4: the Deploy reserve window previews and sends a reserve group."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from typing import Any, Iterator
from unittest.mock import patch

import pytest
from dcs import Point

from tests.groundmovement.test_armor_movement_planning import world  # noqa: F401
from tests.groundmovement.test_base_reserve_groups import stock  # noqa: F401


@pytest.fixture(scope="module")
def app() -> Iterator[Any]:
    from PySide6.QtWidgets import QApplication

    yield QApplication.instance() or QApplication([])


def test_a_reserve_previews_then_sends(app: Any, stock: Any) -> None:
    from qt_ui.windows.basemenu.reservedialog import ReserveDeployDialog

    dialog = ReserveDeployDialog(stock.game, stock.a)
    dialog.counts[stock.units[7]].setValue(1)
    at = Point(80, 10, stock.game.theater.terrain).latlng()
    dialog.coordinates.setText(f"{at.lat:.10f}, {at.lng:.10f}")
    dialog.calculate()
    assert dialog.send_button.isEnabled(), dialog.details.text()
    with patch("qt_ui.windows.basemenu.reservedialog.EventStream"):
        dialog.send()
    assert stock.game.ground_movements.transits


def test_no_coordinates_is_blocked(app: Any, stock: Any) -> None:
    from qt_ui.windows.basemenu.reservedialog import ReserveDeployDialog

    dialog = ReserveDeployDialog(stock.game, stock.a)
    dialog.counts[stock.units[7]].setValue(1)
    dialog.calculate()
    assert not dialog.send_button.isEnabled()
    assert dialog.details.text().startswith("Can't deploy:")
