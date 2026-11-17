"""Send spare armor from a base's stock out as a reserve group (§131 stage 4).

Adapted from the GPS destination in juanjux/dcs-escalation's transfer dialog
(LGPL-3.0). The point is typed as coordinates; there is no map picker yet.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dcs import Point
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from game.coordinates import parse_latlng
from game.dcs.groundunittype import GroundUnitType
from game.groundmovement.base import (
    available_stock,
    dispatch_base_movement,
    preview_base_movement,
)
from game.groundmovement.journey import GroundPosition
from game.groundmovement.settings import METERS_PER_MILE
from game.server import EventStream
from game.sim.gameupdateevents import GameUpdateEvents

if TYPE_CHECKING:
    from game import Game
    from game.groundmovement.base import BaseMovementPreview
    from game.theater.controlpoint import ControlPoint

BLOCKED_STYLE = "QLabel { color: #f0b429; font-weight: bold; }"


class ReserveDeployDialog(QDialog):
    def __init__(
        self, game: Game, base: ControlPoint, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.game = game
        self.base = base
        self.turn = game.turn
        self.preview: BaseMovementPreview | None = None
        self.setWindowTitle(f"Deploy a reserve from {base.name}")
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Pick spare armor to send out as its own group. "
                "Trucks to tow the guns are added for you."
            )
        )
        grid = QGridLayout()
        self.counts: dict[GroundUnitType, QSpinBox] = {}
        stock = available_stock(base)
        for row, (unit, count) in enumerate(
            sorted(stock.items(), key=lambda item: item[0].display_name)
        ):
            grid.addWidget(QLabel(f"{unit.display_name} ({count} spare)"), row, 0)
            spin = QSpinBox()
            spin.setRange(0, count)
            spin.valueChanged.connect(self.invalidate)
            grid.addWidget(spin, row, 1)
            self.counts[unit] = spin
        if not stock:
            grid.addWidget(QLabel("This base has no spare armor."), 0, 0)
        layout.addLayout(grid)
        coordinates = QHBoxLayout()
        self.coordinates = QLineEdit()
        self.coordinates.setPlaceholderText(
            "Where it goes: coordinates in friendly ground (copy them from the map)"
        )
        self.coordinates.textChanged.connect(self.invalidate)
        coordinates.addWidget(self.coordinates, 1)
        paste = QPushButton("Paste")
        paste.clicked.connect(
            lambda: self.coordinates.setText(QApplication.clipboard().text())
        )
        coordinates.addWidget(paste)
        layout.addLayout(coordinates)
        self.details = QLabel("Pick units and a point, then preview the route.")
        self.details.setWordWrap(True)
        self.details.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.details)
        buttons = QHBoxLayout()
        preview = QPushButton("Preview route")
        preview.clicked.connect(self.calculate)
        self.send_button = QPushButton("Send")
        self.send_button.setProperty("style", "btn-success")
        self.send_button.setEnabled(False)
        self.send_button.clicked.connect(self.send)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        for button in (preview, self.send_button, cancel):
            buttons.addWidget(button)
        layout.addLayout(buttons)

    def invalidate(self) -> None:
        self.preview = None
        self.send_button.setEnabled(False)
        self.set_details("Preview the route before sending.")

    def set_details(self, text: str, *, blocked: bool = False) -> None:
        self.details.setStyleSheet(BLOCKED_STYLE if blocked else "")
        self.details.setText(f"Can't deploy: {text}" if blocked else text)

    def selection(self) -> dict[GroundUnitType, int]:
        return {u: s.value() for u, s in self.counts.items() if s.value()}

    def position(self) -> GroundPosition:
        latlng = parse_latlng(self.coordinates.text())
        if latlng is None:
            raise ValueError("enter coordinates, or paste them from the map")
        point = Point.from_latlng(latlng, self.game.theater.terrain)
        return GroundPosition(point.x, point.y)

    def calculate(self) -> None:
        self.invalidate()
        try:
            if self.game.turn != self.turn:
                raise ValueError("the turn changed; close and reopen this window")
            result = preview_base_movement(
                self.game,
                self.base.id,
                self.base.captured,
                self.selection(),
                self.position(),
            )
        except (ValueError, PermissionError) as exc:
            self.set_details(str(exc), blocked=True)
            return
        self.preview = result
        added = ", ".join(f"{n} x {v}" for v, n in result.automatically_added) or "none"
        self.set_details(
            "\n".join(
                [
                    f"{len(result.manifest.unit_ids)} units go.",
                    f"Trucks added to tow: {added}.",
                    f"Road {result.road_distance_m / METERS_PER_MILE:.0f} mi, "
                    f"off-road {result.offroad_distance_m / METERS_PER_MILE:.0f} mi; "
                    f"about {result.arrival_in_turns} turn(s).",
                    "If a front reaches the group, it joins that front's base.",
                ]
            )
        )
        self.send_button.setEnabled(True)

    def send(self) -> None:
        if self.preview is None:
            return
        self.send_button.setEnabled(False)
        events = GameUpdateEvents()
        try:
            if self.game.turn != self.turn:
                raise ValueError("the turn changed; preview again")
            dispatch_base_movement(
                self.game,
                self.base.id,
                self.base.captured,
                self.selection(),
                self.position(),
                events,
            )
        except (ValueError, PermissionError) as exc:
            self.preview = None
            self.set_details(str(exc), blocked=True)
            return
        EventStream.put_nowait(events)
        self.accept()
