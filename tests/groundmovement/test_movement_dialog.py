"""§131 stage 3: the Move window previews a route and sends the column."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from typing import Any, Iterator
from unittest.mock import patch

import pytest

from game.groundmovement.orders import DestinationKind
from game.theater.player import Player
from tests.groundmovement.test_armor_movement_dispatch import prepare
from tests.groundmovement.test_armor_movement_planning import world  # noqa: F401


@pytest.fixture(scope="module")
def app() -> Iterator[Any]:
    from PySide6.QtWidgets import QApplication

    yield QApplication.instance() or QApplication([])


def _dialog(world: Any) -> Any:
    from qt_ui.windows.groundobject.movementdialog import ArmorMovementDialog

    return ArmorMovementDialog(world.game, world.source.id, Player.BLUE)


def test_a_base_move_previews_then_sends(app: Any, world: Any) -> None:
    prepare(world)
    dialog = _dialog(world)
    first = next(i for i, box in dialog.units.items() if box.isEnabled())
    dialog.units[first].setChecked(True)
    dialog.kind.setCurrentIndex(dialog.kind.findData(DestinationKind.BASE))
    assert dialog.target.count() >= 1
    dialog.calculate()
    assert dialog.dispatch_button.isEnabled(), dialog.details.text()
    with patch("qt_ui.windows.groundobject.movementdialog.EventStream"):
        dialog.dispatch()
    assert world.game.ground_movements.transits


def test_nothing_selected_is_blocked_with_a_reason(app: Any, world: Any) -> None:
    dialog = _dialog(world)
    dialog.kind.setCurrentIndex(dialog.kind.findData(DestinationKind.BASE))
    dialog.calculate()
    assert not dialog.dispatch_button.isEnabled()
    assert dialog.details.text().startswith("Can't move:")
    assert not world.game.ground_movements.transits
