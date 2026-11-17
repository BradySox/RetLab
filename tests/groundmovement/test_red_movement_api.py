"""§131 stage 7: red moves only through the outside AI, on red's own groups."""

from __future__ import annotations

from typing import Any

import pytest

from game.agent import groundmovement, schemas
from game.groundmovement.dispatch import dispatch_armor
from game.sim.gameupdateevents import GameUpdateEvents
from game.theater.player import Player
from tests.groundmovement.test_armor_movement_dispatch import prepare
from tests.groundmovement.test_armor_movement_planning import world  # noqa: F401


def test_a_blue_group_cannot_be_ordered_by_the_red_api(world: Any) -> None:
    with pytest.raises(PermissionError):
        groundmovement.options(world.game, str(world.source.id), "armor")


def test_a_blue_base_cannot_send_a_red_reserve(world: Any) -> None:
    with pytest.raises(PermissionError):
        groundmovement.options(world.game, str(world.a.id), "base")


def test_red_movements_leave_out_blue_columns(world: Any) -> None:
    prepare(world)
    dispatch_armor(
        world.game,
        world.source.id,
        Player.BLUE,
        (1, 2),
        world.destination,
        GameUpdateEvents(),
    )
    assert world.game.ground_movements.transits
    assert groundmovement.movements(world.game) == []


def test_a_bad_request_is_an_answer_not_a_server_error(world: Any) -> None:
    request = schemas.GroundMovementRequest(
        source_id="not-an-id",
        destination=schemas.MovementDestinationSpec(kind="position", lat=1, lng=1),
    )
    result = groundmovement.guarded(groundmovement.preview, world.game, request)
    assert result["ok"] is False and "not an id" in result["error"]


def test_a_reserve_needs_a_position(world: Any) -> None:
    request = schemas.GroundMovementRequest(
        source_id=str(world.enemy.id),
        source_kind="base",
        destination=schemas.MovementDestinationSpec(kind="base", base_id="x"),
    )
    result = groundmovement.guarded(groundmovement.preview, world.game, request)
    assert result["ok"] is False and "lat and lng" in result["error"]
