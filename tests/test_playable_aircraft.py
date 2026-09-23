"""What the playable-aircraft window reads off the game.

One row per aircraft the player sits in, the points written down for it grouped by
kind, and a clipboard that moves them between aircraft. Everything here is the model
behind the window rather than the window, which is what the numbers on it come from.
"""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from typing import Any, Optional

from game.ato.savedpoints import PointKind, SavedPoint
from qt_ui.windows.playable import model as data


def _flight(
    pilot: str = "Lt. Cdr. R. Halvorsen",
    aircraft: str = "F-16C_50",
    crewed: int = 1,
    custom: Optional[str] = None,
    package: Any = None,
    points: Optional[list[SavedPoint]] = None,
    helicopter: bool = False,
) -> Any:
    member = SimpleNamespace(is_player=True, pilot=SimpleNamespace(name=pilot))
    return SimpleNamespace(
        iter_members=lambda: iter([member]),
        custom_name=custom,
        client_count=crewed,
        unit_type=SimpleNamespace(
            dcs_unit_type=SimpleNamespace(id=aircraft),
            display_name=aircraft,
            helicopter=helicopter,
        ),
        squadron=SimpleNamespace(
            nickname="Viper",
            name="VFA-000",
            saved_points=points if points is not None else [],
        ),
        flight_type=SimpleNamespace(value="SEAD"),
        package=package,
        flight_plan=SimpleNamespace(tot=datetime(2026, 9, 20, 9, 20)),
    )


def _point(kind: PointKind = PointKind.WAYPOINT, name: str = "SMOKE") -> SavedPoint:
    return SavedPoint(kind=kind, name=name, x=1.0, y=2.0)


def _game(*flights: Any) -> Any:
    return SimpleNamespace(
        blue=SimpleNamespace(
            ato=SimpleNamespace(packages=[SimpleNamespace(flights=list(flights))])
        )
    )


# ------------------------------------------------------- what a row is called


def test_the_row_is_the_pilot_until_it_is_renamed() -> None:
    one = data.Aircraft(_flight())

    assert one.title == "Lt. Cdr. R. Halvorsen"
    assert one.subtitle == ""


def test_an_alias_becomes_the_title_and_keeps_the_pilot_under_it() -> None:
    """The real name never leaves the row."""
    one = data.Aircraft(_flight(custom="Viper 1-1"))

    assert one.title == "Viper 1-1"
    assert one.subtitle == "Lt. Cdr. R. Halvorsen"


def test_renaming_to_nothing_gives_the_pilot_his_name_back() -> None:
    one = data.Aircraft(_flight(custom="Viper 1-1"))

    one.rename("   ")

    assert one.flight.custom_name is None
    assert one.title == "Lt. Cdr. R. Halvorsen"


def test_the_alias_is_the_flight_s_own_name() -> None:
    """Rather than a second name only this window knows: renaming here is the name
    the air tasking order and the kneeboard show as well."""
    one = data.Aircraft(_flight())

    one.rename("Viper 1-1")

    assert one.flight.custom_name == "Viper 1-1"


# ------------------------------------------------------------- what it is flying


def test_an_aircraft_between_assignments_says_so() -> None:
    one = data.Aircraft(_flight(package=None))

    assert one.assigned is False
    assert one.target == ""


def test_an_assigned_aircraft_carries_its_target_and_its_time() -> None:
    package = SimpleNamespace(target=SimpleNamespace(name="Rio Grande"))
    one = data.Aircraft(_flight(package=package))

    assert one.assigned is True
    assert one.target == "Rio Grande"
    assert one.tot == "09:20"
    assert one.flight_name == "Viper"


# ---------------------------------------------------------------- its points


def test_the_points_are_grouped_by_kind_keeping_their_place_in_the_list() -> None:
    """The index is what deletes a point, so grouping must not lose it."""
    points = [
        _point(PointKind.WAYPOINT, "W1"),
        _point(PointKind.MARKPOINT, "M1"),
        _point(PointKind.WAYPOINT, "W2"),
    ]
    one = data.Aircraft(_flight(points=points))

    assert [index for index, _ in one.of_kind(PointKind.WAYPOINT)] == [0, 2]
    assert [index for index, _ in one.of_kind(PointKind.MARKPOINT)] == [1]


def test_the_ceiling_is_what_the_aircraft_can_be_given() -> None:
    """Not a guard figure: the Viper takes 24 steerpoints and no markpoint at all."""
    one = data.Aircraft(_flight(aircraft="F-16C_50"))

    # 24 steerpoints and 3 orbit boxes.
    assert one.ceiling == 27
    assert one.maximum(PointKind.MARKPOINT) == 0


def test_an_airframe_nobody_measured_has_no_ceiling_to_count_against() -> None:
    """Its points are still written down; they only go on the kneeboard."""
    one = data.Aircraft(_flight(aircraft="Ka-50_3", points=[_point()]))

    assert one.ceiling == 0
    assert one.total_used == 1
    assert one.total_room == 0


def test_a_kind_with_points_keeps_its_group_even_when_the_aircraft_takes_none() -> None:
    """Two markpoints on a Hornet are two markpoints to show, however they got
    there."""
    one = data.Aircraft(
        _flight(aircraft="FA-18C_hornet", points=[_point(PointKind.MARKPOINT)])
    )

    assert PointKind.MARKPOINT in one.kinds


def test_a_kind_with_neither_room_nor_points_gets_no_group() -> None:
    one = data.Aircraft(_flight(aircraft="FA-18C_hornet"))

    # The shared navigation pool shows as waypoints; orbits have their own group.
    assert one.kinds == [PointKind.WAYPOINT, PointKind.ORBIT]
    assert data.Aircraft(_flight(aircraft="A-10C_2")).kinds == [PointKind.WAYPOINT]


# ------------------------------------------------------------ the headline


def test_the_headline_counts_aircraft_packages_and_points() -> None:
    package = SimpleNamespace(target=SimpleNamespace(name="Rio Grande"))
    aircraft = [
        data.Aircraft(_flight(package=package, points=[_point(), _point()])),
        data.Aircraft(_flight(package=package, points=[_point()])),
        data.Aircraft(_flight(package=None)),
    ]

    assert data.figures(aircraft) == (3, 1, 3)


def test_no_game_means_no_aircraft() -> None:
    assert data.aircraft_of(None) == []


def test_only_an_aircraft_somebody_is_flying_is_listed() -> None:
    flying = _flight()
    ai = _flight(crewed=0)

    listed = data.aircraft_of(_game(flying, ai))

    assert [one.flight for one in listed] == [flying]


# ------------------------------------------------------------- the clipboard


def test_copying_takes_a_copy_rather_than_the_points_themselves() -> None:
    """Pasting the same clipboard into two aircraft must not give them the same
    objects to rename."""
    source = data.Aircraft(_flight(points=[_point(name="SMOKE")]))
    clipboard = data.Clipboard()

    clipboard.take(source)
    clipboard.points[0].name = "CHANGED"

    assert source.points[0].name == "SMOKE"


def test_pasting_writes_what_fits_and_says_how_many() -> None:
    source = data.Aircraft(_flight(points=[_point(name=f"P{n}") for n in range(30)]))
    # The Viper's steerpoints stop at 24, which is the tightest measured ceiling.
    target = data.Aircraft(_flight(aircraft="F-16C_50"))
    clipboard = data.Clipboard()
    clipboard.take(source)

    assert clipboard.fits(target) == 24
    assert clipboard.paste_into(target) == 24
    assert target.total_used == 24


def test_pasting_twice_does_not_give_two_aircraft_the_same_point() -> None:
    source = data.Aircraft(_flight(points=[_point(name="SMOKE")]))
    first = data.Aircraft(_flight())
    second = data.Aircraft(_flight())
    clipboard = data.Clipboard()
    clipboard.take(source)

    clipboard.paste_into(first)
    clipboard.paste_into(second)
    first.points[0].name = "RENAMED"

    assert second.points[0].name == "SMOKE"


def test_an_empty_clipboard_fits_nowhere() -> None:
    clipboard = data.Clipboard()

    assert clipboard.empty is True
    assert clipboard.fits(data.Aircraft(_flight())) == 0


# ------------------------------------------------- what the row links out to


def test_the_package_reads_as_what_it_is_doing_to_what_and_when() -> None:
    package = SimpleNamespace(target=SimpleNamespace(name="ECHIDNA"))
    one = data.Aircraft(_flight(package=package))

    assert one.package_summary == "SEAD ECHIDNA 09:20"


def test_an_aircraft_between_assignments_has_no_package_to_summarise() -> None:
    assert data.Aircraft(_flight(package=None)).package_summary == ""


# ----------------------------------------------- copying one point, not all


def test_copying_one_point_is_a_copy() -> None:
    """Copying a point and finding Paste still greyed out is the control saying it
    did nothing."""
    source = data.Aircraft(_flight(points=[_point(name="A"), _point(name="B")]))
    clipboard = data.Clipboard()

    clipboard.take_one(source.points[1], source.title)

    assert clipboard.empty is False
    assert [point.name for point in clipboard.points] == ["B"]


def test_the_one_copied_point_is_a_copy_too() -> None:
    source = data.Aircraft(_flight(points=[_point(name="SMOKE")]))
    clipboard = data.Clipboard()

    clipboard.take_one(source.points[0], source.title)
    clipboard.points[0].name = "CHANGED"

    assert source.points[0].name == "SMOKE"


# ------------------------------------------- the room the route leaves (§102)


def _routed(aircraft: str, legs: int, **options: Any) -> Any:
    """A flight whose plan is the spawn row and ``legs`` more, one of them a JOIN."""
    from game.ato.dtcoptions import DtcOptions
    from game.ato.flightwaypointtype import FlightWaypointType

    flight = _flight(aircraft=aircraft, points=[_point(name=f"P{n}") for n in range(3)])
    kinds = [FlightWaypointType.TAKEOFF, FlightWaypointType.JOIN]
    kinds += [FlightWaypointType.NAV] * (legs - 1)
    flight.flight_plan = SimpleNamespace(
        tot=None, waypoints=[SimpleNamespace(waypoint_type=k) for k in kinds]
    )
    flight.dtc_options = DtcOptions(**options)
    return flight


def test_the_route_takes_its_numbers_out_of_the_room() -> None:
    """The Viper's points follow a ten-steerpoint route: 14 of its 24 are left."""
    one = data.Aircraft(_routed("F-16C_50", 10))

    assert one.route_slots == 10
    assert one.ceiling == 14 + 3
    assert one.cockpit_room(PointKind.WAYPOINT) == 14 - 3
    assert one.total_room == 11 + 3


def test_points_are_numbered_after_the_route_as_the_kneeboard_numbers_them() -> None:
    one = data.Aircraft(_routed("F-16C_50", 10, skipped_waypoints=["JOIN"]))

    # The JOIN is left out of the cartridge, so the route takes 9.
    assert one.numbers == [10, 11, 12]


def test_the_tomcat_numbers_its_own_plan_from_one() -> None:
    one = data.Aircraft(_routed("F-14BU", 10))

    assert one.route_slots == 0
    assert one.numbers == [1, 2, 3]


def test_with_the_cartridge_off_the_points_reach_no_cockpit() -> None:
    one = data.Aircraft(_routed("F-16C_50", 10, enabled=False))

    assert not one.reaches_the_jet
    assert one.ceiling == 0
    assert one.total_room == 0
    # Numbered after the kneeboard's own route rows, which count from 0.
    assert one.numbers == [11, 12, 13]


def test_a_kneeboard_only_airframe_still_takes_points() -> None:
    one = data.Aircraft(_flight(aircraft="Ka-50_3", points=[_point()]))

    assert one.room(PointKind.WAYPOINT) == 49


def test_counts_read_as_english() -> None:
    assert data.counted(1, "package") == "1 package"
    assert data.counted(2, "package") == "2 packages"
    assert data.counted(0, "corner") == "0 corners"
