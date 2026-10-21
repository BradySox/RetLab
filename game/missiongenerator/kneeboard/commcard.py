"""The comm card: every preset on both radios, by name, like a squadron's paper card.

Laid out on the comm cards of hand-built campaigns: COMM1 down the left, the channel
number in the middle, COMM2 on the right (user call, 2026-10-21).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional

from ..kneeboard_page import KneeboardPage
from .writer import KneeboardPageWriter

if TYPE_CHECKING:
    from game.missiongenerator.aircraft.flightdata import FlightData
    from game.radio.radios import RadioFrequency


def preset_rows(
    flight: FlightData, labels: dict[RadioFrequency, str]
) -> list[list[str]]:
    """One row per channel: COMM1 name and frequency, channel, COMM2 name and frequency."""
    by_radio: dict[int, dict[int, RadioFrequency]] = {}
    for freq, assignments in flight.frequency_to_channel_map.items():
        for a in assignments:
            by_radio.setdefault(a.radio_id, {})[a.channel] = freq
    radios = sorted(by_radio)[:2]
    if not radios:
        return []
    last = max(max(channels) for channels in by_radio.values())

    def cell(radio: int, channel: int) -> str:
        freq = by_radio.get(radio, {}).get(channel)
        if freq is None:
            return ""
        return f"{labels.get(freq, '')}\n{freq}".strip()

    rows = []
    for channel in range(1, min(last, 20) + 1):
        left = cell(radios[0], channel)
        right = cell(radios[1], channel) if len(radios) > 1 else ""
        if left or right:
            rows.append([left, str(channel), right])
    return rows


class CommCardPage(KneeboardPage):
    """Every preset on the jet's radios, named."""

    def __init__(
        self,
        flight: FlightData,
        labels: dict[RadioFrequency, str],
        dark_kneeboard: bool,
    ) -> None:
        self.flight = flight
        self.labels = labels
        self.dark_kneeboard = dark_kneeboard

    def write(self, path: Path) -> None:
        w = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        w.title(f"{self.flight.callsign} Comm Card")
        by_radio: dict[int, dict[int, RadioFrequency]] = {}
        for freq, assignments in self.flight.frequency_to_channel_map.items():
            for a in assignments:
                by_radio.setdefault(a.radio_id, {})[a.channel] = freq
        radios = sorted(by_radio)[:2]
        if not radios:
            w.text("This aircraft has no preset channels.", wrap=True)
            w.write(path)
            return
        names = [radio_name(self.flight, r) for r in radios]
        _grid(w, by_radio, radios, self.labels, names)
        w.write(path)


def radio_name(flight: FlightData, radio_id: int) -> str:
    """The radio as the other pages name its presets: ``COM1``, ``UHF``, ``AUX``."""
    name = flight.aircraft_type.channel_name(radio_id, 1)
    if name.endswith(" Ch 1") and len(name) > len(" Ch 1"):
        return name[: -len(" Ch 1")]
    return f"COMM {radio_id}"


def fit(text: str, max_px: float, length: Callable[[str], float]) -> str:
    """The text cut down with an ellipsis until it fits; a long tower name ran into
    the Ch column (2026-10-21)."""
    if length(text) <= max_px:
        return text
    while text and length(text + "...") > max_px:
        text = text[:-1]
    return text.rstrip() + "..."


def _grid(
    w: KneeboardPageWriter,
    by_radio: dict[int, dict[int, RadioFrequency]],
    radios: list[int],
    labels: dict[RadioFrequency, str],
    names: Optional[list[str]] = None,
) -> None:
    """A ruled 20-row card: COMM1, channel, COMM2."""
    draw, font, ink = w.draw, w.table_font, w.foreground_fill
    left = w.page_margin
    width = w.image_size[0] - 2 * w.page_margin
    ch_w = 60
    col_w = (width - ch_w) // 2
    xs = [left, left + col_w, left + col_w + ch_w, left + width]
    top = w.y + 6
    rows = max(20, max(max(c) for c in by_radio.values()))
    row_h = min(44, (w.image_size[1] - top - w.page_margin) // (rows + 1))
    names = names or [f"COMM {r}" for r in radios]
    headers = [names[0], "Ch", names[1] if len(radios) > 1 else ""]

    def centred(text: str, x0: int, x1: int, y: int) -> None:
        tw = draw.textlength(text, font=font)
        draw.text((x0 + (x1 - x0 - tw) / 2, y), text, font=font, fill=ink)

    def cell(radio: int, channel: int) -> str:
        freq = by_radio.get(radio, {}).get(channel)
        if freq is None:
            return ""
        name = labels.get(freq, "")
        number = f"{freq.mhz:.3f}"
        if not name:
            return number
        room = col_w - 16 - draw.textlength(f"  {number}", font=font)
        name = fit(name, room, lambda t: draw.textlength(t, font=font))
        return f"{name}  {number}"

    for r in range(rows + 1):
        y = top + r * row_h
        draw.line((xs[0], y, xs[3], y), fill=ink, width=2 if r <= 1 else 1)
        text_y = y + (row_h - 22) // 2
        if r == 0:
            for i, h in enumerate(headers):
                centred(h, xs[i], xs[i + 1], text_y)
            continue
        centred(cell(radios[0], r), xs[0], xs[1], text_y)
        centred(str(r), xs[1], xs[2], text_y)
        if len(radios) > 1:
            centred(cell(radios[1], r), xs[2], xs[3], text_y)
    bottom = top + (rows + 1) * row_h
    draw.line((xs[0], bottom, xs[3], bottom), fill=ink, width=2)
    for x in xs:
        draw.line((x, top, x, bottom), fill=ink, width=2)
    w.y = bottom + 8
