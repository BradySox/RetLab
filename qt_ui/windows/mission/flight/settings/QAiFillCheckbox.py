from PySide6.QtWidgets import QCheckBox, QGroupBox, QLabel, QVBoxLayout

from game.ato.flight import Flight
from game.retlab.ai_fill import ai_fill_wanted, offers_ai_fill


class QAiFillCheckbox(QGroupBox):
    """The per-flight "AI fills if no player" box (§113)."""

    def __init__(self, flight: Flight) -> None:
        super().__init__()
        self.flight = flight

        self.checkbox = QCheckBox("AI fills if no player")
        self.checkbox.toggled.connect(self._on_toggled)
        self.note = QLabel()
        self.note.setWordWrap(True)

        layout = QVBoxLayout()
        layout.addWidget(self.checkbox)
        layout.addWidget(self.note)
        self.setLayout(layout)
        self.refresh()

    def refresh(self) -> None:
        offered = offers_ai_fill(self.flight)
        settings = self.flight.coalition.game.settings
        self.checkbox.blockSignals(True)
        self.checkbox.setEnabled(offered)
        self.checkbox.setChecked(offered and ai_fill_wanted(self.flight, settings))
        self.checkbox.blockSignals(False)
        if offered:
            minutes = int(settings.ai_fill_check_delay.total_seconds() // 60)
            self.note.setText(
                f"If nobody is in any player seat {minutes} minutes after mission "
                "start, an AI copy of those seats starts in the air over the home "
                "base at the planned takeoff time and flies this tasking."
            )
        elif self.flight.client_count == 0:
            self.note.setText("Only a flight with player seats can use this.")
        else:
            self.note.setText("Not available for this task.")

    def _on_toggled(self, checked: bool) -> None:
        self.flight.ai_fills_if_empty = checked
