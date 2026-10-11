"""Each side's losses sorted by what killed them (game/losscauses.py)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Optional

from game.agent import views
from game.data.units import UnitClass
from game.losscauses import KillCause, SideLossCauses, tally
from game.theater.player import Player


class FakeUnitMap:
    """Name -> owner lookups, shaped like UnitMap's."""

    def __init__(self) -> None:
        self.aircraft: dict[str, Any] = {}
        self.front: dict[str, Any] = {}
        self.sites: dict[str, Any] = {}

    def add_aircraft(self, name: str, side: Player) -> None:
        departure = SimpleNamespace(captured=side)
        self.aircraft[name] = SimpleNamespace(
            flight=SimpleNamespace(departure=departure)
        )

    def add_front(self, name: str, side: Player, unit_class: UnitClass) -> None:
        self.front[name] = SimpleNamespace(
            origin=SimpleNamespace(captured=side),
            unit_type=SimpleNamespace(unit_class=unit_class),
        )

    def add_site(self, name: str, side: Player, unit_class: UnitClass) -> None:
        control_point = SimpleNamespace(captured=side)
        self.sites[name] = SimpleNamespace(
            theater_unit=SimpleNamespace(
                unit_type=SimpleNamespace(unit_class=unit_class),
                ground_object=SimpleNamespace(control_point=control_point),
            )
        )

    def flight(self, name: str) -> Optional[Any]:
        return self.aircraft.get(name)

    def front_line_unit(self, name: str) -> Optional[Any]:
        return self.front.get(name)

    def front_line_unit_from_tic_clone(self, name: str) -> Optional[Any]:
        return None

    def motorpool_unit(self, name: str) -> Optional[Any]:
        return None

    def convoy_unit(self, name: str) -> Optional[Any]:
        return None

    def theater_units(self, name: str) -> Optional[Any]:
        return self.sites.get(name)


def _map() -> Any:
    unit_map = FakeUnitMap()
    for n in range(1, 7):
        unit_map.add_aircraft(f"Flanker {n}", Player.RED)
    unit_map.add_aircraft("Viper 1", Player.BLUE)
    unit_map.add_aircraft("Viper 2", Player.BLUE)
    unit_map.add_site("Patriot ln", Player.BLUE, UnitClass.LAUNCHER)
    unit_map.add_site("Vulcan", Player.BLUE, UnitClass.AAA)
    unit_map.add_site("Burke", Player.BLUE, UnitClass.DESTROYER)
    unit_map.add_front("Abrams", Player.BLUE, UnitClass.TANK)
    unit_map.add_front("T-72", Player.RED, UnitClass.TANK)
    unit_map.add_site("SA-10 ln", Player.RED, UnitClass.LAUNCHER)
    return unit_map


def test_state_file_entries_are_parsed_and_junk_is_dropped() -> None:
    raw = [
        {
            "target": "Flanker 1",
            "killer": "Viper 1",
            "killer_type": "F-16C_50",
            "weapon": "AIM-120C",
        },
        {"target": "Flanker 2", "killer": "Patriot ln"},
        {"target": 12345, "killer": "Viper 1"},
        {"killer": "Viper 1"},
        "not a table",
    ]
    assert KillCause.parse(raw) == (
        KillCause("Flanker 1", "Viper 1", "F-16C_50", "AIM-120C"),
        KillCause("Flanker 2", "Patriot ln"),
    )
    # An empty Lua table is written as {} or []; an old state file has no key.
    assert KillCause.parse({}) == ()
    assert KillCause.parse(None) == ()


def test_each_loss_is_sorted_by_what_killed_it() -> None:
    kills = (
        KillCause("Flanker 1", "Viper 1", "F-16C_50", "AIM-120C"),
        KillCause("Flanker 2", "Viper 2", "F-16C_50", "AIM-120C"),
        KillCause("Flanker 3", "Patriot ln", "Patriot ln", "MIM-104"),
        KillCause("Flanker 4", "Vulcan", "Vulcan", None),
        KillCause("Flanker 5", "Burke", "USS_Arleigh_Burke_IIa", "SM-2"),
        KillCause("Flanker 6", "A unit nobody mapped", None, None),
        KillCause("T-72", "Abrams", "M-1 Abrams", None),
        KillCause("T-72", "Viper 1", "F-16C_50", None),  # reported twice: once counts
        KillCause("SA-10 ln", "Viper 1", "F-16C_50", "AGM-88C"),
        KillCause("Viper 2", "Flanker 1", "Su-27", "R-27ER"),
    )
    causes = tally(kills, _map())

    assert causes["red"].by_cause == {
        "aircraft": {"aircraft": 2, "sam": 1, "aaa": 1, "ship": 1, "unknown": 1},
        "front_line": {"ground": 1},
        "sites": {"aircraft": 1},
    }
    assert causes["red"].aircraft_killers == {
        "F-16C_50": 2,
        "Patriot ln": 1,
        "Vulcan": 1,
        "USS_Arleigh_Burke_IIa": 1,
    }
    assert causes["red"].aircraft_weapons == {"AIM-120C": 2, "MIM-104": 1, "SM-2": 1}
    assert causes["blue"].by_cause == {"aircraft": {"aircraft": 1}}
    assert causes["blue"].aircraft_weapons == {"R-27ER": 1}


def test_a_kill_by_the_victims_own_side_is_named_as_that() -> None:
    kills = (KillCause("Flanker 1", "SA-10 ln", "S-300PS 5P85C ln", "5V55"),)
    assert tally(kills, _map())["red"].by_cause == {"aircraft": {"own_side": 1}}


def test_a_victim_the_campaign_does_not_track_is_left_out() -> None:
    kills = (KillCause("A civilian airliner", "Viper 1", "F-16C_50", "AIM-9X"),)
    causes = tally(kills, _map())
    assert causes["red"].is_empty and causes["blue"].is_empty


def _sitrep(**extra: Any) -> Any:
    side = SimpleNamespace(aircraft=3, front_line=1, sites=0)
    return SimpleNamespace(
        turn=4, friendly=side, enemy=side, captured=[], lost=[], **extra
    )


def _game(sitrep: Any) -> Any:
    return SimpleNamespace(
        game_stats=SimpleNamespace(data_per_turn=[]),
        turn=5,
        last_sitrep=sitrep,
        informations=[],
    )


def test_the_ai_link_serves_both_sides_causes() -> None:
    causes = {
        "red": SideLossCauses(
            by_cause={"aircraft": {"aircraft": 2, "sam": 1}},
            aircraft_killers={"F-16C_50": 2},
            aircraft_weapons={"AIM-120C": 2},
        ),
        "blue": SideLossCauses(),
    }
    last_turn = views.build_prev_turns(_game(_sitrep(loss_causes=causes))).last_turn
    assert last_turn is not None
    assert last_turn.red_lost_to == {"aircraft": {"aircraft": 2, "sam": 1}}
    assert last_turn.red_air_killers == {"F-16C_50": 2}
    assert last_turn.red_air_weapons == {"AIM-120C": 2}
    # Nothing recorded for blue: the fields drop out of the payload.
    served = last_turn.model_dump(exclude_none=True)
    assert "blue_lost_to" not in served and "blue_air_killers" not in served


def test_a_summary_saved_before_the_feature_serves_no_causes() -> None:
    last_turn = views.build_prev_turns(_game(_sitrep())).last_turn
    assert last_turn is not None
    assert last_turn.red_lost_to is None and last_turn.blue_lost_to is None


def test_losses_at_a_base_captured_in_the_mission_stay_with_the_side_that_held_it() -> (
    None
):
    # The sitrep is written after captures commit: the base and everything read
    # through it already belong to the capturer.
    base = SimpleNamespace(captured=Player.BLUE)
    unit_map = _map()
    unit_map.aircraft["Flanker 1"].flight.departure = base
    unit_map.sites["SA-10 ln"].theater_unit.ground_object.control_point = base
    unit_map.front["T-72"].origin = base
    kills = (
        KillCause("Flanker 1", "Viper 1", "F-16C_50", "AIM-120C"),
        KillCause("SA-10 ln", "Viper 1", "F-16C_50", "AGM-88C"),
        KillCause("T-72", "Abrams", "M-1 Abrams", None),
        KillCause("Viper 2", "SA-10 ln", "S-300PS 5P85C ln", "5V55"),
    )

    wrong = tally(kills, unit_map)
    assert wrong["red"].is_empty

    causes = tally(kills, unit_map, {id(base): Player.RED})
    assert causes["red"].by_cause == {
        "aircraft": {"aircraft": 1},
        "sites": {"aircraft": 1},
        "front_line": {"ground": 1},
    }
    assert causes["blue"].by_cause == {"aircraft": {"sam": 1}}


def test_the_sitrep_tallies_with_the_owners_from_before_the_captures() -> None:
    from datetime import date

    from game.sitrep import Sitrep

    base = SimpleNamespace(captured=Player.BLUE, name="Captured base")
    unit_map = _map()
    unit_map.aircraft["Flanker 1"].flight.departure = base
    losses = SimpleNamespace(aircraft=0, front_line=0, ground_objects=0)
    debriefing: Any = SimpleNamespace(
        loss_counts=lambda player: losses,
        base_captures=[
            SimpleNamespace(control_point=base, captured_by_player=Player.BLUE)
        ],
        state_data=SimpleNamespace(
            kill_causes=(KillCause("Flanker 1", "Viper 1", "F-16C_50", None),),
            sortie_records=(),
        ),
        unit_map=unit_map,
    )
    sitrep = Sitrep.from_debriefing(debriefing, turn=3, day=date(1990, 1, 1))
    assert sitrep.loss_causes["red"].by_cause == {"aircraft": {"aircraft": 1}}
    assert sitrep.loss_causes["blue"].is_empty
