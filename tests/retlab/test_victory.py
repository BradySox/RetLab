"""Custom victory conditions (§75): parse, evaluation, verdict, surfacing.

Locks the contracts from docs/dev/design/retlab-victory-conditions-notes.md:
AND-within-entry / OR-across-entries semantics (the deliberate divergence from
PhaseCondition's any-field trigger), the no-vacuous-win rules (empty baselines
and absent categories never fire), loss precedence, the knob synthesis, the
announce latch, and that an unconfigured game is a byte-identical no-op all the
way through the real ``Game.check_win_loss`` branch order.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Iterator, Optional, cast

import pytest

from game.retlab import victory as victory_mod
from game.retlab.victory import (
    VictoryCondition,
    VictoryProfile,
    active_victory_profile,
    condition_met,
    describe_condition,
    ensure_victory_baseline,
    parse_victory,
    victory_overview,
    victory_sitrep_lines,
    victory_verdict,
)
from game.theater.player import Player


@pytest.fixture(autouse=True)
def _clean_profile_cache() -> Iterator[None]:
    victory_mod._PROFILE_CACHE.clear()
    yield
    victory_mod._PROFILE_CACHE.clear()


def _cp(
    name: str,
    owner: Player,
    operational: bool = True,
    armor: int = 0,
) -> Any:
    return SimpleNamespace(
        name=name,
        captured=owner,
        runway_is_operational=lambda: operational,
        base=SimpleNamespace(total_armor=armor),
    )


def _tgo(name: str, category: str, cp: Any, *alive: bool) -> Any:
    return SimpleNamespace(
        name=name,
        category=category,
        control_point=cp,
        units=[SimpleNamespace(alive=a) for a in alive],
    )


def _wing(*owned: int) -> Any:
    squadrons = [SimpleNamespace(owned_aircraft=n) for n in owned]
    return SimpleNamespace(iter_squadrons=lambda: list(squadrons))


def _game(
    cps: Optional[list[Any]] = None,
    tgos: Optional[list[Any]] = None,
    red_air: tuple[int, ...] = (10,),
    blue_air: tuple[int, ...] = (10,),
    turn: int = 5,
    campaign_name: Optional[str] = None,
) -> Any:
    wings = {Player.RED: _wing(*red_air), Player.BLUE: _wing(*blue_air)}
    messages: list[tuple[str, str]] = []
    game = SimpleNamespace(
        theater=SimpleNamespace(controlpoints=cps or [], ground_objects=tgos or []),
        air_wing_for=lambda player: wings[player],
        settings=SimpleNamespace(),
        turn=turn,
        campaign_name=campaign_name,
        messages=messages,
    )
    game.message = lambda title, text="": messages.append((title, text))
    return game


def _baseline(game: Any) -> Any:
    return ensure_victory_baseline(cast(Any, game))


# --- parsing --------------------------------------------------------------------------


def test_parse_full_block() -> None:
    profile = parse_victory(
        {
            "description": "Liberate Abkhazia",
            "win_when": [
                {"capture_cps": ["Sukhumi", "Gudauta"], "label": "Take the coast"},
                {"enemy_air_below": 0.1, "min_turn": 4},
            ],
            "lose_when": [{"lose_cps": ["Kutaisi"]}],
        }
    )
    assert profile is not None
    assert profile.description == "Liberate Abkhazia"
    assert profile.win_when[0].capture_cps == ("Sukhumi", "Gudauta")
    assert profile.win_when[0].label == "Take the coast"
    assert profile.win_when[1].enemy_air_below == 0.1
    assert profile.win_when[1].min_turn == 4
    assert profile.lose_when[0].lose_cps == ("Kutaisi",)


def test_parse_absent_block_is_none() -> None:
    assert parse_victory(None) is None
    assert parse_victory({}) is None


def test_parse_rejects_bad_shapes() -> None:
    with pytest.raises(ValueError):
        parse_victory("win")
    with pytest.raises(ValueError):
        parse_victory({"win_when": [{"capture_cps": ["A"]}], "extra": True})
    with pytest.raises(ValueError):
        parse_victory({"win_when": [{"capture_the_flag": ["A"]}]})
    with pytest.raises(ValueError):
        # label/min_turn alone do not end a war.
        parse_victory({"win_when": [{"label": "x", "min_turn": 3}]})
    with pytest.raises(ValueError):
        parse_victory({"description": "no conditions at all"})
    with pytest.raises(ValueError):
        parse_victory({"win_when": [{"capture_cps": []}]})
    with pytest.raises(ValueError):
        parse_victory({"win_when": [{"enemy_air_below": 0.0}]})
    with pytest.raises(ValueError):
        parse_victory({"win_when": [{"enemy_air_below": 1.0}]})
    with pytest.raises(ValueError):
        parse_victory({"win_when": [{"territory_below": 1.0}]})
    with pytest.raises(ValueError):
        parse_victory({"win_when": [{"enemy_air_denied": False}]})


def test_parse_territory_above_one_is_legal() -> None:
    profile = parse_victory({"win_when": [{"territory_above": 1.0}]})
    assert profile is not None
    assert profile.win_when[0].territory_above == 1.0


# --- evaluation -----------------------------------------------------------------------


def test_capture_cps_requires_all_named_blue() -> None:
    game = _game(cps=[_cp("A", Player.BLUE), _cp("B", Player.RED)])
    baseline = _baseline(game)
    partial = VictoryCondition(capture_cps=("A", "B"))
    assert not condition_met(game, partial, baseline)
    game.theater.controlpoints[1].captured = Player.BLUE
    assert condition_met(game, VictoryCondition(capture_cps=("A", "B")), baseline)
    # A typo'd name can never be met -- visible in the UI, never a silent win.
    assert not condition_met(game, VictoryCondition(capture_cps=("Nope",)), baseline)


def test_lose_cps_fires_on_any_named_red() -> None:
    game = _game(cps=[_cp("A", Player.BLUE), _cp("B", Player.RED)])
    baseline = _baseline(game)
    assert condition_met(game, VictoryCondition(lose_cps=("A", "B")), baseline)
    assert not condition_met(game, VictoryCondition(lose_cps=("A",)), baseline)


def test_territory_thresholds() -> None:
    game = _game(
        cps=[
            _cp("A", Player.BLUE),
            _cp("B", Player.BLUE),
            _cp("C", Player.RED),
            _cp("N", Player.NEUTRAL),
        ]
    )
    baseline = _baseline(game)
    # 2/3 non-neutral bases are blue.
    assert condition_met(game, VictoryCondition(territory_above=0.6), baseline)
    assert not condition_met(game, VictoryCondition(territory_above=0.7), baseline)
    assert condition_met(game, VictoryCondition(territory_below=0.7), baseline)
    assert not condition_met(game, VictoryCondition(territory_below=0.5), baseline)


def test_destroy_targets_needs_every_named_tgo_dead() -> None:
    cp = _cp("A", Player.RED)
    game = _game(
        cps=[cp],
        tgos=[
            _tgo("HQ North", "commandcenter", cp, False, False),
            _tgo("HQ South", "commandcenter", cp, True),
        ],
    )
    baseline = _baseline(game)
    assert condition_met(
        game, VictoryCondition(destroy_targets=("hq north",)), baseline
    )
    both = VictoryCondition(destroy_targets=("HQ North", "HQ South"))
    assert not condition_met(game, both, baseline)
    # A name matching nothing can never be met.
    missing = VictoryCondition(destroy_targets=("HQ West",))
    assert not condition_met(game, missing, baseline)


def test_destroy_categories_baseline_guards_the_vacuous_win() -> None:
    cp = _cp("A", Player.RED)
    game = _game(cps=[cp], tgos=[_tgo("Comms", "comms", cp, True)])
    baseline = _baseline(game)
    cond = VictoryCondition(destroy_categories=("comms",))
    assert not condition_met(game, cond, baseline)
    game.theater.ground_objects[0].units[0].alive = False
    assert condition_met(game, cond, baseline)
    # A category the campaign never fielded can never produce a win.
    absent = VictoryCondition(destroy_categories=("power",))
    assert not condition_met(game, absent, baseline)


def test_destroy_categories_capturing_the_site_counts_as_denial() -> None:
    # The last comms site's base gets CAPTURED intact: red owns no alive comms
    # any more, which is the condition's meaning ("the enemy no longer operates
    # any"), and the baseline proves the class existed.
    cp = _cp("A", Player.RED)
    game = _game(cps=[cp], tgos=[_tgo("Comms", "comms", cp, True)])
    baseline = _baseline(game)
    cp.captured = Player.BLUE
    assert condition_met(
        game, VictoryCondition(destroy_categories=("comms",)), baseline
    )


def test_strength_ratios_measure_against_the_baseline() -> None:
    game = _game(red_air=(10, 10), blue_air=(8,))
    baseline = _baseline(game)
    assert baseline.red_air == 20
    cond = VictoryCondition(enemy_air_below=0.5)
    assert not condition_met(game, cond, baseline)
    # Red loses one whole squadron: 10/20 is not < 0.5 ...
    game.air_wing_for(Player.RED).iter_squadrons()[0].owned_aircraft = 0
    assert not condition_met(game, cond, baseline)
    # ... one more airframe down is.
    game.air_wing_for(Player.RED).iter_squadrons()[1].owned_aircraft = 9
    assert condition_met(game, cond, baseline)


def test_empty_baseline_never_fires_a_ratio_condition() -> None:
    game = _game(red_air=(0,))
    baseline = _baseline(game)
    assert not condition_met(game, VictoryCondition(enemy_air_below=0.9), baseline)
    assert not condition_met(game, VictoryCondition(enemy_ground_below=0.9), baseline)


def test_ground_and_friendly_ratios() -> None:
    game = _game(
        cps=[_cp("A", Player.RED, armor=10), _cp("B", Player.BLUE, armor=4)],
        blue_air=(10,),
    )
    baseline = _baseline(game)
    assert baseline.red_ground == 10
    game.theater.controlpoints[0].base.total_armor = 1
    assert condition_met(game, VictoryCondition(enemy_ground_below=0.2), baseline)
    game.air_wing_for(Player.BLUE).iter_squadrons()[0].owned_aircraft = 2
    assert condition_met(game, VictoryCondition(friendly_air_below=0.3), baseline)


def test_air_denial_counts_operational_red_bases() -> None:
    game = _game(
        cps=[
            _cp("Red field", Player.RED, operational=True),
            _cp("Blue field", Player.BLUE, operational=True),
        ]
    )
    baseline = _baseline(game)
    cond = VictoryCondition(enemy_air_denied=True)
    assert not condition_met(game, cond, baseline)
    # Cratered/captured: the red field stops operating; blue fields never count.
    game.theater.controlpoints[0].runway_is_operational = lambda: False
    assert condition_met(game, cond, baseline)


def test_and_semantics_within_one_entry() -> None:
    game = _game(cps=[_cp("A", Player.BLUE)], red_air=(10,), turn=5)
    baseline = _baseline(game)
    both = VictoryCondition(capture_cps=("A",), enemy_air_below=0.5)
    # The CP is held but the air condition is not met -> the entry is not met.
    assert not condition_met(game, both, baseline)
    game.air_wing_for(Player.RED).iter_squadrons()[0].owned_aircraft = 1
    assert condition_met(game, both, baseline)


def test_min_turn_guards_the_entry() -> None:
    game = _game(cps=[_cp("A", Player.BLUE)], turn=2)
    baseline = _baseline(game)
    cond = VictoryCondition(capture_cps=("A",), min_turn=4)
    assert not condition_met(game, cond, baseline)
    game.turn = 4
    assert condition_met(game, cond, baseline)


# --- the baseline latch ---------------------------------------------------------------


def test_baseline_latches_once() -> None:
    game = _game(red_air=(10,))
    first = _baseline(game)
    game.air_wing_for(Player.RED).iter_squadrons()[0].owned_aircraft = 2
    assert _baseline(game) is first
    assert _baseline(game).red_air == 10


# --- the active profile ---------------------------------------------------------------


def test_no_configuration_means_no_profile() -> None:
    assert active_victory_profile(_game()) is None


def _hold_half_the_bases() -> str:
    """An authored domination win at 50%, the driver for the verdict tests."""
    victory_mod._PROFILE_CACHE["Test Campaign"] = VictoryProfile(
        win_when=(VictoryCondition(territory_above=0.5),),
    )
    return "Test Campaign"


def test_the_authored_profile_is_the_active_one() -> None:
    authored = VictoryProfile(
        description="Test war",
        win_when=(VictoryCondition(capture_cps=("A",)),),
        lose_when=(VictoryCondition(lose_cps=("B",)),),
    )
    victory_mod._PROFILE_CACHE["Test Campaign"] = authored
    game = _game(campaign_name="Test Campaign")

    assert active_victory_profile(game) is authored


# --- the verdict ----------------------------------------------------------------------


def test_verdict_none_without_configuration() -> None:
    assert victory_verdict(_game(cps=[_cp("A", Player.BLUE)])) is None


def test_verdict_win_announces_once() -> None:
    game = _game(
        cps=[_cp("A", Player.BLUE), _cp("B", Player.RED)],
        campaign_name=_hold_half_the_bases(),
    )
    assert victory_verdict(game) == "win"
    assert victory_verdict(game) == "win"
    banners = [m for m in game.messages if m[0] == "Victory condition met"]
    assert len(banners) == 1
    assert "50%" in banners[0][1]


def test_a_read_of_the_verdict_announces_nothing() -> None:
    # The outside AI's turn_context reads the verdict; the banner is the turn's.
    game = _game(
        cps=[_cp("A", Player.BLUE), _cp("B", Player.RED)],
        campaign_name=_hold_half_the_bases(),
    )
    assert victory_verdict(game, announce=False) == "win"
    assert game.messages == []
    assert not getattr(game, "victory_announced", None)
    assert victory_verdict(game) == "win"
    assert len(game.messages) == 1


def test_loss_takes_precedence_over_a_simultaneous_win() -> None:
    authored = VictoryProfile(
        win_when=(VictoryCondition(capture_cps=("A",)),),
        lose_when=(VictoryCondition(lose_cps=("B",)),),
    )
    victory_mod._PROFILE_CACHE["Test Campaign"] = authored
    game = _game(
        cps=[_cp("A", Player.BLUE), _cp("B", Player.RED)],
        campaign_name="Test Campaign",
    )
    assert victory_verdict(game) == "loss"
    assert game.messages[0][0] == "Defeat condition met"


def test_verdict_uses_the_label_in_the_banner() -> None:
    authored = VictoryProfile(
        win_when=(VictoryCondition(label="Take the coast", capture_cps=("A",)),),
    )
    victory_mod._PROFILE_CACHE["Test Campaign"] = authored
    game = _game(cps=[_cp("A", Player.BLUE)], campaign_name="Test Campaign")
    assert victory_verdict(game) == "win"
    assert game.messages[0] == ("Victory condition met", "Take the coast")


# --- the real check_win_loss branch order ---------------------------------------------


def test_check_win_loss_wiring() -> None:
    # Drive the REAL Game.check_win_loss with a duck-typed self: the §75 branch
    # wins on an authored domination entry, and with nothing configured the stock
    # territory checks still rule.
    from game.game import Game, TurnState

    cps = [_cp("A", Player.BLUE), _cp("B", Player.RED)]
    game = _game(cps=cps, campaign_name=_hold_half_the_bases())
    game.theater.player_points = lambda state_check=False: [cps[0]]
    game.theater.enemy_points = lambda state_check=False: [cps[1]]
    assert Game.check_win_loss(cast(Any, game)) is TurnState.WIN

    quiet = _game(cps=cps)
    quiet.theater.player_points = lambda state_check=False: [cps[0]]
    quiet.theater.enemy_points = lambda state_check=False: [cps[1]]
    assert Game.check_win_loss(cast(Any, quiet)) is TurnState.CONTINUE


# --- surfacing ------------------------------------------------------------------------


def test_overview_rows_and_live_prose() -> None:
    authored = VictoryProfile(
        description="Test war",
        win_when=(VictoryCondition(enemy_air_below=0.1),),
        lose_when=(VictoryCondition(lose_cps=("B",)),),
    )
    victory_mod._PROFILE_CACHE["Test Campaign"] = authored
    game = _game(
        cps=[_cp("B", Player.BLUE)], red_air=(10,), campaign_name="Test Campaign"
    )
    rows = victory_overview(game)
    assert len(rows) == 2
    assert rows[0]["defeat"] is False
    assert rows[0]["met"] is False
    assert "Enemy air force below 10% of start (now 100%)" in str(rows[0]["text"])
    assert rows[1]["defeat"] is True
    assert "B falls to the enemy (0/1 fallen)" in str(rows[1]["text"])


def test_overview_empty_without_configuration() -> None:
    assert victory_overview(_game()) == []
    assert victory_sitrep_lines(_game()) == []


def test_describe_without_live_values() -> None:
    game = _game(cps=[_cp("A", Player.BLUE)])
    baseline = _baseline(game)
    text = describe_condition(
        game, VictoryCondition(capture_cps=("A",)), baseline, live=False
    )
    assert text == "Capture A"


def test_sitrep_lines_are_prefixed_and_capped() -> None:
    authored = VictoryProfile(
        win_when=(
            VictoryCondition(capture_cps=("A",)),
            VictoryCondition(enemy_air_below=0.1),
            VictoryCondition(enemy_ground_below=0.1),
            VictoryCondition(enemy_air_denied=True),
        ),
        lose_when=(VictoryCondition(lose_cps=("B",)),),
    )
    victory_mod._PROFILE_CACHE["Test Campaign"] = authored
    game = _game(
        cps=[_cp("A", Player.BLUE), _cp("B", Player.RED)],
        campaign_name="Test Campaign",
    )
    lines = victory_sitrep_lines(game)
    assert len(lines) == 5
    assert lines[0].startswith("Victory: ")
    assert lines[-1] == "(+1 more conditions)"


# --- Invert Sides ---------------------------------------------------------------------
# A block is written for the campaign's own blue side. Started inverted, that side is
# the game's red: "take Stanley" is the player's defeat, not a turn-one win.


def _inverted_war() -> Any:
    victory_mod._PROFILE_CACHE["Test Campaign"] = VictoryProfile(
        description="Retake the islands",
        win_when=(VictoryCondition(label="Stanley falls", capture_cps=("Stanley",)),),
        lose_when=(VictoryCondition(lose_cps=("San Carlos",)),),
    )
    # The author's blue (the UK) holds San Carlos; in an inverted game that is red.
    game = _game(
        cps=[_cp("Stanley", Player.BLUE), _cp("San Carlos", Player.RED)],
        campaign_name="Test Campaign",
    )
    game.sides_inverted = True
    return game


def test_an_inverted_game_does_not_end_on_its_first_turn() -> None:
    assert victory_verdict(_inverted_war()) is None


def test_inverted_the_authors_loss_is_the_players_win() -> None:
    game = _inverted_war()
    game.theater.controlpoints[1].captured = Player.BLUE  # the player takes San Carlos
    assert victory_verdict(game) == "win"


def test_inverted_the_authors_win_is_the_players_loss() -> None:
    game = _inverted_war()
    game.theater.controlpoints[0].captured = Player.RED  # the enemy takes Stanley
    assert victory_verdict(game) == "loss"
    # The banner speaks for the player, not with the author's label.
    assert game.messages[0] == ("Defeat condition met", "The enemy takes Stanley")


def test_inverted_strength_ratios_read_the_other_side() -> None:
    game = _game(red_air=(10,), blue_air=(10,))
    game.sides_inverted = True
    baseline = _baseline(game)
    cond = VictoryCondition(enemy_air_below=0.5)
    # The author's enemy is the game's blue: red losses do not count.
    game.air_wing_for(Player.RED).iter_squadrons()[0].owned_aircraft = 1
    assert not condition_met(game, cond, baseline)
    game.air_wing_for(Player.BLUE).iter_squadrons()[0].owned_aircraft = 1
    assert condition_met(game, cond, baseline)


def test_inverted_categories_and_air_denial_read_blue_ground() -> None:
    blue_cp = _cp("Home", Player.BLUE, operational=False)
    game = _game(cps=[blue_cp], tgos=[_tgo("Comms", "comms", blue_cp, True)])
    game.sides_inverted = True
    baseline = _baseline(game)
    assert baseline.blue_categories == {"comms": 1}
    cond = VictoryCondition(destroy_categories=("comms",))
    assert not condition_met(game, cond, baseline)
    game.theater.ground_objects[0].units[0].alive = False
    assert condition_met(game, cond, baseline)
    assert condition_met(game, VictoryCondition(enemy_air_denied=True), baseline)


def test_inverted_overview_mirrors_rows_and_drops_the_authors_words() -> None:
    game = _inverted_war()
    rows = victory_overview(game)
    assert [row["defeat"] for row in rows] == [False, True]
    assert rows[0]["text"] == "Capture San Carlos (0/1 taken)"
    assert rows[1]["text"] == "The enemy takes Stanley (0/1 fallen)"
    assert victory_mod.victory_description(game) is None
    assert victory_mod.victory_description(_game(campaign_name="Test Campaign")) == (
        "Retake the islands"
    )
