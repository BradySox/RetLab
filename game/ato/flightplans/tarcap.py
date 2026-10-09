from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, TYPE_CHECKING, Type

from game.ato.flighttype import FlightType
from game.utils import Distance, Speed
from .capbuilder import CapBuilder
from .patrolling import PatrollingFlightPlan, PatrollingLayout
from .tacticaloverlay import TacticalOverlay, TacticalOverlayDisplay, cap_overlay
from .barcap import station_refuel
from .waypointbuilder import WaypointBuilder
from game.ato.tankeravailability import (
    post_refuel_unneeded,
    serviceable_tanker_planned,
)

if TYPE_CHECKING:
    from ..flightwaypoint import FlightWaypoint

SUPPRESSION_TYPES = frozenset(
    {FlightType.SEAD, FlightType.SEAD_SWEEP, FlightType.SEAD_ESCORT, FlightType.DEAD}
)


@dataclass
class TarCapLayout(PatrollingLayout):
    refuel: FlightWaypoint | None
    #: A theater-tanker stop on the way to station (Flight.refuel_before_push).
    pre_push_refuel: FlightWaypoint | None = None

    def __setstate__(self, state: dict[str, Any]) -> None:
        state.setdefault("pre_push_refuel", None)
        self.__dict__.update(state)

    def iter_waypoints(self) -> Iterator[FlightWaypoint]:
        yield self.departure
        if self.pre_push_refuel is not None:
            yield self.pre_push_refuel
        yield from self.nav_to
        yield self.patrol_start
        yield self.patrol_end
        if self.refuel is not None:
            yield self.refuel
        yield from self.nav_from
        yield self.arrival
        if self.divert is not None:
            yield self.divert
        yield self.bullseye
        yield from self.custom_waypoints

    def delete_waypoint(self, waypoint: FlightWaypoint) -> bool:
        if waypoint is self.pre_push_refuel:
            self.pre_push_refuel = None
            return True
        if waypoint == self.refuel:
            self.refuel = None
            return True
        elif super().delete_waypoint(waypoint):
            return True
        return False


class TarCapFlightPlan(PatrollingFlightPlan[TarCapLayout], TacticalOverlayDisplay):
    @property
    def patrol_duration(self) -> timedelta:
        # Note that this duration only has an effect if there are no
        # flights in the package that have requested escort. If the package
        # requests an escort the CAP self.flight will remain on station for the
        # duration of the escorted mission, or until it is winchester/bingo.
        return self.flight.coalition.doctrine.cap_duration

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

    @staticmethod
    def builder_type() -> Type[Builder]:
        return Builder

    @property
    def combat_speed_waypoints(self) -> set[FlightWaypoint]:
        return {self.layout.patrol_start, self.layout.patrol_end}

    def default_tot_offset(self) -> timedelta:
        return -timedelta(minutes=2)

    def depart_time_for_waypoint(self, waypoint: FlightWaypoint) -> datetime | None:
        if waypoint == self.layout.patrol_end:
            return self.patrol_end_time
        return super().depart_time_for_waypoint(waypoint)

    @property
    def patrol_start_time(self) -> datetime:
        start = self.package.escort_start_time
        patrol_start = self.tot if start is None else start + self.tot_offset
        suppression = self._suppression_tot()
        if suppression is not None and suppression > patrol_start:
            return suppression
        return patrol_start

    def _suppression_tot(self) -> datetime | None:
        """Earliest SEAD/DEAD TOT in the package, when tarcap_behind_sead is on.

        The orbit is on the target; arriving before the suppression parked four
        F-15Cs over an SA-11 for 17 minutes on test 40.
        """
        if not self.flight.coalition.game.settings.tarcap_behind_sead:
            return None
        tots = [
            flight.flight_plan.tot
            for flight in self.package.flights
            if flight.flight_type in SUPPRESSION_TYPES
        ]
        return min(tots, default=None)

    @property
    def patrol_end_time(self) -> datetime:
        end = self.package.escort_end_time
        if end is not None:
            return end
        return super().patrol_end_time


class Builder(CapBuilder[TarCapFlightPlan, TarCapLayout]):
    #: Set for the second build when the tanker stop before station covers the
    #: whole sortie, so the stop coming off station is dropped.
    _drop_post_refuel = False

    def regenerate(self, dump_debug_info: bool = False) -> None:
        self._drop_post_refuel = False
        super().regenerate(dump_debug_info)
        if post_refuel_unneeded(self.flight, getattr(self.built, "layout", None)):
            self._drop_post_refuel = True
            super().regenerate()

    def layout(self) -> TarCapLayout:
        location = self.package.target

        builder = WaypointBuilder(self.flight)
        patrol_alt = builder.get_patrol_altitude

        orbit0p, orbit1p = self.cap_racetrack_for_objective(location, barcap=False)

        start, end = builder.race_track(orbit0p, orbit1p, patrol_alt)
        early_refuel = station_refuel(self.flight, builder, start)
        nav_to_start = self.flight.departure.position
        if early_refuel is not None:
            nav_to_start = early_refuel.position

        refuel = None
        nav_from_origin = orbit1p

        # TARCAP's refuel is doctrinal -- top off coming off station, not a
        # fuel-driven decision -- but it still needs a tanker to exist. A stop
        # before station replaces it when that top-off gets the jet home.
        if (
            not self._drop_post_refuel
            and self.package.waypoints is not None
            and serviceable_tanker_planned(self.flight)
        ):
            refuel = builder.refuel(
                self.flight.refuel_waypoint_position(self.package.waypoints.refuel)
            )
            nav_from_origin = refuel.position

        return TarCapLayout(
            departure=builder.takeoff(self.flight.departure),
            pre_push_refuel=early_refuel,
            nav_to=builder.nav_path(nav_to_start, orbit0p, patrol_alt),
            nav_from=builder.nav_path(
                nav_from_origin, self.flight.arrival.position, patrol_alt
            ),
            patrol_start=start,
            patrol_end=end,
            refuel=refuel,
            arrival=builder.land(self.flight.arrival),
            divert=builder.divert(self.flight.divert),
            bullseye=builder.bullseye(),
            custom_waypoints=list(),
        )

    def build(self, dump_debug_info: bool = False) -> TarCapFlightPlan:
        return TarCapFlightPlan(self.flight, self.layout())
