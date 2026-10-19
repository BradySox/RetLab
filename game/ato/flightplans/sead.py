from __future__ import annotations

from datetime import timedelta
from typing import Type

from game.theater import TheaterGroundObject
from .formationattack import (
    FormationAttackBuilder,
    FormationAttackFlightPlan,
    FormationAttackLayout,
)
from .tacticaloverlay import (
    TacticalOverlay,
    TacticalOverlayDisplay,
    standoff_run_overlay,
)
from .uizonedisplay import UiZone, UiZoneDisplay
from ..flightwaypoint import FlightWaypoint
from ..flightwaypointtype import FlightWaypointType
from ...settings.settings import TargetIntelPrecision
from ...utils import nautical_miles

# Plain SEAD works from its SEAD Search point. The planner draws a fixed HARM-reach
# bubble there rather than the user-tunable SEAD-sweep engagement range.
SEAD_ENGAGEMENT_RANGE = nautical_miles(20)


class SeadFlightPlan(FormationAttackFlightPlan, UiZoneDisplay, TacticalOverlayDisplay):
    @staticmethod
    def builder_type() -> Type[Builder]:
        return Builder

    def default_tot_offset(self) -> timedelta:
        return -timedelta(minutes=1)

    def ui_zone(self) -> UiZone:
        return UiZone([self._search_point.position], SEAD_ENGAGEMENT_RANGE)

    @property
    def _search_point(self) -> FlightWaypoint:
        # The "SEAD Search" point; the target if the layout has none.
        return self.layout.initial or self.tot_waypoint

    def tactical_overlay(self) -> TacticalOverlay:
        search = self._search_point
        return standoff_run_overlay(
            path=[
                self.layout.ingress.position,
                search.position,
                *(wp.position for wp in self.layout.egress_nav),
                self.layout.split.position,
            ],
            engagement_center=search.position,
            engagement_range=SEAD_ENGAGEMENT_RANGE,
            target_position=self.tot_waypoint.position,
        )


class Builder(FormationAttackBuilder[SeadFlightPlan, FormationAttackLayout]):
    def layout(self) -> FormationAttackLayout:
        location = self.package.target
        # Only ground objectives expose individual units with coordinates (the
        # same list the SEAD kneeboard page renders). Against those, give each
        # listed emitter its own waypoint -- NOT every unit, which a HARM shooter
        # cannot use and which leaks the site composition (see sead_targets_for);
        # against e.g. naval groups the kneeboard lists no per-unit coordinates,
        # so fall back to the single target area. Mobile SAMs relocate, so under
        # Approximate intel we also fall back to a single fuzzed target-area
        # waypoint instead of exact per-emitter points.
        targets = (
            self.sead_targets_for(location)
            if (
                isinstance(location, TheaterGroundObject)
                and self.settings.target_intel_precision is TargetIntelPrecision.EXACT
            )
            else None
        )
        return self._build(FlightWaypointType.INGRESS_SEAD, targets)

    def build(self, dump_debug_info: bool = False) -> SeadFlightPlan:
        return SeadFlightPlan(self.flight, self.layout())
