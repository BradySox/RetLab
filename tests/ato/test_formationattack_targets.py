"""Tests for FormationAttackBuilder.strike_targets_for.

This helper turns a ground objective's individual units into the per-target
list used both by the kneeboard target page (with coordinates) and by the
per-target TARGET_POINT waypoints, keeping the two in lockstep for Strike,
DEAD and SEAD.
"""

from datetime import timedelta
from types import SimpleNamespace
from typing import Any

from dcs.mapping import Point
from dcs.terrain import Caucasus

from game.ato.flighttype import FlightType
from game.ato.flightplans.formationattack import (
    FormationAttackBuilder,
    FormationAttackFlightPlan,
)
from game.ato.flightwaypointtype import FlightWaypointType
from game.ato.flightplans.strike import Builder as StrikeBuilder
from game.ato.flightplans.waypointbuilder import StrikeTarget, WaypointBuilder
from game.theater.theatergroup import TheaterUnit


class _FakeType:
    def __init__(self, id_: str) -> None:
        self.id = id_


class _FakeUnit:
    """Stands in for a TheaterUnit (not a SceneryUnit, so .type.id is used)."""

    def __init__(self, id_: str) -> None:
        self.type = _FakeType(id_)


class _FakeLocation:
    def __init__(self, units: list[_FakeUnit]) -> None:
        self.strike_targets = units


def _unit(x: float, y: float) -> TheaterUnit:
    unit = TheaterUnit.__new__(TheaterUnit)
    unit.position = Point(x, y, Caucasus())  # type: ignore[assignment]
    return unit


def test_one_target_per_alive_unit_with_indexed_names() -> None:
    location = _FakeLocation(
        [_FakeUnit("SA-10 ln"), _FakeUnit("SA-10 tr"), _FakeUnit("SA-10 cp")]
    )

    targets = FormationAttackBuilder.strike_targets_for(location)  # type: ignore[arg-type]

    assert [t.name for t in targets] == [
        "SA-10 ln #0",
        "SA-10 tr #1",
        "SA-10 cp #2",
    ]
    # Each StrikeTarget references the originating unit, so the waypoint and the
    # kneeboard row describe the same target.
    assert [t.target for t in targets] == location.strike_targets


def test_no_targets_when_objective_has_no_units() -> None:
    assert FormationAttackBuilder.strike_targets_for(_FakeLocation([])) == []  # type: ignore[arg-type]


def test_target_waypoints_fall_back_to_area_when_no_live_targets() -> None:
    """An objective with all units destroyed yields an empty target list.

    The layout must still get one (area) target waypoint, otherwise
    ``tot_waypoint`` -- which indexes ``targets[0]`` -- raises IndexError while
    planning a Strike/DEAD/SEAD against a fully destroyed objective (regression).
    """
    builder = StrikeBuilder.__new__(StrikeBuilder)  # skip IBuilder.__init__
    builder.flight = SimpleNamespace(  # type: ignore[assignment]
        flight_type=FlightType.STRIKE,
        package=SimpleNamespace(target=object()),
    )
    wp_builder = SimpleNamespace(
        strike_point=lambda target: ("point", target),
        strike_area=lambda location: "area",
        target_site=lambda location, targets, task: ("site", len(targets), task),
    )

    # Empty list (all targets dead) and None both fall back to one area waypoint.
    assert builder._target_waypoints(wp_builder, []) == ["area"]  # type: ignore[arg-type]
    assert builder._target_waypoints(wp_builder, None) == ["area"]  # type: ignore[arg-type]

    # With live targets, a Strike gets one site waypoint carrying all of them.
    targets = [StrikeTarget("a #0", object()), StrikeTarget("b #1", object())]  # type: ignore[arg-type]
    result = builder._target_waypoints(wp_builder, targets)  # type: ignore[arg-type]
    assert result == [("site", 2, "STRIKE")]


def test_sead_keeps_a_waypoint_per_emitter() -> None:
    builder = StrikeBuilder.__new__(StrikeBuilder)  # skip IBuilder.__init__
    builder.flight = SimpleNamespace(  # type: ignore[assignment]
        flight_type=FlightType.SEAD,
        package=SimpleNamespace(target=object()),
    )
    wp_builder = SimpleNamespace(sead_point=lambda target: ("point", target))
    targets = [StrikeTarget("a #0", object()), StrikeTarget("b #1", object())]  # type: ignore[arg-type]
    result = builder._target_waypoints(wp_builder, targets)  # type: ignore[arg-type]
    assert result == [("point", targets[0]), ("point", targets[1])]


def test_site_waypoint_sits_on_the_site_and_carries_its_units() -> None:
    wb: Any = WaypointBuilder.__new__(WaypointBuilder)
    units = [_unit(100, 200), _unit(300, 400)]
    location = SimpleNamespace(name="SA-10 site", position=Point(50, 60, Caucasus()))
    targets = [StrikeTarget(f"u #{i}", u) for i, u in enumerate(units)]

    waypoint = wb.target_site(location, targets, "DEAD")

    assert waypoint.waypoint_type is FlightWaypointType.TARGET_POINT
    assert waypoint.position == location.position
    assert waypoint.targets == units
    assert waypoint.display_name == "DEAD SA-10 site"
    assert waypoint.only_for_player


def test_time_over_target_counts_the_units_a_site_waypoint_carries() -> None:
    site = SimpleNamespace(targets=[1, 2, 3])
    legacy = SimpleNamespace(targets=[])
    plan = SimpleNamespace(layout=SimpleNamespace(targets=[site, legacy]))
    dwell = FormationAttackFlightPlan.time_at_target.fget(plan)  # type: ignore[attr-defined]
    assert dwell == timedelta(minutes=0.75 * 4)
