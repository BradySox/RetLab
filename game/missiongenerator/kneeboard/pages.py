"""Small single-purpose pages: saved points, notes, SITREP and the index."""

from pathlib import Path
from typing import List, Optional, TYPE_CHECKING

from dcs.mapping import Point

from game.ato.savedpoints import PointKind, SavedDrawing, SavedPoint
from game.coordinates import (
    CoordinateFormat,
    format_latlng,
)
from game.dcs.aircrafttype import AircraftType
from game.sitrep import Sitrep
from ..kneeboard_page import KneeboardPage

if TYPE_CHECKING:
    from game.theater.conflicttheater import ConflictTheater
from .writer import KneeboardPageWriter

#: The prefix a saved point's cockpit number carries on the kneeboard.
_SAVED_MARKS = {
    PointKind.MARKPOINT: "MK",
    PointKind.IP: "IP",
    PointKind.TARGET: "TGT",
    PointKind.HOLD: "HLD",
}


class SavedPointsPage(KneeboardPage):
    """The player's saved map points for this aircraft (§102), numbered as the jet
    numbers them. Paginated: an A-10 holds far more than a page does."""

    ROWS_PER_PAGE = 22

    def __init__(
        self,
        callsign: str,
        points: list[SavedPoint],
        theater: "ConflictTheater",
        coordinate_format: CoordinateFormat,
        dark_kneeboard: bool,
        numbers: Optional[list[Optional[int]]] = None,
        page: int = 1,
        total_pages: int = 1,
        drawings: Optional[list[SavedDrawing]] = None,
    ) -> None:
        self.callsign = callsign
        self.points = points
        #: Listed on the first page by their first corner (§102).
        self.drawings = drawings or []
        self.numbers: list[Optional[int]] = (
            numbers if numbers is not None else list(range(1, len(points) + 1))
        )
        self.theater = theater
        self.coordinate_format = coordinate_format
        self.dark_kneeboard = dark_kneeboard
        self.page = page
        self.total_pages = total_pages

    @classmethod
    def split(
        cls,
        callsign: str,
        points: list[SavedPoint],
        theater: "ConflictTheater",
        coordinate_format: CoordinateFormat,
        dark_kneeboard: bool,
        numbers: Optional[list[Optional[int]]] = None,
        drawings: Optional[list[SavedDrawing]] = None,
    ) -> List["SavedPointsPage"]:
        if numbers is None:
            numbers = list(range(1, len(points) + 1))
        starts = list(range(0, max(len(points), 1), cls.ROWS_PER_PAGE))
        return [
            cls(
                callsign,
                points[start : start + cls.ROWS_PER_PAGE],
                theater,
                coordinate_format,
                dark_kneeboard,
                numbers=numbers[start : start + cls.ROWS_PER_PAGE],
                page=index + 1,
                total_pages=len(starts),
                drawings=drawings,
            )
            for index, start in enumerate(starts)
        ]

    def write(self, path: Path) -> None:
        writer = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        counted = f" ({self.page}/{self.total_pages})" if self.total_pages > 1 else ""
        writer.title(f"{self.callsign} saved points{counted}")
        rows = []
        for number, point in zip(self.numbers, self.points):
            at = Point(point.x, point.y, self.theater.terrain)
            # A point with no cockpit number did not fit and must be keyed in.
            mark = _SAVED_MARKS.get(point.kind, "")
            name = point.name
            if point.kind is PointKind.ORBIT:
                name = f"{name} {point.heading_deg:03d}/{point.length_nm:g}nm"
                label = "ORB"
            else:
                label = f"{mark}{number}" if number is not None else "-"
            rows.append(
                [
                    label,
                    name,
                    format_latlng(at.latlng(), self.coordinate_format),
                    f"{point.altitude_ft} ft" if point.altitude_ft else "",
                ]
            )
        for drawing in self.drawings if self.page == 1 else []:
            if not drawing.points:
                continue
            x, y = drawing.points[0]
            at = Point(x, y, self.theater.terrain)
            rows.append(
                [
                    "AREA" if drawing.closed else "LINE",
                    drawing.name,
                    format_latlng(at.latlng(), self.coordinate_format),
                    f"{len(drawing.points)} pts",
                ]
            )
        writer.table(rows, headers=["STPT", "Name", "Position", "Elev"])
        writer.write(path)


class NotesPage(KneeboardPage):
    """A kneeboard page containing the campaign owner's notes."""

    def __init__(
        self,
        notes: str,
        dark_kneeboard: bool,
    ) -> None:
        self.notes = notes
        self.dark_kneeboard = dark_kneeboard

    def write(self, path: Path) -> None:
        writer = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        writer.title("Notes")
        writer.text(self.notes, wrap=True)
        writer.write(path)


class SitrepPage(KneeboardPage):
    """The previous turn's campaign SITREP (§29) on its own page.

    Lived at the bottom of the Mission Info page until a flown 2026-07-19 deck
    clipped the MIA list at the page edge — a busy turn (many losses, POWs and
    evaders) overflows a shared page, so the news gets a page of its own.
    Only generated when there is news (the generator's gates: setting on, not
    turn 1, not a quiet turn), so a quiet deck is unchanged.
    """

    def __init__(self, sitrep: Sitrep, dark_kneeboard: bool) -> None:
        self.sitrep = sitrep
        self.dark_kneeboard = dark_kneeboard

    def write(self, path: Path) -> None:
        writer = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        writer.title(f"SITREP — Turn {self.sitrep.turn}")
        for line in self.sitrep.kneeboard_lines():
            writer.text(line, wrap=True)
        writer.write(path)


class KneeboardIndexPage(KneeboardPage):
    """Flight index fronting a stacked multi-flight airframe deck (§27).

    DCS scopes kneeboards per *airframe*, so every client flight of a type
    shares one stacked deck. This page maps callsign -> start page so a pilot
    can flip straight to their own block. Only generated when 2+ client
    flights share the airframe; a lone flight needs no index.
    """

    HEADERS = ["Flight", "Task", "Page"]

    def __init__(
        self,
        aircraft: AircraftType,
        rows: List[List[str]],
        dark_kneeboard: bool,
    ) -> None:
        self.aircraft = aircraft
        self.rows = rows
        self.dark_kneeboard = dark_kneeboard

    def write(self, path: Path) -> None:
        writer = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        writer.title(f"{self.aircraft.display_name} — Flight Index")
        writer.text(
            "DCS stacks every flight of this airframe into one kneeboard. "
            "Flip to your callsign's start page.",
            wrap=True,
        )
        writer.vspace(6)
        writer.table(self.rows, headers=self.HEADERS)
        writer.write(path)
