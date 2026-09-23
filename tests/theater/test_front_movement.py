import uuid
from typing import Any, cast

from dcs.mapping import Point
from dcs.terrain import Caucasus

from game.ground_forces.combat_stance import CombatStance
from game.server.frontlines.models import FrontMovementJs, MIN_MOVEMENT_METERS
from game.theater.base import Base
from game.theater.frontline import (
    FRONTLINE_MIN_CP_DISTANCE,
    FrontLine,
    FrontLineSegment,
)

ROUTE = 20 * FRONTLINE_MIN_CP_DISTANCE
TERRAIN = Caucasus()


class FakeSettings:
    scale_aware_front_line = False
    terrain_weighted_front_line = False


class FakeGame:
    settings = FakeSettings()


class FakeCoalition:
    game = FakeGame()


class FakeControlPoint:
    def __init__(self, name: str, position: Point) -> None:
        self.base = Base()
        self.position = position
        self.coalition = FakeCoalition()
        self.name = name
        self.id = uuid.uuid4()
        self.stances: dict[uuid.UUID, CombatStance] = {}


def _front() -> FrontLine:
    front = object.__new__(FrontLine)
    # DCS y is east: blue at the west end, red at the east end.
    front.segments = [FrontLineSegment(Point(0, 0, TERRAIN), Point(0, ROUTE, TERRAIN))]
    front.blue_cp = cast(Any, FakeControlPoint("Blueville", Point(0, 0, TERRAIN)))
    front.red_cp = cast(Any, FakeControlPoint("Redburg", Point(0, ROUTE, TERRAIN)))
    front.blue_cp.stances[front.red_cp.id] = CombatStance.AGGRESSIVE
    return front


def test_no_movement_until_two_turns_are_settled() -> None:
    front = _front()
    assert front.movement_since_last_turn is None
    front.settle_position()
    assert front.movement_since_last_turn is None


def test_a_pre_feature_save_has_no_movement() -> None:
    front = _front()
    assert not hasattr(front, "settled_progress")
    assert front.movement_since_last_turn is None


def test_blue_gaining_strength_moves_the_line_toward_red() -> None:
    front = _front()
    front.settle_position()
    front.blue_cp.base.strength = 1.0
    front.red_cp.base.strength = 0.5
    front.settle_position()
    moved = front.movement_since_last_turn
    assert moved is not None and moved > 0


def test_a_held_turn_reports_no_movement() -> None:
    front = _front()
    front.settle_position()
    front.red_cp.base.strength = 0.4
    front.settle_position()
    front.hold_position()
    assert front.movement_since_last_turn == 0


def test_arrow_points_the_way_blue_advanced() -> None:
    front = _front()
    front.previous_progress = ROUTE / 2
    front.settled_progress = ROUTE / 2 + 5_000
    center = Point(0, ROUTE / 2, TERRAIN)
    movement = FrontMovementJs.for_front_line(front, center)
    assert movement is not None
    assert movement.advancing_side == "blue"
    assert movement.toward == "Redburg"
    assert movement.distance_nm == 2.7
    assert movement.blue_stance == "Aggressive"
    tail, tip = movement.shaft
    assert tip.lng > tail.lng
    assert movement.head[1] == tip


def test_arrow_reverses_when_red_advanced() -> None:
    front = _front()
    front.previous_progress = ROUTE / 2
    front.settled_progress = ROUTE / 2 - 5_000
    movement = FrontMovementJs.for_front_line(front, Point(0, ROUTE / 2, TERRAIN))
    assert movement is not None
    assert movement.advancing_side == "red"
    assert movement.toward == "Blueville"
    tail, tip = movement.shaft
    assert tip.lng < tail.lng


def test_no_arrow_under_the_threshold() -> None:
    front = _front()
    front.previous_progress = ROUTE / 2
    front.settled_progress = ROUTE / 2 + MIN_MOVEMENT_METERS / 2
    assert FrontMovementJs.for_front_line(front, Point(0, ROUTE / 2, TERRAIN)) is None
