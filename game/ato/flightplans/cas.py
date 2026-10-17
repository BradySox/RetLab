from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from datetime import timedelta
from typing import TYPE_CHECKING, Any, Type

from game.theater import FrontLine
from game.theater.frontbattles import BattleSite, battles_for
from game.utils import Distance, Speed, kph, dcs_to_shapely_point
from game.utils import nautical_miles
from .ibuilder import IBuilder
from .invalidobjectivelocation import InvalidObjectiveLocation
from .patrolling import PatrollingFlightPlan, PatrollingLayout
from .tacticaloverlay import TacticalOverlay, TacticalOverlayDisplay, cas_overlay
from .uizonedisplay import UiZone, UiZoneDisplay
from .waypointbuilder import WaypointBuilder
from ..flightwaypointtype import FlightWaypointType
from ...flightplan.ipsolver import IpSolver
from ...persistency import waypoint_debug_directory

if TYPE_CHECKING:
    from ..flightwaypoint import FlightWaypoint

#: Most CAS stops between FLOT start and end on a §111 battle line.
MAX_BATTLE_STOPS = 3


def battle_stop_sites(sites: Sequence[BattleSite]) -> list[BattleSite]:
    """The battles between the two outer ones that a CAS flight stops at.

    Up to MAX_BATTLE_STOPS, each the battle nearest an even spacing along the line,
    so every stop sits on a fight. Ordered along the line.
    """
    inner = list(sites[1:-1])
    if len(inner) <= MAX_BATTLE_STOPS:
        return inner
    first, last = sites[0].along, sites[-1].along
    picked: list[BattleSite] = []
    for index in range(1, MAX_BATTLE_STOPS + 1):
        goal = first + (last - first) * index / (MAX_BATTLE_STOPS + 1)
        left = [site for site in inner if site not in picked]
        picked.append(min(left, key=lambda site: abs(site.along - goal)))
    return sorted(picked, key=lambda site: site.along)


@dataclass
class CasLayout(PatrollingLayout):
    ingress: FlightWaypoint
    #: True when the route follows a §111 battle line: a search circle per stop.
    battle_line: bool = False
    #: The BATTLE stops between FLOT start and end, in flying order.
    battle_stops: list[FlightWaypoint] = field(default_factory=list)

    def __setstate__(self, state: dict[str, Any]) -> None:
        state.setdefault("battle_line", False)
        state.setdefault("battle_stops", [])
        self.__dict__.update(state)

    @property
    def on_station(self) -> list[FlightWaypoint]:
        """FLOT start, the battle stops, FLOT end."""
        return [self.patrol_start, *self.battle_stops, self.patrol_end]

    def delete_waypoint(self, waypoint: FlightWaypoint) -> bool:
        for index, stop in enumerate(self.battle_stops):
            if stop is waypoint:
                del self.battle_stops[index]
                return True
        return super().delete_waypoint(waypoint)

    def iter_waypoints(self) -> Iterator[FlightWaypoint]:
        yield self.departure
        yield from self.nav_to
        if self.ingress:
            yield self.ingress
        yield self.patrol_start
        yield from self.battle_stops
        yield self.patrol_end
        yield from self.nav_from
        yield self.arrival
        if self.divert is not None:
            yield self.divert
        yield self.bullseye
        yield from self.custom_waypoints


class CasFlightPlan(
    PatrollingFlightPlan[CasLayout], UiZoneDisplay, TacticalOverlayDisplay
):
    @staticmethod
    def builder_type() -> Type[Builder]:
        return Builder

    @property
    def patrol_duration(self) -> timedelta:
        return self.flight.coalition.doctrine.cas_duration

    @property
    def patrol_speed(self) -> Speed:
        # 2021-08-02: patrol_speed will currently have no effect because
        # CAS doesn't use OrbitAction. But all PatrollingFlightPlan are expected
        # to have patrol_speed
        return kph(0)

    @property
    def engagement_distance(self) -> Distance:
        return nautical_miles(
            self.flight.coalition.game.settings.cas_engagement_range_distance
        )

    @property
    def combat_speed_waypoints(self) -> set[FlightWaypoint]:
        return {self.layout.ingress, *self.layout.on_station}

    def total_time_between_waypoints(
        self, a: FlightWaypoint, b: FlightWaypoint
    ) -> timedelta:
        # With battle stops the on-station time is shared across their legs by
        # length, or every later waypoint's time collapses to flight time.
        if self.layout.battle_stops:
            stops = self.layout.on_station
            legs = list(zip(stops, stops[1:]))
            lengths = [x.position.distance_to_point(y.position) for x, y in legs]
            total = sum(lengths)
            for (x, y), length in zip(legs, lengths):
                if a is x and b is y:
                    share = length / total if total > 0 else 1 / len(legs)
                    return self.patrol_duration * share
        return super().total_time_between_waypoints(a, b)

    def request_escort_at(self) -> FlightWaypoint | None:
        return self.layout.patrol_start

    def dismiss_escort_at(self) -> FlightWaypoint | None:
        return self.layout.patrol_end

    def ui_zone(self) -> UiZone:
        if self.layout.battle_line:
            return UiZone(
                [stop.position for stop in self.layout.on_station],
                self.engagement_distance,
            )
        midpoint = (
            self.layout.patrol_start.position + self.layout.patrol_end.position
        ) / 2
        return UiZone(
            [midpoint],
            self.engagement_distance,
        )

    def tactical_overlay(self) -> TacticalOverlay:
        return cas_overlay(
            patrol_start=self.layout.patrol_start.position,
            patrol_end=self.layout.patrol_end.position,
            engagement_range=self.engagement_distance,
            stops=(
                [stop.position for stop in self.layout.on_station]
                if self.layout.battle_line
                else None
            ),
        )


class Builder(IBuilder[CasFlightPlan, CasLayout]):
    def layout(self, dump_debug_info: bool) -> CasLayout:
        location = self.package.target

        if not isinstance(location, FrontLine):
            raise InvalidObjectiveLocation(self.flight.flight_type, location)

        from game.missiongenerator.frontlineconflictdescription import (
            FrontLineConflictDescription,
        )

        # §111: with battles along the border the route runs from the outer battle
        # nearer home to the far one, stopping at up to 3 battles between.
        battles = battles_for(self.theater, location)
        stop_sites: list[BattleSite] = []
        start_label = end_label = ""
        if battles is not None:
            sites = battles.sites
            first, last = sites[0], sites[-1]
            if len(sites) == 1:
                start_xy = first.point_along(-first.width / 2)
                end_xy = first.point_along(first.width / 2)
            else:
                start_xy, end_xy = (first.x, first.y), (last.x, last.y)
            patrol_start = location.position.new_in_same_map(*start_xy)
            patrol_end = location.position.new_in_same_map(*end_xy)
            start_label, end_label = first.sector, last.sector
            stop_sites = battle_stop_sites(sites)
        else:
            bounds = FrontLineConflictDescription.frontline_bounds(
                location, self.theater
            )
            patrol_start = bounds.left_position
            patrol_end = bounds.right_position

        start_distance = patrol_start.distance_to_point(self.flight.departure.position)
        end_distance = patrol_end.distance_to_point(self.flight.departure.position)
        if end_distance < start_distance:
            patrol_start, patrol_end = patrol_end, patrol_start
            start_label, end_label = end_label, start_label
            stop_sites.reverse()

        builder = WaypointBuilder(self.flight)

        is_helo = self.flight.unit_type.dcs_unit_type.helicopter
        ingress_egress_altitude = builder.get_combat_altitude
        use_agl_patrol_altitude = is_helo

        ip_solver = IpSolver(
            dcs_to_shapely_point(self.flight.departure.position),
            dcs_to_shapely_point(patrol_start),
            self.doctrine,
            self.threat_zones.all,
        )
        ip_solver.set_debug_properties(
            waypoint_debug_directory() / "IP", self.theater.terrain
        )
        ingress_point_shapely = ip_solver.solve()
        if dump_debug_info:
            ip_solver.dump_debug_info()

        ingress_point = patrol_start.new_in_same_map(
            ingress_point_shapely.x, ingress_point_shapely.y
        )

        patrol_start_waypoint = builder.cas(patrol_start, ingress_egress_altitude)
        patrol_start_waypoint.name = "FLOT START"
        patrol_start_waypoint.pretty_name = "FLOT start"
        patrol_start_waypoint.description = "FLOT boundary"

        patrol_end_waypoint = builder.cas(patrol_end, ingress_egress_altitude)
        patrol_end_waypoint.name = "FLOT END"
        patrol_end_waypoint.pretty_name = "FLOT end"
        patrol_end_waypoint.description = "FLOT boundary"

        battle_stops: list[FlightWaypoint] = []
        if battles is not None:
            patrol_start_waypoint.description = f"Battle in {start_label}"
            patrol_end_waypoint.description = f"Battle in {end_label}"
            for number, site in enumerate(stop_sites, start=1):
                stop = builder.cas(
                    patrol_start.new_in_same_map(site.x, site.y),
                    ingress_egress_altitude,
                )
                stop.name = f"BATTLE {number}"
                stop.pretty_name = f"Battle {number}"
                stop.description = f"Battle in {site.sector}"
                battle_stops.append(stop)

        ingress = builder.ingress(
            FlightWaypointType.INGRESS_CAS, ingress_point, location
        )
        ingress.description = f"Ingress to provide CAS at {location}"

        return CasLayout(
            departure=builder.takeoff(self.flight.departure),
            nav_to=builder.nav_path(
                self.flight.departure.position,
                ingress_point,
                ingress_egress_altitude,
                use_agl_patrol_altitude,
            ),
            nav_from=builder.nav_path(
                patrol_end,
                self.flight.arrival.position,
                ingress_egress_altitude,
                use_agl_patrol_altitude,
            ),
            ingress=ingress,
            patrol_start=patrol_start_waypoint,
            patrol_end=patrol_end_waypoint,
            arrival=builder.land(self.flight.arrival),
            divert=builder.divert(self.flight.divert),
            bullseye=builder.bullseye(),
            custom_waypoints=list(),
            battle_line=battles is not None,
            battle_stops=battle_stops,
        )

    def build(self, dump_debug_info: bool = False) -> CasFlightPlan:
        return CasFlightPlan(self.flight, self.layout(dump_debug_info))
