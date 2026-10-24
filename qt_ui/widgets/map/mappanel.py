"""The campaign map's slot in the main window; the map is closed while a mission runs.

The map draws on the video card. Hiding it (#1354) kept ~4 GB of VRAM and software
rendering (#1356) made it crawl, so the web view is destroyed for the mission and a
new one is built when the mission ends. The mission's status panel fills the slot
meanwhile. Features doc §8 (row B267).
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QStackedWidget, QWidget

PLACEHOLDER_TEXT = (
    "The map is closed while the mission runs, to leave video memory to DCS. "
    "It comes back when the mission ends."
)


class MapPanel(QStackedWidget):
    def __init__(
        self, build_map: Callable[[], QWidget], parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self._build_map = build_map
        self.placeholder = QLabel(PLACEHOLDER_TEXT)
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder.setWordWrap(True)
        self.addWidget(self.placeholder)
        self.map_view: Optional[QWidget] = None
        self.status: Optional[QWidget] = None
        self.restore()

    @property
    def released(self) -> bool:
        return self.map_view is None

    def release(self, status: Optional[QWidget] = None) -> None:
        """Closes the map and shows status in its place, or the placeholder."""
        if status is not None and self.status is None:
            self.status = status
            self.addWidget(status)
        if self.map_view is None:
            return
        logging.info("Map closed while the mission runs")
        view = self.map_view
        self.map_view = None
        self.setCurrentWidget(self.status or self.placeholder)
        self.removeWidget(view)
        view.deleteLater()

    def restore(self) -> None:
        if self.status is not None:
            self.removeWidget(self.status)
            self.status = None
        if self.map_view is not None:
            return
        self.map_view = self._build_map()
        self.addWidget(self.map_view)
        self.setCurrentWidget(self.map_view)
