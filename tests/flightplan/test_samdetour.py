"""Straight package legs are steered round SAM rings they do not have to enter.

Found 2026-09-23 on Graveyard of Empires turn 1: every deep blue package flew
JOIN -> INGRESS and TARGET -> SPLIT straight through a Buk-M3 ring (SABERTOOTH)
that covered none of the targets -- 2,349 NM of flight time inside it across the
ATO. With the detour the same replan left 113 NM.
"""

from __future__ import annotations

import pickle
from types import SimpleNamespace
from typing import Any

from dcs.mapping import Point
from dcs.terrain.caucasus.caucasus import Caucasus
from shapely.geometry import LineString, Point as ShapelyPoint

from game.ato.flightplans.formationattack import FormationAttackLayout
from game.ato.flightwaypoint import FlightWaypoint
from game.ato.flightwaypointtype import FlightWaypointType
from game.flightplan.samdetour import SamRing, detour
from game.utils import nautical_miles

TERRAIN = Caucasus()
NM = nautical_miles(1).meters


def point(x_nm: float, y_nm: float) -> Point:
    return Point(x_nm * NM, y_nm * NM, TERRAIN)


def ring(x_nm: float, y_nm: float, radius_nm: float) -> SamRing:
    return SamRing(x_nm * NM, y_nm * NM, radius_nm * NM)


def theater(*extent: Point) -> Any:
    # NavMesh.map_bounds only reads positions; this is the map it pads.
    return SimpleNamespace(
        controlpoints=[SimpleNamespace(position=p, ground_objects=[]) for p in extent],
        terrain=TERRAIN,
    )


def exposure(start: Point, navs: list[Point], end: Point, sam: SamRing) -> float:
    line = LineString([(p.x, p.y) for p in [start, *navs, end]])
    return line.intersection(sam.shape).length / NM


START = point(0, 0)
END = point(0, 120)
THEATER = theater(START, END)


def test_a_leg_through_a_ring_goes_round_it() -> None:
    sam = ring(0, 60, 30)
    navs = detour(THEATER, START, END, [sam])
    assert navs
    assert exposure(START, navs, END, sam) < 1


def test_a_clear_leg_is_left_straight() -> None:
    assert detour(THEATER, START, END, [ring(80, 60, 30)]) == []


def test_a_ring_over_the_target_is_flown_through() -> None:
    sam = ring(0, 60, 30)
    assert detour(THEATER, START, END, [sam], must_enter=[point(0, 55)]) == []


def test_a_join_nudged_inside_the_edge_still_detours() -> None:
    """Joins sit on the threat edge and are then perturbed up to 1 NM inward."""
    sam = ring(0, 60, 30)
    join = point(0, 31)
    assert ShapelyPoint(join.x, join.y).distance(sam.center) < sam.radius
    navs = detour(THEATER, join, END, [sam])
    assert navs
    assert exposure(join, navs, END, sam) < exposure(join, [], END, sam)


def test_a_join_deep_inside_pins_the_ring() -> None:
    sam = ring(0, 60, 30)
    assert detour(THEATER, point(0, 45), END, [sam]) == []


def waypoint(name: str) -> FlightWaypoint:
    return FlightWaypoint(name, FlightWaypointType.NAV, point(0, 0))


def layout() -> FormationAttackLayout:
    return FormationAttackLayout(
        departure=waypoint("TAKEOFF"),
        hold=None,
        nav_to=[],
        join=waypoint("JOIN"),
        split=waypoint("SPLIT"),
        refuel=None,
        nav_from=[],
        arrival=waypoint("LANDING"),
        divert=None,
        bullseye=waypoint("BULLSEYE"),
        custom_waypoints=[],
        ingress=waypoint("INGRESS"),
        targets=[waypoint("TARGET")],
        ingress_nav=[waypoint("IN1")],
        egress_nav=[waypoint("OUT1")],
    )


def test_detour_points_sit_on_their_legs() -> None:
    names = [w.name for w in layout().iter_waypoints()]
    assert names.index("JOIN") < names.index("IN1") < names.index("INGRESS")
    assert names.index("TARGET") < names.index("OUT1") < names.index("SPLIT")


def test_a_detour_point_can_be_deleted() -> None:
    plan = layout()
    assert plan.delete_waypoint(plan.ingress_nav[0])
    assert plan.ingress_nav == []


def test_a_layout_saved_before_the_detour_loads() -> None:
    plan = layout()
    state = dict(plan.__dict__)
    del state["ingress_nav"], state["egress_nav"]
    restored = FormationAttackLayout.__new__(FormationAttackLayout)
    restored.__setstate__(state)
    assert restored.ingress_nav == [] and restored.egress_nav == []
    assert pickle.loads(pickle.dumps(restored)).egress_nav == []
