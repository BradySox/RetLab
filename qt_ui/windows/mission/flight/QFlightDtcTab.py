"""Edit Flight -> DTC tab: the planner's per-flight cartridge controls (§74, §102).

Writes ``flight.dtc_options`` live; the next generation's ``DtcGenerator`` honors it.
Only the sections this airframe's cartridge carries are offered, with what each does
on this jet (``game/missiongenerator/dtc/sections.py``). A section that is off leaves
the jet's own defaults untouched: omitted from the Hornet, Viper and Apache
cartridges, written as the editor's reset state on the Tomcat.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from game import Game
from game.ato.flight import Flight
from game.ato.flightwaypointtype import FlightWaypointType
from game.missiongenerator.dtc.sections import GROUPS, SECTIONS, sections_for

#: Waypoint types never offered in the picker: row 0 is never written.
_NOT_OFFERED = {FlightWaypointType.TAKEOFF}

#: The distance the SAM filter starts at when it is first ticked.
DEFAULT_THREAT_RADIUS_NM = 30


def _waypoint_type_label(name: str) -> str:
    return name.replace("_", " ").title()


class QFlightDtcTab(QFrame):
    """Per-flight native-DTC cartridge controls."""

    def __init__(self, flight: Flight, game: Game) -> None:
        super().__init__()
        self.flight = flight
        self.game = game
        self.section_boxes: list[tuple[QCheckBox, str]] = []
        self.waypoint_list: Optional[QListWidget] = None

        layout = QVBoxLayout()
        intro = QLabel(
            "This flight's DCS data cartridge. Only what this aircraft's cartridge"
            " can hold is listed. Changes apply the next time the mission is"
            " generated."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self.mode_selector = QComboBox()
        self.mode_selector.addItem(self._follow_label(), None)
        self.mode_selector.addItem("Always load for this flight", True)
        self.mode_selector.addItem("Never load for this flight", False)
        self.mode_selector.setCurrentIndex(
            {None: 0, True: 1, False: 2}[flight.dtc_options.enabled]
        )
        self.mode_selector.currentIndexChanged.connect(self.on_mode_changed)
        layout.addWidget(self.mode_selector)

        self.contents_group = QWidget()
        contents = QVBoxLayout()
        contents.setContentsMargins(0, 0, 0, 0)
        contents.addWidget(self._loading_box())
        for group in GROUPS:
            box = self._group_box(group)
            if box is not None:
                contents.addWidget(box)
        self.contents_group.setLayout(contents)
        layout.addWidget(self.contents_group)

        layout.addStretch()
        self.setLayout(layout)
        self._update_enabled_state()

    # ------------------------------------------------------------------ layout

    @property
    def _dcs_id(self) -> Optional[str]:
        unit_type = getattr(self.flight, "unit_type", None)
        dcs_type = getattr(unit_type, "dcs_unit_type", None)
        return getattr(dcs_type, "id", None)

    def _offered(self) -> list[Any]:
        dcs_id = self._dcs_id
        return list(SECTIONS) if dcs_id is None else sections_for(dcs_id)

    def _loading_box(self) -> QGroupBox:
        box = QGroupBox("Loading")
        row = QVBoxLayout()
        self.load_selector = QComboBox()
        self.load_selector.addItem("Load at spawn", True)
        self.load_selector.addItem("Pilot loads it from the DTC page", False)
        self.load_selector.setCurrentIndex(
            0 if self.flight.dtc_options.auto_load else 1
        )
        self.load_selector.currentIndexChanged.connect(self._on_load_changed)
        row.addWidget(self.load_selector)
        row.addWidget(
            self._note(
                "Pilot loads it: the cartridge is still in the jet's list, and"
                " nothing is loaded until the crew selects it."
            )
        )
        box.setLayout(row)
        return box

    def _group_box(self, group: str) -> Optional[QGroupBox]:
        sections = [s for s in self._offered() if s.group == group]
        if not sections:
            return None
        box = QGroupBox(group)
        column = QVBoxLayout()
        dcs_id = self._dcs_id
        for section in sections:
            check = QCheckBox(section.label)
            check.setChecked(getattr(self.flight.dtc_options, section.attr))
            check.toggled.connect(self._make_section_writer(section.attr))
            column.addWidget(check)
            description = (
                section.on.get(dcs_id)
                if dcs_id is not None
                else " / ".join(section.on.values())
            )
            if description:
                column.addWidget(self._note(description, indent=True))
            self.section_boxes.append((check, section.attr))
            if section.attr == "route":
                column.addWidget(self._waypoint_picker())
            elif section.attr == "threat_rings":
                column.addLayout(self._threat_radius_row())
        box.setLayout(column)
        return box

    @staticmethod
    def _note(text: str, indent: bool = False) -> QLabel:
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet(
            "color: #8a99a6; font-size: 11px;"
            + (" margin-left: 22px;" if indent else "")
        )
        return label

    def _waypoint_picker(self) -> QWidget:
        """One row per kind of waypoint in this flight plan; unticked kinds stay out
        of the cartridge, and the numbers after them close up."""
        holder = QWidget()
        column = QVBoxLayout()
        column.setContentsMargins(22, 0, 0, 0)
        column.addWidget(
            self._note(
                "Waypoints in the cartridge. An unticked kind is left out and the"
                " numbers after it close up; the kneeboard prints '-' on its row."
            )
        )
        counts: dict[str, int] = {}
        plan = getattr(self.flight, "flight_plan", None)
        for waypoint in getattr(plan, "waypoints", []) or []:
            if waypoint.waypoint_type in _NOT_OFFERED:
                continue
            name = waypoint.waypoint_type.name
            counts[name] = counts.get(name, 0) + 1
        skipped = set(self.flight.dtc_options.skipped_waypoints)
        for name in skipped - set(counts):
            counts[name] = 0
        listing = QListWidget()
        for name, count in counts.items():
            text = _waypoint_type_label(name) + (f"  ({count})" if count else "")
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Unchecked if name in skipped else Qt.CheckState.Checked
            )
            listing.addItem(item)
        listing.setMaximumHeight(min(22 * max(len(counts), 1) + 8, 190))
        listing.itemChanged.connect(self._on_waypoint_toggled)
        self.waypoint_list = listing
        column.addWidget(listing)
        holder.setLayout(column)
        return holder

    def _threat_radius_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(22, 0, 0, 0)
        radius = self.flight.dtc_options.threat_ring_radius_nm
        self.threat_near_route = QCheckBox("Only sites whose ring comes within")
        self.threat_near_route.setChecked(radius is not None)
        self.threat_radius = QSpinBox()
        self.threat_radius.setRange(0, 300)
        self.threat_radius.setSuffix(" nm of the route")
        self.threat_radius.setValue(
            radius if radius is not None else DEFAULT_THREAT_RADIUS_NM
        )
        self.threat_radius.setEnabled(radius is not None)
        self.threat_near_route.toggled.connect(self._write_threat_radius)
        self.threat_radius.valueChanged.connect(lambda _v: self._write_threat_radius())
        row.addWidget(self.threat_near_route)
        row.addWidget(self.threat_radius)
        row.addStretch()
        return row

    # ------------------------------------------------------------------ writes

    def _follow_label(self) -> str:
        state = "on" if self.game.settings.dtc_data_cartridges else "off"
        return f"Follow the campaign setting (currently {state})"

    @property
    def _resolved_enabled(self) -> bool:
        return self.flight.dtc_options.resolve_enabled(
            self.game.settings.dtc_data_cartridges
        )

    def _update_enabled_state(self) -> None:
        self.contents_group.setEnabled(self._resolved_enabled)

    def on_mode_changed(self, index: int) -> None:
        self.flight.dtc_options.enabled = self.mode_selector.itemData(index)
        self._update_enabled_state()

    def _on_load_changed(self, index: int) -> None:
        self.flight.dtc_options.auto_load = bool(self.load_selector.itemData(index))

    def _write_threat_radius(self) -> None:
        near = self.threat_near_route.isChecked()
        self.threat_radius.setEnabled(near)
        self.flight.dtc_options.threat_ring_radius_nm = (
            self.threat_radius.value() if near else None
        )

    def _on_waypoint_toggled(self, item: QListWidgetItem) -> None:
        name = item.data(Qt.ItemDataRole.UserRole)
        skipped = [n for n in self.flight.dtc_options.skipped_waypoints if n != name]
        if item.checkState() != Qt.CheckState.Checked:
            skipped.append(name)
        self.flight.dtc_options.skipped_waypoints = skipped

    def _make_section_writer(self, attr: str) -> Callable[[bool], None]:
        def write(checked: bool) -> None:
            setattr(self.flight.dtc_options, attr, checked)

        return write
