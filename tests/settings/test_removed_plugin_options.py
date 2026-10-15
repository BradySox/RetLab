"""A removed plugin's or option's saved value is dropped when an old save loads."""

from __future__ import annotations

import pytest

from game.settings import Settings


def _load(plugins: dict[str, object]) -> Settings:
    state = dict(Settings().__dict__)
    state["plugins"] = {**state["plugins"], **plugins}
    settings = Settings()
    settings.__setstate__(state)
    return settings


@pytest.mark.parametrize("plugin", ["aisleep", "bmstrike", "mantisiads", "tic"])
def test_a_save_with_a_removed_plugin_ticked_sheds_its_keys(plugin: str) -> None:
    settings = _load({plugin: True, f"{plugin}.someOption": 3})

    assert not [key for key in settings.plugins if key.split(".")[0] == plugin]


def test_a_removed_option_of_a_live_plugin_is_dropped() -> None:
    settings = _load({"skynetiads.includeRedInRadio": True})

    assert "skynetiads.includeRedInRadio" not in settings.plugins
    assert settings.plugins["skynetiads.radioMenuRed"] is False


def test_live_plugin_values_survive_the_sweep() -> None:
    settings = _load({"ctld": False, "ctld.smoke": False})

    assert settings.plugins["ctld"] is False
    assert settings.plugins["ctld.smoke"] is False
