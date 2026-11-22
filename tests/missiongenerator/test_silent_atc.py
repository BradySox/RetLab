"""§132: the silent-tower script loads only while Silence AI ATC is on."""

from __future__ import annotations

from types import SimpleNamespace as NS
from typing import Any, cast

from dcs import Mission
from dcs.action import DoScriptFile

from game.missiongenerator.luagenerator import LuaGenerator
from game.settings import Settings


def _triggers(silence: bool) -> list[Any]:
    mission = Mission()
    game = NS(settings=NS(silence_ai_atc=silence))
    LuaGenerator(cast(Any, game), mission, cast(Any, NS()))._inject_silent_atc()
    return list(mission.triggerrules.triggers)


def test_on_loads_the_script_at_mission_start() -> None:
    triggers = _triggers(True)
    assert len(triggers) == 1
    assert triggers[0].comment == "Silence AI ATC"
    assert isinstance(triggers[0].actions[0], DoScriptFile)


def test_off_loads_nothing() -> None:
    assert _triggers(False) == []


def test_on_by_default() -> None:
    assert Settings().silence_ai_atc is True
