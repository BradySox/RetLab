"""The support page (tankers, AWACS, JTAC, code words, airfield directory) and the friendly packages list."""

import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING, Tuple

from PIL import ImageFont

from game.radio.radios import RadioFrequency
from game.theater.controlpoint import Airfield
from ..aircraft.flightdata import FlightData
from ..briefinggenerator import CommInfo, JtacInfo
from ..kneeboard_page import KneeboardPage
from ..missiondata import AwacsInfo, TankerInfo

if TYPE_CHECKING:
    from game import Game
from .writer import (
    KneeboardPageWriter,
    TableKneeboardPage,
    _labelled_time,
    format_kneeboard_time,
    format_kneeboard_time_inline,
)


class FriendlyPackagesPage(KneeboardPage):
    """Standalone Friendly Packages coordination list (de-duped from Mission Info).

    Every friendly package with its TOT (strike) or patrol window (CAP/tanker/AWACS),
    laid out two-up (the list is narrow) and paginating onto continuation pages. Pulled
    out of the Mission Info page (design §4) so the same list isn't split across the
    bottom of Mission Info and a near-empty spill page.
    """

    HEADING = "Friendly Packages"
    HEADERS = ["Task", "Target", "TOT / Window"]
    FONT_SIZE = 18

    def __init__(
        self, flight: FlightData, rows: List[List[str]], dark_kneeboard: bool
    ) -> None:
        self.flight = flight
        self.rows = rows
        self.dark_kneeboard = dark_kneeboard

    def _title(self) -> str:
        custom = f' ("{self.flight.custom_name}")' if self.flight.custom_name else ""
        return f"{self.flight.callsign} Friendly Packages{custom}"

    def _font(self) -> ImageFont.FreeTypeFont:
        return ImageFont.truetype(
            "courbd.ttf", self.FONT_SIZE, layout_engine=ImageFont.Layout.BASIC
        )

    def _render(self, writer: KneeboardPageWriter) -> List[List[str]]:
        """Draw title + two-column packages table; return rows that overflowed."""
        writer.title(self._title())
        writer.heading(self.HEADING)
        writer.rule()
        font = self._font()
        single_capacity = writer.remaining_table_rows(font, bool(self.HEADERS))
        if len(self.rows) <= single_capacity:
            return writer.table_paginated(self.rows, headers=self.HEADERS, font=font)
        return writer.table_two_column_paginated(
            self.rows, headers=self.HEADERS, font=font
        )

    def write(self, path: Path) -> None:
        writer = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        self._render(writer)
        writer.write(path)

    def paginate(self) -> List[KneeboardPage]:
        probe = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        overflow = self._render(probe)
        pages: List[KneeboardPage] = [self]
        if overflow:
            pages.extend(
                TableKneeboardPage(
                    self._title(),
                    self.HEADING,
                    self.HEADERS,
                    overflow,
                    self.FONT_SIZE,
                    self.dark_kneeboard,
                    continued=True,
                ).paginate()
            )
        return pages


@dataclass(frozen=True)
class CodeWordsBlock:
    """The side's mission code words, rendered on the Support Info page.

    ``pushes`` is one row per task category present in the ATO: (label, word,
    is_own_task). The event words follow; ``stop_jam`` only when an EW package
    exists. Built by the generator so the page stays decoupled from the ATO.
    """

    theme: str
    pushes: List[Tuple[str, str, bool]]
    success: str
    abort: str
    stop_jam: Optional[str]


class SupportPage(KneeboardPage):
    """A kneeboard page containing information about support units."""

    JTAC_REGION_MAX_LEN = 25

    def __init__(
        self,
        flight: FlightData,
        package_flights: List[FlightData],
        comms: List[CommInfo],
        awacs: List[AwacsInfo],
        tankers: List[TankerInfo],
        jtacs: List[JtacInfo],
        dark_kneeboard: bool,
        airfield_rows: Optional[List[List[str]]] = None,
        code_words: Optional[CodeWordsBlock] = None,
        zulu_tz: Optional[datetime.tzinfo] = None,
    ) -> None:
        self.flight = flight
        self.package_flights = package_flights
        self.comms = list(comms)
        self.awacs = awacs
        self.tankers = tankers
        self.jtacs = jtacs
        self.zulu_tz = zulu_tz
        self.dark_kneeboard = dark_kneeboard
        self.airfield_rows = airfield_rows or []
        self.code_words = code_words
        # Every other row in this table is a callsign, so this one is too. It
        # used to fall back to the literal "Flight", which read as a placeholder
        # on the one row the reader is looking for (flown 2026-08-17: the page
        # header said "Colt 9" and the table said "Flight").
        flight_name = str(self.flight.callsign)
        if self.flight.custom_name:
            flight_name = f"{flight_name}\n({self.flight.custom_name})"
        self.comms.append(CommInfo(flight_name, self.flight.intra_flight_channel))

    #: Folded "Airfield Directory" table presentation, shared by the inline
    #: render and any continuation page that catches its overflow.
    AIRFIELD_HEADING = "Airfield Directory"
    AIRFIELD_HEADERS = ["Field", "ATC", "ATIS", "TCN", "I(C)LS", "RWY"]
    AIRFIELD_FONT_SIZE = 20

    def _airfield_title(self) -> str:
        custom = f' ("{self.flight.custom_name}")' if self.flight.custom_name else ""
        return f"{self.flight.callsign} Airfield Directory{custom}"

    def write(self, path: Path) -> None:
        writer = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        self._render(writer)
        writer.write(path)

    def paginate(self) -> List[KneeboardPage]:
        # Carry any airfield-directory rows that spilled past the bottom onto
        # continuation page(s). The probe image is discarded; write() re-renders.
        probe = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        overflow = self._render(probe)
        pages: List[KneeboardPage] = [self]
        if overflow:
            pages.extend(
                TableKneeboardPage(
                    self._airfield_title(),
                    self.AIRFIELD_HEADING,
                    self.AIRFIELD_HEADERS,
                    overflow,
                    self.AIRFIELD_FONT_SIZE,
                    self.dark_kneeboard,
                    continued=True,
                ).paginate()
            )
        return pages

    def _render(self, writer: KneeboardPageWriter) -> List[List[str]]:
        """Draw the Support Info page; return airfield rows that overflowed."""
        if self.flight.custom_name:
            custom_name_title = ' ("{}")'.format(self.flight.custom_name)
        else:
            custom_name_title = ""
        writer.title(f"{self.flight.callsign} Support Info{custom_name_title}")

        # Package FREQ / TOT line, above the boxed section tables. A package on three
        # radio channels makes a long FREQ ladder; when FREQ + TOT would overrun the
        # page width, split TOT onto its own line (and wrap the FREQ) so the TOT is
        # never clipped off the right edge.
        package = self.flight.package
        custom = f' "{package.custom_name}"' if package.custom_name else ""
        freq = self.format_frequency(package.frequency).replace("\n", " - ")
        tot = self._format_time(package.time_over_target)
        one_line = f"  FREQ: {freq}    TOT: {tot}"
        content_px = writer.image_size[0] - 2 * writer.page_margin
        if writer.table_font.getlength(one_line) <= content_px:
            writer.text(one_line, font=writer.table_font)
        else:
            writer.text(f"  FREQ: {freq}", font=writer.table_font, wrap=True)
            writer.text(f"  TOT: {tot}", font=writer.table_font)

        # Build each support section as (title, rows, headers); they render as
        # bordered boxes with header bars (the professional-campaign look) and
        # are spaced to fill the page rather than leaving the bottom half blank.
        comm_ladder = []
        for comm in self.comms:
            comm_ladder.append(
                [
                    comm.name,
                    self.flight.task_display_name,
                    KneeboardPageWriter.wrap_line(str(self.flight.aircraft_type), 23),
                    str(len(self.flight.units)),
                    self.format_frequency(comm.freq),
                ]
            )
        for f in self.package_flights:
            callsign = f.callsign
            if f.custom_name:
                callsign = f"{callsign}\n({f.custom_name})"
            comm_ladder.append(
                [
                    callsign,
                    f.task_display_name,
                    KneeboardPageWriter.wrap_line(str(f.aircraft_type), 23),
                    str(len(f.units)),
                    self.format_frequency(f.intra_flight_channel),
                ]
            )

        aewc_ladder = []
        for single_aewc in self.awacs:
            if single_aewc.depature_location is None:
                tot_a = "-"
                tos_a = "-"
            else:
                tot_a = format_kneeboard_time(single_aewc.start_time, self.zulu_tz)
                tos_a = self._format_duration(
                    single_aewc.end_time - single_aewc.start_time
                )
            aewc_ladder.append(
                [
                    str(single_aewc.callsign),
                    self.format_frequency(single_aewc.freq),
                    str(single_aewc.depature_location),
                    _labelled_time("TOT:", tot_a) + "\n" + "TOS: " + tos_a,
                ]
            )

        tanker_ladder = []
        for tanker in self.tankers:
            tot_t = format_kneeboard_time(tanker.start_time, self.zulu_tz)
            tos_t = self._format_duration(tanker.end_time - tanker.start_time)
            tanker_ladder.append(
                [
                    tanker.callsign,
                    KneeboardPageWriter.wrap_line(tanker.variant, 21),
                    str(tanker.tacan) if tanker.tacan else "N/A",
                    self.format_frequency(tanker.freq),
                    _labelled_time("TOT:", tot_t) + "\n" + "TOS: " + tos_t,
                ]
            )

        jtac_rows = []
        for jtac in self.jtacs:
            jtac_rows.append(
                [
                    jtac.callsign,
                    KneeboardPageWriter.wrap_line(
                        jtac.region, self.JTAC_REGION_MAX_LEN
                    ),
                    jtac.code,
                    self.format_frequency(jtac.freq),
                ]
            )

        # (title, cells, headers) for each non-empty section. Empty sections are
        # skipped so a mission without (e.g.) a tanker shows no empty heading.
        sections: List[Tuple[str, List[List[str]], List[str]]] = [
            (
                f"{package.package_description} Package{custom}",
                comm_ladder,
                ["Callsign", "Task", "Type", "#A/C", "FREQ"],
            )
        ]
        if aewc_ladder:
            sections.append(
                ("AEW&C", aewc_ladder, ["Callsign", "FREQ", "Departure", "TOT / TOS"])
            )
        if tanker_ladder:
            # Drop the "Task" column (always "Tanker") and shorten TACAN to TCN so
            # the wider FREQ column (COMM1 + COMM2) and TOT/TOS fit.
            sections.append(
                (
                    "Tankers",
                    tanker_ladder,
                    ["Callsign", "Type", "TCN", "FREQ", "TOT / TOS"],
                )
            )
        if jtac_rows:
            # "Laser" not "Laser Code": the 4-digit code padded the column and
            # pushed FREQ off the page.
            sections.append(
                ("JTAC", jtac_rows, ["Callsign", "Region", "Laser", "FREQ"])
            )

        def render_sections(w: KneeboardPageWriter, section_gap: int) -> None:
            for idx, (heading, cells, hdr) in enumerate(sections):
                w.text(heading, font=w.heading_font)
                w.rule()
                w.table(cells, headers=hdr)
                w.vspace(section_gap)
                # Code words ride directly under the package comm ladder: the
                # push/event words are package-coordination data, so they live
                # next to the frequencies they are called on.
                if idx == 0 and self.code_words is not None:
                    self._render_code_words(w)
                    w.vspace(section_gap)

        # When there's no airfield directory below, distribute the leftover
        # vertical space as even gaps so the tables breathe down the page
        # (light underline-rule headings, no boxes). With a directory present we
        # use a small fixed gap and let the directory fill the rest (it paginates).
        gap = 12
        if not self.airfield_rows:
            probe = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
            probe.y = writer.y
            render_sections(probe, 0)
            leftover = (writer.image_size[1] - writer.page_margin) - probe.y
            n_blocks = len(sections) + (1 if self.code_words is not None else 0)
            gap = int(max(12, min(90, leftover // max(1, n_blocks))))

        render_sections(writer, gap)

        # Airfield Directory (friendly fields: ATC / ATIS / TACAN / I(C)LS / RWY).
        # Rows that don't fit spill onto a continuation page (see paginate()).
        overflow: List[List[str]] = []
        if self.airfield_rows:
            writer.text(self.AIRFIELD_HEADING, font=writer.heading_font)
            writer.rule()
            overflow = writer.table_paginated(
                self.airfield_rows,
                headers=self.AIRFIELD_HEADERS,
            )
        return overflow

    def _render_code_words(self, w: KneeboardPageWriter) -> None:
        """The side's code words: a push word per task (yours marked) + event words.

        Colour keys the call: push words blue, SUCCESS green, ABORT red, STOP JAM
        amber -- so the word you need is found without reading labels. This is the
        in-cockpit copy of the code words the planners see on the ATO tooltip.
        """
        cw = self.code_words
        assert cw is not None
        w.text(f"Code Words — {cw.theme}", font=w.heading_font)
        w.rule()
        for label, word, own in cw.pushes:
            runs: List[Tuple[str, Optional[Tuple[int, int, int]]]] = [
                (f"{label:<10}", w.col_muted),
                (word, w.col_nav),
            ]
            if own:
                runs.append(("  (you)", w.col_emphasis))
            w.text_runs(runs, font=w.table_font)
        w.text_runs(
            [("SUCCESS   ", w.col_muted), (cw.success, w.col_success)],
            font=w.table_font,
        )
        w.text_runs(
            [("ABORT     ", w.col_muted), (cw.abort, w.col_danger)],
            font=w.table_font,
        )
        if cw.stop_jam:
            w.text_runs(
                [("STOP JAM  ", w.col_muted), (cw.stop_jam, w.col_caution)],
                font=w.table_font,
            )

    def format_frequency(self, frequency: Optional[RadioFrequency]) -> str:
        if frequency is None:
            return ""
        channels = self.flight.channels_for(frequency)
        if not channels:
            return str(frequency)

        names = " / ".join(
            self.flight.aircraft_type.channel_name(c.radio_id, c.channel)
            for c in channels
        )
        return f"{names}\n{frequency}"

    def _format_time(self, time: datetime.datetime | None) -> str:
        return format_kneeboard_time_inline(time, self.zulu_tz)

    @staticmethod
    def _format_duration(time: Optional[datetime.timedelta]) -> str:
        if time is None:
            return ""
        time -= datetime.timedelta(microseconds=time.microseconds)
        return f"{time}"


def build_airfield_directory_rows(
    game: "Game",
    flight: "FlightData",
    atis_by_name: dict[str, RadioFrequency],
) -> List[List[str]]:
    """Build directory rows (Field | ATC | ATIS | TCN | I(C)LS | RWY) for all
    blue airfields, sorted by name."""

    def fmt(freq: Optional[RadioFrequency]) -> str:
        if freq is None:
            return ""
        channel = flight.channel_for(freq)
        if channel is None:
            return str(freq)
        name = flight.aircraft_type.channel_name(channel.radio_id, channel.channel)
        return f"{name}\n{freq}"

    rows: List[List[str]] = []
    airfields = [
        cp
        for cp in game.theater.controlpoints
        if isinstance(cp, Airfield) and cp.is_friendly(flight.friendly)
    ]
    for cp in sorted(airfields, key=lambda c: c.full_name):
        rw = cp.active_runway(game.theater, game.conditions, {})
        if rw.ils is not None:
            ils = str(rw.ils)
        elif rw.icls is not None:
            ils = str(rw.icls)
        else:
            ils = ""
        rows.append(
            [
                cp.full_name,
                fmt(rw.atc),
                fmt(atis_by_name.get(cp.full_name)),
                str(rw.tacan) if rw.tacan is not None else "",
                ils,
                rw.runway_name,
            ]
        )
    return rows
