from __future__ import annotations

from dataclasses import dataclass

from game.ato.flighttype import FlightType
from game.commander.missionproposals import EscortType
from game.commander.tasks.packageplanningtask import PackagePlanningTask
from game.commander.theaterstate import TheaterState
from game.theater import MissionTarget


@dataclass
class PlanPackageControl(PackagePlanningTask[MissionTarget]):
    """One airborne package controller C-130J per side (§117)."""

    def preconditions_met(self, state: TheaterState) -> bool:
        if not super().preconditions_met(state):
            return False
        return self.target in state.package_control_targets

    def apply_effects(self, state: TheaterState) -> None:
        state.package_control_targets.remove(self.target)
        super().apply_effects(state)

    def propose_flights(self) -> None:
        self.propose_flight(FlightType.PACKAGE_CONTROL, 1)
        # Threat-gated like the AEW&C escort, so a shortage never scrubs the C-130.
        self.propose_flight(FlightType.ESCORT, 2, EscortType.AirToAir)

    @property
    def asap(self) -> bool:
        # Up before the first packages push, like the AWACS.
        return True
