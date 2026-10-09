"""The join is the safe spot nearest the IP, not the nearest threat edge.

Anatolian Reach turn 1: a DEAD on a radar near Konya, launched from the carrier.
The only threat edge crossing the join ring was Bassel's fighter zone, far to the
east, and the old preference for threat edges put the join there: 269 NM to the
IP instead of 194.
"""

from __future__ import annotations

from typing import Any

import pytest
from dcs.mapping import Point
from dcs.terrain.caucasus.caucasus import Caucasus
from shapely.geometry import MultiPolygon, Point as ShapelyPoint

from game.flightplan.joinzonegeometry import JoinZoneGeometry
from game.utils import nautical_miles

TERRAIN = Caucasus()
NM = nautical_miles(1).meters

HOME = Point(0, 0, TERRAIN)
TARGET = Point(240 * NM, 0, TERRAIN)
IP = Point(190 * NM, 0, TERRAIN)


class FakeDoctrine:
    join_distance = nautical_miles(20)


class FakeThreatZone:
    def __init__(self, shape: Any) -> None:
        self.all = shape


class FakeCoalition:
    def __init__(self, threat: Any) -> None:
        self.doctrine = FakeDoctrine()
        self.opponent = type("Opp", (), {"threat_zone": FakeThreatZone(threat)})()


def join_for(threat: Any) -> Point:
    geometry = JoinZoneGeometry(
        TARGET, HOME, IP, FakeCoalition(threat)  # type: ignore[arg-type]
    )
    return geometry.find_best_join_point()


def test_a_far_threat_edge_does_not_pull_the_join_off_course() -> None:
    # Crosses the join ring well off the home-to-IP line, inside the IP wedge.
    off_to_the_side = ShapelyPoint(60 * NM, 75 * NM).buffer(20 * NM)
    geometry = JoinZoneGeometry(
        TARGET,
        HOME,
        IP,
        FakeCoalition(MultiPolygon([off_to_the_side])),  # type: ignore[arg-type]
    )
    assert not geometry.preferred_lines.is_empty, "no threat edge on the ring"

    join = geometry.find_best_join_point()

    assert abs(join.y) / NM < 1.0, f"join pulled {join.y / NM:.0f} NM off course"
    assert join.distance_to_point(IP) / NM == pytest.approx(190 - 86.4, abs=0.5)


def test_with_no_threat_the_join_sits_on_the_home_to_ip_line() -> None:
    join = join_for(MultiPolygon([]))
    assert abs(join.y) / NM < 1.0
    assert HOME.distance_to_point(join) / NM == pytest.approx(86.4, abs=0.5)


def test_a_threat_on_the_line_still_puts_the_join_on_its_edge() -> None:
    on_the_line = ShapelyPoint(85 * NM, 0).buffer(10 * NM)
    join = join_for(MultiPolygon([on_the_line]))
    edge_distance = on_the_line.exterior.distance(ShapelyPoint(join.x, join.y))
    assert edge_distance / NM < 0.5, "join is not on the threat edge"
    assert not on_the_line.buffer(-1).contains(ShapelyPoint(join.x, join.y))
