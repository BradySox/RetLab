"""File > Phone link: turn the phone map on and show the QR code a phone scans."""

from __future__ import annotations

from io import BytesIO
from typing import Optional

import segno
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QImage, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from game.server.phone import PhoneAccess, lan_address, phone_url
from game.server.settings import ServerSettings
from qt_ui import liberation_install

QR_SIZE_PX = 280


def _qr_pixmap(text: str) -> QPixmap:
    png = BytesIO()
    segno.make(text, error="m").save(png, kind="png", scale=8, border=2)
    image = QImage.fromData(png.getvalue(), "PNG")
    return QPixmap.fromImage(image).scaled(
        QR_SIZE_PX,
        QR_SIZE_PX,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.FastTransformation,
    )


class PhoneLinkDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Phone link")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)

        self.enabled = QCheckBox("Let my phone see the map (home Wi-Fi)")
        self.enabled.setChecked(liberation_install.phone_access())
        self.enabled.toggled.connect(self._on_toggled)
        layout.addWidget(self.enabled)

        intro = QLabel(
            "Your phone can view the map, but not change anything. It must be on "
            "the same Wi-Fi as this PC, and Retribution must be open. The first "
            "time, Windows may ask to let Retribution through the firewall: allow "
            "it on private networks."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        self.qr = QLabel()
        self.qr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.qr)

        self.link = QLabel()
        self.link.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.link)

        buttons = QHBoxLayout()
        self.copy = QPushButton("Copy link")
        self.copy.clicked.connect(self._copy_link)
        buttons.addWidget(self.copy)
        self.new_key = QPushButton("New link")
        self.new_key.setToolTip(
            "Make a new link. Phones holding the old one lose access at once."
        )
        self.new_key.clicked.connect(self._new_link)
        buttons.addWidget(self.new_key)
        buttons.addStretch()
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        buttons.addWidget(close)
        layout.addLayout(buttons)

        self._refresh()

    def _url(self) -> Optional[str]:
        address = lan_address()
        if address is None:
            return None
        port = ServerSettings.get(liberation_install.server_port()).server_port
        return phone_url(address, port, liberation_install.phone_key())

    def _refresh(self) -> None:
        wanted = self.enabled.isChecked()
        url = self._url() if wanted else None
        if not wanted:
            message = "Off. Tick the box to get a link for your phone."
        elif url is None:
            message = "This PC is not on a network, so there is no link to give."
        elif PhoneAccess.listening:
            message = "On. Scan the code with your phone's camera."
        else:
            message = (
                "Restart Retribution to finish turning this on. The code below "
                "will work after the restart."
            )
        self.status.setText(message)
        self.copy.setEnabled(url is not None)
        self.new_key.setEnabled(wanted)
        if url is None:
            self.qr.clear()
            self.link.clear()
        else:
            self.qr.setPixmap(_qr_pixmap(url))
            # The full link is too long to read; it is on the code and the button.
            self.link.setText(url.split("/phone/", 1)[0])

    def _on_toggled(self, checked: bool) -> None:
        liberation_install.set_phone_access(checked)
        self._apply()

    def _new_link(self) -> None:
        liberation_install.set_phone_access(True, new_key=True)
        self._apply()

    def _apply(self) -> None:
        # Off and a new key take hold at once; on needs the socket a restart opens.
        PhoneAccess.configure(
            liberation_install.phone_access(), liberation_install.phone_key()
        )
        self._refresh()

    def _copy_link(self) -> None:
        url = self._url()
        if url is not None:
            QGuiApplication.clipboard().setText(url)
