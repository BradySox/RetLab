from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

from game.ato.flighttype import FlightType
from game.missiongenerator.aircraft.untaskedculling import (
    PLAYER_VIEW_RADIUS,
    airfields_players_see,
)
from game.theater.controlpoint import ControlPoint
from game.theater.player import Player

NM = PLAYER_VIEW_RADIUS.meters / 20


def _cp(name: str, x: float, y: float, side: Player = Player.RED) -> Any:
    cp = MagicMock(spec=ControlPoint)
    cp.name = name
    cp.position = SimpleNamespace(x=x, y=y)
    cp.captured = side
    return cp


def _flight(
    departure: Any,
    route: list[tuple[float, float]],
    clients: int = 1,
    divert: Any = None,
    flight_type: FlightType = FlightType.STRIKE,
) -> Any:
    return SimpleNamespace(
        client_count=clients,
        departure=departure,
        arrival=departure,
        divert=divert,
        flight_type=flight_type,
        flight_plan=SimpleNamespace(
            waypoints=[
                SimpleNamespace(position=SimpleNamespace(x=x, y=y)) for x, y in route
            ]
        ),
    )


def _game(flights: list[Any], target: Any = None, dynamic_slots: bool = False) -> Any:
    package = SimpleNamespace(flights=flights, target=target)
    return SimpleNamespace(
        blue=SimpleNamespace(ato=SimpleNamespace(packages=[package])),
        red=SimpleNamespace(ato=SimpleNamespace(packages=[])),
        settings=SimpleNamespace(dynamic_slots=dynamic_slots),
    )


def test_player_home_divert_and_route_neighbours_keep_their_jets() -> None:
    home = _cp("home", 0, 0, Player.BLUE)
    divert = _cp("divert", 0, 500 * NM, Player.BLUE)
    beside_route = _cp("beside", 100 * NM, 15 * NM)
    far = _cp("far", 100 * NM, 60 * NM)
    flight = _flight(home, [(0, 0), (200 * NM, 0), (0, 0)], divert=divert)

    seen = airfields_players_see(_game([flight]), [home, divert, beside_route, far])

    assert seen == {home, divert, beside_route}


def test_ai_flights_do_not_keep_an_airfield() -> None:
    home = _cp("home", 0, 0, Player.BLUE)
    flight = _flight(home, [(0, 0), (200 * NM, 0)], clients=0)

    assert airfields_players_see(_game([flight]), [home]) == set()


def test_oca_aircraft_target_keeps_its_ramp() -> None:
    home = _cp("home", 0, 0, Player.BLUE)
    target = _cp("target", 400 * NM, 400 * NM)
    flight = _flight(
        home, [(0, 0), (1, 1)], clients=0, flight_type=FlightType.OCA_AIRCRAFT
    )

    assert airfields_players_see(_game([flight], target=target), [target]) == {target}


def test_dynamic_slots_keep_every_ownfor_field() -> None:
    blue = _cp("blue", 0, 0, Player.BLUE)
    red = _cp("red", 0, 0, Player.RED)

    assert airfields_players_see(_game([], dynamic_slots=True), [blue, red]) == {blue}
