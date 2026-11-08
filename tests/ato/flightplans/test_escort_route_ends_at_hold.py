"""An escort's route ends at its Escort Hold, not on the defended site.

A player F-15C escort's route ran ESCORT HOLD -> TARGET, with the TARGET point on
the SAM its package's shooters launch at, then out the far side (Afghanistan,
2026-11-07). The TARGET point is kept as the package-TOT reference only.
"""

from __future__ import annotations

from datetime import timedelta

from dcs import Point
from dcs.terrain import Caucasus

from game.ato.flightplans.escort import EscortFlightPlan, EscortLayout
from game.ato.flightplans.formationattack import FormationAttackLayout
from game.ato.flightwaypoint import FlightWaypoint
from game.ato.flightwaypointtype import FlightWaypointType
from game.utils import feet


def _wp(name: str) -> FlightWaypoint:
    return FlightWaypoint(
        name, FlightWaypointType.NAV, Point(0, 0, Caucasus()), feet(20000)
    )


def _layout(cls: type[FormationAttackLayout]) -> FormationAttackLayout:
    names = ["TAKEOFF", "JOIN", "INGRESS", "ESCORT HOLD", "TARGET", "EGRESS"]
    names += ["SPLIT", "LANDING", "BULLSEYE"]
    w = {n: _wp(n) for n in names}
    return cls(
        departure=w["TAKEOFF"],
        hold=None,
        nav_to=[],
        join=w["JOIN"],
        ingress=w["INGRESS"],
        initial=w["ESCORT HOLD"],
        targets=[w["TARGET"]],
        split=w["SPLIT"],
        refuel=None,
        nav_from=[],
        arrival=w["LANDING"],
        divert=None,
        bullseye=w["BULLSEYE"],
        custom_waypoints=[],
        egress_nav=[w["EGRESS"]],
    )


def test_the_escort_turns_for_home_at_the_hold() -> None:
    names = [wp.name for wp in _layout(EscortLayout).iter_waypoints()]
    assert names == [
        "TAKEOFF",
        "JOIN",
        "INGRESS",
        "ESCORT HOLD",
        "EGRESS",
        "SPLIT",
        "LANDING",
        "BULLSEYE",
    ]


def test_other_attack_layouts_still_fly_to_the_target() -> None:
    names = [wp.name for wp in _layout(FormationAttackLayout).iter_waypoints()]
    assert "TARGET" in names


def test_the_unflown_target_still_times_the_escort_through_the_hold() -> None:
    # Takeoff is the package TOT less the time to TARGET, so dropping the point
    # must not shorten that time, or the escort launches late.
    layout = _layout(EscortLayout)
    plan = object.__new__(EscortFlightPlan)
    plan.layout = layout
    plan.total_time_between_waypoints = (  # type: ignore[method-assign]
        lambda a, b: timedelta(minutes=1, seconds=0.5)
    )
    target = layout.targets[0]
    # TAKEOFF -> JOIN -> INGRESS -> ESCORT HOLD, then ESCORT HOLD -> TARGET.
    assert plan._travel_time_to_waypoint(target) == timedelta(seconds=242)
