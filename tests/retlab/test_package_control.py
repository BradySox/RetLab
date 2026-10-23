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


def _join(minutes: int) -> FlightWaypoint:
    join = FlightWaypoint(
        "JOIN", FlightWaypointType.JOIN, Point(3000, 4000, Caucasus()), alt=feet(22000)
    )
    join.tot = START + timedelta(minutes=minutes)
    return join


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
        waypoints=[
            _waypoint(FlightWaypointType.LOITER, 20000),
            _join(push_minutes + 5),
        ],
        arrival=SimpleNamespace(airfield_name="Incirlik"),
        squadron=SimpleNamespace(country=SimpleNamespace(name="USA")),
    )


def _game(voice_awacs: bool = False) -> Any:
    settings = SimpleNamespace(
        voice_awacs=voice_awacs,
        voice_awacs_frequency="251.0 AM",
        voice_awacs_callsign="Chalice, Chainsaw, Image",
    )
    return SimpleNamespace(
        conditions=SimpleNamespace(start_time=START), settings=settings, turn=1
    )


def _mission_data(controller: bool = True, player: bool = True) -> Any:
    package = SimpleNamespace(
        frequency=MHz(251, 250),
        time_over_target=START + timedelta(minutes=25),
        target=SimpleNamespace(name="Bridge", position=Point(0, 0, Caucasus())),
    )
    flights = [
        _flight(package, "Colt", FlightType.STRIKE, player, 10),
        _flight(package, "Weasel", FlightType.SEAD, False, 8),
    ]
    control_package = SimpleNamespace(
        frequency=MHz(240), time_over_target=START, target=package.target
    )
    controllers = (
        [_flight(control_package, "Anvil", FlightType.ABCCC, False, 0)]
        if controller
        else []
    )
    return SimpleNamespace(
        packages={1: flights, 2: controllers},
        flights=flights + controllers,
        strike_frequency=MHz(264, 500) if controller else None,
    )


def _serialized(mission_data: Any, voice_awacs: bool = False) -> str:
    root = LuaData("dcsRetribution")
    populate_package_control_lua(root, _game(voice_awacs), mission_data)
    return root.serialize()


def test_without_an_abccc_skyeye_still_gets_its_name_for_the_turn() -> None:
    text = _serialized(_mission_data(controller=False), voice_awacs=True)
    assert 'awacsCallsign = "Chainsaw"' in text
    assert "awacsVoice = " in text
    assert "strikeFreq" not in text


def test_no_controller_writes_nothing() -> None:
    assert "packageControl" not in _serialized(_mission_data(controller=False))


def test_no_player_package_writes_nothing() -> None:
    assert "packageControl" not in _serialized(_mission_data(player=False))


def test_a_player_package_runs_on_strike_with_opposite_voices() -> None:
    text = _serialized(_mission_data())
    for expected in (
        'startSeconds = "50400"',
        'strikeFreq = "264.500"',
        'strikeModulation = "AM"',
        'callsign = "Anvil"',
        'name = "Colt"',
        'totAfter = "1500"',
        'role = "strike"',
        'role = "sead"',
        'pushAfter = "600"',
        'pushAfter = "480"',
        'holdAngels = "20"',
        'holdIndex = "1"',
        'joinAfter = "900"',
        'joinX = "3000"',
        'joinY = "4000"',
        'joinAngels = "22"',
        'home = "Incirlik"',
        'client = "true"',
    ):
        assert expected in text, expected
    assert 'freq = "251.250"' not in text


def test_roles_and_spoken_callsigns() -> None:
    assert role_for(FlightType.SEAD_ESCORT) == "sead"
    assert role_for(FlightType.ESCORT) == "escort"
    assert role_for(FlightType.BAI) == "strike"
    assert spoken_callsign("Anvil1-1") == "Anvil"
    assert spoken_callsign("Magic 1") == "Magic"


def test_a_player_flight_is_its_leads_seat_and_the_ai_its_flight() -> None:
    data = _mission_data()
    colt, weasel = data.packages[1]
    colt.callsign, weasel.callsign = "Ford 5", "Uzi 8"
    text = _serialized(data)
    assert 'callsign = "Ford 5-1"' in text
    assert 'callsign = "Uzi 8"' in text


def test_every_blue_player_flight_is_listed_for_the_awacs() -> None:
    data = _mission_data(controller=False)
    data.flights[0].callsign = "Ford 9"
    text = _serialized(data, voice_awacs=True)
    assert "players" in text
    assert 'group = "Colt"' in text
    assert 'callsign = "Ford 9-1"' in text
    assert 'group = "Weasel"' not in text
