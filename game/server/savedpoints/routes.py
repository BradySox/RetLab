"""Putting a point or a drawing from the map into one of the player's own aircraft.

Ported from juanjux/dcs-escalation (LGPL-3.0); kinds, orbits and drawings are §102.
"""

from __future__ import annotations

from uuid import UUID

from dcs.mapping import LatLng, Point
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from game import Game
from game.ato.flight import Flight
from game.ato.savedpoints import (
    DEFAULT_ORBIT_LENGTH_NM,
    PointKind,
    SavedDrawing,
    SavedPoint,
    add_drawing,
    add_point,
    drawing_capacity_for,
    drawings_of,
    kinds_for,
    points_of,
    receivers,
    remove_drawing,
    remove_point,
    room_for,
)
from game.coordinates import coordinate_format, format_latlng
from game.server import GameContext
from game.server.leaflet import LeafletPoint
from .notifications import publish_points_changed

router: APIRouter = APIRouter(prefix="/saved-points")


class SavedPointJs(BaseModel):
    id: UUID
    kind: str
    name: str
    #: Written in the campaign's coordinate format, as the kneeboard writes it.
    coordinates: str
    altitude_ft: int
    position: LeafletPoint
    heading_deg: int
    length_nm: float
    #: An orbit's far end; the point itself otherwise.
    end: LeafletPoint


class SavedDrawingJs(BaseModel):
    name: str
    points: list[LeafletPoint]
    closed: bool


class ReceiverJs(BaseModel):
    """One aircraft the player is flying, and what it will still take."""

    id: UUID
    #: The flight's own name if it has one, otherwise its task.
    callsign: str
    aircraft: str
    departure: str
    #: The kinds this airframe can be handed; a kind it cannot take is not offered.
    kinds: list[str]
    #: How many more of each kind it has room for, keyed by kind.
    room: dict[str, int]
    points: list[SavedPointJs]
    drawings: list[SavedDrawingJs]
    #: How many drawings its cartridge takes; 0 means kneeboard and map only.
    drawing_room: int


class NewPointJs(BaseModel):
    kind: str
    name: str
    lat: float = Field(ge=-90, le=90, allow_inf_nan=False)
    lng: float = Field(ge=-180, le=180, allow_inf_nan=False)
    altitude_ft: int = 0
    heading_deg: int = 90
    length_nm: float = DEFAULT_ORBIT_LENGTH_NM


class SavedPointPosition(BaseModel):
    lat: float = Field(ge=-90, le=90, allow_inf_nan=False)
    lng: float = Field(ge=-180, le=180, allow_inf_nan=False)


class SavedPointEdit(BaseModel):
    """What a map pin can change: the name, where the point is, or both."""

    name: str | None = None
    position: SavedPointPosition | None = None


class NewDrawingJs(BaseModel):
    name: str
    points: list[LeafletPoint]
    closed: bool = False


def _kind(name: str) -> PointKind:
    try:
        return PointKind(name)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"No such kind of point: {name}")


def _latlng(game: Game, x: float, y: float) -> LeafletPoint:
    at = Point(x, y, game.theater.terrain).latlng()
    return LeafletPoint(lat=at.lat, lng=at.lng)


def _describe(game: Game, flight: Flight) -> ReceiverJs:
    aircraft = flight.unit_type.dcs_unit_type.id
    chosen = coordinate_format(game.settings)
    drawings, _vertices = drawing_capacity_for(aircraft)
    points = []
    for point in points_of(flight):
        end_x, end_y = (
            point.orbit_end() if point.kind is PointKind.ORBIT else (point.x, point.y)
        )
        points.append(
            SavedPointJs(
                id=point.id,
                kind=point.kind.value,
                name=point.name,
                coordinates=format_latlng(
                    Point(point.x, point.y, game.theater.terrain).latlng(), chosen
                ),
                altitude_ft=point.altitude_ft,
                position=_latlng(game, point.x, point.y),
                heading_deg=point.heading_deg,
                length_nm=point.length_nm,
                end=_latlng(game, end_x, end_y),
            )
        )
    return ReceiverJs(
        id=flight.id,
        callsign=flight.custom_name or str(flight.flight_type.value),
        aircraft=flight.unit_type.display_name,
        departure=flight.departure.name,
        kinds=[kind.value for kind in kinds_for(aircraft)],
        room={kind.value: room_for(flight, kind) for kind in PointKind},
        points=points,
        drawings=[
            SavedDrawingJs(
                name=drawing.name,
                points=[_latlng(game, x, y) for x, y in drawing.points],
                closed=drawing.closed,
            )
            for drawing in drawings_of(flight)
        ],
        drawing_room=max(drawings - len(drawings_of(flight)), 0),
    )


def _player_flight(game: Game, flight_id: UUID) -> Flight:
    """The flight, if it is one the player is flying on blue's ATO this turn."""
    try:
        flight = game.db.flights.get(flight_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="No such flight")
    if not any(one is flight for one in receivers(game.blue)):
        raise HTTPException(status_code=403, detail="Not a player aircraft")
    return flight


def _point(game: Game, flight_id: UUID, point_id: UUID) -> SavedPoint:
    for point in points_of(_player_flight(game, flight_id)):
        if point.id == point_id:
            return point
    raise HTTPException(status_code=404, detail="No such point")


@router.get("/", operation_id="list_point_receivers", response_model=list[ReceiverJs])
def list_receivers(game: Game = Depends(GameContext.require)) -> list[ReceiverJs]:
    """Every aircraft the player is actually flying this turn."""
    return [_describe(game, flight) for flight in receivers(game.blue)]


@router.post("/{flight_id}", operation_id="add_saved_point", response_model=ReceiverJs)
def add(
    flight_id: UUID,
    point: NewPointJs,
    game: Game = Depends(GameContext.require),
) -> ReceiverJs:
    flight = _player_flight(game, flight_id)
    at = Point.from_latlng(LatLng(point.lat, point.lng), game.theater.terrain)
    saved = SavedPoint(
        kind=_kind(point.kind),
        name=point.name.strip()[:24] or "Point",
        x=at.x,
        y=at.y,
        altitude_ft=max(0, point.altitude_ft),
        heading_deg=point.heading_deg % 360,
        length_nm=max(1.0, point.length_nm),
    )
    if not add_point(flight, saved):
        raise HTTPException(status_code=409, detail="No room for another")
    publish_points_changed()
    return _describe(game, flight)


@router.patch(
    "/{flight_id}/points/{point_id}",
    operation_id="edit_saved_point",
    response_model=ReceiverJs,
)
def edit(
    flight_id: UUID,
    point_id: UUID,
    changes: SavedPointEdit,
    game: Game = Depends(GameContext.require),
) -> ReceiverJs:
    """Rename a point, move it, or both. A moved orbit keeps its heading and length,
    so its far end moves with it."""
    point = _point(game, flight_id, point_id)
    at = None
    height = None
    if changes.position is not None:
        # Everything that can fail runs before the name changes: no half-applied edit.
        at = Point.from_latlng(
            LatLng(changes.position.lat, changes.position.lng), game.theater.terrain
        )
        from game.elevation import elevation_ft

        height = elevation_ft(changes.position.lat, changes.position.lng)
        # The lookup can take seconds, in which the window may delete the point or
        # its flight. Found again, so an edit never lands on a detached point.
        point = _point(game, flight_id, point_id)
    if changes.name is not None:
        point.name = changes.name.strip()[:24] or point.name
    if at is not None:
        point.x, point.y = at.x, at.y
        if height is not None:
            point.altitude_ft = max(0, height)
    publish_points_changed()
    return _describe(game, _player_flight(game, flight_id))


@router.delete(
    "/{flight_id}/points/{point_id}",
    operation_id="delete_saved_point_by_id",
    response_model=ReceiverJs,
)
def delete_by_id(
    flight_id: UUID, point_id: UUID, game: Game = Depends(GameContext.require)
) -> ReceiverJs:
    point = _point(game, flight_id, point_id)
    flight = _player_flight(game, flight_id)
    points_of(flight)[:] = [one for one in points_of(flight) if one is not point]
    publish_points_changed()
    return _describe(game, flight)


@router.delete(
    "/{flight_id}/{index}", operation_id="remove_saved_point", response_model=ReceiverJs
)
def remove(
    flight_id: UUID, index: int, game: Game = Depends(GameContext.require)
) -> ReceiverJs:
    flight = _player_flight(game, flight_id)
    if not remove_point(flight, index):
        raise HTTPException(status_code=404, detail="No such point")
    publish_points_changed()
    return _describe(game, flight)


@router.post(
    "/{flight_id}/drawings", operation_id="add_saved_drawing", response_model=ReceiverJs
)
def add_line(
    flight_id: UUID,
    drawing: NewDrawingJs,
    game: Game = Depends(GameContext.require),
) -> ReceiverJs:
    flight = _player_flight(game, flight_id)
    points = [
        Point.from_latlng(LatLng(p.lat, p.lng), game.theater.terrain)
        for p in drawing.points
    ]
    saved = SavedDrawing(
        name=drawing.name.strip()[:24] or ("Area" if drawing.closed else "Line"),
        points=[(p.x, p.y) for p in points],
        closed=drawing.closed,
    )
    if not add_drawing(flight, saved):
        raise HTTPException(status_code=400, detail="A line needs two points")
    publish_points_changed()
    return _describe(game, flight)


@router.delete(
    "/{flight_id}/drawings/{index}",
    operation_id="remove_saved_drawing",
    response_model=ReceiverJs,
)
def remove_line(
    flight_id: UUID, index: int, game: Game = Depends(GameContext.require)
) -> ReceiverJs:
    flight = _player_flight(game, flight_id)
    if not remove_drawing(flight, index):
        raise HTTPException(status_code=404, detail="No such drawing")
    publish_points_changed()
    return _describe(game, flight)
