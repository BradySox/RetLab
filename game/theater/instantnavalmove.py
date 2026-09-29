"""Instant naval move cheat: a carrier or ship moved on the map arrives now.

Without the cheat a move is capped at the hull's max move distance and applied
at the end of the turn. With it the move has no range cap and is applied as
soon as it is ordered, so every flight plan built against the old position is
rebuilt here: flights based on the boat, and flights whose target is it.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from dcs import Point

from game.ato.flightplans.custom import CustomFlightPlan
from game.ato.flightplans.planningerror import PlanningError
from game.theater.shipmovement import reparent_ship, snap_ship

if TYPE_CHECKING:
    from game import Game
    from game.sim import GameUpdateEvents
    from game.theater import ControlPoint
    from game.theater.theatergroundobject import ShipGroundObject


def instant_naval_move_enabled(game: Game) -> bool:
    return game.settings.enable_instant_naval_move_cheat


def destination_is_open_sea(game: Game, origin: Point, destination: Point) -> bool:
    """Where a move may go. The cheat teleports, so only the destination must be
    at sea; a normal move sails there and must not cross land."""
    landmap = game.theater.landmap
    if not landmap:
        return True
    if instant_naval_move_enabled(game):
        return game.theater.is_in_sea(destination)
    return not landmap.land_inbetween(origin, destination)


def move_control_point_now(
    game: Game, cp: ControlPoint, events: GameUpdateEvents
) -> None:
    cp.apply_pending_move()
    events.update_control_point(cp)
    for ground_object in cp.ground_objects:
        events.update_tgo(ground_object)
    _replan_after_move(game, cp, [cp, *cp.ground_objects], events)


def move_ship_now(game: Game, ship: ShipGroundObject, events: GameUpdateEvents) -> None:
    snap_ship(ship)
    reparent_ship(ship, game.theater.controlpoints)
    events.update_tgo(ship)
    _replan_after_move(game, None, [ship], events)


def _replan_after_move(
    game: Game,
    moved_cp: ControlPoint | None,
    moved_targets: list[object],
    events: GameUpdateEvents,
) -> None:
    for coalition in game.coalitions:
        for package in coalition.ato.packages:
            targets_moved = any(package.target is t for t in moved_targets)
            for flight in package.flights:
                based_on_moved = moved_cp is not None and any(
                    cp is moved_cp
                    for cp in (flight.departure, flight.arrival, flight.divert)
                )
                if not targets_moved and not based_on_moved:
                    continue
                if moved_cp is not None and isinstance(
                    flight.flight_plan, CustomFlightPlan
                ):
                    # Same fix-up as the instant squadron transfer cheat.
                    for waypoint in flight.flight_plan.waypoints:
                        if waypoint.control_point is moved_cp:
                            waypoint.position = moved_cp.position
                try:
                    flight.recreate_flight_plan()
                except PlanningError as ex:
                    logging.warning(
                        f"Could not replan {flight} after a naval move: {ex}"
                    )
                    continue
                events.update_flight(flight)
    game.compute_threat_zones(events)
