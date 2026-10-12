"""Five options were removed 2026-10-12; old saves must shed them.

QRA radio callouts, cosmetic base battle damage, the planner's automatic recon
flight, the two generic victory sliders and package code words. None was on in
the DM's default settings or in any of his saves.
"""

from __future__ import annotations

import io
from typing import Any

import pytest

from game.coalition import Coalition
from game.persistency import REMOVED_MODULES, DummyObject, MigrationUnpickler
from game.settings import Settings
from game.settings.migration import migrate_legacy_settings

REMOVED_SETTINGS = (
    "qra_comms_enabled",
    "base_battle_damage",
    "auto_add_tarps_recon",
    "alternate_victory_domination",
    "alternate_victory_attrition",
    "enable_package_code_words",
)


@pytest.mark.parametrize("name", REMOVED_SETTINGS)
def test_the_setting_is_gone_and_an_old_save_sheds_its_key(name: str) -> None:
    assert not hasattr(Settings(), name)
    assert name not in migrate_legacy_settings({name: True})


def test_a_saved_code_word_table_resolves_to_a_placeholder() -> None:
    """`Coalition._code_words` held a `MissionCodeWords` in a save that used them."""
    assert "game.ato.codewords" in REMOVED_MODULES
    unpickler = MigrationUnpickler(io.BytesIO(b""))

    assert unpickler.find_class("game.ato.codewords", "MissionCodeWords") is DummyObject
    assert unpickler.find_class("game.ato.codewords", "PushCategory") is DummyObject


def test_a_coalition_drops_its_saved_code_word_table() -> None:
    """A placeholder left on the coalition would be a crash at first use."""

    class _Stop(Exception):
        pass

    class _State(dict[str, Any]):
        """Stops the load right after the code word keys are handled."""

        def setdefault(self, key: str, default: Any = None) -> Any:
            if key == "bullseye_pinned":
                raise _Stop
            return super().setdefault(key, default)

    state = _State(player=True, _code_words=DummyObject(), _code_words_turn=3)
    coalition = object.__new__(Coalition)

    with pytest.raises(_Stop):
        coalition.__setstate__(state)

    assert "_code_words" not in state
    assert "_code_words_turn" not in state
