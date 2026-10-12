"""The convoy ambush (§50) was removed 2026-10-11; old saves must shed it.

A save from before the removal can hold hidden red ambush teams on a blue supply
road. Nothing sweeps them and nothing hides them any more, so a team left in the
save would stand there as an ordinary red group.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from game.migrator import Migrator
from game.settings import Settings
from game.settings.migration import migrate_legacy_settings


def _migrator(game: Any) -> Migrator:
    migrator = Migrator.__new__(Migrator)
    migrator.game = game
    return migrator


def _game(control_point: Any, state: Any, removed: list[str]) -> Any:
    game = SimpleNamespace(
        theater=SimpleNamespace(controlpoints=[control_point]),
        db=SimpleNamespace(tgos=SimpleNamespace(remove=removed.append)),
    )
    if state is not None:
        game.convoy_ambush_state = state
    return game


def test_an_old_saves_ambush_teams_are_deleted_on_load() -> None:
    hidden = SimpleNamespace(id="team-1", name="HAMSTER", map_hidden=True)
    # Sold through the ground object menu: an empty shell the state still lists.
    listed = SimpleNamespace(id="team-2", name="PELICAN")
    keeper = SimpleNamespace(id="sam-1", name="GERBIL", map_hidden=False)
    cp = SimpleNamespace(connected_objectives=[hidden, listed, keeper])
    removed: list[str] = []
    game = _game(
        cp, {"ambushes": [{"tgo_id": "team-2", "convoy": "Convoy 001"}]}, removed
    )

    _migrator(game)._remove_convoy_ambush_teams()

    assert cp.connected_objectives == [keeper]
    assert removed == ["team-1", "team-2"]
    assert not hasattr(game, "convoy_ambush_state")
    assert "map_hidden" not in vars(keeper)


def test_a_save_with_no_ambush_state_loads_untouched() -> None:
    keeper = SimpleNamespace(id="sam-1", name="GERBIL")
    cp = SimpleNamespace(connected_objectives=[keeper])
    removed: list[str] = []

    _migrator(_game(cp, None, removed))._remove_convoy_ambush_teams()

    assert cp.connected_objectives == [keeper]
    assert removed == []


def test_a_team_missing_from_the_database_does_not_stop_the_load() -> None:
    hidden = SimpleNamespace(id="team-1", name="HAMSTER", map_hidden=True)
    cp = SimpleNamespace(connected_objectives=[hidden])

    def missing(tgo_id: str) -> None:
        raise KeyError(tgo_id)

    game = SimpleNamespace(
        theater=SimpleNamespace(controlpoints=[cp]),
        db=SimpleNamespace(tgos=SimpleNamespace(remove=missing)),
    )

    _migrator(game)._remove_convoy_ambush_teams()

    assert cp.connected_objectives == []


def test_the_setting_is_gone_and_an_old_save_sheds_its_key() -> None:
    assert not hasattr(Settings(), "convoy_ambush")
    assert "convoy_ambush" not in migrate_legacy_settings({"convoy_ambush": True})
