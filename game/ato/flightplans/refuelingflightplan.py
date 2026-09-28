from __future__ import annotations

from abc import ABC
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING

from game.utils import Speed, knots, Distance, meters
from .patrolling import PatrollingFlightPlan, PatrollingLayout

if TYPE_CHECKING:
    from dcs import Point

    from ..flightwaypoint import FlightWaypoint


@dataclass
class TankerBoxLayout(PatrollingLayout):
    """A four-corner tanker track: patrol_start, three corners, then patrol_end
    back on patrol_start's position. DCS loops corner 1 to patrol_end until the
    on-station time is up; see docs/dev/design/retlab-tanker-box-notes.md."""

    box_corners: list[FlightWaypoint]

    def iter_waypoints(self) -> Iterator[FlightWaypoint]:
        yield self.departure
        yield from self.nav_to
        yield self.patrol_start
        yield from self.box_corners
        yield self.patrol_end
        yield from self.nav_from
        yield self.arrival
        if self.divert is not None:
            yield self.divert
        yield self.bullseye
        yield from self.custom_waypoints

    @property
    def lap(self) -> list[FlightWaypoint]:
        """The repeating circuit: every corner, then patrol_end."""
        return [*self.box_corners, self.patrol_end]


def move_box(layout: object, waypoint: FlightWaypoint, to: Point) -> bool:
    """Move a tanker box whole when any of its points is dragged to ``to``.

    False when ``waypoint`` is not a box point, so the caller moves it alone.
    """
    if not isinstance(layout, TankerBoxLayout):
        return False
    box = [layout.patrol_start, *layout.box_corners, layout.patrol_end]
    if not any(waypoint is point for point in box):
        return False
    dx = to.x - waypoint.position.x
    dy = to.y - waypoint.position.y
    for point in box:
        point.position = point.position.new_in_same_map(
            point.position.x + dx, point.position.y + dy
        )
    return True


def orbit_leg_end(layout: object) -> FlightWaypoint | None:
    """The far end of the leg a receiver meets the tanker on: the racetrack's
    end, or a box's first corner (its patrol_end sits back on its start)."""
    if isinstance(layout, TankerBoxLayout):
        return layout.box_corners[0]
    return getattr(layout, "patrol_end", None)


class RefuelingFlightPlan(PatrollingFlightPlan[PatrollingLayout], ABC):
    # The carrier recovery tanker's speed is set by its RecoveryTanker task.
    honors_orbit_speed = True

    @property
    def patrol_duration(self) -> timedelta:
        return self.flight.coalition.game.settings.desired_tanker_on_station_time

    @property
    def patrol_speed(self) -> Speed:
        kias = getattr(self.flight, "orbit_speed_kias", None)
        if kias is None or not self.honors_orbit_speed:
            return self._aircraft_patrol_speed()
        wanted = Speed.from_calibrated(knots(kias), self.layout.patrol_start.alt)
        if not self.flight.unit_type.dcs_unit_type.max_speed:
            return wanted
        return min(wanted, self.flight.unit_type.max_speed)

    def _aircraft_patrol_speed(self) -> Speed:
        # TODO: Could use self.flight.unit_type.preferred_patrol_speed(altitude).
        if self.flight.unit_type.patrol_speed is not None:
            return self.flight.unit_type.patrol_speed
        # ~280 knots IAS at 21000.
        return knots(400)

    @property
    def engagement_distance(self) -> Distance:
        # TODO: Factor out a common base of the combat and non-combat race-tracks.
        # No harm in setting this, but we ought to clean up a bit.
        return meters(0)

    def _is_first_box_leg(self, a: FlightWaypoint, b: FlightWaypoint) -> bool:
        layout = self.layout
        return (
            isinstance(layout, TankerBoxLayout)
            and a is layout.patrol_start
            and b is layout.box_corners[0]
        )

    def _later_box_legs(self) -> list[tuple[FlightWaypoint, FlightWaypoint]]:
        assert isinstance(self.layout, TankerBoxLayout)
        lap = self.layout.lap
        return list(zip(lap, lap[1:]))

    def total_time_between_waypoints(
        self, a: FlightWaypoint, b: FlightWaypoint
    ) -> timedelta:
        # A box charges its on-station time to the first leg, as a racetrack charges
        # it to start -> end, so patrol_end still falls on patrol_end_time.
        if self._is_first_box_leg(a, b):
            rest = sum(
                (
                    self.travel_time_between_waypoints(x, y)
                    for x, y in self._later_box_legs()
                ),
                timedelta(),
            )
            return max(self.patrol_duration - rest, timedelta())
        return super().total_time_between_waypoints(a, b)

    def fuel_burn_distance_between_points(
        self, a: FlightWaypoint, b: FlightWaypoint
    ) -> Distance:
        if self._is_first_box_leg(a, b):
            hours = self.patrol_duration.total_seconds() / 3600.0
            on_station = self.patrol_speed.knots * hours
            rest = sum(
                x.position.distance_to_point(y.position) / 1852
                for x, y in self._later_box_legs()
            )
            direct = super().fuel_burn_distance_between_points(a, b)
            return max(Distance.from_nautical_miles(on_station - rest), direct)
        return super().fuel_burn_distance_between_points(a, b)
