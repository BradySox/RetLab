"""The base-capture trigger leaves downed pilots out of both zone checks.

DCS's own zone conditions count any ground unit, and a downed pilot is an
infantry group: on test 59 an ejected F-15E crew captured an empty Gazipasa.
The trigger now ends with a Lua predicate (dcs_retribution.lua
``capture_zone_taken``) that repeats the checks without them.
"""

from __future__ import annotations

from types import SimpleNamespace

from dcs.condition import Condition, PartOfCoalitionInZone, Predicate

from game.missiongenerator.triggergenerator import TriggerGenerator
from game.theater.controlpoint import TRIGGER_RADIUS_CAPTURE


def _trigger() -> object:
    cp = SimpleNamespace(
        id="cp-1",
        full_name="Gazipasa",
        position=SimpleNamespace(x=158145.0, y=-319393.0),
    )
    return TriggerGenerator._create_capture_trigger(
        None,  # type: ignore[arg-type]  # the method reads nothing from self
        trigger_zone_id=5,
        flag=12,
        capturing_coalition="blue",
        losing_coalition="red",
        capturing_coalition_int=2,
        cp=cp,  # type: ignore[arg-type]
    )


def test_the_lua_check_runs_last() -> None:
    rules = _trigger().rules  # type: ignore[attr-defined]
    assert isinstance(rules[0], PartOfCoalitionInZone)
    assert isinstance(rules[-1], Predicate)


def test_the_predicate_passes_the_zone_and_both_sides() -> None:
    predicate = _trigger().rules[-1]  # type: ignore[attr-defined]
    # Untranslated, so the Lua is the String's key; DCS's getValueDictByKey
    # returns the key itself, as for the capture DoScript.
    lua = predicate.text.id
    assert "capture_zone_taken(158145.0, -319393.0, " in lua
    assert f", {TRIGGER_RADIUS_CAPTURE}, " in lua
    assert "coalition.side.BLUE, coalition.side.RED)" in lua
    assert lua.startswith("return capture_zone_taken ~= nil and ")


def test_the_conditions_compile_to_one_and_chain() -> None:
    compiled = Condition.condition_str(_trigger().rules)  # type: ignore[attr-defined]
    assert " or " not in compiled
    assert compiled.index("c_part_of_coalition_in_zone") < compiled.index("c_predicate")
