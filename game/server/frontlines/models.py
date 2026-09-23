from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel

from game.missiongenerator.frontlineconflictdescription import (
    FrontLineConflictDescription,
)
from game.server.leaflet import LeafletPoint
from game.utils import Heading, meters

if TYPE_CHECKING:
    from dcs.mapping import Point

    from game import Game
    from game.theater import FrontLine, ConflictTheater

#: Below this the line held; an arrow would only show rounding.
MIN_MOVEMENT_METERS = 500.0

#: Drawn arrow length is the movement, kept readable at every zoom.
_ARROW_MIN_METERS = 3_000.0
_ARROW_MAX_METERS = 12_000.0
_BARB_DEGREES = 150


class FrontMovementJs(BaseModel):
    advancing_side: str
    distance_nm: float
    toward: str
    blue_stance: Optional[str]
    shaft: list[LeafletPoint]
    head: list[LeafletPoint]

    class Config:
        title = "FrontMovement"

    @staticmethod
    def for_front_line(
        front_line: FrontLine, center: Point
    ) -> Optional[FrontMovementJs]:
        moved = front_line.movement_since_last_turn
        if moved is None or abs(moved) < MIN_MOVEMENT_METERS:
            return None
        blue_advanced = moved > 0
        heading = front_line.blue_forward_heading
        if not blue_advanced:
            heading = heading.opposite
        length = min(max(abs(moved), _ARROW_MIN_METERS), _ARROW_MAX_METERS)
        tail = center.point_from_heading(heading.opposite.degrees, length / 2)
        tip = center.point_from_heading(heading.degrees, length / 2)
        barb = length * 0.3
        left = tip.point_from_heading(
            (heading + Heading.from_degrees(_BARB_DEGREES)).degrees, barb
        )
        right = tip.point_from_heading(
            (heading - Heading.from_degrees(_BARB_DEGREES)).degrees, barb
        )
        # Blue's own stance only: red's is not something blue would know.
        stance = front_line.blue_cp.stances.get(front_line.red_cp.id)
        return FrontMovementJs(
            advancing_side="blue" if blue_advanced else "red",
            distance_nm=round(meters(abs(moved)).nautical_miles, 1),
            toward=(front_line.red_cp if blue_advanced else front_line.blue_cp).name,
            blue_stance=None if stance is None else stance.name.title(),
            shaft=[tail.latlng(), tip.latlng()],
            head=[left.latlng(), tip.latlng(), right.latlng()],
        )


class FrontLineJs(BaseModel):
    id: UUID
    extents: list[LeafletPoint]
    movement: Optional[FrontMovementJs] = None

    class Config:
        title = "FrontLine"

    @staticmethod
    def for_front_line(theater: ConflictTheater, front_line: FrontLine) -> FrontLineJs:
        bounds = FrontLineConflictDescription.frontline_bounds(front_line, theater)
        # The whole trace, not just the two ends: §90 rung E bows the front, and
        # this is the map the player plans on. `polyline` is exactly the two
        # endpoints when the front has no sector depths, so a straight front is
        # byte-identical to what this sent before.
        return FrontLineJs(
            id=front_line.id,
            extents=[point.latlng() for point in bounds.polyline],
            movement=FrontMovementJs.for_front_line(front_line, bounds.center),
        )

    @staticmethod
    def all_in_game(game: Game) -> list[FrontLineJs]:
        return [
            FrontLineJs.for_front_line(game.theater, f)
            for f in game.theater.conflicts()
        ]
