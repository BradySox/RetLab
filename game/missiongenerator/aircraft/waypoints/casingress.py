import logging

from dcs.mapping import Vector2
from dcs.point import MovingPoint
from dcs.task import EngageTargets, EngageTargetsInZone, TargetType, Targets

from game.ato.flightplans.cas import CasFlightPlan
from game.utils import nautical_miles
from .pydcswaypointbuilder import PydcsWaypointBuilder

CAS_TARGETS: list[type[TargetType]] = [
    Targets.All.GroundUnits.GroundVehicles,
    Targets.All.GroundUnits.AirDefence.AAA,
    Targets.All.GroundUnits.Infantry,
]


def cas_search_zone(flight_plan: CasFlightPlan, centre: Vector2) -> EngageTargetsInZone:
    return EngageTargetsInZone(
        position=centre,
        radius=int(flight_plan.engagement_distance.meters),
        targets=CAS_TARGETS,
    )


class CasIngressBuilder(PydcsWaypointBuilder):
    def add_tasks(self, waypoint: MovingPoint) -> None:
        self.register_special_ingress_points()
        if isinstance(self.flight.flight_plan, CasFlightPlan):
            layout = self.flight.flight_plan.layout
            if layout.battle_line:
                # §111: the first of the circles along the battle line;
                # CasStopBuilder adds the rest at their own stops.
                centre = layout.patrol_start.position
            else:
                centre = (layout.patrol_start.position + layout.patrol_end.position) / 2
            waypoint.add_task(cas_search_zone(self.flight.flight_plan, centre))
        else:
            logging.error("No CAS waypoint found. Falling back to search and engage")
            waypoint.add_task(
                EngageTargets(
                    max_distance=int(
                        nautical_miles(
                            self.flight.coalition.game.settings.cas_engagement_range_distance
                        ).meters
                    ),
                    targets=CAS_TARGETS,
                )
            )


class CasStopBuilder(PydcsWaypointBuilder):
    """A CAS waypoint. On a §111 battle line each stop after FLOT start adds its
    own search circle. These are en-route tasks: each stays on for the rest of
    the route, so by FLOT END the AI searches the circles, never one wide zone."""

    def add_tasks(self, waypoint: MovingPoint) -> None:
        plan = self.flight.flight_plan
        if not isinstance(plan, CasFlightPlan) or not plan.layout.battle_line:
            return
        if any(self.waypoint is stop for stop in plan.layout.on_station[1:]):
            waypoint.add_task(cas_search_zone(plan, self.waypoint.position))
