"""Vacuum ELINT (§118): the planner rule, the radar labels and the STRIKE test."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from game.ato.flighttype import FlightType
from game.data.units import UnitClass
from game.retlab.vacuum import (
    covers_route,
    emitter_label,
    has_vacuum,
    plan_vacuum,
)
from game.theater.player import Player

NM = 1852


def _unit(display_name: str, unit_class: UnitClass = UnitClass.TRACK_RADAR) -> Any:
    return SimpleNamespace(
        unit_type=SimpleNamespace(display_name=display_name, unit_class=unit_class),
        type=SimpleNamespace(id=display_name),
    )


def test_labels_are_nato_names_where_there_is_one() -> None:
    assert emitter_label(_unit('SAM SA-6 Kub "Straight Flush" STR')) == "SA-6"
    assert emitter_label(_unit("SAM SA-11 Buk SR 9S18M1")) == "SA-11"
    assert emitter_label(_unit("HQ-7 Self-Propelled STR")) == "HQ-7"


def test_labels_fall_back_to_the_system_name() -> None:
    assert emitter_label(_unit("SAM Hawk TR (AN/MPQ-46)")) == "Hawk"
    assert emitter_label(_unit("SAM Patriot STR")) == "Patriot"
    assert (
        emitter_label(_unit("EWR 1L13", UnitClass.EARLY_WARNING_RADAR))
        == "early warning radar"
    )


def test_a_ring_over_a_leg_covers_the_route() -> None:
    route = [(0.0, 0.0), (100 * NM, 0.0)]
    assert covers_route((50 * NM, 10 * NM), 12 * NM, [route])
    assert not covers_route((50 * NM, 30 * NM), 12 * NM, [route])
    # Past the end of the leg the distance is to the endpoint.
    assert not covers_route((120 * NM, 0.0), 12 * NM, [route])


def test_a_ring_over_a_lone_target_covers_it() -> None:
    assert covers_route((5 * NM, 0.0), 10 * NM, [[(0.0, 0.0)]])
    assert not covers_route((15 * NM, 0.0), 10 * NM, [[(0.0, 0.0)]])


def _package(primary: FlightType, *tasks: FlightType) -> Any:
    flights = [SimpleNamespace(flight_type=t) for t in (primary, *tasks)]
    return SimpleNamespace(
        primary_task=primary,
        primary_flight=SimpleNamespace(departure="Incirlik"),
        flights=flights,
        target=SimpleNamespace(is_carrier=False, is_fleet=False),
    )


def _coalition(packages: list[Any], on: bool = True, squadron: Any = None) -> Any:
    wing = SimpleNamespace(best_squadron_for=lambda *a, **k: squadron)
    game = SimpleNamespace(settings=SimpleNamespace(vacuum_elint=on))
    return SimpleNamespace(
        player=Player.BLUE,
        game=game,
        ato=SimpleNamespace(packages=packages),
        air_wing=wing,
    )


def test_no_vacuum_without_two_sead_flights() -> None:
    ato = [_package(FlightType.AEWC), _package(FlightType.SEAD)]
    calls: list[Any] = []
    coalition = _coalition(ato)
    coalition.air_wing.best_squadron_for = lambda *a, **k: calls.append(a)
    assert plan_vacuum(coalition) is None
    assert calls == []


def test_no_vacuum_with_the_setting_off() -> None:
    ato = [_package(FlightType.AEWC), _package(FlightType.SEAD, FlightType.DEAD)]
    assert plan_vacuum(_coalition(ato, on=False)) is None


def test_two_sead_flights_ask_the_wing_for_a_vacuum() -> None:
    asked: list[Any] = []
    ato = [_package(FlightType.AEWC), _package(FlightType.SEAD, FlightType.DEAD)]
    coalition = _coalition(ato)

    def best(*args: Any, **kwargs: Any) -> None:
        asked.append(args)

    coalition.air_wing.best_squadron_for = best
    assert plan_vacuum(coalition) is None  # no squadron free
    assert asked == [("Incirlik", FlightType.ELINT, 1, False)]


def test_one_vacuum_a_turn() -> None:
    ato = [
        _package(FlightType.AEWC, FlightType.ELINT),
        _package(FlightType.SEAD, FlightType.DEAD),
    ]
    assert has_vacuum(SimpleNamespace(packages=ato))  # type: ignore[arg-type]
    assert plan_vacuum(_coalition(ato)) is None


def test_the_lua_names_each_player_flight_with_its_package_target() -> None:
    from game.missiongenerator.luagenerator import LuaData
    from game.radio.radios import MHz
    from game.retlab.vacuum import populate_vacuum_lua

    target = SimpleNamespace(position=SimpleNamespace(x=1000.0, y=2000.0))
    package = SimpleNamespace(target=target)

    def flight(group: str, task: FlightType, client: bool) -> Any:
        return SimpleNamespace(
            package=package,
            group_name=group,
            callsign=group + " 9",
            flight_type=task,
            client_units=[object()] if client else [],
            friendly=Player.BLUE,
            waypoints=[],
            squadron=SimpleNamespace(country=SimpleNamespace(name="USA")),
        )

    vacuum = flight("Vacuum", FlightType.ELINT, False)
    ford, ai = flight("Ford", FlightType.SEAD, True), flight(
        "Dodge", FlightType.SEAD, False
    )
    mission_data = SimpleNamespace(
        flights=[vacuum, ford, ai],
        packages={1: [ford, ai]},
        vacuum_frequency=MHz(262),
        strike_frequency=None,
        skyeye_voices=[],
    )
    game = SimpleNamespace(theater=SimpleNamespace(controlpoints=[]))
    root = LuaData("dcsRetribution")
    populate_vacuum_lua(root, game, mission_data)  # type: ignore[arg-type]
    text = root.serialize()
    assert 'callsign = "Ford 9-1"' in text
    assert 'group = "Ford"' in text
    assert 'targetX = "1000.0"' in text and 'targetY = "2000.0"' in text
    assert 'group = "Dodge"' not in text
