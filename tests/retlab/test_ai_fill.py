"""AI fills an empty player flight (§113): the rule, the twin view, the Lua record.

The twin's spawn in a real mission was checked by generating one; the DCS side
(the launch, the AI flying the copied plan) is checklist row B234.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest

from game.ato.flightmember import FlightMember
from game.ato.flightstate import WaitingForStart
from game.ato.flighttype import FlightType
from game.ato.starttype import StartType
from game.missiongenerator.aircraft.aitwin import (
    AiTwinSeat,
    ai_twin_view,
    copy_identity,
    player_units,
    twin_group_name,
)
from game.missiongenerator.luagenerator import LuaData
from game.missiongenerator.missiondata import MissionData
from game.retlab.ai_fill import (
    NO_AI_FILL_TASKS,
    AiFillPair,
    ai_fill_wanted,
    offers_ai_fill,
    populate_ai_fill_lua,
)
from game.settings import Settings

START = datetime(2026, 10, 16, 12, 0)


def _member(player: bool) -> FlightMember:
    pilot = SimpleNamespace(player=player)
    return FlightMember(pilot, SimpleNamespace(name="loadout"))  # type: ignore[arg-type]


class _Roster:
    def __init__(self, members: list[FlightMember]) -> None:
        self.members = members

    @property
    def player_count(self) -> int:
        return len([m for m in self.members if m.is_player])


class _Flight:
    """The parts of a Flight the rule and the twin view read."""

    def __init__(
        self,
        seats: tuple[bool, ...] = (True, True),
        flight_type: FlightType = FlightType.BARCAP,
        cargo: Any = None,
        takeoff: datetime = START + timedelta(minutes=25),
    ) -> None:
        self.roster = _Roster([_member(p) for p in seats])
        self.flight_type = flight_type
        self.cargo = cargo
        self.start_type = StartType.COLD
        self.group_id = 7
        self.ai_fills_if_empty: bool | None = None
        self.squadron = SimpleNamespace(settings=Settings())
        waypoint = SimpleNamespace(tot=START, min_fuel=1.0, fuel_planned=2.0)
        self.flight_plan = SimpleNamespace(
            waypoints=[waypoint], takeoff_time=lambda: takeoff
        )
        self.state: Any = WaitingForStart(self, Settings(), START)  # type: ignore[arg-type]

    @property
    def client_count(self) -> int:
        return self.roster.player_count

    def iter_members(self) -> Any:
        yield from self.roster.members

    def set_state(self, state: Any) -> None:
        self.state = state


def test_only_flights_with_player_seats_offer_it() -> None:
    assert offers_ai_fill(_Flight((True, False)))  # type: ignore[arg-type]
    assert not offers_ai_fill(_Flight((False, False)))  # type: ignore[arg-type]


@pytest.mark.parametrize("task", sorted(NO_AI_FILL_TASKS, key=str))
def test_tasks_an_ai_copy_cannot_fly_are_excluded(task: FlightType) -> None:
    assert not offers_ai_fill(_Flight(flight_type=task))  # type: ignore[arg-type]


def test_a_cargo_flight_is_excluded() -> None:
    assert not offers_ai_fill(_Flight(cargo=object()))  # type: ignore[arg-type]


def test_the_flights_box_wins_and_an_untouched_box_follows_the_setting() -> None:
    settings = Settings()
    flight = _Flight()
    assert not ai_fill_wanted(flight, settings)  # type: ignore[arg-type]
    settings.ai_fills_empty_player_flights = True
    assert ai_fill_wanted(flight, settings)  # type: ignore[arg-type]
    flight.ai_fills_if_empty = False
    assert not ai_fill_wanted(flight, settings)  # type: ignore[arg-type]
    settings.ai_fills_empty_player_flights = False
    flight.ai_fills_if_empty = True
    assert ai_fill_wanted(flight, settings)  # type: ignore[arg-type]


def test_the_defaults_are_off_five_minutes_and_announced() -> None:
    settings = Settings()
    assert settings.ai_fills_empty_player_flights is False
    assert settings.ai_fill_check_delay == timedelta(minutes=5)
    assert settings.ai_fill_announce is True


def test_a_twin_seat_keeps_the_seat_but_is_ai() -> None:
    seat = _member(True)
    seat.livery = "VF-31"
    twin = AiTwinSeat(seat)
    assert twin.pilot is seat.pilot
    assert twin.loadout is seat.loadout
    assert twin.livery == "VF-31"
    assert not twin.is_player
    assert seat.is_player


def test_the_view_is_an_air_start_of_the_player_seats_at_takeoff() -> None:
    flight = _Flight((True, False, True, False))
    with ai_twin_view(flight, START):  # type: ignore[arg-type]
        assert len(flight.roster.members) == 2
        assert flight.client_count == 0
        assert flight.start_type is StartType.IN_FLIGHT
        assert isinstance(flight.state, WaitingForStart)
        assert flight.state.time_remaining(START) == timedelta(minutes=25)


def test_a_takeoff_already_past_launches_at_mission_start() -> None:
    flight = _Flight(takeoff=START - timedelta(minutes=3))
    with ai_twin_view(flight, START):  # type: ignore[arg-type]
        assert flight.state.time_remaining(START) == timedelta()


def test_the_view_puts_everything_back() -> None:
    flight = _Flight((True, False))
    roster, state = flight.roster, flight.state
    waypoint = flight.flight_plan.waypoints[0]
    with ai_twin_view(flight, START):  # type: ignore[arg-type]
        flight.group_id = 99
        waypoint.tot = None
        waypoint.min_fuel = 5.0
        waypoint.fuel_planned = None
    assert flight.roster is roster
    assert flight.state is state
    assert flight.start_type is StartType.COLD
    assert flight.group_id == 7
    assert (waypoint.tot, waypoint.min_fuel, waypoint.fuel_planned) == (
        START,
        1.0,
        2.0,
    )


def test_the_view_puts_everything_back_after_an_error() -> None:
    flight = _Flight()
    roster = flight.roster
    with pytest.raises(RuntimeError):
        with ai_twin_view(flight, START):  # type: ignore[arg-type]
            raise RuntimeError("spawn failed")
    assert flight.roster is roster
    assert flight.start_type is StartType.COLD


def test_player_units_are_the_player_seats_in_order() -> None:
    flight = _Flight((False, True, False, True))
    group = SimpleNamespace(units=["u1", "u2", "u3", "u4"])
    assert player_units(flight, group) == ["u2", "u4"]  # type: ignore[arg-type]


def test_the_twin_takes_the_seats_callsigns_and_board_numbers() -> None:
    client = [
        SimpleNamespace(
            callsign=None, callsign_dict={"name": "Gypsy11"}, onboard_num="108"
        )
    ]
    twin_unit = SimpleNamespace(callsign=None, callsign_dict={}, onboard_num="010")
    copy_identity(client, SimpleNamespace(units=[twin_unit]))  # type: ignore[arg-type]
    assert twin_unit.callsign_dict == {"name": "Gypsy11"}
    assert twin_unit.callsign_dict is not client[0].callsign_dict
    assert twin_unit.onboard_num == "108"


def test_the_twin_name_keeps_the_task_at_the_end_of_the_first_field() -> None:
    name = twin_group_name("Kobuleti BARCAP|12|F-14B|")
    assert name == "AI Kobuleti BARCAP|12|F-14B|"
    assert name.split("|")[0].endswith(" BARCAP")


def _emit(pairs: list[AiFillPair], settings: Settings) -> str:
    root = LuaData("dcsRetribution")
    mission_data = MissionData()
    mission_data.ai_fill_pairs.extend(pairs)
    populate_ai_fill_lua(root, SimpleNamespace(settings=settings), mission_data)  # type: ignore[arg-type]
    return root.serialize()


def test_no_twin_emits_no_node() -> None:
    assert "aiFill" not in _emit([], Settings())


def test_the_lua_record_carries_each_pair_and_the_settings() -> None:
    settings = Settings()
    settings.ai_fill_check_delay = timedelta(minutes=3)
    settings.ai_fill_announce = False
    lua = _emit(
        [
            AiFillPair(
                "Hog 1 grp", "AI Hog 1 grp", "blue", 1500, "Hog 1 has no players."
            )
        ],
        settings,
    )
    assert "aiFill" in lua
    assert 'checkDelay = "180"' in lua
    assert 'announce = ""' in lua
    assert 'client = "Hog 1 grp"' in lua
    assert 'twin = "AI Hog 1 grp"' in lua
    assert 'coalition = "blue"' in lua
    assert 'activateAfter = "1500"' in lua
