from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QLabel,
    QMessageBox,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from dcs import Point

from game.ato.flight import Flight
from game.ato.flightplans.barcap import BarCapFlightPlan
from game.ato.flightplans.formationattack import FormationAttackLayout
from game.ato.flightplans.planningerror import PlanningError
from game.ato.flightplans.tarcap import TarCapFlightPlan
from game.ato.tankeravailability import early_refuel_point


def is_cap(flight: Flight) -> bool:
    return isinstance(flight.flight_plan, (BarCapFlightPlan, TarCapFlightPlan))


def offers_refuel_before_push(flight: Flight) -> bool:
    """Whether the tick box applies: a fixed-wing flight that holds before its join,
    or a CAP on its way to station."""
    plan = flight.flight_plan
    if flight.is_helo or plan.is_custom:
        return False
    if is_cap(flight):
        return True
    return (
        isinstance(plan.layout, FormationAttackLayout) and plan.layout.hold is not None
    )


def _planned_point(flight: Flight) -> Optional[Point]:
    if is_cap(flight):
        start = flight.flight_plan.layout.patrol_start.position
        return flight.departure.position.lerp(start, 0.75)
    waypoints = flight.package.waypoints
    return None if waypoints is None else waypoints.refuel


def no_tanker_reason(flight: Flight) -> Optional[str]:
    """Why no stop can be planned, or None when a theater tanker serves the jet."""
    planned = _planned_point(flight)
    if planned is None or early_refuel_point(flight, planned) is None:
        return (
            "No theater tanker that can refuel this aircraft is on the ATO, so "
            "there is no stop to plan."
        )
    return None


class QRefuelBeforePush(QWidget):
    """Plan the flight's tanker stop between the hold and the join."""

    changed = Signal()

    def __init__(self, flight: Flight) -> None:
        super().__init__()
        self.flight = flight
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QLabel("<strong>Tanker :</strong>"))
        cap = is_cap(flight)
        self.checkbox = QCheckBox(
            "Refuel before station" if cap else "Refuel before the push"
        )
        self.checkbox.setChecked(flight.refuel_before_push)
        layout.addWidget(self.checkbox)

        reason = no_tanker_reason(flight)
        if cap:
            text = (
                "Ticked, the flight tanks at a theater tanker between Takeoff and "
                "Race-track start, and takes off earlier to make it; the station "
                "times stay put. AI flights fill to 90%. Changing this rebuilds "
                "the route and resets manual timing."
            )
        else:
            text = (
                "Ticked, the flight tanks at a theater tanker between Hold and "
                "Join, and leaves Hold earlier to make it; the TOT stays put. The "
                "stop after the strike is kept only if the jet cannot get home "
                "without it. AI flights fill to 90%. Changing this rebuilds the "
                "route and resets manual timing."
            )
        if reason is not None:
            text = f"{reason} {text}"
            self.checkbox.setEnabled(flight.refuel_before_push)
        description = QLabel(f"<small>{text}</small>")
        description.setWordWrap(True)
        # Wrap into the column's width instead of widening the column.
        policy = QSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Minimum)
        policy.setHeightForWidth(True)
        description.setSizePolicy(policy)
        layout.addWidget(description)

        self.checkbox.toggled.connect(self._on_toggled)

    def _on_toggled(self, checked: bool) -> None:
        self.flight.refuel_before_push = checked
        try:
            self.flight.recreate_flight_plan()
        except PlanningError as ex:
            self.flight.refuel_before_push = not checked
            self.flight.recreate_flight_plan()
            self.checkbox.blockSignals(True)
            self.checkbox.setChecked(not checked)
            self.checkbox.blockSignals(False)
            QMessageBox.critical(self, "Could not replan the flight", str(ex))
            return
        if no_tanker_reason(self.flight) is not None:
            self.checkbox.setEnabled(checked)
        self.changed.emit()
