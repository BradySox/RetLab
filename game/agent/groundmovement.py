"""Red's ground movement through the outside AI (§109, §131 stage 7).

Red never moves on its own planner's account (DM call, 2026-11-16); only an outside
AI may send red armor, reserves or SAM batteries, through the same checks and the
same journey the human's Move windows use. Adapted from juanjux/dcs-escalation
game/agent/groundmovement.py (LGPL-3.0).
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING
from uuid import UUID

from dcs import Point
from dcs.mapping import LatLng

from game.dcs.groundunittype import GroundUnitType
from game.groundmovement.base import (
    available_stock,
    dispatch_base_movement,
    preview_base_movement,
)
from game.groundmovement.dispatch import dispatch_armor, stop_armor
from game.groundmovement.journey import GroundPosition
from game.groundmovement.orders import DestinationKind, MovementDestination
from game.groundmovement.planning import (
    armor_movement_options,
    movement_destination,
    preview_armor_movement,
)
from game.groundmovement.report import destination_label, movement_reports
from game.groundmovement.settings import METERS_PER_MILE, enabled
from game.server import EventStream
from game.sim.gameupdateevents import GameUpdateEvents
from game.theater.player import Player

if TYPE_CHECKING:
    from game import Game
    from game.agent import schemas

OWNER = Player.RED


def _uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError:
        raise ValueError(f"not an id: {value}")


def _position(game: Game, lat: float, lng: float) -> GroundPosition:
    point = Point.from_latlng(LatLng(lat, lng), game.theater.terrain)
    return GroundPosition(point.x, point.y)


def _destination(
    game: Game, spec: schemas.MovementDestinationSpec
) -> MovementDestination:
    kind = DestinationKind(spec.kind)
    if kind is DestinationKind.POSITION:
        if spec.lat is None or spec.lng is None:
            raise ValueError("a position destination needs lat and lng")
        return movement_destination(
            game, OWNER, kind, position=_position(game, spec.lat, spec.lng)
        )
    if spec.base_id is None:
        raise ValueError("a base or front destination needs base_id")
    return movement_destination(
        game,
        OWNER,
        kind,
        base_id=_uuid(spec.base_id),
        opposing_base_id=(
            _uuid(spec.opposing_base_id) if spec.opposing_base_id else None
        ),
    )


def _stock_selection(game: Game, units: dict[str, int]) -> dict[GroundUnitType, int]:
    selection: dict[GroundUnitType, int] = {}
    for name, count in units.items():
        if not GroundUnitType.exists(name):
            raise ValueError(f"unknown unit type: {name}")
        selection[GroundUnitType.named(name)] = count
    return selection


def options(game: Game, source_id: str, source_kind: str) -> dict[str, Any]:
    """What a red group or base can send, before choosing a destination."""
    if source_kind == "base":
        base = next(
            (cp for cp in game.theater.controlpoints if str(cp.id) == source_id), None
        )
        if base is None or not base.captured.is_red:
            raise PermissionError("not a red base")
        return {
            "enabled": enabled(game.settings),
            "stock": {u.variant_id: n for u, n in available_stock(base).items()},
        }
    result = armor_movement_options(game, _uuid(source_id), OWNER)
    return {
        "enabled": result.enabled,
        "units": [
            {
                "id": u.id,
                "name": u.name,
                "mobility": u.mobility,
                "can_tow": u.can_tow,
                "selectable": u.selectable,
            }
            for u in result.units
        ],
        "warnings": list(result.warnings),
    }


def _summary(preview: Any) -> dict[str, Any]:
    return {
        "units": len(preview.manifest.unit_ids),
        "road_miles": round(preview.road_distance_m / METERS_PER_MILE, 1),
        "off_road_miles": round(preview.offroad_distance_m / METERS_PER_MILE, 1),
        "turns": preview.arrival_in_turns,
        "warnings": list(getattr(preview, "warnings", ())),
    }


def preview(game: Game, request: schemas.GroundMovementRequest) -> dict[str, Any]:
    if request.source_kind == "base":
        if request.destination.lat is None or request.destination.lng is None:
            raise ValueError("a reserve goes to a position: give lat and lng")
        return _summary(
            preview_base_movement(
                game,
                _uuid(request.source_id),
                OWNER,
                _stock_selection(game, request.stock),
                _position(game, request.destination.lat, request.destination.lng),
            )
        )
    return _summary(
        preview_armor_movement(
            game,
            _uuid(request.source_id),
            OWNER,
            request.unit_ids,
            _destination(game, request.destination),
        )
    )


def dispatch(game: Game, request: schemas.GroundMovementRequest) -> dict[str, Any]:
    events = GameUpdateEvents()
    if request.source_kind == "base":
        if request.destination.lat is None or request.destination.lng is None:
            raise ValueError("a reserve goes to a position: give lat and lng")
        transit = dispatch_base_movement(
            game,
            _uuid(request.source_id),
            OWNER,
            _stock_selection(game, request.stock),
            _position(game, request.destination.lat, request.destination.lng),
            events,
        )
    else:
        transit = dispatch_armor(
            game,
            _uuid(request.source_id),
            OWNER,
            request.unit_ids,
            _destination(game, request.destination),
            events,
        )
    EventStream.put_nowait(events)
    return {"order_id": str(transit.order_id), "group_id": str(transit.detachment_id)}


def movements(game: Game) -> list[dict[str, Any]]:
    """Every red movement: where it is going and how far it has left."""
    return [
        {
            "order_id": str(r.order_id),
            "group_id": str(r.detachment_id),
            "status": r.status,
            "waiting": r.pause_reason,
            "to": destination_label(game, r.destination),
            "miles_left": round(r.remaining_distance_m / METERS_PER_MILE, 1),
            "turns_left": r.remaining_turns,
            "units": r.surviving_units,
        }
        for r in movement_reports(game, None, OWNER)
    ]


def stop(game: Game, order_id: str) -> dict[str, Any]:
    events = GameUpdateEvents()
    stop_armor(game, _uuid(order_id), OWNER, events)
    EventStream.put_nowait(events)
    return {"ok": True}


def guarded(fn: Any, *args: Any) -> dict[str, Any]:
    """A movement error is the AI's to read, not a server failure."""
    try:
        return fn(*args)
    except (ValueError, KeyError) as ex:
        return {"ok": False, "error": str(ex)}
