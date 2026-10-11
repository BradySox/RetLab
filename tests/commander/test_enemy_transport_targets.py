"""The planner's convoy and cargo-ship targets are the enemy's, not its own."""

from types import SimpleNamespace
from typing import Any

from game.commander.objectivefinder import ObjectiveFinder
from game.theater.player import Player


def _game(red_base: Any) -> Any:
    def coalition_for(player: Player) -> Any:
        mine = ["red transport"] if player.is_red else ["blue transport"]
        travelling = SimpleNamespace(
            travelling_to=lambda cp: list(mine) if cp is red_base else []
        )
        return SimpleNamespace(
            transfers=SimpleNamespace(convoys=travelling, cargo_ships=travelling)
        )

    front_line = SimpleNamespace(control_point_hostile_to=lambda _player: red_base)
    return SimpleNamespace(
        settings=SimpleNamespace(
            perf_disable_convoys=False, perf_disable_cargo_ships=False
        ),
        theater=SimpleNamespace(conflicts=lambda: [front_line]),
        coalition_for=coalition_for,
    )


def test_blue_planner_sees_red_transports_heading_for_reds_front_base() -> None:
    game = _game(red_base=SimpleNamespace(name="Red forward base"))
    finder = ObjectiveFinder(game, Player.BLUE)
    assert list(finder.convoys()) == ["red transport"]
    assert list(finder.cargo_ships()) == ["red transport"]


def test_disabled_transports_are_not_targets() -> None:
    game = _game(red_base=SimpleNamespace(name="Red forward base"))
    finder = ObjectiveFinder(game, Player.BLUE)
    game.settings.perf_disable_convoys = True
    game.settings.perf_disable_cargo_ships = True
    assert list(finder.convoys()) == []
    assert list(finder.cargo_ships()) == []


def test_a_transport_bound_for_a_base_on_two_fronts_is_listed_once() -> None:
    """Each entry draws a package, so a repeat sent two at one convoy."""
    red_base = SimpleNamespace(name="Red forward base")
    game = _game(red_base=red_base)
    front_line = SimpleNamespace(control_point_hostile_to=lambda _player: red_base)
    game.theater.conflicts = lambda: [front_line, front_line]
    finder = ObjectiveFinder(game, Player.BLUE)
    assert list(finder.convoys()) == ["red transport"]
    assert list(finder.cargo_ships()) == ["red transport"]
