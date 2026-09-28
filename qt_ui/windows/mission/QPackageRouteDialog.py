"""The package route window: the way in and out every flight in a package flies.

A view over game/ato/packageroute.py, which does the work and is where the rules are.
Points are moved on the map, from any flight of the package (game/ato/routeedit.py),
so the window is not modal and reads the package again when it is next active.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from game.ato import packageroute
from game.ato.packageroute import Kind, Leg, RoutePoint
from game.coordinates import format_for
from game.server import EventStream
from game.sim import GameUpdateEvents
from qt_ui.models import PackageModel
from qt_ui.uiconstants import EVENT_ICONS

HEADER_LABELS = ["Point", "Leg", "Coordinates"]


class QPackageRouteDialog(QDialog):
    def __init__(self, package_model: PackageModel, parent: QWidget) -> None:
        super().__init__(parent)
        self.package_model = package_model
        package = package_model.package
        self.setWindowTitle(
            f"Package route: {package.custom_name or package.target.name}"
        )
        self.setWindowIcon(EVENT_ICONS["strike"])
        self.setMinimumSize(560, 420)

        layout = QVBoxLayout(self)
        intro = QLabel(
            "The way in (join to IP) and the way out (target to split) are flown by "
            "every flight in the package together. A NAV point added or deleted here "
            "changes every flight's route, so the package still meets at the join."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self.table = QTableWidget(0, len(HEADER_LABELS))
        self.table.setHorizontalHeaderLabels(HEADER_LABELS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self.table.itemSelectionChanged.connect(self.update_buttons)
        layout.addWidget(self.table)

        self.move_hint = QLabel()
        self.move_hint.setWordWrap(True)
        layout.addWidget(self.move_hint)

        buttons = QHBoxLayout()
        self.insert_button = QPushButton("Insert NAV point")
        self.insert_button.setToolTip(
            "Adds a NAV point halfway along the leg after the selected point, for "
            "every flight. Selecting the IP or the split adds it on the leg before."
        )
        self.insert_button.clicked.connect(self.on_insert)
        buttons.addWidget(self.insert_button)
        self.delete_button = QPushButton("Delete NAV point")
        self.delete_button.clicked.connect(self.on_delete)
        buttons.addWidget(self.delete_button)
        self.up_button = QPushButton("Move Up")
        self.up_button.clicked.connect(lambda: self.on_move(-1))
        buttons.addWidget(self.up_button)
        self.down_button = QPushButton("Move Down")
        self.down_button.clicked.connect(lambda: self.on_move(1))
        buttons.addWidget(self.down_button)
        buttons.addStretch()
        self.reset_button = QPushButton("Reset to planned route")
        self.reset_button.setToolTip(
            "Removes your points from both legs, for every flight, and puts back the "
            "planner's detours round the SAM rings."
        )
        self.reset_button.clicked.connect(self.on_reset)
        buttons.addWidget(self.reset_button)
        layout.addLayout(buttons)

        self.flights_label = QLabel()
        self.flights_label.setWordWrap(True)
        self.flights_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(self.flights_label)

        close_row = QHBoxLayout()
        close_row.addStretch()
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        close_row.addWidget(close_button)
        layout.addLayout(close_row)

        self.rows: list[RoutePoint] = []
        # A row selected from the start, or every button opens greyed out.
        self.refresh(select=0)

    def changeEvent(self, event: QEvent) -> None:
        # A drag on the map moved a point while this window was in the background.
        if event.type() == QEvent.Type.ActivationChange and self.isActiveWindow():
            self.refresh(self.selected_row())
        super().changeEvent(event)

    def refresh(self, select: Optional[int] = None) -> None:
        package = self.package_model.package
        self.rows = packageroute.route_points(package)
        game = self.package_model.game_model.game
        settings = game.settings if game is not None else None
        self.table.setRowCount(len(self.rows))
        for row, point in enumerate(self.rows):
            name = (
                f"Target: {package.target.name}"
                if point.kind is Kind.TARGET
                else point.kind.value
            )
            cells = [
                name,
                point.leg.value if point.leg is not None else "",
                format_for(settings, point.position),
            ]
            for column, text in enumerate(cells):
                self.table.setItem(row, column, QTableWidgetItem(text))
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        if select is not None and 0 <= select < len(self.rows):
            self.table.selectRow(select)
        self.refresh_labels()
        self.update_buttons()

    def refresh_labels(self) -> None:
        package = self.package_model.package
        flying = packageroute.route_flights(package)
        own_way = [f for f in package.flights if f not in flying]
        if not flying:
            self.move_hint.setText(
                "This package has no shared route: its primary flight flies its own "
                "way to the target (a patrol, a helicopter, an air assault or a "
                "custom plan)."
            )
        else:
            self.move_hint.setText(
                "On the map, with any flight of this package selected: drag a point "
                "to move it for the whole package, double-click the route to add a "
                "point there, and right-click a point to delete it."
            )
        lines = [f"Flown by: {', '.join(str(f) for f in flying) or 'none'}"]
        if own_way:
            lines.append(f"Flies its own way: {', '.join(str(f) for f in own_way)}")
        if packageroute.is_edited(package):
            lines.append("Set by you. Reset puts back the planner's detours.")
        self.flights_label.setText("\n".join(lines))

    def selected_row(self) -> Optional[int]:
        rows = self.table.selectionModel().selectedRows()
        return rows[0].row() if rows else None

    def selected_nav(self) -> Optional[RoutePoint]:
        row = self.selected_row()
        if row is None or row >= len(self.rows):
            return None
        point = self.rows[row]
        return point if point.kind is Kind.NAV else None

    def update_buttons(self) -> None:
        has_route = bool(self.rows)
        nav = self.selected_nav()
        leg_length = (
            len(packageroute.points(self.package_model.package, nav.leg))
            if nav is not None and nav.leg is not None
            else 0
        )
        self.insert_button.setEnabled(has_route and self.selected_row() is not None)
        self.delete_button.setEnabled(nav is not None)
        self.up_button.setEnabled(nav is not None and nav.index > 0)
        self.down_button.setEnabled(nav is not None and nav.index < leg_length - 1)
        self.reset_button.setEnabled(
            has_route and packageroute.is_edited(self.package_model.package)
        )

    def on_insert(self) -> None:
        row = self.selected_row()
        if row is None:
            return
        placed = packageroute.insert_beside(self.package_model.package, row)
        if placed is not None:
            self.changed(select=self.row_of(*placed))

    def on_delete(self) -> None:
        nav = self.selected_nav()
        if nav is None or nav.leg is None:
            return
        packageroute.delete(self.package_model.package, nav.leg, nav.index)
        self.changed(select=self.selected_row())

    def on_move(self, direction: int) -> None:
        nav = self.selected_nav()
        if nav is None or nav.leg is None:
            return
        package = self.package_model.package
        if packageroute.move(package, nav.leg, nav.index, direction):
            self.changed(select=self.row_of(nav.leg, nav.index + direction))

    def on_reset(self) -> None:
        result = QMessageBox.question(
            self,
            "Reset the package route?",
            "Remove your NAV points from the way in and the way out, for every "
            "flight in the package, and put back the planner's route?",
            QMessageBox.StandardButton.Yes,
            QMessageBox.StandardButton.No,
        )
        if result != QMessageBox.StandardButton.Yes:
            return
        packageroute.reset(self.package_model.package)
        self.changed()

    def row_of(self, leg: Leg, index: int) -> Optional[int]:
        for row, point in enumerate(
            packageroute.route_points(self.package_model.package)
        ):
            if point.leg is leg and point.index == index:
                return row
        return None

    def changed(self, select: Optional[int] = None) -> None:
        """Every flight moved: redraw them on the map and re-time the package."""
        package = self.package_model.package
        EventStream.put_nowait(GameUpdateEvents().update_flights_in_package(package))
        self.package_model.update_tot()
        self.refresh(select)
