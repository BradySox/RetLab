"""The per-mission briefing card DCS shows on the briefing screen (§107).

Drawn fresh at every generation: campaign, turn, date and time, weather and the
player flights, in the same chart style as RetLab's static picture. A player's
own ``briefing.png`` still wins (see ``briefing_image.py``).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Union

from PIL import Image, ImageChops, ImageDraw, ImageFont

from game.retlab.briefing_image import DEFAULT_BRIEFING_IMAGE
from game.utils import meters, mps

if TYPE_CHECKING:
    from game import Game
    from game.missiongenerator.aircraft.flightdata import FlightData

WIDTH = 1600
HEIGHT = 1067
MAX_FLIGHT_ROWS = 6

BG_TOP = (12, 19, 30)
BG_BOTTOM = (29, 43, 59)
GRID = (30, 42, 56)
RING = (40, 54, 70)
GOLD = (214, 166, 64)
TEXT = (232, 237, 243)
MUTED = (150, 164, 180)
ROW_SHADE = (22, 33, 46)

# Where the F-16 sits in the static picture; it is lifted from there so both
# pictures share one drawing.
JET_BOX = (560, 100, 890, 380)

SEP = "  ·  "

Font = Union[ImageFont.FreeTypeFont, ImageFont.ImageFont]


@dataclass(frozen=True)
class CardFlight:
    callsign: str
    aircraft: str
    task: str
    target: str
    departs: str


@dataclass(frozen=True)
class BriefingCard:
    title: str
    subtitle: str
    weather: list[str]
    flights: list[CardFlight] = field(default_factory=list)


def _font(size: int, bold: bool = False) -> Font:
    # Bahnschrift is DIN, like the static picture. The app runs on Windows; the
    # fallbacks are for CI.
    try:
        font = ImageFont.truetype("bahnschrift.ttf", size)
        try:
            font.set_variation_by_name("Bold" if bold else "Regular")
        except (OSError, ValueError):
            pass
        return font
    except OSError:
        pass
    try:
        return ImageFont.truetype("arialbd.ttf" if bold else "arial.ttf", size)
    except OSError:
        return ImageFont.load_default(size)


def _text_width(draw: ImageDraw.ImageDraw, text: str, font: Font) -> float:
    return draw.textlength(text, font=font)


def _fit(draw: ImageDraw.ImageDraw, text: str, font: Font, width: float) -> str:
    """Trim *text* with an ellipsis until it fits *width* pixels."""
    if _text_width(draw, text, font) <= width:
        return text
    while text and _text_width(draw, text + "…", font) > width:
        text = text[:-1]
    return text.rstrip() + "…"


def _wrap(
    draw: ImageDraw.ImageDraw, parts: list[str], font: Font, width: float
) -> list[str]:
    """Join *parts* with dots, breaking between parts to fit *width* pixels."""
    lines: list[str] = []
    for part in parts:
        if lines and _text_width(draw, lines[-1] + SEP + part, font) <= width:
            lines[-1] += SEP + part
        else:
            lines.append(_fit(draw, part, font, width))
    return lines


def _background() -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), BG_TOP)
    draw = ImageDraw.Draw(image)
    for y in range(HEIGHT):
        t = y / (HEIGHT - 1)
        r, g, b = (round(a + (z - a) * t) for a, z in zip(BG_TOP, BG_BOTTOM))
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))
    for x in range(0, WIDTH, 80):
        draw.line([(x, 0), (x, HEIGHT)], fill=GRID)
    for y in range(0, HEIGHT, 80):
        draw.line([(0, y), (WIDTH, y)], fill=GRID)
    cx, cy = 1230, 330
    for r in (160, 300, 440, 580):
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=RING, width=2)
    for angle in (35, 125):
        dx = math.cos(math.radians(angle)) * 640
        dy = math.sin(math.radians(angle)) * 640
        draw.line([(cx - dx, cy - dy), (cx + dx, cy + dy)], fill=RING, width=1)
    # Corner brackets, as on the static picture.
    m, arm = 40, 54
    for x, y, sx, sy in (
        (m, m, 1, 1),
        (WIDTH - m, m, -1, 1),
        (m, HEIGHT - m, 1, -1),
        (WIDTH - m, HEIGHT - m, -1, -1),
    ):
        draw.line([(x, y), (x + sx * arm, y)], fill=GOLD, width=3)
        draw.line([(x, y), (x, y + sy * arm)], fill=GOLD, width=3)
    return image


def _paste_jet(image: Image.Image) -> None:
    try:
        source = Image.open(DEFAULT_BRIEFING_IMAGE).convert("RGB")
    except OSError:
        return
    jet = source.crop(JET_BOX)
    # The jet is the only light shape in the box; a soft brightness key lifts
    # it without the chart lines behind it.
    luma = jet.convert("L")
    mask = luma.point(lambda v: max(0, min(255, (v - 90) * 3)))
    # Flood the outside so the dark canopy, a hole in the key, stays solid.
    outside = luma.point(lambda v: 255 if v > 120 else 0)
    ImageDraw.floodfill(outside, (0, 0), 128)
    holes = outside.point(lambda v: 255 if v == 0 else 0)
    mask = ImageChops.lighter(mask, holes)
    scale = 1.25
    size = (round(jet.width * scale), round(jet.height * scale))
    jet = jet.resize(size, Image.Resampling.LANCZOS)
    mask = mask.resize(size, Image.Resampling.LANCZOS)
    image.paste(jet, (1230 - size[0] // 2, 330 - size[1] // 2), mask)


def render_briefing_card(card: BriefingCard, path: Path) -> Path:
    image = _background()
    _paste_jet(image)
    draw = ImageDraw.Draw(image)
    left = 110

    draw.text((left, 100), "R E T L A B", font=_font(30, bold=True), fill=GOLD)
    title = card.title.upper()
    size = 80
    title_font = _font(size, bold=True)
    while size > 48 and _text_width(draw, title, title_font) > 820:
        size -= 4
        title_font = _font(size, bold=True)
    draw.text(
        (left, 230),
        _fit(draw, title, title_font, 820),
        font=title_font,
        fill=TEXT,
        anchor="ls",
    )
    draw.line([(left, 262), (left + 640, 262)], fill=GOLD, width=4)
    draw.text((left, 290), card.subtitle, font=_font(38), fill=TEXT)
    weather_font = _font(30)
    for index, line in enumerate(_wrap(draw, card.weather, weather_font, 800)[:2]):
        draw.text((left, 350 + index * 42), line, font=weather_font, fill=MUTED)

    top = 560
    draw.text((left, top), "YOUR FLIGHTS", font=_font(30, bold=True), fill=GOLD)
    columns = (
        ("CALLSIGN", left),
        ("AIRCRAFT", left + 210),
        ("TASK", left + 590),
        ("TARGET", left + 820),
        ("DEPARTS", left + 1180),
    )
    header_font = _font(22, bold=True)
    if card.flights:
        for label, x in columns:
            draw.text((x, top + 52), label, font=header_font, fill=MUTED)
    row_font = _font(28)
    y = top + 90
    if not card.flights:
        draw.text(
            (left, top + 56),
            "No player flights this turn.",
            font=row_font,
            fill=MUTED,
        )
    shown = card.flights[:MAX_FLIGHT_ROWS]
    for index, flight in enumerate(shown):
        if index % 2 == 0:
            draw.rectangle((left - 14, y - 2, WIDTH - 110, y + 44), fill=ROW_SHADE)
        values = (
            flight.callsign,
            flight.aircraft,
            flight.task,
            flight.target,
            flight.departs,
        )
        for (_, x), value, next_x in zip(
            columns, values, [c[1] for c in columns[1:]] + [WIDTH - 110]
        ):
            draw.text(
                (x, y + 4),
                _fit(draw, value, row_font, next_x - x - 24),
                font=row_font,
                fill=TEXT,
            )
        y += 48
    extra = len(card.flights) - len(shown)
    if extra > 0:
        draw.text(
            (left, y + 8),
            f"+{extra} more player flights",
            font=_font(24),
            fill=MUTED,
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "PNG", optimize=True)
    return path


def _weather_parts(game: "Game") -> list[str]:
    from game.missiongenerator.kneeboard_recon.atis import wind_from_deg

    weather = game.conditions.weather
    wind = weather.wind.at_0m
    parts = [
        f"WIND {wind_from_deg(wind.direction):03d}° "
        f"{round(mps(wind.speed).knots)} KT"
    ]
    clouds = weather.clouds
    if clouds is None:
        parts.append("CAVOK")
    else:
        base = int(round(meters(clouds.base).feet, -2))
        layer = f" {clouds.preset.ui_name[:-2].upper()}" if clouds.preset else ""
        parts.append(f"CLOUDS {base:,} FT{layer}")
    temp_f = round(weather.atmospheric.temperature_celsius * 9 / 5 + 32)
    parts.append(f"{temp_f}°F")
    parts.append(f"QNH {weather.atmospheric.qnh.inches_hg:.2f} IN")
    return parts


def build_briefing_card(game: "Game", flights: list["FlightData"]) -> BriefingCard:
    start = game.conditions.start_time
    title = getattr(game, "campaign_name", None) or game.theater.terrain.name
    subtitle = (
        f"TURN {game.turn}{SEP}{start.strftime('%d %b %Y').upper()}"
        f"{SEP}{start.strftime('%H%M')} LOCAL"
    )
    rows = []
    for flight in sorted(flights, key=lambda f: f.departure_delay):
        minutes = int(flight.departure_delay.total_seconds() // 60)
        hours, mins = divmod(minutes, 60)
        clock = (start + flight.departure_delay).strftime("%H%M")
        rows.append(
            CardFlight(
                callsign=flight.callsign,
                aircraft=flight.aircraft_type.display_name,
                task=str(flight.flight_type),
                target=flight.package.target.name,
                departs=f"{clock} (+{hours}:{mins:02d})",
            )
        )
    return BriefingCard(title, subtitle, _weather_parts(game), rows)
