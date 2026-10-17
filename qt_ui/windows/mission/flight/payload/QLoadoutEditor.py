from collections.abc import Iterator
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractScrollArea,
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from game import Game
from game.ato.flight import Flight
from game.ato.flightmember import FlightMember
from game.data.gunammunition import (
    GAU8_AIRCRAFT,
    GAU8_AMMUNITION,
    GAU8_DEFAULT_AMMUNITION,
)
from game.data.weapons import Pylon
from qt_ui.blocksignals import block_signals
from qt_ui.windows.mission.flight.payload.QPylonEditor import QPylonEditor


class QLoadoutEditor(QGroupBox):
    def __init__(self, flight: Flight, flight_member: FlightMember, game: Game) -> None:
        super().__init__("Use custom loadout")
        self.flight = flight
        self.flight_member = flight_member
        self.game = game
        self.setCheckable(True)
        self.setChecked(flight_member.loadout.is_custom)

        vbox = QVBoxLayout(self)

        self.show_training_check = QCheckBox("Show training and non-combat stores")
        self.show_training_check.toggled.connect(self._show_training_changed)
        vbox.addWidget(self.show_training_check)
        training_hint = QLabel(
            "Practice, captive and inert weapons, smoke and illumination stores, "
            "TCTS/ACMI and travel pods. White phosphorus marking rockets are always "
            "listed, and so is a store already fitted on the pylon."
        )
        training_hint.setWordWrap(True)
        training_hint.setStyleSheet("color: gray;")
        vbox.addWidget(training_hint)

        self.ammunition_selector: Optional[QComboBox] = None
        if self.flight.unit_type.dcs_unit_type.id in GAU8_AIRCRAFT:
            ammo_row = QHBoxLayout()
            ammo_row.addWidget(QLabel("GAU-8 ammunition"))
            self.ammunition_selector = QComboBox()
            for value, label in GAU8_AMMUNITION.items():
                self.ammunition_selector.addItem(label, value)
            self.ammunition_selector.setToolTip(
                "Ammunition loaded into the gun. Tick Use custom loadout to change "
                "it."
            )
            ammo_row.addWidget(self.ammunition_selector, 1)
            self._sync_ammunition()
            self.ammunition_selector.currentIndexChanged.connect(
                self._ammunition_changed
            )
            vbox.addLayout(ammo_row)

        pylon_grid = QGridLayout()
        for i, pylon in enumerate(Pylon.iter_pylons(self.flight.unit_type)):
            label = QLabel(f"<b>{pylon.number}</b>")
            label.setSizePolicy(
                QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            )
            pylon_grid.addWidget(label, i, 0)
            pylon_grid.addWidget(QPylonEditor(game, flight, flight_member, pylon), i, 1)

        # The pylon list scrolls rather than shrinking its rows when the window
        # cannot be tall enough for every station. Without the scroll the list's
        # full height was also its *minimum*, so the screen-fit clamp (which
        # relaxes a minimum to get a window on screen) squeezed the rows until
        # their text clipped: 19 pylons on an F-15E ask for more height than a
        # 1440p panel at 150% scaling has.
        #
        # It still *shows* every station, because the payload tab gives this
        # widget its whole column to stretch into. That is load-bearing, and the
        # reason an earlier attempt at a scroll here was reverted for "opening
        # showing only a few rows": QScrollArea::sizeHint is hard-capped at 24
        # font-heights (~360 px), so a scroll can never ask for a tall list no
        # matter its size-adjust policy -- it can only grow into space something
        # else has claimed. AdjustToContents keeps the hint tracking the content
        # up to that cap; the column stretch does the rest.
        pylon_content = QWidget()
        pylon_content.setLayout(pylon_grid)
        pylon_scroll = QScrollArea()
        pylon_scroll.setWidget(pylon_content)
        pylon_scroll.setWidgetResizable(True)
        pylon_scroll.setFrameShape(QFrame.Shape.NoFrame)
        pylon_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        pylon_scroll.setSizeAdjustPolicy(
            QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents
        )
        vbox.addWidget(pylon_scroll, stretch=1)

        self.setLayout(vbox)

        for pylon_editor in self.iter_pylon_editors():
            pylon_editor.set_from(self.flight_member.loadout)

    def iter_pylon_editors(self) -> Iterator[QPylonEditor]:
        yield from self.findChildren(QPylonEditor)

    def _show_training_changed(self, show: bool) -> None:
        for pylon_editor in self.iter_pylon_editors():
            pylon_editor.set_show_training(show)

    def _sync_ammunition(self) -> None:
        if self.ammunition_selector is not None:
            ammo = self.flight_member.loadout.ammo_type
            if ammo not in GAU8_AMMUNITION:
                ammo = GAU8_DEFAULT_AMMUNITION
            with block_signals(self.ammunition_selector):
                self.ammunition_selector.setCurrentIndex(
                    self.ammunition_selector.findData(ammo)
                )

    def _ammunition_changed(self, _index: int) -> None:
        if self.ammunition_selector is not None and self.isChecked():
            self.flight_member.loadout.ammo_type = (
                self.ammunition_selector.currentData()
            )

    def set_flight_member(self, flight_member: FlightMember) -> None:
        self.flight_member = flight_member
        with block_signals(self):
            self.setChecked(self.flight_member.use_custom_loadout)
        for pylon_editor in self.iter_pylon_editors():
            pylon_editor.set_flight_member(flight_member)
        self._sync_ammunition()

    def reset_pylons(self) -> None:
        self.flight_member.use_custom_loadout = self.isChecked()
        self._sync_ammunition()
        if not self.isChecked():
            for pylon_editor in self.iter_pylon_editors():
                pylon_editor.set_from(self.flight_member.loadout)
