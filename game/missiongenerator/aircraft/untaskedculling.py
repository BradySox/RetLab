"""Which airfields keep their untasked parked aircraft under the culling settings.

"Disable untasked OWNFOR/OPFOR aircraft at airfields" skips the parked jets only
where no human will see them: a field a player flight departs from, lands at,
diverts to or passes within ``PLAYER_VIEW_RADIUS`` of keeps its ramp. A field a
package is fragged against with OCA/Aircraft keeps it too, so the strike has
targets. With dynamic slots on, every OWNFOR field is a possible player spawn.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Iterable

from game.ato.flighttype import FlightType
from game.theater.controlpoint import ControlPoint
from game.utils import Distance, nautical_miles

if TYPE_CHECKING:
    from game import Game
    from game.ato import Flight
    from dcs import Point

PLAYER_VIEW_RADIUS: Distance = nautical_miles(20)


def _distance_to_segment(p: Point, a: Point, b: Point) -> float:
    dx = b.x - a.x
    dy = b.y - a.y
    length_sq = dx * dx + dy * dy
    if length_sq == 0:
        return math.hypot(p.x - a.x, p.y - a.y)
    t = max(0.0, min(1.0, ((p.x - a.x) * dx + (p.y - a.y) * dy) / length_sq))
    return math.hypot(p.x - (a.x + t * dx), p.y - (a.y + t * dy))


def _near_route(position: Point, route: list[Point], radius_m: float) -> bool:
    if len(route) == 1:
        return _distance_to_segment(position, route[0], route[0]) <= radius_m
    return any(
        _distance_to_segment(position, a, b) <= radius_m
        for a, b in zip(route, route[1:])
    )


def _player_flights(game: Game) -> Iterable[Flight]:
    for coalition in (game.blue, game.red):
        for package in coalition.ato.packages:
            for flight in package.flights:
                if flight.client_count > 0:
                    yield flight


def airfields_players_see(
    game: Game, candidates: Iterable[ControlPoint]
) -> set[ControlPoint]:
    """The candidates whose untasked aircraft should still spawn."""
    candidates = list(candidates)
    seen: set[ControlPoint] = set()
    radius_m = PLAYER_VIEW_RADIUS.meters

    routes: list[list[Point]] = []
    for flight in _player_flights(game):
        seen.add(flight.departure)
        seen.add(flight.arrival)
        if flight.divert is not None:
            seen.add(flight.divert)
        route = [wpt.position for wpt in flight.flight_plan.waypoints]
        if route:
            routes.append(route)

    for coalition in (game.blue, game.red):
        for package in coalition.ato.packages:
            if isinstance(package.target, ControlPoint) and any(
                f.flight_type is FlightType.OCA_AIRCRAFT for f in package.flights
            ):
                seen.add(package.target)

    for cp in candidates:
        if cp in seen:
            continue
        if game.settings.dynamic_slots and cp.captured.is_blue:
            seen.add(cp)
            continue
        if any(_near_route(cp.position, route, radius_m) for route in routes):
            seen.add(cp)

    return seen.intersection(candidates)
