from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from dcs import Point

from game.ato.flight import Flight
from game.ato.flightplans.barcap import BarCapFlightPlan
from game.ato.flightplans.formationattack import FormationAttackLayout
from game.ato.flightplans.planningerror import PlanningError
from game.ato.flightplans.tarcap import TarCapFlightPlan
from game.ato.tankeravailability import (
    auto_tanking_minutes,
    early_refuel_point,
    post_refuel_shortfall,
)


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


def kept_stop_text(flight: Flight) -> Optional[str]:
    """Why the second tanker stop is still on the route, or None when it is not."""
    if not flight.refuel_before_push:
        return None
    shortfall = post_refuel_shortfall(flight, flight.flight_plan.layout)
    if shortfall is None:
        return None
    return (
        f"The second Refuel stayed: without it this jet lands {shortfall:,.0f} lb "
        "under its reserve."
    )


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

        row = QHBoxLayout()
        row.addWidget(QLabel("Minutes on the tanker"))
        self.minutes = QSpinBox()
        self.minutes.setRange(1, 60)
        self.minutes.setSuffix(" min")
        self.minutes.setValue(self._shown_minutes())
        row.addWidget(self.minutes)
        self.reset = QPushButton("Reset")
        self.reset.setToolTip("Back to 4 minutes a jet, plus 1")
        row.addWidget(self.reset)
        row.addStretch()
        layout.addLayout(row)

        reason = no_tanker_reason(flight)
        if cap:
            text = (
                "Ticked, the flight tanks at a theater tanker between Takeoff and "
                "Race-track start, and takes off earlier to make it; the station "
                "times stay put. Minutes on the tanker is the time planned for the "
                "stop, 4 a jet plus 1 until you type one. A TARCAP keeps its stop coming off station only "
                "if the jet cannot get home without it. AI flights fill to 90%. "
                "Changing this rebuilds the route and resets manual timing."
            )
        else:
            text = (
                "Ticked, the flight tanks at a theater tanker between Hold and "
                "Join, and leaves Hold earlier to make it; the TOT stays put. "
                "Minutes on the tanker is the time planned for the stop, 4 a jet "
                "plus 1 until you type one. The stop after the strike is kept only if the jet cannot get home "
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

        self.kept = QLabel()
        self.kept.setWordWrap(True)
        self.kept.setSizePolicy(policy)
        layout.addWidget(self.kept)
        self._update_kept()
        self._update_minutes_enabled()

        self.checkbox.toggled.connect(self._on_toggled)
        self.minutes.valueChanged.connect(self._on_minutes)
        self.reset.clicked.connect(self._on_reset)

    def _shown_minutes(self) -> int:
        minutes = self.flight.tanking_minutes
        return auto_tanking_minutes(self.flight) if minutes is None else minutes

    def _update_minutes_enabled(self) -> None:
        on = self.flight.refuel_before_push
        self.minutes.setEnabled(on)
        self.reset.setEnabled(on and self.flight.tanking_minutes is not None)

    def _on_minutes(self, value: int) -> None:
        # Only the clock moves (Hold or takeoff leaves earlier); no route rebuild.
        self.flight.tanking_minutes = value
        self._update_minutes_enabled()
        self.changed.emit()

    def _on_reset(self) -> None:
        self.flight.tanking_minutes = None
        self.minutes.blockSignals(True)
        self.minutes.setValue(self._shown_minutes())
        self.minutes.blockSignals(False)
        self._update_minutes_enabled()
        self.changed.emit()

    def _update_kept(self) -> None:
        text = kept_stop_text(self.flight)
        self.kept.setText(f"<small><strong>{text}</strong></small>" if text else "")
        self.kept.setVisible(text is not None)

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
        self._update_kept()
        self._update_minutes_enabled()
        self.changed.emit()
