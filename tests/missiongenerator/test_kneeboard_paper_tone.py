"""The daytime kneeboard paper is mid grey, and every ink still reads on it.

The 210 grey text pages and near-white map pages glared in the cockpit
(2026-10-25). The paper went darker and the colored inks with it; this pins
both halves so a later tweak cannot brighten the paper or sink an ink.
"""

from __future__ import annotations

from game.missiongenerator.kneeboard import KneeboardPageWriter
from game.missiongenerator.kneeboard_recon.pages import _LIGHT_PALETTE


def _luminance(colour: tuple[int, int, int]) -> float:
    def channel(v: int) -> float:
        c = v / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = colour
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def _contrast(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    hi, lo = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_daytime_paper_is_no_brighter_than_the_softer_tone() -> None:
    writer = KneeboardPageWriter(dark_theme=False)
    assert max(writer.background_fill) <= 185
    assert max(_LIGHT_PALETTE.page_bg) <= 205
    assert max(_LIGHT_PALETTE.panel_bg) <= 212


def test_every_daytime_ink_keeps_its_contrast_on_the_darker_paper() -> None:
    writer = KneeboardPageWriter(dark_theme=False)
    for ink in (
        writer.foreground_fill,
        writer.col_nav,
        writer.col_caution,
        writer.col_success,
        writer.col_danger,
        writer.col_muted,
    ):
        assert _contrast(ink, writer.background_fill) >= 4.5, ink
