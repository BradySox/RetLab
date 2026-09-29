from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from game.ato.flight import Flight


class QTankerOrbitSpeed(QWidget):
    """A tanker flight's speed on its track, in KIAS."""

    DEFAULT_KIAS = 280

    def __init__(self, flight: Flight) -> None:
        super().__init__()
        self.flight = flight
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QLabel("<strong>Orbit speed :</strong>"))
        row = QHBoxLayout()
        self.enabled = QCheckBox("Set orbit speed")
        self.enabled.setChecked(flight.orbit_speed_kias is not None)
        row.addWidget(self.enabled)
        self.kias = QSpinBox()
        self.kias.setRange(100, 350)
        self.kias.setSingleStep(5)
        self.kias.setSuffix(" KIAS")
        self.kias.setValue(flight.orbit_speed_kias or self.DEFAULT_KIAS)
        self.kias.setEnabled(flight.orbit_speed_kias is not None)
        row.addWidget(self.kias)
        layout.addLayout(row)

        description = QLabel(
            "<small>Indicated airspeed on the tanker's track, to suit its "
            "receivers: 275-285 for the Hornet, 275 for the Harrier, 120-130 for "
            "helicopters. Unticked, the tanker flies its own speed. A tanker that "
            "cannot reach the speed flies at its top speed. A carrier recovery "
            "tanker ignores it.</small>"
        )
        description.setWordWrap(True)
        # Wrap into the column's width instead of widening the column.
        policy = QSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Minimum)
        policy.setHeightForWidth(True)
        description.setSizePolicy(policy)
        layout.addWidget(description)

        self.enabled.toggled.connect(self._on_change)
        self.kias.valueChanged.connect(self._on_change)

    def _on_change(self) -> None:
        on = self.enabled.isChecked()
        self.kias.setEnabled(on)
        self.flight.orbit_speed_kias = self.kias.value() if on else None
