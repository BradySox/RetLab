import logging

from dcs.point import MovingPoint
from dcs.task import (
    ControlledTask,
    SetUnlimitedFuelCommand,
    SwitchWaypoint,
)

from game.ato.flightplans.patrolling import PatrollingFlightPlan
from game.ato.flightplans.refuelingflightplan import TankerBoxLayout
from .pydcswaypointbuilder import PydcsWaypointBuilder


class RaceTrackEndBuilder(PydcsWaypointBuilder):
    def add_tasks(self, waypoint: MovingPoint) -> None:
        # A box passes this point every lap, so this would re-enable it on station.
        if isinstance(self.flight.flight_plan.layout, TankerBoxLayout):
            return
        # Unlimited fuel option : enable at racetrack end. Must be first option to work.
        if self.flight.squadron.coalition.game.settings.ai_unlimited_fuel:
            waypoint.tasks.insert(0, SetUnlimitedFuelCommand(True))

    def build(self) -> MovingPoint:
        waypoint = super().build()

        if not isinstance(self.flight.flight_plan, PatrollingFlightPlan):
            flight_plan_type = self.flight.flight_plan.__class__.__name__
            logging.error(
                f"Cannot create race track for {self.flight} because "
                f"{flight_plan_type} does not define a patrol."
            )
            return waypoint

        self.waypoint.departure_time = self.flight.flight_plan.patrol_end_time
        if isinstance(self.flight.flight_plan.layout, TankerBoxLayout):
            self._loop_box(waypoint)
        return waypoint

    def _loop_box(self, waypoint: MovingPoint) -> None:
        flight_plan = self.flight.flight_plan
        assert isinstance(flight_plan, PatrollingFlightPlan)
        assert isinstance(flight_plan.layout, TankerBoxLayout)
        lap_length = len(flight_plan.layout.lap)
        # DCS waypoint indices are 1-based; this point is the last one added.
        end_index = len(self.group.points)
        first_corner_index = end_index - lap_length + 1
        # A waypoint's speed is the speed flown toward it.
        for point in self.group.points[first_corner_index - 1 :]:
            point.speed = flight_plan.patrol_speed.meters_per_second
        # Back to corner 2, not the start: its ETA is locked, and a passed locked
        # ETA sends the AI chasing it.
        end_elapsed = int((flight_plan.patrol_end_time - self.now).total_seconds())
        loop = ControlledTask(
            SwitchWaypoint(from_waypoint=end_index, to_waypoint=first_corner_index)
        )
        loop.start_if_lua_predicate(f"return timer.getTime() < {end_elapsed}")
        waypoint.add_task(loop)
