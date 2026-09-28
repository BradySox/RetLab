from abc import ABC
from datetime import timedelta

from game.utils import Speed, knots, Distance, meters
from .patrolling import PatrollingFlightPlan, PatrollingLayout

# Below this an airframe is a helicopter tanker (the KC-130J's 125 KIAS); a
# fast-jet track speed would make it useless to the receivers it exists for.
MIN_OVERRIDABLE_TANKER_KIAS = 200


class RefuelingFlightPlan(PatrollingFlightPlan[PatrollingLayout], ABC):
    # The carrier recovery tanker's speed is set by its RecoveryTanker task.
    honors_orbit_speed_setting = True

    @property
    def patrol_duration(self) -> timedelta:
        return self.flight.coalition.game.settings.desired_tanker_on_station_time

    @property
    def patrol_speed(self) -> Speed:
        default = self._aircraft_patrol_speed()
        settings = self.flight.coalition.game.settings
        if not (self.honors_orbit_speed_setting and settings.tanker_orbit_speed_set):
            return default
        altitude = self.layout.patrol_start.alt
        slow_limit = Speed.from_calibrated(knots(MIN_OVERRIDABLE_TANKER_KIAS), altitude)
        if default < slow_limit:
            return default
        wanted = Speed.from_calibrated(
            knots(settings.tanker_orbit_speed_kias), altitude
        )
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
