"""AWACS package controller (§117): the dcsRetribution.packageControl record."""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any

from dcs import Point
from dcs.terrain import Caucasus

from game.ato.flighttype import FlightType
from game.ato.flightwaypoint import FlightWaypoint
from game.ato.flightwaypointtype import FlightWaypointType
from game.missiongenerator.luagenerator import LuaData
from game.radio.radios import MHz
from game.retlab.package_control import (
    populate_package_control_lua,
    role_for,
    spoken_callsign,
)
from game.theater.player import Player
from game.utils import feet

START = datetime(2026, 10, 20, 14, 0)


def _waypoint(kind: FlightWaypointType, alt_ft: int = 0) -> FlightWaypoint:
    return FlightWaypoint("HOLD", kind, Point(1000, 2000, Caucasus()), alt=feet(alt_ft))


def _flight(
    package: Any, group: str, task: FlightType, client: bool, push_minutes: int
) -> Any:
    return SimpleNamespace(
        package=package,
        group_name=group,
        callsign=group + "1-1",
        flight_type=task,
        client_units=[object()] if client else [],
        friendly=Player.BLUE,
        mission_start=START,
        push_time=START + timedelta(minutes=push_minutes),
        waypoints=[_waypoint(FlightWaypointType.LOITER, 20000)],
    )


def _game(on: bool = True) -> Any:
    return SimpleNamespace(
        settings=SimpleNamespace(
            package_controller=on, package_controller_srs_path="C:\\SRS"
        ),
        conditions=SimpleNamespace(start_time=START),
    )


def _mission_data(awacs: bool = True) -> Any:
    package = SimpleNamespace(
        frequency=MHz(251, 250),
        time_over_target=START + timedelta(minutes=25),
        target=SimpleNamespace(name="Bridge", position=Point(0, 0, Caucasus())),
    )
    flights = [
        _flight(package, "Colt", FlightType.STRIKE, True, 10),
        _flight(package, "Weasel", FlightType.SEAD, False, 8),
    ]
    return SimpleNamespace(
        packages={1: flights},
        flights=flights,
        awacs=(
            [
                SimpleNamespace(
                    group_name="E-3", callsign="Darkstar1-1", blue=Player.BLUE
                )
            ]
            if awacs
            else []
        ),
    )


def _serialized(game: Any, mission_data: Any) -> str:
    root = LuaData("dcsRetribution")
    populate_package_control_lua(root, game, mission_data)
    return root.serialize()


def test_off_writes_nothing() -> None:
    assert "packageControl" not in _serialized(_game(on=False), _mission_data())


def test_no_awacs_writes_nothing() -> None:
    assert "packageControl" not in _serialized(_game(), _mission_data(awacs=False))


def test_a_player_package_carries_its_frequency_push_and_roles() -> None:
    text = _serialized(_game(), _mission_data())
    for expected in (
        'startSeconds = "50400"',
        'callsign = "Darkstar"',
        'name = "Colt"',
        'freq = "251.250"',
        'modulation = "AM"',
        'totAfter = "1500"',
        'role = "strike"',
        'role = "sead"',
        'pushAfter = "600"',
        'pushAfter = "480"',
        'holdAngels = "20"',
        'client = "true"',
    ):
        assert expected in text, expected


def test_roles_and_spoken_callsigns() -> None:
    assert role_for(FlightType.SEAD_ESCORT) == "sead"
    assert role_for(FlightType.ESCORT) == "escort"
    assert role_for(FlightType.BAI) == "strike"
    assert spoken_callsign("Darkstar1-1") == "Darkstar"
    assert spoken_callsign("Magic 1") == "Magic"
