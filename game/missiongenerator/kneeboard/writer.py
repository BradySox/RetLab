"""The page writer every kneeboard page draws with, and the time formats they share."""

import datetime
import re
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont
from tabulate import tabulate

from ..kneeboard_page import KneeboardPage, save_kneeboard_image


class KneeboardPageWriter:
    """Creates kneeboard images."""

    def __init__(
        self, page_margin: int = 24, line_spacing: int = 12, dark_theme: bool = False
    ) -> None:
        if dark_theme:
            self.foreground_fill = (215, 200, 200)
            self.background_fill = (10, 5, 5)
            # Semantic accent palette for the Brief Sheet (§ brief sheet). Colour
            # encodes meaning, not decoration: nav/comms, caution, go, emergency.
            # Light, desaturated shades read on the near-black night background.
            self.col_nav = (127, 176, 216)  # blue: route, freqs, bullseye, divert
            self.col_caution = (216, 176, 112)  # amber: threats, bingo/joker
            self.col_success = (132, 192, 138)  # green: SUCCESS / go
            self.col_danger = (224, 138, 138)  # red: ABORT / emergency
            self.col_muted = (150, 134, 134)  # field labels
            self.col_emphasis = (240, 232, 232)  # header lines
        else:
            self.foreground_fill = (15, 15, 15)
            # Light grey rather than near-white: avoids glare under HDR / Auto-HDR
            # while staying perfectly readable in daylight.
            self.background_fill = (210, 210, 210)
            # Darker variants of the same four hues so they stay legible on the
            # daytime light-grey background (the night shades would wash out).
            self.col_nav = (24, 86, 140)
            self.col_caution = (130, 84, 12)
            self.col_success = (28, 104, 40)
            self.col_danger = (158, 36, 36)
            self.col_muted = (96, 88, 88)
            self.col_emphasis = (0, 0, 0)
        self.image_size = (960, 1080)
        self.image = Image.new("RGB", self.image_size, self.background_fill)
        # These font sizes create a relatively full page for current sorties. If
        # we start generating more complicated flight plans, or start including
        # more information in the comm ladder (the latter of which we should
        # probably do), we'll need to split some of this information off into a
        # second page.
        self.title_font = ImageFont.truetype(
            "courbd.ttf", 32, layout_engine=ImageFont.Layout.BASIC
        )
        self.heading_font = ImageFont.truetype(
            "courbd.ttf", 24, layout_engine=ImageFont.Layout.BASIC
        )
        self.content_font = ImageFont.truetype(
            "courbd.ttf", 16, layout_engine=ImageFont.Layout.BASIC
        )
        self.table_font = ImageFont.truetype(
            "courbd.ttf", 20, layout_engine=ImageFont.Layout.BASIC
        )
        self.draw = ImageDraw.Draw(self.image)
        self.page_margin = page_margin
        self.x = page_margin
        self.y = page_margin
        self.line_spacing = line_spacing
        self.text_buffer: List[str] = []

    @property
    def position(self) -> Tuple[int, int]:
        return self.x, self.y

    def text(
        self,
        text: str,
        font: Optional[ImageFont.FreeTypeFont] = None,
        fill: Optional[Tuple[int, int, int]] = None,
        wrap: bool = False,
    ) -> None:
        if font is None:
            font = self.content_font
        if fill is None:
            fill = self.foreground_fill

        if wrap:
            text = "\n".join(
                self.wrap_line_with_font(
                    line, self.image_size[0] - self.page_margin - self.x, font
                )
                for line in text.splitlines()
            )

        self.draw.text(self.position, text, font=font, fill=fill)
        box = self.draw.textbbox(self.position, text, font=font)
        height = abs(box[1] - box[3])  # abs(top - bottom) => offset
        self.y += height + self.line_spacing
        self.text_buffer.append(text)

    def text_runs(
        self,
        runs: List[Tuple[str, Optional[Tuple[int, int, int]]]],
        font: Optional[ImageFont.FreeTypeFont] = None,
    ) -> None:
        """Draw a single line made of coloured segments, left to right.

        Each run is ``(text, fill)``; ``fill`` None falls back to the foreground.
        Runs carry their own spacing (trailing blanks), so the caller controls gaps.
        Advances the cursor one line down. Used by the Brief Sheet to colour
        individual tokens (a freq, the ABORT word) inside an otherwise plain line.
        """
        if font is None:
            font = self.content_font
        x = self.x
        for text, fill in runs:
            self.draw.text(
                (x, self.y), text, font=font, fill=fill or self.foreground_fill
            )
            x += int(round(font.getlength(text)))
            self.text_buffer.append(text)
        box = self.draw.textbbox((self.x, self.y), "Ag", font=font)
        self.y += abs(box[1] - box[3]) + self.line_spacing

    def flush_text_buffer(self) -> None:
        self.text_buffer = []

    def get_text_string(self) -> str:
        return "\n".join(x for x in self.text_buffer)

    def title(self, title: str) -> None:
        self.text(title, font=self.title_font, fill=self.foreground_fill)

    def heading(self, text: str) -> None:
        self.text(text, font=self.heading_font, fill=self.foreground_fill)

    def table(
        self,
        cells: List[List[str]],
        headers: Optional[List[str]] = None,
        font: Optional[ImageFont.FreeTypeFont] = None,
        highlight: Optional["re.Pattern[str]"] = None,
        highlight_fill: Optional[Tuple[int, int, int]] = None,
    ) -> None:
        if headers is None:
            headers = []
        if font is None:
            font = self.table_font
        maxcolwidths = self._fit_col_widths(cells, headers, font)
        table = tabulate(
            cells, headers=headers, numalign="right", maxcolwidths=maxcolwidths
        )
        if highlight is None or highlight_fill is None:
            self.text(table, font, fill=self.foreground_fill)
            return
        self._text_highlighted(table, font, highlight, highlight_fill)

    def _text_highlighted(
        self,
        text: str,
        font: ImageFont.FreeTypeFont,
        pattern: "re.Pattern[str]",
        fill: Tuple[int, int, int],
    ) -> None:
        """Draw a monospace block, recolouring every match of ``pattern``.

        Segments advance by measured width, so a match keeps the column alignment
        the single-call path gives it, and the cursor lands exactly where ``text``
        would have left it -- nothing below the table moves.
        """
        line_height = self._line_advance(font)
        y = self.y
        for line in text.splitlines():
            x = self.x
            cursor = 0
            for match in pattern.finditer(line):
                for chunk, chunk_fill in (
                    (line[cursor : match.start()], self.foreground_fill),
                    (match.group(), fill),
                ):
                    if chunk:
                        self.draw.text((x, y), chunk, font=font, fill=chunk_fill)
                        x += int(round(font.getlength(chunk)))
                cursor = match.end()
            if line[cursor:]:
                self.draw.text(
                    (x, y), line[cursor:], font=font, fill=self.foreground_fill
                )
            y += line_height
        box = self.draw.textbbox(self.position, text, font=font)
        self.y += abs(box[1] - box[3]) + self.line_spacing
        self.text_buffer.append(text)

    def _line_advance(self, font: ImageFont.FreeTypeFont) -> int:
        """Pillow's own line pitch for this font, taken from a two-line sample."""
        two = self.draw.textbbox((0, 0), "Ag" + chr(10) + "Ag", font=font)
        one = self.draw.textbbox((0, 0), "Ag", font=font)
        return abs(two[3] - two[1]) - abs(one[3] - one[1])

    def _fit_col_widths(
        self,
        cells: List[List[str]],
        headers: List[str],
        font: ImageFont.FreeTypeFont,
    ) -> Optional[List[int]]:
        """Per-column character caps that keep a table within the page width.

        Returns ``maxcolwidths`` for ``tabulate`` (which word-wraps any cell past its
        cap) or ``None`` when the table already fits. Shrinks the widest column first,
        down to a floor, so a runaway column (e.g. a 3-radio FREQ ladder) wraps instead
        of running off the right edge and losing data. The fit is measured against
        ``tabulate``'s *actual* rendered output (its padding is hard to predict), so a
        table that already fits returns ``None`` and is byte-identical to before.
        """
        rows = list(cells) + ([headers] if headers else [])
        ncols = max((len(r) for r in rows), default=0)
        if ncols == 0:
            return None

        max_px = self.image_size[0] - self.page_margin - self.x

        def widest_line_px(maxcolwidths: Optional[List[int]]) -> float:
            rendered = tabulate(
                cells, headers=headers, numalign="right", maxcolwidths=maxcolwidths
            )
            return max(
                (font.getlength(line) for line in rendered.splitlines()), default=0.0
            )

        if widest_line_px(None) <= max_px:
            return None

        def natural(col: int) -> int:
            return max(
                (
                    len(line)
                    for r in rows
                    if col < len(r)
                    for line in str(r[col]).splitlines()
                ),
                default=1,
            )

        widths = [natural(col) for col in range(ncols)]
        floor = 8  # never crush a column below a legible minimum
        # Shrink the widest column one char at a time until the rendered table fits (or
        # nothing can shrink further -- then we've done all we can without illegibility).
        while widest_line_px(widths) > max_px:
            widest = max(range(ncols), key=lambda i: widths[i])
            if widths[widest] <= floor:
                break
            widths[widest] -= 1
        return widths

    def rule(self, thickness: int = 2, gap_above: int = 2, gap_below: int = 8) -> None:
        """Draw a thin horizontal separator across the content width.

        A light alternative to a boxed panel: it underlines a heading (or
        divides sections) without the heavy filled-bar / full-border look.
        """
        self.y += gap_above
        self.draw.line(
            (self.x, self.y, self.image_size[0] - self.page_margin, self.y),
            fill=self.foreground_fill,
            width=thickness,
        )
        self.y += thickness + gap_below

    def vspace(self, pixels: int) -> None:
        """Advance the cursor by ``pixels`` to add vertical breathing room."""
        self.y += max(0, pixels)

    def _line_height(self, font: ImageFont.FreeTypeFont) -> int:
        """Vertical advance of one rendered text line for the given font.

        Measured from the delta between a one-line and two-line bbox so it
        matches PIL's actual multiline layout (including its inter-line
        padding) rather than relying on font metrics.
        """
        one = self.draw.textbbox((0, 0), "Ag", font=font)
        two = self.draw.textbbox((0, 0), "Ag\nAg", font=font)
        return (two[3] - two[1]) - (one[3] - one[1])

    def remaining_table_rows(
        self, font: ImageFont.FreeTypeFont, has_headers: bool
    ) -> int:
        """Number of data rows that still fit below the cursor for a table.

        Accounts for tabulate's two lines of header chrome (header + separator)
        and leaves one row of slack so a table never kisses the bottom edge.
        """
        line_height = self._line_height(font)
        if line_height <= 0:
            return 0
        available = (self.image_size[1] - self.page_margin) - self.y
        capacity = available // line_height
        if has_headers:
            capacity -= 2
        return max(0, capacity - 1)

    def table_paginated(
        self,
        cells: List[List[str]],
        headers: Optional[List[str]] = None,
        font: Optional[ImageFont.FreeTypeFont] = None,
    ) -> List[List[str]]:
        """Render as many rows as fit below the cursor; return the overflow.

        The returned rows did not fit on this page and should be carried onto a
        continuation page (see ``TableKneeboardPage``). Deterministic for a
        given starting cursor, so callers can replay it to discover the split
        without saving an image.
        """
        if font is None:
            font = self.table_font
        max_rows = self.remaining_table_rows(font, bool(headers))
        if max_rows <= 0:
            return list(cells)
        shown, overflow = cells[:max_rows], cells[max_rows:]
        self.table(shown, headers=headers, font=font)
        return overflow

    def table_two_column_paginated(
        self,
        cells: List[List[str]],
        headers: Optional[List[str]] = None,
        font: Optional[ImageFont.FreeTypeFont] = None,
        col_gap: int = 48,
    ) -> List[List[str]]:
        """Render a narrow table in two side-by-side columns; return overflow.

        Used for the Friendly Packages list, which is narrow enough that a
        single column wastes the right half of the page (and spills a handful
        of rows onto a near-empty continuation page). Filling the left column
        first, then the right, roughly doubles the rows per page. Rows beyond
        both columns are returned to paginate onto a continuation page.
        """
        if font is None:
            font = self.table_font
        capacity = self.remaining_table_rows(font, bool(headers))
        if capacity <= 0:
            return list(cells)
        left_rows = cells[:capacity]
        right_rows = cells[capacity : 2 * capacity]
        overflow = cells[2 * capacity :]

        start_x, start_y = self.x, self.y
        self.table(left_rows, headers=headers, font=font)
        left_bottom = self.y
        if right_rows:
            half = (self.image_size[0] - 2 * self.page_margin - col_gap) // 2
            self.x = start_x + half + col_gap
            self.y = start_y
            self.table(right_rows, headers=headers, font=font)
            self.x = start_x
            self.y = max(left_bottom, self.y)
        return overflow

    def write(self, path: Path) -> None:
        save_kneeboard_image(self.image, path)
        path.with_suffix(".txt").write_text(self.get_text_string(), "utf8")

    @staticmethod
    def wrap_line(inputstr: str, max_length: int) -> str:
        if len(inputstr) <= max_length:
            return inputstr
        tokens = inputstr.split(" ")
        output = ""
        segments = []
        for token in tokens:
            combo = output + " " + token
            if len(combo) > max_length:
                combo = output + "\n" + token
                segments.append(combo)
                output = ""
            else:
                output = combo
        return "".join(segments + [output]).strip()

    @staticmethod
    def wrap_line_with_font(
        inputstr: str, max_width: int, font: ImageFont.FreeTypeFont
    ) -> str:
        if font.getlength(inputstr) <= max_width:
            return inputstr
        tokens = inputstr.split(" ")
        output = ""
        segments = []
        for token in tokens:
            combo = output + " " + token
            if font.getlength(combo) > max_width:
                segments.append(output + "\n")
                output = token
            else:
                output = combo
        return "".join(segments + [output]).strip()


#: The local half of a flight-plan Time cell ("17:28L"), for recolouring it apart
#: from the Zulu half that leads it. Zulu keeps the page foreground because it is
#: the figure that matches the DED. Deliberately does not match a prose form,
#: which is parenthesised and needs no colour to read apart.
LOCAL_CELL_TOKEN = re.compile(r"(?<!\d:)\d{2}:\d{2}L")


def _format_clock(time: Optional[datetime.datetime]) -> str:
    """Render a clock cell, marking Zulu when the value carries a zone."""
    if time is None:
        return ""
    return f"{time.strftime('%H:%M:%S')}{'Z' if time.tzinfo is not None else ''}"


def _zulu_text(
    time: Optional[datetime.datetime], zulu_tz: Optional[datetime.tzinfo]
) -> Optional[str]:
    """The Zulu rendering of a naive theater-local time, or None if not wanted.

    ``zulu_tz`` is the theater timezone for an airframe whose avionics run UTC
    (``utc_kneeboard``) and None for every other.
    """
    if time is None or zulu_tz is None or time.tzinfo is not None:
        return None
    return _format_clock(time.replace(tzinfo=zulu_tz).astimezone(datetime.timezone.utc))


def format_kneeboard_time(
    time: Optional[datetime.datetime], zulu_tz: Optional[datetime.tzinfo] = None
) -> str:
    """A table cell's time, Zulu leading and local under it when the airframe asks.

    Both, never one: Zulu is what the DED reads, and a squadron flying mixed types
    coordinates off local. Zulu leads because it is the figure the cockpit shows.
    Stacked rather than side by side, so the column width is unchanged (see
    docs/dev/design/retlab-dtc-cartridge-notes.md).
    """
    local = _format_clock(time)
    zulu = _zulu_text(time, zulu_tz)
    return local if zulu is None else f"{zulu}\n{local}L"


def format_kneeboard_time_inline(
    time: Optional[datetime.datetime], zulu_tz: Optional[datetime.tzinfo] = None
) -> str:
    """The same pair for a time embedded in a line of prose: ``14:53:16Z (17:53:16L)``."""
    local = _format_clock(time)
    zulu = _zulu_text(time, zulu_tz)
    return local if zulu is None else f"{zulu} ({local}L)"


def format_kneeboard_time_compact(
    time: Optional[datetime.datetime], zulu_tz: Optional[datetime.tzinfo] = None
) -> str:
    """The pair for a table cell: ``14:28Z 17:28L``, Zulu leading and both labelled.

    Thirteen characters against the flight-plan Time column's budget of thirteen,
    measured with ``_fit_col_widths``. Three constraints shaped it:

    * Stacking cost a second line on every waypoint row and pushed the Laser Code
      table off the bottom of the page (flown 2026-08-21).
    * Seconds do not fit -- a 15-character cell wraps the column, which brings the
      second line straight back. They stay on the BLUF's TOT, which is prose.
    * **Zulu leads** because it is the figure the DED shows, so it is the one being
      cross-checked in the cockpit. Local follows for the wingman who is not.

    An airframe that does not ask for Zulu is untouched, seconds and all.
    """
    text = _format_clock(time)
    if time is None or zulu_tz is None or time.tzinfo is not None:
        return text
    zulu = time.replace(tzinfo=zulu_tz).astimezone(datetime.timezone.utc)
    return f"{zulu.strftime('%H:%M')}Z {time.strftime('%H:%M')}L"


def _labelled_time(label: str, value: str) -> str:
    """A ``TOT: hh:mm:ss`` cell, with a Zulu second line indented under the time.

    The TOT/TOS column is the narrowest place a time appears, so the pair stacks
    rather than parenthesising; the indent is what keeps the Zulu figure reading
    as the TOT and not as the TOS below it.
    """
    first, *rest = value.splitlines() or [""]
    pad = " " * (len(label) + 1)
    return "\n".join([f"{label} {first}"] + [pad + line for line in rest])


class TableKneeboardPage(KneeboardPage):
    """A standalone title + table page that auto-paginates across images.

    Used to hold the overflow of a folded list (friendly packages, airfield
    directory) that did not fit on its host page. ``paginate`` pre-splits the
    rows into per-page slices that fit, so each rendered image stays within the
    bottom margin.
    """

    def __init__(
        self,
        title: str,
        heading: str,
        headers: List[str],
        rows: List[List[str]],
        font_size: int,
        dark_kneeboard: bool,
        continued: bool = False,
    ) -> None:
        self.title = title
        self.heading = heading
        self.headers = headers
        self.rows = rows
        self.font_size = font_size
        self.dark_kneeboard = dark_kneeboard
        self.continued = continued

    def _font(self) -> ImageFont.FreeTypeFont:
        return ImageFont.truetype(
            "courbd.ttf", self.font_size, layout_engine=ImageFont.Layout.BASIC
        )

    def _draw_header(self, writer: "KneeboardPageWriter", continued: bool) -> None:
        writer.title(self.title)
        writer.heading(f"{self.heading} (cont.)" if continued else self.heading)
        writer.rule()

    def paginate(self) -> List[KneeboardPage]:
        """Split the rows into the smallest set of pages that all fit."""
        pages: List[KneeboardPage] = []
        remaining = self.rows
        continued = self.continued
        while remaining:
            probe = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
            self._draw_header(probe, continued)
            # Always place at least one row so a pathological case can't loop.
            capacity = max(
                1, probe.remaining_table_rows(self._font(), bool(self.headers))
            )
            slice_rows, remaining = remaining[:capacity], remaining[capacity:]
            pages.append(
                TableKneeboardPage(
                    self.title,
                    self.heading,
                    self.headers,
                    slice_rows,
                    self.font_size,
                    self.dark_kneeboard,
                    continued=continued,
                )
            )
            continued = True
        return pages

    def write(self, path: Path) -> None:
        writer = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        self._draw_header(writer, self.continued)
        writer.table(self.rows, headers=self.headers, font=self._font())
        writer.write(path)
