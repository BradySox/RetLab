"""The Package route window edits the way in and out for the whole package.

Drives the real dialog offscreen over the same faked package the route tests use.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from types import SimpleNamespace
from typing import Any, Iterator, cast

import pytest

from tests.ato.test_package_route import _package, _point


@pytest.fixture(scope="module")
def qapp() -> Iterator[Any]:
    from PySide6.QtWidgets import QApplication

    yield QApplication.instance() or QApplication([])


class _Events:
    def update_flights_in_package(self, package: Any) -> "_Events":
        return self


def _dialog(package: Any, monkeypatch: pytest.MonkeyPatch) -> tuple[Any, list[int]]:
    from PySide6.QtGui import QIcon

    from qt_ui.windows.mission import QPackageRouteDialog as module

    # Filled at app startup, which a test never runs.
    monkeypatch.setitem(module.EVENT_ICONS, "strike", QIcon())
    monkeypatch.setattr(module, "GameUpdateEvents", _Events)
    monkeypatch.setattr(module.EventStream, "put_nowait", lambda _events: None)
    retimed: list[int] = []
    package.custom_name = None
    model = SimpleNamespace(
        package=package,
        game_model=SimpleNamespace(game=None),
        update_tot=lambda: retimed.append(1),
    )
    return module.QPackageRouteDialog(cast(Any, model), cast(Any, None)), retimed


def _names(dialog: Any) -> list[str]:
    return [dialog.table.item(r, 0).text() for r in range(dialog.table.rowCount())]


def test_the_window_lists_the_route_in_flying_order(
    qapp: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    dialog, _ = _dialog(_package(egress_nav=1), monkeypatch)
    assert _names(dialog) == [
        "Join",
        "Ingress (IP)",
        "Target: AARDWOLF",
        "Nav",
        "Split",
    ]
    assert dialog.table.item(3, 1).text() == "Way out"


def test_insert_adds_a_point_for_every_flight_and_retimes(
    qapp: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = _package()
    dialog, retimed = _dialog(package, monkeypatch)
    dialog.table.selectRow(0)
    dialog.insert_button.click()
    assert _names(dialog)[1] == "Nav"
    assert dialog.selected_row() == 1
    assert package.waypoints.ingress_nav == [_point(35)]
    assert retimed == [1]
    assert dialog.reset_button.isEnabled()


def test_delete_and_move_act_on_the_selected_nav_point(
    qapp: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = _package(ingress_nav=2)
    dialog, _ = _dialog(package, monkeypatch)
    dialog.table.selectRow(1)
    assert dialog.delete_button.isEnabled()
    assert not dialog.up_button.isEnabled()
    assert dialog.down_button.isEnabled()
    dialog.down_button.click()
    assert package.waypoints.ingress_nav == [_point(31), _point(30)]
    assert dialog.selected_row() == 2
    dialog.delete_button.click()
    assert package.waypoints.ingress_nav == [_point(31)]


def test_fixed_points_cannot_be_deleted_or_moved(
    qapp: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    dialog, _ = _dialog(_package(), monkeypatch)
    dialog.table.selectRow(0)
    assert dialog.insert_button.isEnabled()
    assert not dialog.delete_button.isEnabled()
    assert not dialog.up_button.isEnabled()
    assert not dialog.down_button.isEnabled()
    assert not dialog.reset_button.isEnabled()


def test_a_package_with_no_route_says_so(
    qapp: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = _package()
    package.flights.reverse()
    dialog, _ = _dialog(package, monkeypatch)
    assert dialog.table.rowCount() == 0
    assert not dialog.insert_button.isEnabled()
    assert "no shared route" in dialog.move_hint.text()


def test_the_window_opens_ready_to_insert(
    qapp: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every button opened greyed out until a row was clicked (2026-09-28)."""
    dialog, _ = _dialog(_package(), monkeypatch)
    assert dialog.selected_row() == 0
    assert dialog.insert_button.isEnabled()
    assert "double-click the route" in dialog.move_hint.text()
