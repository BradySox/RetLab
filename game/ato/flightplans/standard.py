from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, TypeVar

from game.ato.flightplans.flightplan import FlightPlan, Layout

if TYPE_CHECKING:
    from ..flightwaypoint import FlightWaypoint


@dataclass
class StandardLayout(Layout, ABC):
    arrival: FlightWaypoint
    divert: FlightWaypoint | None
    bullseye: FlightWaypoint
    nav_to: list[FlightWaypoint]
    nav_from: list[FlightWaypoint]

    def nav_sequences(self) -> list[list[FlightWaypoint]]:
        return [self.nav_to, self.nav_from, *super().nav_sequences()]

    def delete_waypoint(self, waypoint: FlightWaypoint) -> bool:
        if waypoint is self.divert:
            self.divert = None
            return True
        elif waypoint in self.nav_to:
            self.nav_to.remove(waypoint)
            return True
        elif waypoint in self.nav_from:
            self.nav_from.remove(waypoint)
            return True
        elif waypoint in self.custom_waypoints:
            self.custom_waypoints.remove(waypoint)
            return True
        return False


LayoutT = TypeVar("LayoutT", bound=StandardLayout)


class StandardFlightPlan(FlightPlan[LayoutT], ABC):
    """Base type for all non-custom flight plans.

    We can't reason about custom flight plans so they get special treatment, but all
    others are guaranteed to have certain properties like departure and arrival points,
    potentially a divert field, and a bullseye
    """

    @property
    def landing_time(self) -> datetime:
        return_time = self.total_time_between_waypoints(
            self.tot_waypoint, self.layout.arrival
        )
        return self.mission_departure_time + return_time
