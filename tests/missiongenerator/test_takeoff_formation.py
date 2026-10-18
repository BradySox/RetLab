"""A ground-start flight flies a loose trail from takeoff.

DCS holds a lead slow and low until the flight is joined (2026-10-17 Syria test: Viper
leads at 250 kt and 1,700 ft for 4.5 min). The trail is the experiment against that.
"""

from types import SimpleNamespace
from typing import Any

from dcs.task import OptFormation

from game.missiongenerator.aircraft.aircraftbehavior import AircraftBehavior


def _group(point_type: str) -> Any:
    return SimpleNamespace(points=[SimpleNamespace(type=point_type, tasks=[])])


def _flight(count: int = 4, is_helo: bool = False) -> Any:
    return SimpleNamespace(count=count, is_helo=is_helo)


def _formations(group: Any) -> list[dict[str, Any]]:
    return [
        t.dict()["params"]["action"]["params"]
        for t in group.points[0].tasks
        if t.dict()["params"]["action"]["params"].get("name") == 5
    ]


def test_ground_start_flight_gets_loose_trail() -> None:
    for point_type in ("TakeOffParkingHot", "TakeOffParking", "TakeOff"):
        group = _group(point_type)
        AircraftBehavior.configure_takeoff_formation(_flight(), group)
        assert _formations(group) == [
            OptFormation.trail_open().dict()["params"]["action"]["params"]
        ]


def test_air_start_single_ship_and_helo_are_left_alone() -> None:
    cases = [
        (_flight(), _group("Turning Point")),
        (_flight(count=1), _group("TakeOffParkingHot")),
        (_flight(is_helo=True), _group("TakeOffParkingHot")),
    ]
    for flight, group in cases:
        AircraftBehavior.configure_takeoff_formation(flight, group)
        assert _formations(group) == []
