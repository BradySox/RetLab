"""The campaign map's slot in the main window; the map steps aside while a mission runs.

A hidden QWebEngineView tells Chromium its page is not visible, and Chromium frees
the page's compositor tiles and decoded images, where the map's video memory goes.
The page is not discarded: it keeps taking the server's updates and comes back at
the same view. Features doc §8 (row B267).
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QStackedWidget, QWidget

PLACEHOLDER_TEXT = (
    "The map is paused while the mission runs, to leave video memory to DCS. "
    "It comes back when the mission window closes."
)


class MapPanel(QStackedWidget):
    def __init__(self, map_view: QWidget, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.map_view = map_view
        self.placeholder = QLabel(PLACEHOLDER_TEXT)
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder.setWordWrap(True)
        self.addWidget(map_view)
        self.addWidget(self.placeholder)
        self.setCurrentWidget(map_view)

    @property
    def released(self) -> bool:
        return self.currentWidget() is self.placeholder

    def release(self) -> None:
        if not self.released:
            logging.info("Map hidden while the mission runs")
            self.setCurrentWidget(self.placeholder)

    def restore(self) -> None:
        if self.released:
            logging.info("Map shown again")
            self.setCurrentWidget(self.map_view)


@contextmanager
def map_released(panel: Optional[MapPanel]) -> Iterator[None]:
    """Hides the map for the body of the block and always brings it back."""
    if panel is None:
        yield
        return
    panel.release()
    try:
        yield
    finally:
        panel.restore()
