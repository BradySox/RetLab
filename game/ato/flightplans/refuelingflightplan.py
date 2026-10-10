from __future__ import annotations

from abc import ABC
from datetime import timedelta
from typing import Any

from game.utils import Speed, knots, Distance, meters
from .patrolling import PatrollingFlightPlan, PatrollingLayout


class TankerBoxLayout(PatrollingLayout):
    """Loads a save made while theater tankers flew a four-corner box (2026-09-28
    to 2026-10-09) as the racetrack along its front leg. Nothing builds one;
    see docs/dev/design/retlab-tanker-box-notes.md."""

    def __setstate__(self, state: dict[str, Any]) -> None:
        corners = state.pop("box_corners", [])
        self.__dict__.update(state)
        if corners:
            # BOX END sat back on BOX 1; the racetrack's end is the first corner.
            self.patrol_end.position = corners[0].position
        for point, name in (
            (self.patrol_start, "RACETRACK START"),
            (self.patrol_end, "RACETRACK END"),
        ):
            point.name = name
            point.pretty_name = name.capitalize().replace("track", "-track")
        self.__class__ = PatrollingLayout  # type: ignore[assignment]


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
