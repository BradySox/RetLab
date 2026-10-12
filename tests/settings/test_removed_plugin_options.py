"""A removed plugin's saved options are dropped when an old save loads."""

from __future__ import annotations

import pytest

from game.settings import Settings


@pytest.mark.parametrize("plugin", ["aisleep", "bmstrike"])
def test_a_save_with_a_removed_plugin_ticked_sheds_its_keys(plugin: str) -> None:
    state = dict(Settings().__dict__)
    state["plugins"] = {**state["plugins"], plugin: True, f"{plugin}.someOption": 3}

    settings = Settings()
    settings.__setstate__(state)

    assert not [key for key in settings.plugins if key.split(".")[0] == plugin]
