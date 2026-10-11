"""An airlift cargo stop lands on a ship by unit, on a field by airdrome."""

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

from game.missiongenerator.aircraft.waypoints.cargostop import CargoStopBuilder
from game.missiongenerator.aircraft.waypoints.pydcswaypointbuilder import (
    PydcsWaypointBuilder,
)
from game.theater import NavalControlPoint
from game.theater.controlpoint import ControlPoint


def _build(control_point: Any) -> Any:
    builder: Any = object.__new__(CargoStopBuilder)
    builder.waypoint = SimpleNamespace(control_point=control_point)
    point = SimpleNamespace(airdrome_id=None, helipad_id=None, link_unit=None)
    with patch.object(PydcsWaypointBuilder, "build", return_value=point):
        return builder.build()


def test_carrier_cargo_stop_links_the_ship() -> None:
    carrier = MagicMock(spec=NavalControlPoint)
    carrier.airdrome_id_for_landing = 1234
    point = _build(carrier)
    assert point.helipad_id == 1234
    assert point.link_unit == 1234
    assert point.airdrome_id is None


def test_airfield_cargo_stop_uses_the_airdrome() -> None:
    field = MagicMock(spec=ControlPoint)
    field.airdrome_id_for_landing = 21
    point = _build(field)
    assert point.airdrome_id == 21
    assert point.helipad_id is None
