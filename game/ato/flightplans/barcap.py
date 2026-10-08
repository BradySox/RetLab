from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Optional, Type

from game.theater import FrontLine
from game.utils import Distance, Speed
from .capbuilder import CapBuilder
from .invalidobjectivelocation import InvalidObjectiveLocation
from .patrolling import PatrollingFlightPlan, PatrollingLayout
from .tacticaloverlay import TacticalOverlay, TacticalOverlayDisplay, cap_overlay
from .waypointbuilder import WaypointBuilder
from ..flightwaypoint import FlightWaypoint
from ..tankeravailability import early_refuel_point


@dataclass
class BarCapLayout(PatrollingLayout):
    #: A theater-tanker stop on the way to station (Flight.refuel_before_push).
    pre_push_refuel: Optional[FlightWaypoint] = None

    def iter_waypoints(self) -> Iterator[FlightWaypoint]:
        waypoints = super().iter_waypoints()
        yield next(waypoints)
        if self.pre_push_refuel is not None:
            yield self.pre_push_refuel
        yield from waypoints

    def delete_waypoint(self, waypoint: FlightWaypoint) -> bool:
        if waypoint is self.pre_push_refuel:
            self.pre_push_refuel = None
            return True
        return super().delete_waypoint(waypoint)


def station_refuel(
    flight: Any, builder: WaypointBuilder, start: FlightWaypoint
) -> Optional[FlightWaypoint]:
    """The ticked tanker stop on a CAP's way out, or None."""
    if not getattr(flight, "refuel_before_push", False) or flight.is_helo:
        return None
    planned = flight.departure.position.lerp(start.position, 0.75)
    position = early_refuel_point(flight, planned)
    if position is None:
        return None
    refuel = builder.refuel(position)
    refuel.pretty_name = "Refuel (before station)"
    refuel.description = "Refuel from the theater tanker before going on station"
    return refuel


class BarCapFlightPlan(PatrollingFlightPlan[PatrollingLayout], TacticalOverlayDisplay):
    @staticmethod
    def builder_type() -> Type[Builder]:
        return Builder

    @property
    def patrol_duration(self) -> timedelta:
        return self.flight.coalition.game.settings.desired_barcap_mission_duration

    @property
    def patrol_speed(self) -> Speed:
        return self.flight.unit_type.preferred_patrol_speed(
            self.layout.patrol_start.alt
        )

    @property
    def engagement_distance(self) -> Distance:
        return self.flight.coalition.doctrine.cap_engagement_range

    def tactical_overlay(self) -> TacticalOverlay:
        return cap_overlay(self)


class Builder(CapBuilder[BarCapFlightPlan, PatrollingLayout]):
    def layout(self) -> BarCapLayout:
        location = self.package.target

        if isinstance(location, FrontLine):
            raise InvalidObjectiveLocation(self.flight.flight_type, location)

        start_pos, end_pos = self.cap_racetrack_for_objective(location, barcap=True)

        builder = WaypointBuilder(self.flight)
        patrol_alt = builder.get_patrol_altitude

        start, end = builder.race_track(start_pos, end_pos, patrol_alt)
        refuel = station_refuel(self.flight, builder, start)
        nav_to_start = self.flight.departure.position
        if refuel is not None:
            nav_to_start = refuel.position

        return BarCapLayout(
            departure=builder.takeoff(self.flight.departure),
            pre_push_refuel=refuel,
            nav_to=builder.nav_path(nav_to_start, start.position, patrol_alt),
            nav_from=builder.nav_path(
                end.position, self.flight.arrival.position, patrol_alt
            ),
            patrol_start=start,
            patrol_end=end,
            arrival=builder.land(self.flight.arrival),
            divert=builder.divert(self.flight.divert),
            bullseye=builder.bullseye(),
            custom_waypoints=list(),
        )

    def build(self, dump_debug_info: bool = False) -> BarCapFlightPlan:
        return BarCapFlightPlan(self.flight, self.layout())
