"""The flight-plan table: numbered waypoints with times, fuel and altitudes."""

import datetime
from dataclasses import dataclass
from typing import List, Optional


from game.ato.flightwaypoint import FlightWaypoint
from game.ato.flightwaypointtype import FlightWaypointType
from game.utils import Distance, Speed, UnitSystem, meters, mps, pounds

from .writer import KneeboardPageWriter, _format_clock, format_kneeboard_time_compact


@dataclass(frozen=True)
class NumberedWaypoint:
    number: int | str
    waypoint: FlightWaypoint


class FlightPlanBuilder:
    WAYPOINT_DESC_MAX_LEN = 25

    #: Post-landing reference rows: the divert option and the bullseye ride the
    #: jet's route as steerpoints (so the nav system carries them), but they are
    #: not flown legs of the plan. The chained ETA past the landing point reads
    #: "when you would get there if you kept flying after landing" -- noise -- so
    #: their Time/GS/Mach cells stay blank, matching the Fuel column's treatment.
    REFERENCE_WAYPOINT_TYPES = (
        FlightWaypointType.DIVERT,
        FlightWaypointType.BULLSEYE,
    )

    def __init__(
        self,
        units: UnitSystem,
        patrol_speed: Optional[Speed] = None,
        zulu_tz: Optional[datetime.tzinfo] = None,
    ) -> None:
        # Set for an airframe whose card runs Zulu. Every time printed below
        # converts through it; the elapsed-time maths stays on the naive values.
        self.zulu_tz = zulu_tz
        self.rows: List[List[str]] = []
        self.target_points: List[NumberedWaypoint] = []
        self.last_waypoint: Optional[FlightWaypoint] = None
        self.units = units
        # The plan's on-station speed for a racetrack flight; the racetrack-end
        # row shows it in the GS cell, where distance / schedule-time would
        # divide the track length by the whole on-station dwell.
        self.patrol_speed = patrol_speed
        # Per-waypoint (planned - min) fuel margins. Constant up to a tanker and
        # constant again after it, so min() is the unrefuelled RTB margin and the
        # rows from the REFUEL waypoint on carry the with-tanker figure.
        self.fuel_margins: List[float] = []
        self.tanked_margins: List[float] = []
        self.refuel_seen = False
        # On-station planned minutes and fuel burn, captured from the racetrack
        # rows for the endurance call-out ("fuel supports ~N min on station").
        self.patrol_dwell: Optional[datetime.timedelta] = None
        self.patrol_burn: Optional[float] = None
        self.patrol_push_margin: Optional[float] = None

    def add_waypoint(self, waypoint_num: int | str, waypoint: FlightWaypoint) -> None:
        if waypoint.waypoint_type == FlightWaypointType.TARGET_POINT:
            self.target_points.append(NumberedWaypoint(waypoint_num, waypoint))
            return

        if self.target_points:
            self.coalesce_target_points()
            self.target_points = []

        self.add_waypoint_row(NumberedWaypoint(waypoint_num, waypoint))
        self.last_waypoint = waypoint

    def coalesce_target_points(self) -> None:
        if len(self.target_points) <= 4:
            for steerpoint in self.target_points:
                self.add_waypoint_row(steerpoint)
            if self.target_points:
                self.last_waypoint = self.target_points[-1].waypoint
            return

        first_waypoint_num = self.target_points[0].number
        last_waypoint_num = self.target_points[-1].number

        row = [
            f"{first_waypoint_num}-{last_waypoint_num}",
            "Target points",
            "0",
            self._waypoint_distance(self.target_points[0].waypoint),
            self._ground_speed(self.target_points[0].waypoint),
            self._mach(self.target_points[0].waypoint, meters(0)),
            self._format_time(self.target_points[0].waypoint.tot),
            self._format_departure_time(self.target_points[0].waypoint.departure_time),
            self._format_fuel(self.target_points[0].waypoint),
        ]
        self.rows.append(row)
        self.last_waypoint = self.target_points[-1].waypoint

    def add_waypoint_row(self, waypoint: NumberedWaypoint) -> None:
        if (
            waypoint.waypoint.waypoint_type is FlightWaypointType.PATROL
            and self.last_waypoint is not None
            and self.last_waypoint.waypoint_type is FlightWaypointType.PATROL_TRACK
        ):
            self._record_patrol(self.last_waypoint, waypoint.waypoint)
        # Kneeboards are only generated for client flights (see
        # client_flights_by_airframe), so a ground-marked waypoint is always zeroed in
        # the .miz for this reader -- print what the cockpit will actually show rather
        # than the AI track altitude the planner recorded.
        alt = (
            meters(0)
            if waypoint.waypoint.marks_ground_for_player
            else waypoint.waypoint.alt
        )
        is_reference = (
            waypoint.waypoint.waypoint_type
            in FlightPlanBuilder.REFERENCE_WAYPOINT_TYPES
        )
        if waypoint.waypoint.waypoint_type is FlightWaypointType.REFUEL:
            self.refuel_seen = True
        row = [
            str(waypoint.number),
            KneeboardPageWriter.wrap_line(
                waypoint.waypoint.display_name,
                FlightPlanBuilder.WAYPOINT_DESC_MAX_LEN,
            ),
            self._format_alt(alt),
            self._waypoint_distance(waypoint.waypoint),
            "" if is_reference else self._ground_speed(waypoint.waypoint),
            "" if is_reference else self._mach(waypoint.waypoint, alt),
            "" if is_reference else self._format_time(waypoint.waypoint.tot),
            (
                ""
                if is_reference
                else self._format_departure_time(waypoint.waypoint.departure_time)
            ),
            self._format_fuel(waypoint.waypoint),
        ]
        self.rows.append(row)

    def _format_time(self, time: datetime.datetime | None) -> str:
        # Compact, not stacked: doubling nine waypoint rows pushed the Laser Code
        # table off the bottom of the Mission Info page (flown 2026-08-21).
        return format_kneeboard_time_compact(time, self.zulu_tz)

    def _format_departure_time(self, time: datetime.datetime | None) -> str:
        """Zulu only, labelled to match the Time cell beside it.

        Carrying the pair here too takes the Time column's last character back and
        wraps both. This column holds one row on a typical plan, so it shows the
        figure being cross-checked against the DED and leaves the offset to the
        Time cell next to it.
        """
        if time is None or self.zulu_tz is None or time.tzinfo is not None:
            return _format_clock(time)
        zulu = time.replace(tzinfo=self.zulu_tz).astimezone(datetime.timezone.utc)
        return f"{zulu.strftime('%H:%M')}Z"

    def _format_alt(self, alt: Distance) -> str:
        return f"{self.units.distance_short(alt):.0f}"

    def _waypoint_distance(self, waypoint: FlightWaypoint) -> str:
        if self.last_waypoint is None:
            return "-"

        distance = meters(
            self.last_waypoint.position.distance_to_point(waypoint.position)
        )

        return f"{self.units.distance_long(distance):.1f}"

    def _ground_speed(self, waypoint: FlightWaypoint) -> str:
        speed = self._leg_speed(waypoint)
        if speed is None:
            return "-"
        return f"{self.units.speed(speed):.0f}"

    def _mach(self, waypoint: FlightWaypoint, alt: Distance) -> str:
        """The GS cell's speed as a Mach number at the row's altitude, still air."""
        speed = self._leg_speed(waypoint)
        if speed is None:
            return "-"
        return f"{speed.mach(alt):.2f}"

    def _leg_speed(self, waypoint: FlightWaypoint) -> Optional[Speed]:
        if waypoint.waypoint_type is FlightWaypointType.PATROL:
            # The racetrack-end row: its schedule time is the on-station dwell
            # (the flight laps the track until push), so distance / time would
            # print the track length over the whole patrol -- a nonsense figure
            # like 19 kt. Show the speed actually flown on station instead.
            return self.patrol_speed

        if self.last_waypoint is None:
            return None

        if waypoint.tot is None:
            return None

        if self.last_waypoint.departure_time is not None:
            last_time = self.last_waypoint.departure_time
        elif self.last_waypoint.tot is not None:
            last_time = self.last_waypoint.tot
        else:
            return None

        if (waypoint.tot - last_time).total_seconds() <= 0.0:
            # A zero or negative leg time (drifted structural vs chained clocks,
            # degenerate manual timing) has no meaningful ground speed.
            return None

        return mps(
            self.last_waypoint.position.distance_to_point(waypoint.position)
            / (waypoint.tot - last_time).total_seconds()
        )

    def _format_fuel(self, waypoint: FlightWaypoint) -> str:
        """The fuel ladder folded into the flight plan: planned fuel remaining.

        Only genuine RTB checkpoints (those with a min-to-RTB figure) get a fuel
        entry; post-landing reference points like the bullseye carry a forward-burn
        "fuel" that isn't a real arrival state, so their cell stays blank. The
        constant (planned - min) margin is collected once per row for the one-line
        RTB call-out under the table instead of repeating a Min/Margin pair per row.
        """
        if waypoint.min_fuel is None:
            return ""
        if waypoint.fuel_planned is None:
            return "-"
        margin = waypoint.fuel_planned - waypoint.min_fuel
        self.fuel_margins.append(margin)
        if self.refuel_seen:
            self.tanked_margins.append(margin)
        return f"{self.units.mass(pounds(waypoint.fuel_planned)):.0f}"

    def _record_patrol(self, start: FlightWaypoint, end: FlightWaypoint) -> None:
        """Capture the racetrack leg's dwell, burn, and push-time fuel margin.

        Feeds the on-station endurance call-out. The dwell is the schedule gap
        between the track's ends (arrival on station to push), the burn is the
        planned-fuel drop across it, and the margin at push is how much longer
        the gas holds the station beyond the planned departure.
        """
        if start.tot is not None and end.tot is not None:
            dwell = end.tot - start.tot
            if dwell.total_seconds() > 0:
                self.patrol_dwell = dwell
        if start.fuel_planned is not None and end.fuel_planned is not None:
            burn = start.fuel_planned - end.fuel_planned
            if burn > 0:
                self.patrol_burn = burn
        if end.fuel_planned is not None and end.min_fuel is not None:
            self.patrol_push_margin = end.fuel_planned - end.min_fuel

    def fuel_margin_line(self) -> Optional[str]:
        """The one-line RTB margin call-out for the flight plan, or None.

        (Planned - min) is constant up to a tanker (start fuel - total burn -
        reserve: the unrefuelled margin) and constant again after it, so the
        worst case is reported once instead of printing Min and Margin columns
        that repeat the same number every row. A planned tanker pass never
        raises this figure; tanker_line carries the with-tanker number.
        """
        if not self.fuel_margins:
            return None
        surplus = min(self.fuel_margins)
        uom = self.units.mass_uom
        amount = f"{self.units.mass(pounds(abs(surplus))):.0f}"
        if surplus >= 0:
            return (
                f"RTB margin +{amount} {uom} — spare over the minimum to get home "
                "with reserves."
            )
        return (
            f"RTB margin -{amount} {uom} — short of getting home as planned; "
            "tank or divert."
        )

    def tanker_line(self) -> Optional[str]:
        """The with-tanker margin, only when the sortie depends on the pass.

        Same rule as the Payload tab's fuel brief: a refuel waypoint means a
        tanker is planned, never that the gas was taken, so the with-tanker
        figure is printed only when the jet does not get home without it.
        """
        if not self.fuel_margins or not self.tanked_margins:
            return None
        dry = min(self.fuel_margins)
        tanked = min(self.tanked_margins)
        if dry >= 0 or tanked < 0:
            return None
        amount = f"{self.units.mass(pounds(tanked)):.0f}"
        return (
            f"Does not get home without the tanker: +{amount} "
            f"{self.units.mass_uom} with the planned pass."
        )

    def patrol_endurance_line(self) -> Optional[str]:
        """For a racetrack flight: how long the gas actually holds the station.

        The planner's on-station time is doctrine (the desired BARCAP duration
        and the wave relief schedule), not a fuel computation, so this line
        answers the pilot's real question -- "can I stay past the planned push,
        and how long?" -- from the same ladder the Fuel column shows: planned
        dwell plus the push-time margin divided by the on-station burn rate.
        """
        if self.patrol_dwell is None or self.patrol_burn is None:
            return None
        if self.patrol_push_margin is None:
            return None
        dwell_minutes = self.patrol_dwell.total_seconds() / 60.0
        burn_per_min = self.patrol_burn / dwell_minutes
        if burn_per_min <= 0:
            return None
        supported = dwell_minutes + self.patrol_push_margin / burn_per_min
        if supported < 0:
            supported = 0
        return (
            f"On station {dwell_minutes:.0f} min planned; fuel supports "
            f"~{supported:.0f} min before bingo (RTB minimum)."
        )

    @property
    def patrol_endurance_is_short(self) -> bool:
        """True when the gas does not cover the planned on-station time."""
        return self.patrol_push_margin is not None and self.patrol_push_margin < 0

    def build(self) -> List[List[str]]:
        if self.target_points:
            self.coalesce_target_points()
            self.target_points = []
        return self.rows
