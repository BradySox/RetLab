"""Putting a point or a drawing from the map into one of the player's own aircraft.

Ported from juanjux/dcs-escalation (LGPL-3.0); kinds, orbits and drawings are §102.
"""

from __future__ import annotations

from uuid import UUID

from dcs.mapping import LatLng, Point
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from game import Game
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

router: APIRouter = APIRouter(prefix="/saved-points")


class SavedPointJs(BaseModel):
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
    lat: float
    lng: float
    altitude_ft: int = 0
    heading_deg: int = 90
    length_nm: float = DEFAULT_ORBIT_LENGTH_NM


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


def _describe(game: Game, flight: object) -> ReceiverJs:
    from game.ato.flight import Flight

    assert isinstance(flight, Flight)
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


def _player_flight(game: Game, flight_id: UUID) -> object:
    flight = game.db.flights.get(flight_id)
    if flight.client_count <= 0:
        raise HTTPException(
            status_code=400, detail="Nobody is flying that aircraft to read it"
        )
    return flight


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
    if not add_point(flight, saved):  # type: ignore[arg-type]
        raise HTTPException(status_code=409, detail="No room for another")
    return _describe(game, flight)


@router.delete(
    "/{flight_id}/{index}", operation_id="remove_saved_point", response_model=ReceiverJs
)
def remove(
    flight_id: UUID, index: int, game: Game = Depends(GameContext.require)
) -> ReceiverJs:
    flight = game.db.flights.get(flight_id)
    if not remove_point(flight, index):
        raise HTTPException(status_code=404, detail="No such point")
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
    if not add_drawing(flight, saved):  # type: ignore[arg-type]
        raise HTTPException(status_code=400, detail="A line needs two points")
    return _describe(game, flight)


@router.delete(
    "/{flight_id}/drawings/{index}",
    operation_id="remove_saved_drawing",
    response_model=ReceiverJs,
)
def remove_line(
    flight_id: UUID, index: int, game: Game = Depends(GameContext.require)
) -> ReceiverJs:
    flight = game.db.flights.get(flight_id)
    if not remove_drawing(flight, index):
        raise HTTPException(status_code=404, detail="No such drawing")
    return _describe(game, flight)
