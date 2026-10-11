"""A map edit redraws the open My aircraft window, and the window's edits reach the
map (§102).

Ported from juanjux/dcs-escalation (LGPL-3.0).
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from datetime import datetime
from types import SimpleNamespace
from typing import Any, Iterator
from unittest.mock import Mock

import pytest
from dcs.terrain import Caucasus
from PySide6.QtWidgets import QAbstractItemView, QApplication, QWidget

from game.ato.savedpoints import PointKind, SavedDrawing, SavedPoint
from game.server.eventstream.models import GameUpdateEventsJs
from game.server.savedpoints.notifications import publish_points_changed
from qt_ui.windows.GameUpdateSignal import GameUpdateSignal
from qt_ui.windows.playable.dialog import PlayableAircraftDialog
from qt_ui.windows.playable.rows import ELEVATION, NAME


@pytest.fixture
def dialog(monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    app = QApplication.instance() or QApplication([])
    previous_signal = GameUpdateSignal.instance
    signal = GameUpdateSignal()
    monkeypatch.setattr(GameUpdateSignal, "instance", signal)
    point = SavedPoint(PointKind.WAYPOINT, "TARGET", 0, 0, 100)
    member = SimpleNamespace(is_player=True, pilot=SimpleNamespace(name="Pilot"))
    flight = SimpleNamespace(
        iter_members=lambda: iter([member]),
        client_count=1,
        custom_name="Hawg",
        unit_type=SimpleNamespace(
            dcs_unit_type=SimpleNamespace(id="A-10C_2"),
            display_name="A-10C II",
            helicopter=False,
        ),
        squadron=SimpleNamespace(
            nickname="Hawg", name="Squadron", saved_points=[point]
        ),
        saved_drawings=[],
        flight_type=SimpleNamespace(value="Strike"),
        package=None,
    )
    game = SimpleNamespace(
        blue=SimpleNamespace(
            ato=SimpleNamespace(packages=[SimpleNamespace(flights=[flight])])
        ),
        settings=SimpleNamespace(coordinate_format=None),
        theater=SimpleNamespace(terrain=Caucasus()),
        turn=1,
        conditions=SimpleNamespace(start_time=datetime(2026, 1, 1)),
    )
    send = Mock()
    monkeypatch.setattr(
        "game.server.savedpoints.notifications.EventStream.put_nowait", send
    )
    # The real Payload tab needs a real flight; this window's points do not.
    monkeypatch.setattr(
        PlayableAircraftDialog, "_payload_tab", lambda self, flight: QWidget()
    )
    window = PlayableAircraftDialog(SimpleNamespace(game=game))
    window.points_view.setCurrentIndex(window.points_model.index(1, NAME))
    yield SimpleNamespace(app=app, window=window, point=point, flight=flight, send=send)
    window.close()
    window.deleteLater()
    app.processEvents()
    GameUpdateSignal.instance = previous_signal


def test_a_map_edit_redraws_the_points_and_keeps_the_seat_the_tab_and_the_selection(
    dialog: Any,
) -> None:
    window = dialog.window
    selected = window.selected
    window.tabs.setCurrentIndex(window.dtc_index)
    payload = window.tabs.widget(window.payload_index)
    dialog.point.name = "BRIDGE"
    dialog.point.altitude_ft = 420

    publish_points_changed()
    dialog.app.processEvents()

    assert window.selected is selected
    assert window.current_point().point is dialog.point
    assert window.tabs.currentIndex() == window.dtc_index
    assert window.tabs.widget(window.payload_index) is payload
    assert "BRIDGE" in window.points_model.index(1, NAME).data()
    assert window.points_model.index(1, ELEVATION).data() == "420 ft"
    event = dialog.send.call_args.args[0]
    assert GameUpdateEventsJs.from_events(event, None).saved_points_updated


def test_a_map_deletion_redraws_the_open_list(dialog: Any) -> None:
    dialog.flight.squadron.saved_points.clear()

    publish_points_changed()
    dialog.app.processEvents()

    assert dialog.window.current_point() is None
    assert dialog.window.selected.total_used == 0
    assert not dialog.window.copy_all.isEnabled()


def test_a_drawing_made_on_the_map_appears_in_the_open_window(dialog: Any) -> None:
    dialog.flight.saved_drawings.append(SavedDrawing("FLOT", [(0.0, 0.0), (1.0, 1.0)]))

    publish_points_changed()
    dialog.app.processEvents()

    assert dialog.window.drawings_view.count() == 1


def test_the_window_s_rename_elevation_and_delete_tell_the_map(dialog: Any) -> None:
    window = dialog.window
    model = window.points_model

    assert model.setData(model.index(1, NAME), "RENAMED")
    assert dialog.point.name == "RENAMED"
    assert dialog.send.call_args.args[0].saved_points_updated
    assert model.setData(model.index(1, ELEVATION), "250")
    assert dialog.point.altitude_ft == 250
    assert dialog.send.call_count == 2
    dialog.app.processEvents()

    window.delete_current()

    assert dialog.flight.squadron.saved_points == []
    assert dialog.send.call_count == 3


def test_a_stale_selection_neither_deletes_nor_renames_the_next_point(
    dialog: Any,
) -> None:
    other = SavedPoint(PointKind.WAYPOINT, "OTHER", 1, 1)
    # The map has deleted the point; the window has not yet had its queued refresh.
    dialog.flight.squadron.saved_points[:] = [other]
    window = dialog.window
    model = window.points_model

    assert not model.setData(model.index(1, NAME), "WRONG")
    assert not model.setData(model.index(1, ELEVATION), "999")
    window.delete_current()

    assert dialog.flight.squadron.saved_points == [other]
    assert (other.name, other.altitude_ft) == ("OTHER", 0)


def test_a_closed_window_stops_redrawing(dialog: Any) -> None:
    window = dialog.window
    # Closing also reports the seat as an edited flight, which this fake is not.
    window.editing = None
    window.finished.emit(0)
    rows = window.points_model.rowCount()
    dialog.flight.squadron.saved_points.append(
        SavedPoint(PointKind.WAYPOINT, "LATER", 1, 1)
    )

    publish_points_changed()
    dialog.app.processEvents()

    assert window.points_model.rowCount() == rows


def test_a_refresh_does_not_close_the_cell_being_typed_in(dialog: Any) -> None:
    """The window's own rename comes back as a refresh, after Tab has already
    opened the next cell."""
    window = dialog.window
    view = window.points_view
    view.edit(window.points_model.index(1, ELEVATION))
    assert view.state() == QAbstractItemView.State.EditingState

    publish_points_changed()
    dialog.app.processEvents()

    assert view.state() == QAbstractItemView.State.EditingState
