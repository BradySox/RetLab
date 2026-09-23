"""The My aircraft window (§102) builds offscreen, and old saves load with no points."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from types import SimpleNamespace
from typing import Iterator

import pytest
from PySide6.QtWidgets import QApplication

from game.squadrons.squadron import Squadron


@pytest.fixture(scope="module", autouse=True)
def _qt_app() -> Iterator[QApplication]:
    app = QApplication.instance() or QApplication([])
    assert isinstance(app, QApplication)
    yield app


def test_the_window_opens_with_no_game_and_says_so() -> None:
    from qt_ui.windows.playable import PlayableAircraftDialog

    dialog = PlayableAircraftDialog(SimpleNamespace(game=None))
    assert dialog.windowTitle() == "My aircraft"
    assert [dialog.tabs.tabText(i) for i in range(dialog.tabs.count())] == [
        "Saved points",
        "Payload",
        "DTC",
    ]
    assert dialog.selected is None
    assert dialog.empty.isVisibleTo(dialog)
    assert not dialog.splitter.isVisibleTo(dialog)


def test_a_squadron_saved_before_the_feature_has_no_points() -> None:
    squadron = Squadron.__new__(Squadron)
    squadron.__setstate__({"name": "VFA-83"})
    assert squadron.saved_points == []


def test_the_points_pane_numbers_as_the_jet_does() -> None:
    from game.ato.dtcoptions import DtcOptions
    from game.ato.flightwaypointtype import FlightWaypointType
    from game.ato.savedpoints import PointKind, SavedPoint
    from qt_ui.windows.playable.model import Aircraft
    from qt_ui.windows.playable.rows import NAME, PointsModel

    points = [
        SavedPoint(kind=PointKind.WAYPOINT, name="SMOKE", x=0.0, y=0.0),
        SavedPoint(kind=PointKind.IP, name="", x=0.0, y=0.0),
    ]
    route = [FlightWaypointType.TAKEOFF] + [FlightWaypointType.NAV] * 5
    flight = SimpleNamespace(
        unit_type=SimpleNamespace(dcs_unit_type=SimpleNamespace(id="F-16C_50")),
        squadron=SimpleNamespace(saved_points=points),
        flight_plan=SimpleNamespace(
            waypoints=[SimpleNamespace(waypoint_type=k) for k in route]
        ),
        dtc_options=DtcOptions(),
    )
    model = PointsModel()
    model.show(Aircraft(flight), lambda _point: "")
    texts = [model.data(model.index(row, NAME)) for row in range(model.rowCount())]

    # The route takes steerpoints 1-5; 24 less the route and the two points is 17.
    assert texts == [
        "WAYPOINTS   1 · room for 17 more in the jet",
        "W6   SMOKE",
        "IPs   1 · room for 17 more in the jet",
        "IP7   Unnamed (double-click to name)",
        "ORBITS   0 · room for 3 more in the jet",
    ]
