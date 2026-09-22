"""The window's palette and the few styled controls it builds.

Lifted from juanjux/dcs-escalation's ``qt_ui/widgets/cards.py`` and ``controls.py``
(LGPL-3.0), trimmed to what this window uses rather than porting his whole restyle.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QPushButton, QWidget

CARD_BG = "#14202B"
CARD_BORDER = "#1D2731"
CAPTION = "#6B7A87"

CONTROL_HEIGHT = 28
VALUE = "#D3DFE8"
IDLE_BG = "#26343F"
BORDER = "#3A4B5C"
DISABLED_BG = "#1B2530"
DISABLED_TEXT = "#4F6070"
DISABLED_BORDER = "#28333D"

BUTTON_KINDS = {
    "normal": (IDLE_BG, BORDER, VALUE, "#31424F"),
    "primary": ("#2B506D", "#3F6B8C", "#DCE9F4", "#34617F"),
}

_CARD_SERIAL = [0]


def mono(size: int = 13) -> QFont:
    font = QFont("Consolas")
    font.setStyleHint(QFont.StyleHint.Monospace)
    font.setPixelSize(size)
    return font


def card() -> QWidget:
    """An empty card; the rule is scoped to its object name so it does not cascade."""
    widget = QWidget()
    widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    _CARD_SERIAL[0] += 1
    widget.setObjectName(f"playablecard{_CARD_SERIAL[0]}")
    widget.setStyleSheet(
        f"#{widget.objectName()} {{ background: {CARD_BG};"
        f" border: 1px solid {CARD_BORDER}; border-radius: 3px; }}"
    )
    return widget


def styled_input(widget: QWidget, width: Optional[int] = None) -> QWidget:
    widget.setFixedHeight(CONTROL_HEIGHT)
    if width is not None:
        widget.setFixedWidth(width)
    widget.setStyleSheet(
        f"QWidget {{ background: {IDLE_BG}; color: {VALUE};"
        f" border: 1px solid {BORDER}; border-radius: 3px; padding: 0 6px;"
        " font-size: 12px; }"
        f"QWidget:disabled {{ background: {DISABLED_BG}; color: {DISABLED_TEXT};"
        f" border-color: {DISABLED_BORDER}; }}"
    )
    return widget


def style_button(widget: QPushButton, kind: str = "normal") -> QPushButton:
    background, border, ink, hover = BUTTON_KINDS[kind]
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    widget.setMinimumHeight(CONTROL_HEIGHT)
    widget.setStyleSheet(
        f"QPushButton {{ background: {background}; color: {ink};"
        f" border: 1px solid {border}; border-radius: 3px; padding: 4px 14px;"
        f" font-size: 12px; font-weight: {'600' if kind != 'normal' else 'normal'}; }}"
        f"QPushButton:hover {{ background: {hover}; }}"
        f"QPushButton:disabled {{ background: {DISABLED_BG}; color: {DISABLED_TEXT};"
        f" border-color: {DISABLED_BORDER}; }}"
    )
    return widget
