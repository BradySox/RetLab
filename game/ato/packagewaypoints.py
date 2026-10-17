from __future__ import annotations

import logging
import random
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Optional

from dcs import Point

from game.ato.flighttype import FlightType
from game.ato.flightplans.waypointbuilder import WaypointBuilder
from game.flightplan import JoinZoneGeometry
from game.flightplan.ipsolver import IpSolver
from game.flightplan.refuelzonegeometry import RefuelZoneGeometry
from game.persistency import waypoint_debug_directory
from game.data.doctrine import Doctrine
from game.utils import Distance, dcs_to_shapely_point, meters
from game.utils import nautical_miles

if TYPE_CHECKING:
    from game.ato import Package
    from game.coalition import Coalition


@dataclass
class PackageWaypoints:
    join: Point
    ingress: Point
    initial: Point
    split: Point
    refuel: Point
    #: The player's nav points on the way in (JOIN -> IP) and out (target -> SPLIT),
    #: flown by every flight in the package. None leaves the leg to the planner's SAM
    #: detour. game/ato/packageroute.py
    ingress_nav: Optional[list[Point]] = None
    egress_nav: Optional[list[Point]] = None

    #: The ingress may not be pushed past this fraction of the departure-to-target
    #: leg. JoinZoneGeometry puts the join at 35-36% of that leg from home, so an
    #: ingress beyond ~64% (measured from the target) would sit BEHIND the join and
    #: inverts the route. 60% keeps the ingress inside the join-to-target segment
    #: with margin, whatever a weapon's authored range says.
    MAX_STANDOFF_FRACTION_OF_LEG = 0.6

    @staticmethod
    def standoff_doctrine(
        package: Package, doctrine: Doctrine, leg: Distance
    ) -> Doctrine:
        """Doctrine with the ingress bound widened to the package's own weapons.

        The attack task does not activate until the flight reaches the ingress
        point, so a package whose weapon out-ranges the doctrine bound flies PAST
        its own launch range and into the target's defenses without shooting --
        the bound is weapon-agnostic and 45 nm on modern doctrine. Only weapons
        that declare a range move it, it only ever widens, and it is capped so the
        route cannot invert (see MAX_STANDOFF_FRACTION_OF_LEG).

        The number is a PLANNING bound -- where the attack run begins -- not a
        promise the AI shoots from there. DCS releases at its own doctrine
        distance regardless; what this buys is that the flight is not dragged
        inside the defenses before its attack task exists.
        """
        standoff = PackageWaypoints._package_standoff_range(package)
        if standoff is None or standoff <= doctrine.max_ingress_distance:
            return doctrine
        widened = min(
            standoff,
            Distance.from_meters(
                leg.meters * PackageWaypoints.MAX_STANDOFF_FRACTION_OF_LEG
            ),
        )
        if widened <= doctrine.max_ingress_distance:
            return doctrine
        logging.debug(
            "Widening %s ingress for %s from %s to %s (weapons reach %s): its "
            "stand-off weapons out-range the doctrine bound",
            doctrine.name,
            package.target.name,
            doctrine.max_ingress_distance,
            widened,
            standoff,
        )
        return replace(doctrine, max_ingress_distance=widened)

    @staticmethod
    def _package_standoff_range(package: Package) -> Optional[Distance]:
        # The package flies to one ingress point, so it can only stand off as far
        # as its least-capable shooter. A flight carrying nothing with an authored
        # range (an escort, a short-legged strike) is not a shooter here and does
        # not drag the number down -- it is excluded, not counted as zero.
        ranges = [
            r for r in (f.max_standoff_range for f in package.flights) if r is not None
        ]
        return min(ranges) if ranges else None

    @staticmethod
    def create(
        package: Package, coalition: Coalition, dump_debug_info: bool
    ) -> PackageWaypoints:
        origin = package.departure_closest_to_target()

        # Start by picking the best IP for the attack.
        ip_solver = IpSolver(
            dcs_to_shapely_point(origin.position),
            dcs_to_shapely_point(package.target.position),
            PackageWaypoints.standoff_doctrine(
                package,
                coalition.doctrine,
                meters(origin.position.distance_to_point(package.target.position)),
            ),
            coalition.opponent.threat_zone.air_defenses,
        )
        ip_solver.set_debug_properties(
            waypoint_debug_directory() / "IP", coalition.game.theater.terrain
        )
        ingress_point_shapely = ip_solver.solve()
        if dump_debug_info:
            ip_solver.dump_debug_info()

        ingress_point = origin.position.new_in_same_map(
            ingress_point_shapely.x, ingress_point_shapely.y
        )

        tgt_point = package.target.position
        initial_point = PackageWaypoints.get_initial_point(ingress_point, tgt_point)

        join_point = JoinZoneGeometry(
            package.target.position,
            origin.position,
            ingress_point,
            coalition,
        ).find_best_join_point()

        # Join/split are derived from this base join_point. JoinZoneGeometry
        # fixes the base join distance between 35% and 36% of the home-to-target
        # leg, and WaypointBuilder.perturb then applies a small offset to
        # produce the final join/split waypoints.

        refuel_point = RefuelZoneGeometry(
            origin.position,
            join_point,
            coalition,
        ).find_best_refuel_point()

        # And the split point based on the best route from the IP. Since that's no
        # different than the best route *to* the IP, this is the same as the join point.
        # TODO: Estimate attack completion point based on the IP and split from there?
        return PackageWaypoints(
            WaypointBuilder.perturb(join_point),
            ingress_point,
            initial_point,
            WaypointBuilder.perturb(join_point),
            refuel_point,
        )

    @staticmethod
    def get_initial_point(ingress_point: Point, tgt_point: Point) -> Point:
        hdg = tgt_point.heading_between_point(ingress_point)
        # Generate a waypoint randomly between 7 & 9 NM
        dist = nautical_miles(random.random() * 2 + 7).meters
        initial_point = tgt_point.point_from_heading(hdg, dist)
        return initial_point

    @staticmethod
    def escort_hold_point(package: Package) -> Point:
        """Where the package's escorts anchor: the IP, or the shooters' launch range.

        A stand-off shooter starts its run at its own launch range (see
        standoff_doctrine), not at the 7-9 nm IP. Holding the escorts at the IP put
        a Patriot DEAD's escorts 7 nm from the Patriot while its Kh-59M shooters
        turned 62 nm out (Desert Trident turn 1, 2026-10-16).

        Only the package's attackers count: a SEAD escort's ARM says nothing about
        where bombers release, and one attacker with no ranged weapon flies to the
        target, so its escorts keep the IP.

        SEAD and SEAD sweep fly to their SEAD Search point, not to their ARM's
        authored range (80 nm for a HARM), so their escorts hold there.
        """
        waypoints = package.waypoints
        assert waypoints is not None
        target = package.target.position
        ip_distance = waypoints.initial.distance_to_point(target)
        if package.primary_task in (FlightType.SEAD, FlightType.SEAD_SWEEP):
            searches = [
                WaypointBuilder.sead_search_point(f, package.target)
                for f in package.flights
                if f.flight_type is package.primary_task
            ]
            if not searches:
                return waypoints.initial
            nearest = min(searches, key=lambda p: p.distance_to_point(target))
            if nearest.distance_to_point(target) <= ip_distance:
                return waypoints.initial
            return nearest
        ranges = [
            f.max_standoff_range
            for f in package.flights
            if f.flight_type is package.primary_task
        ]
        if not ranges or any(r is None for r in ranges):
            return waypoints.initial
        launch = min(r.meters for r in ranges if r is not None)
        if launch <= ip_distance:
            return waypoints.initial
        ingress_distance = waypoints.ingress.distance_to_point(target)
        hold_distance = max(ip_distance, min(launch, ingress_distance))
        heading = target.heading_between_point(waypoints.ingress)
        return target.point_from_heading(heading, hold_distance)
