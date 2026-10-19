from __future__ import annotations

from datetime import timedelta
from typing import Type

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
from .uizonedisplay import UiZoneDisplay, UiZone
from ..flightwaypoint import FlightWaypoint
from ..flightwaypointtype import FlightWaypointType
from ...utils import Distance, nautical_miles


class SeadSweepFlightPlan(
    FormationAttackFlightPlan, UiZoneDisplay, TacticalOverlayDisplay
):
    @staticmethod
    def builder_type() -> Type[Builder]:
        return Builder

    def default_tot_offset(self) -> timedelta:
        return -timedelta(minutes=2)

    @property
    def _sweep_point(self) -> FlightWaypoint:
        return self.layout.initial or self.tot_waypoint

    @property
    def _engagement_range(self) -> Distance:
        return nautical_miles(
            self.flight.coalition.game.settings.sead_sweep_engagement_range_distance
        )

    def tactical_overlay(self) -> TacticalOverlay:
        # Sweep flies to its sweep point, but its EngageTargetsInZone bubble is
        # centered on the target, so the run and the bubble sit in different places.
        return standoff_run_overlay(
            path=[
                self.layout.ingress.position,
                self._sweep_point.position,
                *(wp.position for wp in self.layout.egress_nav),
                self.layout.split.position,
            ],
            engagement_center=self.tot_waypoint.position,
            engagement_range=self._engagement_range,
            target_position=self.tot_waypoint.position,
        )

    def ui_zone(self) -> UiZone:
        return UiZone([self.tot_waypoint.position], self._engagement_range)


class Builder(FormationAttackBuilder[SeadSweepFlightPlan, FormationAttackLayout]):
    def layout(self) -> FormationAttackLayout:
        return self._build(FlightWaypointType.INGRESS_SEAD_SWEEP)

    def build(self, dump_debug_info: bool = False) -> SeadSweepFlightPlan:
        return SeadSweepFlightPlan(self.flight, self.layout())
