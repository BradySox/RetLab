"""Insert NAV point finds a leg beside the selected waypoint, in every layout.

It used to know only the transit legs, so every point between a strike's join and
its split said "select a different waypoint" (2026-09-27, a Strike's line-up NAV).
"""

from __future__ import annotations

from dcs import Point
from dcs.terrain import Caucasus

from game.ato.flightplans.custom import CustomLayout
from game.ato.flightplans.formationattack import FormationAttackLayout
from game.ato.flightplans.navinsert import nav_insert_next_to
from game.ato.flightwaypoint import FlightWaypoint
from game.ato.flightwaypointtype import FlightWaypointType as T
from game.utils import feet

TERRAIN = Caucasus()


def _wp(name: str, kind: T, north_nm: float, alt_ft: int = 20000) -> FlightWaypoint:
    return FlightWaypoint(name, kind, Point(0, north_nm * 1852, TERRAIN), feet(alt_ft))


def _strike(
    *,
    hold: bool = True,
    lineup: bool = True,
    refuel: bool = False,
    targets: int = 1,
    ingress_nav: int = 0,
    egress_nav: int = 0,
) -> FormationAttackLayout:
    """A strike laid out northwards, 10 NM a waypoint, so every midpoint is distinct."""
    return FormationAttackLayout(
        departure=_wp("TAKEOFF", T.TAKEOFF, 0, 0),
        hold=_wp("HOLD", T.LOITER, 5) if hold else None,
        nav_to=[_wp("NAV", T.NAV, 10)],
        join=_wp("JOIN", T.JOIN, 20),
        ingress_nav=[_wp("NAV", T.NAV, 30 + i) for i in range(ingress_nav)],
        lineup=_wp("NAV", T.NAV, 40) if lineup else None,
        ingress=_wp("INGRESS", T.INGRESS_STRIKE, 50),
        targets=[_wp(f"STRIKE {i}", T.TARGET_POINT, 60 + i, 0) for i in range(targets)],
        egress_nav=[_wp("NAV", T.NAV, 70 + i) for i in range(egress_nav)],
        split=_wp("SPLIT", T.SPLIT, 80),
        refuel=_wp("REFUEL", T.REFUEL, 90) if refuel else None,
        nav_from=[_wp("NAV", T.NAV, 100)],
        arrival=_wp("LANDING", T.LANDING_POINT, 0, 0),
        divert=None,
        bullseye=_wp("BULLSEYE", T.BULLSEYE, 200, 0),
        custom_waypoints=[],
    )


def _insert_beside(
    layout: FormationAttackLayout | CustomLayout, anchor: FlightWaypoint
) -> FlightWaypoint:
    slot = nav_insert_next_to(layout, anchor)
    assert slot is not None
    slot.apply()
    return slot.waypoint


def _neighbours(
    layout: FormationAttackLayout, waypoint: FlightWaypoint
) -> tuple[FlightWaypoint, FlightWaypoint]:
    route = layout.waypoints
    at = next(i for i, w in enumerate(route) if w is waypoint)
    return route[at - 1], route[at + 1]


def test_a_point_after_the_join_goes_on_the_way_in() -> None:
    layout = _strike()
    new = _insert_beside(layout, layout.join)
    assert layout.ingress_nav == [new]
    assert _neighbours(layout, new) == (layout.join, layout.lineup)
    assert new.position.y == 30 * 1852


def test_a_point_after_a_way_in_nav_follows_it() -> None:
    layout = _strike(ingress_nav=2)
    first = layout.ingress_nav[0]
    new = _insert_beside(layout, first)
    assert layout.ingress_nav[1] is new
    assert _neighbours(layout, new)[0] is first


def test_the_line_up_takes_a_point_on_the_leg_before_it() -> None:
    """The reported case: nothing fits between a strike's line-up and its IP."""
    layout = _strike()
    assert layout.lineup is not None
    new = _insert_beside(layout, layout.lineup)
    assert layout.ingress_nav == [new]
    assert _neighbours(layout, new) == (layout.join, layout.lineup)


def test_a_point_after_the_last_target_goes_on_the_way_out() -> None:
    layout = _strike(targets=2)
    new = _insert_beside(layout, layout.targets[-1])
    assert layout.egress_nav == [new]
    assert _neighbours(layout, new) == (layout.targets[-1], layout.split)
    assert new.alt == layout.split.alt


def test_the_split_before_a_tanker_takes_a_point_before_it() -> None:
    """The old rule put it after the tanker, halfway back: a Z through the refuel."""
    layout = _strike(refuel=True)
    new = _insert_beside(layout, layout.split)
    assert layout.egress_nav == [new]
    assert _neighbours(layout, new) == (layout.targets[-1], layout.split)


def test_takeoff_before_a_hold_has_no_room() -> None:
    """The old rule put it after the hold, halfway back to the field."""
    layout = _strike()
    assert nav_insert_next_to(layout, layout.departure) is None


def test_the_hold_opens_the_transit_leg() -> None:
    layout = _strike()
    new = _insert_beside(layout, layout.hold)  # type: ignore[arg-type]
    assert layout.nav_to[0] is new


def test_takeoff_with_no_hold_opens_the_transit_leg() -> None:
    layout = _strike(hold=False)
    new = _insert_beside(layout, layout.departure)
    assert layout.nav_to[0] is new


def test_the_attack_run_has_no_room() -> None:
    layout = _strike(targets=3)
    for anchor in (layout.ingress, layout.targets[0], layout.targets[1]):
        assert nav_insert_next_to(layout, anchor) is None


def test_a_point_is_never_put_after_the_bullseye() -> None:
    layout = _strike()
    assert nav_insert_next_to(layout, layout.bullseye) is None


def test_landing_takes_a_point_on_the_way_home() -> None:
    layout = _strike()
    new = _insert_beside(layout, layout.arrival)
    assert layout.nav_from[-1] is new


def test_a_point_equal_to_another_is_still_found_by_itself() -> None:
    """Waypoints compare by value; the anchor on the way out is not the one in."""
    layout = _strike(ingress_nav=1, egress_nav=1)
    twin = layout.egress_nav[0]
    twin.position = layout.ingress_nav[0].position
    assert twin == layout.ingress_nav[0]
    new = _insert_beside(layout, twin)
    assert layout.egress_nav == [twin, new]
    assert len(layout.ingress_nav) == 1


def test_nothing_changes_until_the_slot_is_applied() -> None:
    layout = _strike()
    before = layout.waypoints
    assert nav_insert_next_to(layout, layout.join) is not None
    assert layout.waypoints == before
    assert layout.ingress_nav == []


def test_the_way_in_reorders_within_itself() -> None:
    layout = _strike(ingress_nav=2)
    first, second = layout.ingress_nav
    assert layout.move_waypoint(first, 1) is True
    assert layout.ingress_nav == [second, first]
    assert layout.move_waypoint(first, 1) is False


def _custom() -> tuple[CustomLayout, FlightWaypoint, FlightWaypoint]:
    a, b = _wp("a", T.NAV, 10), _wp("b", T.NAV, 20)
    return CustomLayout(_wp("dep", T.TAKEOFF, 0, 0), [a, b]), a, b


def test_a_custom_plan_takes_a_point_after_its_own() -> None:
    layout, a, b = _custom()
    new = _insert_beside(layout, a)
    assert layout.custom_waypoints == [a, new, b]


def test_a_custom_plan_takes_a_point_after_takeoff() -> None:
    layout, a, _ = _custom()
    new = _insert_beside(layout, layout.departure)
    assert layout.custom_waypoints[0] is new


def test_a_custom_plan_takes_a_point_after_its_last() -> None:
    layout, _, b = _custom()
    new = _insert_beside(layout, b)
    assert layout.custom_waypoints[-1] is new


def test_a_waypoint_not_in_the_plan_takes_nothing() -> None:
    layout, _, _ = _custom()
    assert nav_insert_next_to(layout, _wp("ghost", T.NAV, 5)) is None
