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

from game.ato.flight import Flight
from game.ato.flightplans.formationattack import (
    FormationAttackLayout,
    pre_push_refuel_point,
)
from game.ato.flightplans.planningerror import PlanningError


def offers_refuel_before_push(flight: Flight) -> bool:
    """Whether the tick box applies: a fixed-wing flight that holds before its join."""
    plan = flight.flight_plan
    return (
        not flight.is_helo
        and not plan.is_custom
        and isinstance(plan.layout, FormationAttackLayout)
        and plan.layout.hold is not None
    )


def no_tanker_reason(flight: Flight) -> Optional[str]:
    """Why no stop can be planned, or None when a theater tanker serves the jet."""
    waypoints = flight.package.waypoints
    if waypoints is None or pre_push_refuel_point(flight, waypoints.refuel) is None:
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
        self.checkbox = QCheckBox("Refuel before the push")
        self.checkbox.setChecked(flight.refuel_before_push)
        layout.addWidget(self.checkbox)

        reason = no_tanker_reason(flight)
        text = (
            "Ticked, the flight tanks at a theater tanker between Hold and Join, "
            "and leaves Hold earlier to make it; the TOT stays put. The stop after "
            "the strike is kept only if the jet cannot get home without it. AI "
            "flights fill to 90%. Changing this rebuilds the route and resets "
            "manual timing."
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
