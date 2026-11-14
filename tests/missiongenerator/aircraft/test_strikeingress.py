from typing import Any
from unittest.mock import MagicMock

from dcs.task import Bombing, CarpetBombing, OptFormation

from game.ato import FlightType
from game.missiongenerator.aircraft.waypoints.strikeingress import (
    StrikeIngressBuilder,
)
from game.missiongenerator.vietnamopsluadata import is_arc_light_strike


def test_add_strike_tasks_handles_no_targets() -> None:
    """Regression: a Strike against an objective whose units are all destroyed
    leaves the strike waypoint with no targets. add_strike_tasks must not divide
    by zero (len(units) / len(targets)) and must add no bombing task.
    """
    # Bypass __init__ (needs a full mission/flight); only add_strike_tasks() and
    # the attributes it reads are exercised.
    builder: Any = object.__new__(StrikeIngressBuilder)
    builder.waypoint = MagicMock()
    builder.waypoint.targets = []
    builder.group = MagicMock()
    builder.group.units = [MagicMock()]  # would make the ratio 1 / 0 if reached

    waypoint = MagicMock()
    waypoint.tasks = []

    builder.add_strike_tasks(waypoint)  # must not raise ZeroDivisionError

    assert waypoint.tasks == []


def _arc_light_builder(arc_light_on: bool) -> Any:
    builder: Any = object.__new__(StrikeIngressBuilder)
    builder.flight = MagicMock()
    builder.flight.coalition.game.settings.vietnam_arc_light = arc_light_on
    builder.flight.flight_type = FlightType.STRIKE
    builder.flight.unit_type.dcs_unit_type.id = "B-52H"
    return builder


def test_arc_light_bomber_flies_over_without_bombing_tasks() -> None:
    """Arc Light on: the carpet is the strike, so the B-52's ingress carries no bombing
    task and the target is hit once (DM call 2026-11-13)."""
    builder = _arc_light_builder(True)
    waypoint = MagicMock()
    waypoint.tasks = []

    builder.add_tasks(waypoint)

    assert not any(isinstance(t, (Bombing, CarpetBombing)) for t in waypoint.tasks)
    assert len(waypoint.tasks) == 1
    assert waypoint.tasks[0].dict() == OptFormation.ww2_bomber_element_close().dict()


def test_arc_light_eligibility() -> None:
    assert is_arc_light_strike(True, FlightType.STRIKE, "B-52H")
    assert not is_arc_light_strike(False, FlightType.STRIKE, "B-52H")
    assert not is_arc_light_strike(True, FlightType.BAI, "B-52H")
    assert not is_arc_light_strike(True, FlightType.STRIKE, "F-4E-45MC")
