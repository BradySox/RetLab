"""The log of the SkyEye that Take off started, which runs with no window (§120)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QDialog, QPlainTextEdit, QVBoxLayout, QWidget

from game.retlab import skyeye_launcher
from qt_ui import liberation_install

#: Enough for the current Take off; the file keeps every one.
SHOWN_LINES = 500
REFRESH_MS = 2000


def log_tail(log: Path, lines: int = SHOWN_LINES) -> str:
    try:
        text = log.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return f"No SkyEye log yet at {log}. Take off writes it."
    return "\n".join(text.splitlines()[-lines:])


class SkyEyeLogDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("SkyEye log")
        self.setMinimumSize(800, 500)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.log = liberation_install.skyeye_dir() / skyeye_launcher.SKYEYE_LOG
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        layout = QVBoxLayout(self)
        layout.addWidget(self.text)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(REFRESH_MS)
        self.refresh()

    def refresh(self) -> None:
        text = log_tail(self.log)
        if text == self.text.toPlainText():
            return
        bar = self.text.verticalScrollBar()
        at_end = bar.value() == bar.maximum()
        self.text.setPlainText(text)
        if at_end:
            bar.setValue(bar.maximum())
