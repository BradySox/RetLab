"""Keeps the campaign map off the video card, leaving its memory to DCS.

QtWebEngine renders in the app's own process, and on the GPU it held ~4 GB of
dedicated VRAM next to DCS; hiding the view did not free it. Chromium renders in
software with these flags, and Qt Quick (which composites the web view inside the
widget) uses its software scene graph. Features doc §8 (row B267).
"""

from __future__ import annotations

from typing import MutableMapping

CHROMIUM_FLAGS_VAR = "QTWEBENGINE_CHROMIUM_FLAGS"
CHROMIUM_FLAGS = ("--disable-gpu", "--disable-gpu-compositing")
QUICK_BACKEND_VAR = "QT_QUICK_BACKEND"
QUICK_BACKEND = "software"


def chromium_flags_value(existing: str | None) -> str:
    """The user's own flags first, then any of ours they did not already pass."""
    flags = (existing or "").split()
    for flag in CHROMIUM_FLAGS:
        if flag not in flags:
            flags.append(flag)
    return " ".join(flags)


def apply_software_rendering(env: MutableMapping[str, str]) -> None:
    """Must run before the QApplication exists; a user's own backend choice wins."""
    env[CHROMIUM_FLAGS_VAR] = chromium_flags_value(env.get(CHROMIUM_FLAGS_VAR))
    env.setdefault(QUICK_BACKEND_VAR, QUICK_BACKEND)
