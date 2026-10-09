from __future__ import annotations

from abc import ABC
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any
from datetime import datetime, timedelta
from typing import Optional
from typing import TYPE_CHECKING, TypeVar

from dcs import Point

from game.flightplan import HoldZoneGeometry
from game.flightplan.samdetour import package_detour
from game.theater import MissionTarget, TheaterGroundObject
from game.theater.theatergroup import SceneryUnit, TheaterUnit
from game.utils import Distance, nautical_miles, Speed, feet
from game.theater.theatergroundobject import MotorpoolGroundObject
from .flightplan import FlightPlan
from .formation import FormationFlightPlan, FormationLayout
from .ibuilder import IBuilder
from .planningerror import PlanningError
from .waypointbuilder import StrikeTarget, WaypointBuilder
from .. import FlightType
from ..flightwaypoint import FlightWaypoint
from ..flightwaypointtype import FlightWaypointType
from ..tankeravailability import (
    early_refuel_point,
    post_refuel_unneeded,
    serviceable_tanker_planned,
    tanking_time,
)

if TYPE_CHECKING:
    from game.coalition import Coalition
    from ..flight import Flight
    from ..package import Package

#: Tasks that get one steerpoint per target site instead of one per unit. SEAD
#: keeps its per-emitter points: a HARM shooter aims at each radar.
SITE_WAYPOINT_TASKS = {FlightType.STRIKE: "STRIKE", FlightType.DEAD: "DEAD"}


class FormationAttackFlightPlan(FormationFlightPlan, ABC):
    @property
    def package_speed_waypoints(self) -> set[FlightWaypoint]:
        # Ingress is here so the join->ingress leg is paced to the package. It was
        # the one transit leg every flight priced on its own, which let the light
        # escorts run ahead of the strikers they were escorting.
        return (
            {
                self.layout.ingress,
                self.layout.join,
                self.layout.split,
            }
            | set(self.layout.targets)
            | set(self.layout.ingress_nav)
            | set(self.layout.egress_nav)
        )

    @property
    def combat_speed_waypoints(self) -> set[FlightWaypoint]:
        # Deliberately NOT package_speed_waypoints: ingress is paced with the
        # package but is not a combat leg, and this set drives fuel burn. Including
        # it would charge combat consumption from the join on every strike package.
        return (
            {
                self.layout.join,
                self.layout.split,
            }
            | set(self.layout.targets)
            | set(self.layout.egress_nav)
        )

    def speed_between_waypoints(self, a: FlightWaypoint, b: FlightWaypoint) -> Speed:
        # FlightWaypoint is only comparable by identity, so adding
        # target_area_waypoint to package_speed_waypoints is useless.
        if b.waypoint_type == FlightWaypointType.TARGET_GROUP_LOC:
            speed = self.package.formation_speed(self.flight.is_helo)
            if speed is None:
                # No other formation flight in the package (e.g. solo escort
                # being edited before the strike is added). Use this flight's
                # own cruise speed as a reasonable fallback.
                return self.best_flight_formation_speed
            # A flight slower than the package formation speed (the tag-along
            # TARPS bird, excluded from the package minimum) can't fly it; cap
            # at this flight's own capability.
            return min(speed, self.best_flight_formation_speed)
        return super().speed_between_waypoints(a, b)

    @property
    def tot_waypoint(self) -> FlightWaypoint:
        return self.layout.targets[0]

    @property
    def target_area_waypoint(self) -> FlightWaypoint:
        return FlightWaypoint(
            "TARGET AREA",
            FlightWaypointType.TARGET_GROUP_LOC,
            self.package.target.position,
            feet(0),
            "RADIO",
        )

    @property
    def travel_time_to_target(self) -> timedelta:
        """The estimated time between the first waypoint and the target."""
        destination = self.tot_waypoint
        total = timedelta()
        for previous_waypoint, waypoint in self.edges():
            if waypoint == self.tot_waypoint:
                # For anything strike-like the TOT waypoint is the *flight's*
                # mission target, but to synchronize with the rest of the
                # package we need to use the travel time to the same position as
                # the others.
                total += self.travel_time_between_waypoints(
                    previous_waypoint, self.target_area_waypoint
                )
                break
            total += self.travel_time_between_waypoints(previous_waypoint, waypoint)
        else:
            raise PlanningError(
                f"Did not find destination waypoint {destination} in "
                f"waypoints for {self.flight}"
            )
        return total

    def _time_along(self, legs: list[FlightWaypoint]) -> timedelta:
        return sum(
            (self.total_time_between_waypoints(a, b) for a, b in zip(legs, legs[1:])),
            timedelta(),
        )

    @property
    def join_time(self) -> datetime:
        travel_time = self._time_along(
            [self.layout.join, *self.layout.ingress_nav, self.layout.ingress]
        )
        return self.ingress_time - travel_time

    @property
    def time_at_target(self) -> timedelta:
        """Time the package spends over the target: 45 s per aimpoint.

        A site waypoint counts each unit it carries, so collapsing a site to one
        steerpoint leaves the package timing as it was.
        """
        aimpoints = sum(max(1, len(wp.targets)) for wp in self.layout.targets)
        return timedelta(minutes=0.75 * aimpoints)

    def total_time_between_waypoints(
        self, a: FlightWaypoint, b: FlightWaypoint
    ) -> timedelta:
        # The leg out of the target carries the time spent over it. The forward
        # chain (refuel, RTB and landing ETAs, the kneeboard clock) sums this per
        # leg; without it the chain ran ahead of the locked split by the whole
        # dwell -- a 4-target DEAD put the tanker ETA 27 s before the split.
        total = super().total_time_between_waypoints(a, b)
        if b is self.layout.split:
            return total + self.time_at_target
        if a is self.layout.pre_push_refuel:
            return total + self.tanking_time
        return total

    @property
    def tanking_time(self) -> timedelta:
        return tanking_time(self.flight)

    @property
    def push_time(self) -> datetime:
        refuel = self.layout.pre_push_refuel
        if refuel is None or self.layout.hold is None:
            return super().push_time
        to_join = self._time_along([refuel, *self.layout.nav_to, self.layout.join])
        return (
            self.join_time
            - to_join
            - self.travel_time_between_waypoints(self.layout.hold, refuel)
        )

    @property
    def split_time(self) -> datetime:
        travel_time_ingress = self.total_time_between_waypoints(
            self.layout.ingress, self.target_area_waypoint
        )
        # Carries time_at_target: see total_time_between_waypoints.
        travel_time_egress = self._time_along(
            [self.target_area_waypoint, *self.layout.egress_nav, self.layout.split]
        )
        return self.ingress_time + travel_time_ingress + travel_time_egress

    @property
    def ingress_time(self) -> datetime:
        tot = self.tot
        travel_time = self.total_time_between_waypoints(
            self.layout.ingress, self.target_area_waypoint
        )
        return tot - travel_time

    @property
    def initial_time(self) -> datetime:
        tot = self.tot
        travel_time = self.travel_time_between_waypoints(
            self.layout.initial, self.target_area_waypoint
        )
        return tot - travel_time

    def tot_for_waypoint(self, waypoint: FlightWaypoint) -> datetime | None:
        if waypoint == self.layout.ingress:
            return self.ingress_time
        elif waypoint == self.layout.initial:
            return self.initial_time
        elif waypoint in self.layout.targets:
            return self.tot
        elif waypoint is self.layout.pre_push_refuel and self.layout.hold is not None:
            return self.push_time + self.travel_time_between_waypoints(
                self.layout.hold, waypoint
            )
        return super().tot_for_waypoint(waypoint)


@dataclass
class FormationAttackLayout(FormationLayout):
    ingress: FlightWaypoint
    targets: list[FlightWaypoint]
    initial: Optional[FlightWaypoint] = None
    lineup: Optional[FlightWaypoint] = None
    #: Detours round SAM rings on the straight legs (samdetour.py).
    ingress_nav: list[FlightWaypoint] = field(default_factory=list)
    egress_nav: list[FlightWaypoint] = field(default_factory=list)
    #: A theater-tanker stop between the hold and the join (Flight.refuel_before_push).
    pre_push_refuel: Optional[FlightWaypoint] = None

    def __setstate__(self, state: dict[str, Any]) -> None:
        state.setdefault("ingress_nav", [])
        state.setdefault("egress_nav", [])
        state.setdefault("pre_push_refuel", None)
        self.__dict__.update(state)

    def iter_waypoints(self) -> Iterator[FlightWaypoint]:
        yield self.departure
        if self.hold:
            yield self.hold
        if self.pre_push_refuel is not None:
            yield self.pre_push_refuel
        yield from self.nav_to
        yield self.join
        yield from self.ingress_nav
        if self.lineup:
            yield self.lineup
        yield self.ingress
        if self.initial is not None:
            yield self.initial
        yield from self.targets
        yield from self.egress_nav
        yield self.split
        if self.refuel is not None:
            yield self.refuel
        yield from self.nav_from
        yield self.arrival
        if self.divert is not None:
            yield self.divert
        yield self.bullseye
        yield from self.custom_waypoints

    def nav_sequences(self) -> list[list[FlightWaypoint]]:
        return [self.ingress_nav, self.egress_nav, *super().nav_sequences()]

    def delete_waypoint(self, waypoint: FlightWaypoint) -> bool:
        for sequence in (self.ingress_nav, self.egress_nav):
            if waypoint in sequence:
                sequence.remove(waypoint)
                return True
        if waypoint is self.pre_push_refuel:
            self.pre_push_refuel = None
            return True
        return super().delete_waypoint(waypoint)


def _copy(point: Point) -> Point:
    # A waypoint's position is its own: the package keeps the original.
    return point.new_in_same_map(point.x, point.y)


def lineup_position(package: Package, ingress: Point) -> Point:
    """A strike's line-up: 10 NM short of the IP on the target's bearing."""
    hdg = package.target.position.heading_between_point(ingress)
    return ingress.point_from_heading(hdg, nautical_miles(10).meters)


def package_route_points(
    package: Package, coalition: Coalition, planned: bool = False
) -> tuple[list[Point], list[Point]]:
    """The nav points on the package's way in (JOIN -> IP) and out (target -> SPLIT).

    The player's once they have set them (packageroute.py), else the planner's detour
    round the SAM rings each leg cuts. ``planned`` asks for the planner's regardless.
    """
    waypoints = package.waypoints
    assert waypoints is not None
    ingress = None if planned else waypoints.ingress_nav
    if ingress is None:
        # Routed to the strike line-up point, which sits just short of the IP.
        ingress = package_detour(
            package,
            coalition,
            waypoints.join,
            lineup_position(package, waypoints.ingress),
        )
    egress = None if planned else waypoints.egress_nav
    if egress is None:
        egress = package_detour(
            package, coalition, package.target.position, waypoints.split
        )
    return list(ingress), list(egress)


FlightPlanT = TypeVar("FlightPlanT", bound=FlightPlan[FormationAttackLayout])
LayoutT = TypeVar("LayoutT", bound=FormationAttackLayout)


class FormationAttackBuilder(IBuilder[FlightPlanT, LayoutT], ABC):
    #: Set for the second build when the tanker stop before the push covers the
    #: whole sortie, so the stop after the strike is dropped.
    _drop_post_refuel = False

    def regenerate(self, dump_debug_info: bool = False) -> None:
        self._drop_post_refuel = False
        super().regenerate(dump_debug_info)
        if self._post_refuel_unneeded():
            self._drop_post_refuel = True
            super().regenerate()

    def _post_refuel_unneeded(self) -> bool:
        """Whether the flight gets home on the pre-push top-off alone (DM 2026-10-07)."""
        return post_refuel_unneeded(self.flight, getattr(self.built, "layout", None))

    def _build_pre_push_refuel(
        self, builder: WaypointBuilder, hold: Optional[FlightWaypoint]
    ) -> Optional[FlightWaypoint]:
        if not getattr(self.flight, "refuel_before_push", False) or hold is None:
            return None
        assert self.package.waypoints is not None
        position = early_refuel_point(self.flight, self.package.waypoints.refuel)
        if position is None:
            return None
        refuel = builder.refuel(position)
        refuel.pretty_name = "Refuel (before push)"
        refuel.description = "Refuel from the theater tanker before the push"
        return refuel

    def _build(
        self,
        ingress_type: FlightWaypointType,
        targets: list[StrikeTarget] | None = None,
    ) -> FormationAttackLayout:
        assert self.package.waypoints is not None
        builder = WaypointBuilder(self.flight, targets)

        target_waypoints = self._target_waypoints(builder, targets)

        hold = None
        if not self.flight.is_helo:
            hold = builder.hold(self._hold_point())
        join_pos = self.package.waypoints.join
        if self.flight.is_helo:
            join_pos = self.package.waypoints.ingress
            join_pos = WaypointBuilder.perturb(join_pos, feet(500))
        join = builder.join(join_pos)
        split = builder.split(self._get_split())

        ingress = builder.ingress(
            ingress_type, self.package.waypoints.ingress, self.package.target
        )

        initial = None
        if ingress_type == FlightWaypointType.INGRESS_SEAD:
            initial = builder.sead_search(self.package.target)
        elif ingress_type == FlightWaypointType.INGRESS_SEAD_SWEEP:
            initial = builder.sead_sweep(self.package.target)

        lineup = None
        if self.flight.flight_type == FlightType.STRIKE:
            lineup = builder.nav(
                self._lineup_position(ingress.position), builder.get_combat_altitude
            )

        is_helo = self.flight.is_helo
        ingress_egress_altitude = builder.get_combat_altitude
        use_agl_ingress_egress = is_helo

        refuel = self._build_refuel(builder)
        pre_push_refuel = self._build_pre_push_refuel(builder, hold)
        ingress_nav, egress_nav = self._sam_detours(
            builder, ingress_egress_altitude, use_agl_ingress_egress
        )
        nav_to_start = self.flight.departure.position
        if pre_push_refuel is not None:
            nav_to_start = pre_push_refuel.position
        elif hold is not None:
            nav_to_start = hold.position

        return FormationAttackLayout(
            departure=builder.takeoff(self.flight.departure),
            hold=hold,
            pre_push_refuel=pre_push_refuel,
            nav_to=builder.nav_path(
                nav_to_start,
                join.position,
                ingress_egress_altitude,
                use_agl_ingress_egress,
            ),
            join=join,
            lineup=lineup,
            ingress=ingress,
            initial=initial,
            targets=target_waypoints,
            split=split,
            refuel=refuel,
            nav_from=builder.nav_path(
                refuel.position if refuel else split.position,
                self.flight.arrival.position,
                ingress_egress_altitude,
                use_agl_ingress_egress,
            ),
            arrival=builder.land(self.flight.arrival),
            divert=builder.divert(self.flight.divert),
            bullseye=builder.bullseye(),
            custom_waypoints=list(),
            ingress_nav=ingress_nav,
            egress_nav=egress_nav,
        )

    def _lineup_position(self, ingress: Point) -> Point:
        return lineup_position(self.package, ingress)

    def _sam_detours(
        self, builder: WaypointBuilder, altitude: Distance, altitude_is_agl: bool
    ) -> tuple[list[FlightWaypoint], list[FlightWaypoint]]:
        """Nav points on the package's way in and out: the package route.

        Built from the package's shared points, so every flight in it (escorts
        included) flies the same legs. Helos fly their own low-level legs.
        """
        if self.flight.is_helo or self.package.waypoints is None:
            return [], []
        ingress, egress = package_route_points(self.package, self.coalition)
        return (
            [builder.nav(_copy(p), altitude, altitude_is_agl) for p in ingress],
            [builder.nav(_copy(p), altitude, altitude_is_agl) for p in egress],
        )

    def _build_refuel(self, builder: WaypointBuilder) -> Optional[FlightWaypoint]:
        refuel: Optional[FlightWaypoint] = None
        if self._drop_post_refuel:
            return None
        # Owning a tanker squadron is not the same as having a tanker up this
        # turn, and the old test asked the first question. A waypoint with no
        # tanker behind it is a detour, and the fuel readout credits a top-off
        # from it that never happens. Still NOT a fuel-need test -- see
        # game/ato/tankeravailability.py.
        can_plan = self.flight.coalition.air_wing.can_auto_plan(
            FlightType.REFUELING
        ) and serviceable_tanker_planned(self.flight)
        if not self.flight.is_helo and can_plan and self.package.waypoints:
            # refuel_waypoint_position honors the §44 long-range-carrier override;
            # without one it returns the package refuel point (the stock behavior).
            refuel = builder.refuel(
                self.flight.refuel_waypoint_position(self.package.waypoints.refuel)
            )
        return refuel

    def _target_waypoints(
        self, builder: WaypointBuilder, targets: list[StrikeTarget] | None
    ) -> list[FlightWaypoint]:
        # `targets` can be an *empty* list (not just None) -- e.g. a Strike/DEAD/
        # SEAD against an objective whose units are all already destroyed, since
        # strike_targets_for() only lists live units. Fall back to a single
        # target-area waypoint in that case so the layout always has at least one
        # target (tot_waypoint and the timing math index targets[0]).
        if targets and self.flight.flight_type in SITE_WAYPOINT_TASKS:
            task = SITE_WAYPOINT_TASKS[self.flight.flight_type]
            return [builder.target_site(self.flight.package.target, targets, task)]
        motorpool = self.package.target
        if isinstance(motorpool, MotorpoolGroundObject):
            # One waypoint for the whole depot: BAI names it like any BAI target,
            # Armed Recon searches the area. Strike already folded into the site.
            if self.flight.flight_type is FlightType.BAI:
                return [builder.bai_group(StrikeTarget(motorpool.name, motorpool))]
            return [self.target_area_waypoint(self.flight, motorpool, builder)]
        if targets:
            return [
                self.target_waypoint(self.flight, builder, target) for target in targets
            ]
        return [
            self.target_area_waypoint(self.flight, self.flight.package.target, builder)
        ]

    @property
    def primary_flight_is_air_assault(self) -> bool:
        if self.flight is self.package.primary_flight:
            # Can't call self.package.primary_flight.flight_plan here
            # because the flight-plan wasn't created yet.
            # Calling the fligh_plan property would result in infinite recursion.
            return self.flight.flight_type is FlightType.AIR_ASSAULT
        else:
            assert self.package.primary_flight is not None
            fp = self.package.primary_flight.flight_plan
            return fp.is_airassault

    @staticmethod
    def strike_targets_for(location: TheaterGroundObject) -> list[StrikeTarget]:
        """One StrikeTarget per individual unit of a ground objective.

        This is the same per-unit list the kneeboard target page renders (with
        coordinates). Strike and DEAD fold it into one site waypoint that carries
        the units (``SITE_WAYPOINT_TASKS``); the ingress gets it for the AI task.
        """
        return FormationAttackBuilder._targets_for(location.strike_targets)

    @staticmethod
    def sead_targets_for(location: TheaterGroundObject) -> list[StrikeTarget]:
        """``strike_targets_for`` narrowed to the site's emitters.

        Plain SEAD stands off and fires HARMs, so a steerpoint on a fuel bowser
        or an optically aimed gun is unusable, and listing every unit hands over
        the composition the SEAD kneeboard withholds (recon fog §3). The
        kneeboard pairs its emitter rows with these waypoints by position, so it
        reads the same ``sead_targets`` list in the same order.
        """
        return FormationAttackBuilder._targets_for(location.sead_targets)

    @staticmethod
    def _targets_for(units: list[TheaterUnit]) -> list[StrikeTarget]:
        targets: list[StrikeTarget] = []
        for idx, unit in enumerate(units):
            name = unit.name if isinstance(unit, SceneryUnit) else unit.type.id
            targets.append(StrikeTarget(f"{name} #{idx}", unit))
        return targets

    @staticmethod
    def target_waypoint(
        flight: Flight, builder: WaypointBuilder, target: StrikeTarget
    ) -> FlightWaypoint:
        if flight.flight_type in {FlightType.ANTISHIP, FlightType.BAI}:
            return builder.bai_group(target)
        elif flight.flight_type == FlightType.DEAD:
            return builder.dead_point(target)
        elif flight.flight_type in {FlightType.SEAD, FlightType.SEAD_SWEEP}:
            return builder.sead_point(target)
        else:
            return builder.strike_point(target)

    @staticmethod
    def target_area_waypoint(
        flight: Flight, location: MissionTarget, builder: WaypointBuilder
    ) -> FlightWaypoint:
        if flight.flight_type == FlightType.DEAD:
            return builder.dead_area(location)
        elif flight.flight_type == FlightType.SEAD:
            return builder.sead_area(location)
        elif flight.flight_type == FlightType.OCA_AIRCRAFT:
            return builder.oca_strike_area(location)
        elif flight.flight_type == FlightType.ARMED_RECON:
            return builder.armed_recon_area(location)
        elif flight.flight_type == FlightType.TARPS:
            return builder.recon_area(location)
        else:
            return builder.strike_area(location)

    def _hold_point(self) -> Point:
        assert self.package.waypoints is not None
        origin = self.flight.departure.position
        target = self.package.target.position
        join = self.package.waypoints.join
        ip = self.package.waypoints.ingress
        return HoldZoneGeometry(
            target, origin, ip, join, self.coalition, self.theater
        ).find_best_hold_point()

    def _get_split(self) -> Point:
        assert self.package.waypoints is not None
        assert self.package.primary_flight is not None
        split_pos = (
            self.package.primary_flight.arrival.position
            if self.package.primary_flight.is_helo
            else self.package.waypoints.split
        )
        return split_pos
