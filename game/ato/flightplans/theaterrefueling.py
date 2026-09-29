from __future__ import annotations

from typing import Type

from dcs import Point

from game.ato.flighttype import FlightType
from game.utils import Distance, Heading, meters, nautical_miles
from .ibuilder import IBuilder
from .patrolling import PatrollingLayout, step_back_from_threat
from .refuelingflightplan import RefuelingFlightPlan, TankerBoxLayout
from .waypointbuilder import WaypointBuilder


class TheaterRefuelingFlightPlan(RefuelingFlightPlan):
    @staticmethod
    def builder_type() -> Type[Builder]:
        return Builder


#: How far apart consecutive theater tankers sit, measured back from the threat.
#:
#: A coalition flying both boom and probe receivers gets one tanker of each, and
#: without this they would be handed the same racetrack -- two orbits in the same
#: airspace at the same altitude.
TANKER_ORBIT_SPACING = nautical_miles(15)

#: The tanker box's front leg, across the threat axis. Shrunk from 40 NM (DM 2026-09-29).
TANKER_BOX_LENGTH = nautical_miles(30)

#: How far a tanker box extends back from its front leg. Added to the spacing so a
#: second tanker's box starts behind the first one's back leg.
TANKER_BOX_DEPTH = nautical_miles(15)


class Builder(IBuilder[TheaterRefuelingFlightPlan, PatrollingLayout]):
    def _orbit_index(self) -> int:
        """This tanker's place in its package, so several do not stack up.

        Identity, not equality: ``list.index`` would match the first flight that
        merely compares equal, which is how two tankers end up sharing a slot.
        """
        index = 0
        for flight in self.package.flights:
            if flight is self.flight:
                return index
            if flight.flight_type is FlightType.REFUELING:
                index += 1
        return 0

    def layout(self) -> TankerBoxLayout:
        racetrack_half_distance = TANKER_BOX_LENGTH.meters / 2

        location = self.package.target

        closest_boundary = self.threat_zones.closest_boundary(location.position)
        heading_to_threat_boundary = Heading.from_degrees(
            location.position.heading_between_point(closest_boundary)
        )
        distance_to_threat = meters(
            location.position.distance_to_point(closest_boundary)
        )
        orbit_heading = heading_to_threat_boundary

        # Station 70nm outside the threat zone.
        threat_buffer = nautical_miles(
            self.coalition.game.settings.tanker_threat_buffer_min_distance
        )
        threatened = self.threat_zones.threatened(location.position)
        if threatened:
            orbit_distance = distance_to_threat + threat_buffer
        else:
            orbit_distance = distance_to_threat - threat_buffer

        # Each further tanker sits another step back from the threat. Backwards
        # rather than forwards so an extra tanker can never be pushed into the
        # threat zone the buffer above just cleared -- which for a threatened
        # anchor means further past the edge, not back toward it.
        spacing = TANKER_ORBIT_SPACING + TANKER_BOX_DEPTH
        orbit_distance = step_back_from_threat(
            orbit_distance,
            threatened=threatened,
            step=spacing * self._orbit_index(),
        )

        racetrack_center = location.position.point_from_heading(
            orbit_heading.degrees, orbit_distance.meters
        )

        racetrack_start = racetrack_center.point_from_heading(
            orbit_heading.right.degrees, racetrack_half_distance
        )

        racetrack_end = racetrack_center.point_from_heading(
            orbit_heading.left.degrees, racetrack_half_distance
        )

        builder = WaypointBuilder(self.flight)
        # Back from the threat, as step_back_from_threat reads it.
        back = orbit_heading if threatened else orbit_heading.opposite
        return self._box_layout(
            builder,
            racetrack_start,
            racetrack_end,
            back,
            builder.get_patrol_altitude,
        )

    def _box_layout(
        self,
        builder: WaypointBuilder,
        front_start: Point,
        front_end: Point,
        back: Heading,
        altitude: Distance,
    ) -> TankerBoxLayout:
        depth = TANKER_BOX_DEPTH.meters
        corners = [
            front_end,
            front_end.point_from_heading(back.degrees, depth),
            front_start.point_from_heading(back.degrees, depth),
        ]
        box_corners = []
        for number, position in enumerate(corners, start=2):
            corner = builder.nav(position, altitude)
            corner.name = f"BOX {number}"
            corner.pretty_name = f"Tanker box {number}"
            corner.description = "Tanker box corner"
            box_corners.append(corner)
        start = builder.race_track_start(front_start, altitude)
        start.name = "BOX 1"
        start.pretty_name = "Tanker box start"
        start.description = "Fly the box through the next corners"
        end = builder.race_track_end(front_start, altitude)
        end.name = "BOX END"
        end.pretty_name = "Tanker box end"
        end.description = "Back to box 2 until on-station time is up"
        return TankerBoxLayout(
            departure=builder.takeoff(self.flight.departure),
            nav_to=builder.nav_path(
                self.flight.departure.position, front_start, altitude
            ),
            nav_from=builder.nav_path(
                front_start, self.flight.arrival.position, altitude
            ),
            patrol_start=start,
            patrol_end=end,
            box_corners=box_corners,
            arrival=builder.land(self.flight.arrival),
            divert=builder.divert(self.flight.divert),
            bullseye=builder.bullseye(),
            custom_waypoints=list(),
        )

    def build(self, dump_debug_info: bool = False) -> TheaterRefuelingFlightPlan:
        return TheaterRefuelingFlightPlan(self.flight, self.layout())
