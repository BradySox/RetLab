from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from dcs.mapping import LatLng, Point
from fastapi import APIRouter, Depends, HTTPException, status
from starlette.responses import Response

from game import Game
from game.ato import Flight, packageroute, routeedit
from game.ato.flightwaypoint import FlightWaypoint
from game.ato.flightwaypointtype import FlightWaypointType
from game.server import GameContext
from game.server.leaflet import LeafletPoint
from game.server.waypoints.models import FlightWaypointJs
from game.sim import GameUpdateEvents
from game.utils import meters

if TYPE_CHECKING:
    from qt_ui.models import PackageModel

router: APIRouter = APIRouter(prefix="/waypoints")


def waypoints_for_flight(flight: Flight) -> list[FlightWaypointJs]:
    departure = FlightWaypointJs.for_waypoint(
        FlightWaypoint(
            "TAKEOFF",
            FlightWaypointType.TAKEOFF,
            flight.departure.position,
            meters(0),
            "RADIO",
        ),
        flight,
        0,
    )
    return [departure] + [
        FlightWaypointJs.for_waypoint(w, flight, i)
        for i, w in enumerate(flight.flight_plan.waypoints, 1)
    ]


@router.get(
    "/{flight_id}",
    operation_id="list_all_waypoints_for_flight",
    response_model=list[FlightWaypointJs],
)
def all_waypoints_for_flight(
    flight_id: UUID, game: Game = Depends(GameContext.require)
) -> list[FlightWaypointJs]:
    return waypoints_for_flight(game.db.flights.get(flight_id))


@router.post(
    "/{flight_id}/{waypoint_idx}/position",
    operation_id="set_waypoint_position",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def set_position(
    flight_id: UUID,
    waypoint_idx: int,
    position: LeafletPoint,
    game: Game = Depends(GameContext.require),
) -> None:
    from game.server import EventStream

    flight = game.db.flights.get(flight_id)
    if waypoint_idx == 0:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    waypoint = flight.flight_plan.waypoints[waypoint_idx - 1]
    waypoint.position = Point.from_latlng(
        LatLng(position.lat, position.lng), game.theater.terrain
    )
    package_model = (
        GameContext.get_model()
        .ato_model_for(flight.blue)
        .find_matching_package_model(flight.package)
    )
    if package_model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not find PackageModel owning {flight}",
        )
    events = GameUpdateEvents()
    update_package_waypoints(waypoint, flight, events)
    package_model.update_tot()
    EventStream.put_nowait(events.update_flight(flight))


@router.post(
    "/{flight_id}/insert",
    operation_id="insert_waypoint",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def insert_waypoint(
    flight_id: UUID,
    position: LeafletPoint,
    game: Game = Depends(GameContext.require),
) -> None:
    """A NAV point where the route was clicked, on the leg nearest the click."""
    flight = game.db.flights.get(flight_id)
    package_model = _package_model(flight)
    point = Point.from_latlng(LatLng(position.lat, position.lng), game.theater.terrain)
    try:
        moved = routeedit.insert_nav_at(flight, point)
    except routeedit.RouteEditRefused as refused:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(refused))
    package_model.update_tot()
    _publish(moved)


@router.delete(
    "/{flight_id}/{waypoint_idx}",
    operation_id="delete_waypoint",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def delete_waypoint(
    flight_id: UUID,
    waypoint_idx: int,
    game: Game = Depends(GameContext.require),
) -> None:
    flight = game.db.flights.get(flight_id)
    if waypoint_idx == 0:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    package_model = _package_model(flight)
    waypoint = flight.flight_plan.waypoints[waypoint_idx - 1]
    try:
        moved = routeedit.delete_nav(flight, waypoint)
    except routeedit.RouteEditRefused as refused:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(refused))
    package_model.update_tot()
    _publish(moved)


def _package_model(flight: Flight) -> PackageModel:
    package_model = (
        GameContext.get_model()
        .ato_model_for(flight.blue)
        .find_matching_package_model(flight.package)
    )
    if package_model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not find PackageModel owning {flight}",
        )
    return package_model


def _publish(flights: list[Flight]) -> None:
    from game.server import EventStream

    events = GameUpdateEvents()
    for flight in flights:
        events.update_flight(flight)
    EventStream.put_nowait(events)


def update_package_waypoints(
    waypoint: FlightWaypoint,
    flight: Flight,
    events: GameUpdateEvents,
) -> None:
    """A dragged package point moves for the whole package (packageroute.py)."""
    wpts = flight.package.waypoints
    if wpts and packageroute.moves_package(flight, waypoint):
        on_route = packageroute.find(flight, waypoint)
        if on_route is not None:
            leg, index = on_route
            packageroute.set_position(flight.package, leg, index, waypoint.position)
            for f in packageroute.route_flights(flight.package):
                if f is not flight:
                    events.update_flight(f)
            return
        if waypoint.waypoint_type is FlightWaypointType.JOIN:
            wpts.join = waypoint.position
        elif waypoint.waypoint_type is FlightWaypointType.SPLIT:
            wpts.split = waypoint.position
        elif waypoint.waypoint_type is FlightWaypointType.REFUEL:
            wpts.refuel = waypoint.position
        elif "INGRESS" in waypoint.waypoint_type.name:
            wpts.ingress = waypoint.position
            wpts.initial = wpts.get_initial_point(
                waypoint.position, flight.package.target.position
            )
        else:
            return
        for f in flight.package.flights:
            if f is flight:
                continue
            for wpt in f.flight_plan.iter_waypoints():
                if wpt.waypoint_type == waypoint.waypoint_type or (
                    "INGRESS" in wpt.waypoint_type.name
                    and "INGRESS" in waypoint.waypoint_type.name
                ):
                    wpt.position = waypoint.position.new_in_same_map(
                        waypoint.position.x, waypoint.position.y
                    )
                    events.update_flight(f)
                    break
