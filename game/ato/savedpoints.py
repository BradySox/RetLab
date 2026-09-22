"""Points the player puts in his own aircraft.

A spot on the map is worth writing down long before it is worth a flight plan: the
smoke somebody called in, the ship that was not there yesterday, the field the convoy
turns at. The coordinate picker can read any point; this is where one goes once it has
been read, and it goes to one aircraft -- the player's -- rather than into the flight
plan everyone else has to fly.

Two kinds, because the aircraft make the distinction: a **waypoint** is part of the
navigation set and the aircraft flies to it, a **markpoint** is a spot marked for
reference. How many of each an airframe holds is its own business -- a number per
module, read off DCS's own data-cartridge scripts rather than remembered -- and an
airframe nobody has measured claims none.

They belong to the squadron the player flies out of rather than to one flight,
because a flight is a plan and a plan is cancelled and rebuilt several times a turn.

They appear on a kneeboard page of their own, so the route page stays the route, and
in the aircraft itself where the airframe can hold them: the data cartridge on the
Hornet and the Viper, the navigation computer on the A-10. Always outside the route
the mission generated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Iterable, Optional

if TYPE_CHECKING:
    from game.ato.flight import Flight


class PointKind(Enum):
    """The values are the save format: renaming one breaks a campaign in progress."""

    WAYPOINT = "waypoint"
    MARKPOINT = "markpoint"
    IP = "ip"
    TARGET = "target"
    HOLD = "hold"
    ORBIT = "orbit"

    @property
    def label(self) -> str:
        return _LABELS[self]

    @property
    def is_navigation(self) -> bool:
        """A point in the aircraft's navigation set, sharing its waypoint room."""
        return self in NAVIGATION_KINDS


_LABELS = {
    PointKind.WAYPOINT: "Waypoint",
    PointKind.MARKPOINT: "Markpoint",
    PointKind.IP: "IP",
    PointKind.TARGET: "Target",
    PointKind.HOLD: "Hold",
    PointKind.ORBIT: "Orbit",
}

#: Kinds that are points in the navigation set; the kind only picks the symbol or
#: code the airframe shows it with.
NAVIGATION_KINDS = frozenset(
    {PointKind.WAYPOINT, PointKind.IP, PointKind.TARGET, PointKind.HOLD}
)

#: An orbit the player adds without saying how long: a 20 nm racetrack.
DEFAULT_ORBIT_LENGTH_NM = 20.0


@dataclass
class SavedPoint:
    """One point, as the player wrote it down."""

    kind: PointKind
    name: str
    #: DCS world coordinates, the frame everything else in the campaign uses.
    x: float
    y: float
    altitude_ft: int = 0
    #: An orbit's racetrack: from the point, along this heading, this long.
    heading_deg: int = 90
    length_nm: float = DEFAULT_ORBIT_LENGTH_NM

    def __setstate__(self, state: dict[str, Any]) -> None:
        state.setdefault("heading_deg", 90)
        state.setdefault("length_nm", DEFAULT_ORBIT_LENGTH_NM)
        self.__dict__.update(state)

    def orbit_end(self) -> tuple[float, float]:
        """The racetrack's far end, in DCS x (north) / y (east)."""
        import math

        rad = math.radians(self.heading_deg)
        metres = self.length_nm * 1852.0
        return self.x + metres * math.cos(rad), self.y + metres * math.sin(rad)


@dataclass(frozen=True)
class Capacity:
    """How many of each kind an airframe will take.

    Zero is not "unsupported": a point with nowhere to go still goes on the
    kneeboard, which is where the player reads it off and enters it himself. It is
    the number the aircraft can be *given*.
    """

    waypoints: int
    markpoints: int
    orbits: int = 0

    def of(self, kind: PointKind) -> int:
        if kind.is_navigation:
            return self.waypoints
        if kind is PointKind.ORBIT:
            return self.orbits
        return self.markpoints


#: An airframe nobody has measured. It is not refused -- its points ride on the
#: kneeboard like everyone else's -- it simply gets the fallback below rather than a
#: number it cannot keep.
UNMEASURED = Capacity(waypoints=0, markpoints=0)

#: What an unmeasured airframe is allowed. Not a page: the kneeboard paginates, so
#: this is only a guard against a list nobody could use, for an aircraft whose real
#: ceiling nobody has looked up yet.
UNKNOWN_CEILING = 50

#: What each airframe's cockpit is actually handed in this fork, from the module's
#: own DTC scripts (design note §2):
#: - Hornet: WYPT_NAV.lua caps the set at 59 (58/59 HOME and the bullseye); orbits
#:   are CAP_PTS, 9 in all, shared with the flight's own and the support orbits.
#: - Viper: STPT 25 is the bullseye; an orbit is a box on HSD line sets 2-4.
#: - Tomcat: plan 3 holds 50; an orbit is a plot-line box, four lines a plan.
#: - Apache: WPTHZ 1-50; an orbit is a TSD area, 12 in all.
#: - A-10: NavigationComputer_param.lua indexes 0-2050; no orbit element.
#: None of them can be handed a markpoint. Everything else is kneeboard only.
CAPACITY: dict[str, Capacity] = {
    "FA-18C_hornet": Capacity(waypoints=57, markpoints=0, orbits=6),
    "F-16C_50": Capacity(waypoints=24, markpoints=0, orbits=3),
    "F-14BU": Capacity(waypoints=50, markpoints=0, orbits=4),
    "AH-64D_BLK_II": Capacity(waypoints=50, markpoints=0, orbits=12),
    "A-10C": Capacity(waypoints=2050, markpoints=0),
    "A-10C_2": Capacity(waypoints=2050, markpoints=0),
}


def capacity_for(dcs_id: str) -> Capacity:
    return CAPACITY.get(dcs_id, UNMEASURED)


def points_of(flight: Flight) -> list[SavedPoint]:
    """The points saved for this aircraft.

    They belong to the squadron, not to the flight: a flight is cancelled and rebuilt
    with the same aircraft and the same player several times a turn, and points kept
    on the flight went with it.

    A save written while they were on the flight has them moved across here once,
    the first time anything asks.
    """
    squadron = flight.squadron
    points = getattr(squadron, "saved_points", None)
    if points is None:
        points = []
        squadron.saved_points = points

    # Popped from the instance dict rather than read off the flight, because
    # Flight.saved_points is a property and the property is what attribute access
    # finds.
    for point in flight.__dict__.pop("saved_points", None) or []:
        if point not in points:
            points.append(point)
    return points


def kinds_for(dcs_id: str) -> list[PointKind]:
    """The kinds this airframe can be handed, most useful first.

    Only what will actually reach the aircraft. Offering a markpoint to a Hornet and
    then explaining in a dialog that it will only reach the kneeboard is a question
    the player should never have been asked: the answer is in the airframe, and the
    control can just not offer it.

    An airframe nobody has measured is offered nothing, which is the truth about it.
    """
    return [kind for kind in PointKind if reaches_the_aircraft(dcs_id, kind)]


def reaches_the_aircraft(dcs_id: str, kind: PointKind) -> bool:
    """Whether the airframe's own cartridge or database carries this kind.

    False for an airframe nobody has measured as well: a point that cannot be shown
    to go in is one to say so about. Either way the point is still written down --
    the kneeboard takes both kinds -- it just does not reach the cockpit by itself.
    """
    return capacity_for(dcs_id).of(kind) > 0


def room_for(flight: Flight, kind: PointKind) -> int:
    """How many more of this kind the flight will take.

    The aircraft's own number, not the kneeboard's: an A-10 indexes two thousand
    waypoints and the page paginates to suit. Only an airframe nobody has measured
    falls back to a guard figure.
    """
    held = sum(
        1
        for point in points_of(flight)
        if point.kind is kind or (point.kind.is_navigation and kind.is_navigation)
    )
    aircraft = capacity_for(flight.unit_type.dcs_unit_type.id).of(kind)
    return max((aircraft or UNKNOWN_CEILING) - held, 0)


def add_point(flight: Flight, point: SavedPoint) -> bool:
    """Write one down, unless there is no room left for its kind."""
    if room_for(flight, point.kind) <= 0:
        return False
    points_of(flight).append(point)
    return True


def remove_point(flight: Flight, index: int) -> bool:
    points = points_of(flight)
    if not 0 <= index < len(points):
        return False
    del points[index]
    return True


def receivers(coalition: Any) -> Iterable[Flight]:
    """Every flight the player is actually flying, which is the only kind that can
    be handed a point: an AI aircraft has nobody in it to read one."""
    for package in coalition.ato.packages:
        for flight in package.flights:
            if flight.client_count > 0:
                yield flight


# ------------------------------------------------------------------ drawings


@dataclass
class SavedDrawing:
    """A line or an area the player drew for this aircraft (§102)."""

    name: str
    #: DCS world (x, y) vertices, in drawing order.
    points: list[tuple[float, float]] = field(default_factory=list)
    #: An area: the last vertex joins the first.
    closed: bool = False


#: How many drawings an airframe's cartridge has room for after what §74 already
#: draws; the vertex cap is per drawing. Zero means kneeboard and map only.
DRAWING_CAPACITY: dict[str, tuple[int, int]] = {
    # FLOT lines the boundary gives up (it keeps one), 7 points each.
    "FA-18C_hornet": (2, 7),
    # HSD line sets 2-4, 15 of the 25 shared points; the boundary keeps 10.
    "F-16C_50": (3, 15),
    # Plan 3's four plot lines, 9 points (8 closed).
    "F-14BU": (4, 9),
    # TSD lines of 2-4 vertices (longer lines are split) and 4-corner areas.
    "AH-64D_BLK_II": (12, 4),
}

#: Fewer vertices than this is not a line.
MIN_DRAWING_POINTS = 2


def drawing_capacity_for(dcs_id: str) -> tuple[int, int]:
    """(drawings, vertices per drawing) the cockpit takes."""
    return DRAWING_CAPACITY.get(dcs_id, (0, 0))


def drawings_of(flight: Flight) -> list[SavedDrawing]:
    """The drawings saved for this aircraft; kept on the squadron like the points."""
    squadron = flight.squadron
    drawings = getattr(squadron, "saved_drawings", None)
    if drawings is None:
        drawings = []
        squadron.saved_drawings = drawings
    return drawings


def add_drawing(flight: Flight, drawing: SavedDrawing) -> bool:
    if len(drawing.points) < MIN_DRAWING_POINTS:
        return False
    drawings_of(flight).append(drawing)
    return True


def remove_drawing(flight: Flight, index: int) -> bool:
    drawings = drawings_of(flight)
    if not 0 <= index < len(drawings):
        return False
    del drawings[index]
    return True
