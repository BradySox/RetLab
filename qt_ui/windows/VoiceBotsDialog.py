"""File > Voice bots: start SRS and SkyEye on Take Off (§120)."""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from game.retlab import skyeye_launcher
from qt_ui import liberation_install


class VoiceBotsDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Voice bots")
        self.setMinimumWidth(460)
        layout = QVBoxLayout(self)

        self.autostart = QCheckBox("Start SRS and SkyEye when I press Take off")
        self.autostart.setChecked(liberation_install.skyeye_autostart())
        layout.addWidget(self.autostart)

        intro = QLabel(
            "Take off starts the SRS server and waits for it, starts SkyEye in a "
            "minimized window, then starts your SRS client and connects it to your "
            "own server. Anything already running is left alone. SkyEye stops when "
            "the mission results come in; SRS keeps running."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        layout.addWidget(QLabel("SkyEye folder (skyeye.exe and config.yaml):"))
        row = QHBoxLayout()
        self.folder = QLineEdit(str(liberation_install.skyeye_dir()))
        self.folder.textChanged.connect(self._refresh)
        row.addWidget(self.folder)
        browse = QPushButton("Browse...")
        browse.clicked.connect(self._browse)
        row.addWidget(browse)
        layout.addLayout(row)

        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        buttons = QHBoxLayout()
        log = QPushButton("SkyEye log")
        log.clicked.connect(self._show_log)
        buttons.addWidget(log)
        buttons.addStretch()
        save = QPushButton("Save")
        save.setDefault(True)
        save.clicked.connect(self._save)
        buttons.addWidget(save)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)
        self._refresh()

    def _show_log(self) -> None:
        from qt_ui.windows.SkyEyeLogDialog import SkyEyeLogDialog

        SkyEyeLogDialog(self).show()

    def _browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "SkyEye folder", self.folder.text()
        )
        if folder:
            self.folder.setText(folder)

    def _refresh(self) -> None:
        from pathlib import Path

        folder = Path(self.folder.text())
        srs = skyeye_launcher.srs_dir()
        lines = [
            _found("skyeye.exe", (folder / skyeye_launcher.SKYEYE_EXE).exists()),
            _found("config.yaml", (folder / skyeye_launcher.SKYEYE_CONFIG).exists()),
            _found(
                "SRS server",
                (srs / "Server" / skyeye_launcher.SRS_SERVER_EXE).exists(),
            ),
            _found(
                "SRS client",
                (srs / "Client" / skyeye_launcher.SRS_CLIENT_EXE).exists(),
            ),
        ]
        self.status.setText("<br>".join(lines))

    def _save(self) -> None:
        liberation_install.set_skyeye(self.autostart.isChecked(), self.folder.text())
        self.accept()


def _found(name: str, ok: bool) -> str:
    return f"{name}: {'found' if ok else '<b>not found</b>'}"
