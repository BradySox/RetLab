"""Map pins edit the same saved points the My aircraft window shows (§102).

Ported from juanjux/dcs-escalation (LGPL-3.0). The routes are called directly, as
the other route tests here do: the HTTP test client is not a dependency.
"""

from __future__ import annotations

import pickle
from types import SimpleNamespace
from typing import Any, Callable, Iterator
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from dcs.mapping import LatLng, Point
from dcs.terrain import Caucasus
from fastapi import HTTPException
from pydantic import ValidationError

from game.ato.flight import Flight
from game.ato.savedpoints import (
    PointKind,
    SavedDrawing,
    SavedPoint,
    drawings_of,
    points_of,
)
from game.server.leaflet import LeafletPoint
from game.server.savedpoints import routes
from game.server.savedpoints.routes import (
    NewDrawingJs,
    NewPointJs,
    SavedPointEdit,
    SavedPointPosition,
)
from qt_ui.windows.playable.model import Aircraft, Clipboard


def _flight() -> Any:
    flight = MagicMock(spec=Flight)
    flight.id = uuid4()
    flight.client_count = 1
    flight.custom_name = "Hawg"
    flight.unit_type = SimpleNamespace(
        dcs_unit_type=SimpleNamespace(id="FA-18C_hornet"), display_name="F/A-18C"
    )
    flight.departure = SimpleNamespace(name="Base")
    flight.squadron = SimpleNamespace(saved_points=[])
    return flight


def _move(lat: float = 43, lng: float = 43, name: str | None = None) -> SavedPointEdit:
    return SavedPointEdit(name=name, position=SavedPointPosition(lat=lat, lng=lng))


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    flight = _flight()
    terrain = Caucasus()
    at = Point.from_latlng(LatLng(42, 42), terrain)
    point = SavedPoint(PointKind.WAYPOINT, "Target", at.x, at.y, 100)
    points_of(flight).append(point)
    flights = {flight.id: flight}
    package = SimpleNamespace(flights=[flight])
    game = SimpleNamespace(
        blue=SimpleNamespace(ato=SimpleNamespace(packages=[package])),
        db=SimpleNamespace(flights=SimpleNamespace(get=lambda key: flights[key])),
        theater=SimpleNamespace(terrain=terrain),
        settings=SimpleNamespace(coordinate_format=None),
    )
    notify = MagicMock()
    monkeypatch.setattr(routes, "publish_points_changed", notify)
    monkeypatch.setattr("game.elevation.elevation_ft", lambda lat, lng: 321)
    yield SimpleNamespace(
        game=game,
        flight=flight,
        point=point,
        package=package,
        flights=flights,
        notify=notify,
    )


def _status(call: Callable[[], Any]) -> int:
    with pytest.raises(HTTPException) as refused:
        call()
    return refused.value.status_code


def test_an_old_point_is_given_an_id_once_and_the_save_keeps_it() -> None:
    point = SavedPoint(PointKind.WAYPOINT, "Old", 1, 2)
    del point.id
    # As a save from before the id unpickles: through __setstate__, with no id.
    old = pickle.loads(pickle.dumps(point))
    assert not hasattr(old, "id")
    flight = _flight()
    flight.squadron.saved_points = [old]

    migrated = points_of(flight)[0]
    identity = migrated.id

    assert points_of(flight)[0].id == identity
    assert pickle.loads(pickle.dumps(migrated)).id == identity
    assert migrated == SavedPoint(PointKind.WAYPOINT, "Old", 1, 2)


def test_two_points_written_down_alike_have_their_own_ids() -> None:
    first = SavedPoint(PointKind.WAYPOINT, "Same", 1, 2)
    second = SavedPoint(PointKind.WAYPOINT, "Same", 1, 2)

    assert first == second
    assert first.id != second.id


def test_a_pasted_point_is_not_the_point_it_was_copied_from() -> None:
    source, target = _flight(), _flight()
    original = SavedPoint(PointKind.WAYPOINT, "Target", 1, 2)
    points_of(source).append(original)
    clipboard = Clipboard()

    clipboard.take_one(original, "Source")
    assert clipboard.paste_into(Aircraft(target)) == 1
    assert clipboard.paste_into(Aircraft(target)) == 1
    clipboard.take(Aircraft(source))
    assert clipboard.paste_into(Aircraft(target)) == 1

    assert len({original.id, *(point.id for point in points_of(target))}) == 4


def test_the_list_carries_the_position_and_one_id_for_a_shared_point(api: Any) -> None:
    another = _flight()
    another.squadron = api.flight.squadron
    api.package.flights.append(another)

    body = routes.list_receivers(api.game)

    assert [one.points[0].id for one in body] == [api.point.id] * 2
    assert body[0].points[0].position.lat == pytest.approx(42)
    assert body[0].points[0].position.lng == pytest.approx(42)


def test_saving_from_the_picker_notifies_and_returns_the_pin(api: Any) -> None:
    new = NewPointJs(kind="waypoint", name="New", lat=43, lng=43)

    body = routes.add(api.flight.id, new, api.game)

    assert body.points[-1].id == points_of(api.flight)[-1].id
    api.notify.assert_called_once()


def test_a_rename_changes_the_same_object_and_does_not_move_it(api: Any) -> None:
    before = api.point.x, api.point.y, api.point.altitude_ft

    routes.edit(api.flight.id, api.point.id, SavedPointEdit(name=" Renamed "), api.game)

    assert api.point.name == "Renamed"
    assert (api.point.x, api.point.y, api.point.altitude_ft) == before
    assert points_of(api.flight)[0] is api.point
    api.notify.assert_called_once()


def test_an_empty_name_keeps_the_old_one(api: Any) -> None:
    routes.edit(api.flight.id, api.point.id, SavedPointEdit(name="   "), api.game)

    assert api.point.name == "Target"


@pytest.mark.parametrize("height", [None, 456])
def test_a_drag_moves_the_point_and_takes_the_ground_height_when_there_is_one(
    api: Any, monkeypatch: pytest.MonkeyPatch, height: Any
) -> None:
    monkeypatch.setattr("game.elevation.elevation_ft", lambda lat, lng: height)

    body = routes.edit(api.flight.id, api.point.id, _move(), api.game)

    actual = Point(api.point.x, api.point.y, api.game.theater.terrain).latlng()
    assert actual.lat == pytest.approx(43)
    assert actual.lng == pytest.approx(43)
    assert api.point.altitude_ft == (100 if height is None else height)
    assert body.points[0].position.lat == pytest.approx(43)
    api.notify.assert_called_once()


def test_a_dragged_orbit_keeps_its_racetrack_and_the_far_end_follows(api: Any) -> None:
    orbit = SavedPoint(
        PointKind.ORBIT,
        "CAP",
        api.point.x,
        api.point.y,
        heading_deg=135,
        length_nm=30.0,
    )
    points_of(api.flight).append(orbit)
    start = orbit.x, orbit.y
    end = orbit.orbit_end()
    leg = end[0] - start[0], end[1] - start[1]

    body = routes.edit(api.flight.id, orbit.id, _move(), api.game)

    assert (orbit.heading_deg, orbit.length_nm) == (135, 30.0)
    assert (orbit.x, orbit.y) != start
    moved = orbit.orbit_end()
    assert moved[0] - orbit.x == pytest.approx(leg[0])
    assert moved[1] - orbit.y == pytest.approx(leg[1])
    served = next(one for one in body.points if one.id == orbit.id)
    there = Point(moved[0], moved[1], api.game.theater.terrain).latlng()
    assert served.end.lat == pytest.approx(there.lat)
    assert served.end.lng == pytest.approx(there.lng)
    assert (served.heading_deg, served.length_nm) == (135, 30.0)


def test_a_deleted_point_is_not_stood_in_for_by_the_next_one(api: Any) -> None:
    other = SavedPoint(PointKind.WAYPOINT, "Other", 1, 2)
    points_of(api.flight).append(other)
    flight, point = api.flight.id, api.point.id

    routes.delete_by_id(flight, point, api.game)

    rename = SavedPointEdit(name="Wrong")
    assert _status(lambda: routes.edit(flight, point, rename, api.game)) == 404
    assert _status(lambda: routes.delete_by_id(flight, point, api.game)) == 404
    assert points_of(api.flight) == [other]
    assert other.name == "Other"
    api.notify.assert_called_once()


def test_deleting_by_the_old_index_still_works_and_notifies(api: Any) -> None:
    routes.remove(api.flight.id, 0, api.game)

    assert points_of(api.flight) == []
    api.notify.assert_called_once()
    assert _status(lambda: routes.remove(api.flight.id, 0, api.game)) == 404


def test_drawings_notify_too(api: Any) -> None:
    corners = [LeafletPoint(lat=42, lng=42), LeafletPoint(lat=42.1, lng=42.1)]

    routes.add_line(api.flight.id, NewDrawingJs(name="FLOT", points=corners), api.game)
    assert [one.name for one in drawings_of(api.flight)] == ["FLOT"]
    routes.remove_line(api.flight.id, 0, api.game)

    assert drawings_of(api.flight) == []
    assert api.notify.call_count == 2


_ROUTES: dict[str, Callable[[Any], Any]] = {
    "rename": lambda api: routes.edit(
        api.flight.id, api.point.id, SavedPointEdit(name="Wrong"), api.game
    ),
    "delete": lambda api: routes.delete_by_id(api.flight.id, api.point.id, api.game),
    "add": lambda api: routes.add(
        api.flight.id, NewPointJs(kind="waypoint", name="Wrong", lat=1, lng=1), api.game
    ),
    "delete by index": lambda api: routes.remove(api.flight.id, 0, api.game),
    "draw": lambda api: routes.add_line(
        api.flight.id,
        NewDrawingJs(
            name="Wrong",
            points=[LeafletPoint(lat=42, lng=42), LeafletPoint(lat=43, lng=43)],
        ),
        api.game,
    ),
    "delete drawing": lambda api: routes.remove_line(api.flight.id, 0, api.game),
}


@pytest.mark.parametrize("mode", ["cancelled", "ai", "enemy", "unknown"])
@pytest.mark.parametrize("route", list(_ROUTES))
def test_only_a_blue_flight_the_player_is_flying_can_be_edited(
    api: Any, mode: str, route: str
) -> None:
    drawings_of(api.flight).append(SavedDrawing("Line", [(0.0, 0.0), (1.0, 1.0)]))
    if mode == "ai":
        api.flight.client_count = 0
    elif mode == "unknown":
        api.flights.clear()
    else:
        # A cancelled flight and a red one are both absent from blue's ATO.
        api.package.flights.clear()

    status = _status(lambda: _ROUTES[route](api))

    assert status == (404 if mode == "unknown" else 403)
    assert [one.name for one in points_of(api.flight)] == ["Target"]
    assert len(drawings_of(api.flight)) == 1
    api.notify.assert_not_called()


def test_a_point_deleted_during_the_elevation_lookup_is_not_moved(
    api: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    before = api.point.x, api.point.y

    def lookup(lat: float, lng: float) -> int:
        points_of(api.flight).clear()
        return 321

    monkeypatch.setattr("game.elevation.elevation_ft", lookup)

    status = _status(
        lambda: routes.edit(api.flight.id, api.point.id, _move(name="Wrong"), api.game)
    )

    assert status == 404
    assert api.point.name == "Target"
    assert (api.point.x, api.point.y) == before
    api.notify.assert_not_called()


@pytest.mark.parametrize(
    "position",
    [{"lat": 100, "lng": 42}, {"lat": 42, "lng": 181}, {"lat": "nan", "lng": 42}],
)
def test_a_position_off_the_globe_is_refused_before_anything_is_applied(
    position: dict[str, Any],
) -> None:
    """Validation fails the whole request, so a rename sent with it is not applied."""
    with pytest.raises(ValidationError):
        SavedPointEdit.model_validate({"name": "Wrong", "position": position})
    with pytest.raises(ValidationError):
        NewPointJs.model_validate({"kind": "waypoint", "name": "Wrong", **position})
