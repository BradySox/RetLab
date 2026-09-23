"""What the playable-aircraft window is made of.

One row per aircraft the player sits in, and under each one the points written down
for it. Nothing here touches Qt: the window draws what this returns, and the tests
read it directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterator, Optional, Sequence

from game.ato.savedpoints import (
    PointKind,
    SavedPoint,
    capacity_for,
    points_of,
    receivers,
    room_for,
)


@dataclass(frozen=True)
class Aircraft:
    """One aircraft with somebody in it, as the list shows it."""

    flight: Any
    #: The campaign's Pre-load DTC data cartridges setting, which the flight's own
    #: DTC choice can override.
    dtc_setting: bool = True

    @property
    def pilot_name(self) -> str:
        """The player's own name, which is the row's identity until it is renamed."""
        for member in self.flight.iter_members():
            if member.is_player and member.pilot is not None:
                return str(member.pilot.name)
        return "Player"

    @property
    def alias(self) -> Optional[str]:
        """The name the player gave this aircraft, if any.

        It is the flight's own ``custom_name``, so renaming here renames it in the
        air tasking order and on the kneeboard as well rather than adding a second
        name that only this window knows about.
        """
        name = getattr(self.flight, "custom_name", None)
        return str(name) if name else None

    @property
    def title(self) -> str:
        return self.alias or self.pilot_name

    @property
    def subtitle(self) -> str:
        """The real name, shown under the alias so renaming never loses it."""
        return self.pilot_name if self.alias else ""

    def rename(self, name: str) -> None:
        """An empty name restores the pilot's."""
        self.flight.custom_name = name.strip() or None

    @property
    def dcs_id(self) -> str:
        return str(self.flight.unit_type.dcs_unit_type.id)

    @property
    def aircraft_name(self) -> str:
        return str(self.flight.unit_type.display_name)

    @property
    def is_helicopter(self) -> bool:
        return bool(getattr(self.flight.unit_type, "helicopter", False))

    @property
    def assigned(self) -> bool:
        return getattr(self.flight, "package", None) is not None

    @property
    def flight_name(self) -> str:
        """What the flight is called on the map: its squadron's nickname, or its
        squadron."""
        squadron = getattr(self.flight, "squadron", None)
        nickname = getattr(squadron, "nickname", None)
        if nickname:
            return str(nickname)
        return str(getattr(squadron, "name", "") or "Flight")

    @property
    def task(self) -> str:
        return str(self.flight.flight_type.value)

    @property
    def target(self) -> str:
        package = getattr(self.flight, "package", None)
        target = getattr(package, "target", None)
        return str(getattr(target, "name", "") or "")

    @property
    def package_summary(self) -> str:
        """The package in a few words: what it is doing, to what, and when.

        "Strike ECHIDNA 12:33". It is what the row shows and what opens the package
        dialog, so it carries only what tells one package from another.
        """
        if not self.assigned:
            return ""
        parts = [self.task]
        if self.target:
            parts.append(self.target)
        if self.tot:
            parts.append(self.tot)
        return " ".join(parts)

    @property
    def tot(self) -> str:
        """The time over target, or empty when the flight plan has none yet."""
        plan = getattr(self.flight, "flight_plan", None)
        when = getattr(plan, "tot", None)
        if not isinstance(when, datetime):
            return ""
        return when.strftime("%H:%M")

    # ------------------------------------------------------------- its points

    @property
    def points(self) -> list[SavedPoint]:
        return points_of(self.flight)

    def of_kind(self, kind: PointKind) -> list[tuple[int, SavedPoint]]:
        """This kind's points, with the index each one has in the whole list.

        The index is what removes one, so it has to survive being grouped.
        """
        return [
            (index, point)
            for index, point in enumerate(self.points)
            if point.kind is kind
        ]

    def used(self, kind: PointKind) -> int:
        return len(self.of_kind(kind))

    def maximum(self, kind: PointKind) -> int:
        return capacity_for(self.dcs_id).of(kind)

    def room(self, kind: PointKind) -> int:
        """How many more of this kind Add takes, kneeboard-only ones included."""
        return room_for(self.flight, kind)

    @property
    def total_used(self) -> int:
        return len(self.points)

    @property
    def _dtc_options(self) -> Any:
        from game.ato.dtcoptions import DtcOptions

        return getattr(self.flight, "dtc_options", None) or DtcOptions()

    @property
    def _waypoints(self) -> list[Any]:
        plan = getattr(self.flight, "flight_plan", None)
        return list(getattr(plan, "waypoints", None) or [])

    @property
    def in_cartridge(self) -> bool:
        """Whether the data cartridge carries this aircraft's points."""
        from game.missiongenerator.dtc.savedpoints import cartridge_takes_points

        return cartridge_takes_points(self.dcs_id, self._dtc_options, self.dtc_setting)

    @property
    def in_cdu(self) -> bool:
        from game.missiongenerator.a10cdu import AIRCRAFT as A10

        return self.dcs_id in A10

    @property
    def reaches_the_jet(self) -> bool:
        return self.in_cartridge or self.in_cdu

    @property
    def route_slots(self) -> int:
        """The cockpit numbers the planned route takes ahead of the points.

        From the plan, not the generated mission: generation only ever drops rows,
        so this never overstates the room."""
        from game.missiongenerator.dtc.savedpoints import route_slots

        waypoints = self._waypoints
        if self.in_cdu:
            return len(waypoints)
        options = self._dtc_options
        skipped = options.skipped_waypoints
        flown = [w for w in waypoints[1:] if w.waypoint_type.name not in skipped]
        return route_slots(self.dcs_id, len(flown), options.route)

    @property
    def numbers(self) -> list[Optional[int]]:
        """The number the jet and the kneeboard give each point; None for an orbit,
        a markpoint, or a point past the last cockpit number."""
        from game.missiongenerator.dtc.savedpoints import point_numbers

        return point_numbers(
            self.dcs_id,
            self._waypoints,
            self._dtc_options,
            self.points,
            self.in_cartridge,
            self.in_cdu,
        )

    def cockpit_room(self, kind: PointKind) -> int:
        """How many more of this kind reach the jet itself."""
        if not self.reaches_the_jet:
            return 0
        top = self.maximum(kind)
        if kind.is_navigation:
            top = max(top - self.route_slots, 0)
            held = sum(1 for point in self.points if point.kind.is_navigation)
        else:
            held = self.used(kind)
        return max(top - held, 0)

    @property
    def ceiling(self) -> int:
        """How many points reach the jet: the navigation numbers the route leaves,
        plus the orbit slots. Zero where they only go on the kneeboard."""
        if not self.reaches_the_jet:
            return 0
        capacity = capacity_for(self.dcs_id)
        navigation = max(capacity.waypoints - self.route_slots, 0)
        return navigation + capacity.markpoints + capacity.orbits

    @property
    def total_room(self) -> int:
        """How many more reach the jet, across the pools."""
        return sum(
            self.cockpit_room(kind)
            for kind in (PointKind.WAYPOINT, PointKind.MARKPOINT, PointKind.ORBIT)
        )

    @property
    def kinds(self) -> list[PointKind]:
        """The groups the points pane shows: waypoints whenever the airframe takes
        any, any other kind once it has points, and orbits when it takes them."""
        shown = []
        for kind in PointKind:
            if self.used(kind):
                shown.append(kind)
            elif kind is PointKind.WAYPOINT and self.maximum(kind) > 0:
                shown.append(kind)
            elif kind is PointKind.ORBIT and self.maximum(kind) > 0:
                shown.append(kind)
        return shown

    def rename_point(self, index: int, name: str) -> None:
        points = self.points
        if 0 <= index < len(points):
            points[index].name = name.strip()[: self.name_length] or points[index].name

    @property
    def name_length(self) -> int:
        """How long a point's name may be before the cockpit truncates it.

        The Hornet's cartridge and the A-10's database both cut a note at 24; nothing
        measured is longer, so this is one number rather than a table of one value.
        """
        return NAME_LENGTH


#: What every module that carries a note for a point allows.
NAME_LENGTH = 24


def counted(number: int, one: str, many: Optional[str] = None) -> str:
    """ "1 package", "2 packages"."""
    return f"{number} {one if number == 1 else (many or one + 's')}"


def aircraft_of(game: Any) -> list[Aircraft]:
    """Every aircraft the player is flying this turn.

    In flight-plan order, which is the order the air tasking order shows, so the
    window and the ATO read the same way down the page.
    """
    if game is None:
        return []
    settings = getattr(game, "settings", None)
    setting = bool(getattr(settings, "dtc_data_cartridges", True))
    return [Aircraft(flight, setting) for flight in receivers(game.blue)]


def figures(aircraft: Sequence[Aircraft]) -> tuple[int, int, int]:
    """The three headline numbers: aircraft, packages, points."""
    packages = {
        id(one.flight.package) for one in aircraft if one.assigned
    }  # by identity: a package has no id of its own
    points = sum(one.total_used for one in aircraft)
    return len(aircraft), len(packages), points


@dataclass
class Clipboard:
    """What Copy all put aside, and where it came from.

    Points are copied rather than moved, and the copy is deep: pasting the same
    clipboard into two aircraft must not give them the same objects to rename.
    """

    points: list[SavedPoint] = field(default_factory=list)
    source: str = ""

    @property
    def empty(self) -> bool:
        return not self.points

    def take(self, aircraft: Aircraft) -> None:
        self.points = [
            SavedPoint(
                kind=point.kind,
                name=point.name,
                x=point.x,
                y=point.y,
                altitude_ft=point.altitude_ft,
            )
            for point in aircraft.points
        ]
        self.source = aircraft.title

    def take_one(self, point: SavedPoint, source: str) -> None:
        """Copying one point is a copy too: the Paste beside it has to light up."""
        self.points = [
            SavedPoint(
                kind=point.kind,
                name=point.name,
                x=point.x,
                y=point.y,
                altitude_ft=point.altitude_ft,
            )
        ]
        self.source = source

    def fits(self, aircraft: Aircraft) -> int:
        """How many of the copied points the target will actually take."""
        room = {kind: aircraft.room(kind) for kind in PointKind}
        taken = 0
        for point in self.points:
            if room[point.kind] > 0:
                room[point.kind] -= 1
                taken += 1
        return taken

    def paste_into(self, aircraft: Aircraft) -> int:
        """Write what fits, in order, and say how many went in."""
        from game.ato.savedpoints import add_point

        written = 0
        for point in self.points:
            copy = SavedPoint(
                kind=point.kind,
                name=point.name,
                x=point.x,
                y=point.y,
                altitude_ft=point.altitude_ft,
            )
            if add_point(aircraft.flight, copy):
                written += 1
        return written


def kind_rows(aircraft: Aircraft) -> Iterator[tuple[PointKind, list[tuple[int, Any]]]]:
    """The groups the points pane draws, in the airframe's own order."""
    for kind in aircraft.kinds:
        yield kind, aircraft.of_kind(kind)
