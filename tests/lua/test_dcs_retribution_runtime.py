"""Headless runtime check for the base plugin's ejection bookkeeping.

`ejection_events` is how a downed pilot reaches the campaign: the ejection
records the aircraft's position, and the parachute landing that follows refines
it to where the pilot actually came down. The landing carries no unit name, so it
has to be matched back to an ejection.

The match used to be "the most recent ejection without a landing". DCS fires one
landing per crew member, so a two-seat crew touching down wrote its second
landing onto whichever other survivor had none -- test 30 (2026-09-13, Persian
Gulf) recorded an AV-8B pilot who came down in the Strait of Hormuz as landed
170 km away beside an F-4E's crash. The landing is now matched to the nearest
open ejection within `LANDING_MATCH_M`, and a landing that matches nothing is
dropped.

The script's file-scope side effects (MIST logger, state-file discovery, the
event registration) run against the stubs below; nothing here models DCS.
"""

from __future__ import annotations

from typing import Any

from tests.lua.harness import DcsPluginHarness

PLUGIN = "resources/plugins/base/dcs_retribution.lua"

# What dcs_retribution.lua touches at file scope beyond the harness's DCS surface:
# MIST's logger/scheduler/event registration, the json library, and the state-file
# path probe. `os`/`lfs` are removed so the probe finds no folder and never opens
# a file on the developer's machine.
_PRELUDE = """
os = nil
lfs = nil
json = { encode = function(_, t) return "{}" end }
mist = {
    Logger = { new = function() return {
        info = function() end, warn = function() end, error = function() end,
    } end },
    message = { add = function() end },
    scheduleFunction = function() end,
    addEventHandler = function(fn)
        world.addEventHandler({ onEvent = function(_, e) return fn(e) end })
    end,
    getHeading = function() return 0 end,
    DBs = {},
}
"""


def _load() -> DcsPluginHarness:
    harness = DcsPluginHarness()
    harness.lua.execute(_PRELUDE)
    harness.load_plugin_script(PLUGIN)
    harness.assert_no_lua_errors()
    return harness


def _eject(harness: DcsPluginHarness, unit: str, x: float, z: float) -> None:
    initiator = harness.lua.eval(
        "function(n, x, z) return {"
        "  getName = function(self) return n end,"
        "  getPosition = function(self) return { p = { x = x, y = 0, z = z } } end,"
        "} end"
    )(unit, x, z)
    harness.fire_event({"id": 6, "initiator": initiator})
    harness.assert_no_lua_errors()


def _land(harness: DcsPluginHarness, x: float, z: float) -> None:
    initiator = harness.lua.eval(
        "function(x, z) return {"
        "  getPoint = function(self) return { x = x, y = 0, z = z } end,"
        "} end"
    )(x, z)
    harness.fire_event({"id": 31, "initiator": initiator})
    harness.assert_no_lua_errors()


def _ejections(harness: DcsPluginHarness) -> dict[str, dict[str, Any]]:
    raw = harness.to_python(harness.lua.eval("ejection_events"))
    assert isinstance(raw, list)
    return {str(e["unit"]): e for e in raw}


def test_the_script_loads_without_erroring() -> None:
    harness = _load()
    assert harness.to_python(harness.lua.eval("LANDING_MATCH_M")) == 20000


def test_a_landing_refines_the_ejection_it_is_nearest_to() -> None:
    harness = _load()
    _eject(harness, "Harrier-1", 0.0, 0.0)
    _eject(harness, "Harrier-2", 1800.0, 0.0)

    # The lead's chute comes down first, closer to the lead's ejection point
    # than to the wingman's, even though the wingman ejected last.
    _land(harness, 300.0, -100.0)

    events = _ejections(harness)
    assert events["Harrier-1"]["landed"] is True
    assert events["Harrier-1"]["x"] == 300.0
    assert events["Harrier-1"]["z"] == -100.0
    assert "landed" not in events["Harrier-2"]
    assert events["Harrier-2"]["x"] == 1800.0


def test_a_second_crew_member_landing_does_not_move_another_survivor() -> None:
    harness = _load()
    _eject(harness, "Harrier-4", -60040.0, 159481.0)
    _eject(harness, "Phantom-1", 110519.0, 120.0)

    # Both Phantom crew land beside the Phantom's crash. The second landing has
    # no open ejection within reach and must not be written onto the Harrier.
    _land(harness, 110433.0, -161.0)
    _land(harness, 110389.0, -76.0)

    events = _ejections(harness)
    assert events["Phantom-1"]["landed"] is True
    assert events["Phantom-1"]["x"] == 110433.0
    assert "landed" not in events["Harrier-4"]
    assert events["Harrier-4"]["x"] == -60040.0
    assert events["Harrier-4"]["z"] == 159481.0


def test_a_landing_with_no_ejection_in_reach_is_dropped() -> None:
    harness = _load()
    _eject(harness, "Hornet-1", 0.0, 0.0)

    _land(harness, 50000.0, 0.0)

    events = _ejections(harness)
    assert "landed" not in events["Hornet-1"]
    assert events["Hornet-1"]["x"] == 0.0


def test_an_ejection_without_a_position_never_claims_a_landing() -> None:
    harness = _load()
    initiator = harness.lua.eval(
        "function() return { getName = function(self) return 'Blind-1' end } end"
    )()
    harness.fire_event({"id": 6, "initiator": initiator})
    harness.assert_no_lua_errors()
    _eject(harness, "Hornet-1", 500.0, 500.0)

    _land(harness, 600.0, 400.0)

    events = _ejections(harness)
    assert "x" not in events["Blind-1"]
    assert "landed" not in events["Blind-1"]
    assert events["Hornet-1"]["landed"] is True


def _crash(harness: DcsPluginHarness, unit: str, x: float, z: float) -> None:
    initiator = harness.lua.eval(
        "function(n, x, z) return {"
        "  getName = function(self) return n end,"
        "  getPoint = function(self) return { x = x, y = 0, z = z } end,"
        "} end"
    )(unit, x, z)
    harness.fire_event({"id": 5, "initiator": initiator})
    harness.assert_no_lua_errors()


def test_a_crash_records_where_the_aircraft_came_down() -> None:
    # A survivor with no ejection is placed here, not at his package's target
    # (test 39: nine survivors 23-42 km from their jets).
    harness = _load()
    _crash(harness, "Eagle 1-2", -73158.0, -322203.0)
    raw = harness.to_python(harness.lua.eval("crash_positions"))
    assert raw == [{"unit": "Eagle 1-2", "x": -73158.0, "z": -322203.0}]
    assert harness.to_python(harness.lua.eval("crash_events")) == ["Eagle 1-2"]


def _unit(harness: DcsPluginHarness, name: Any, type_name: str = "") -> Any:
    return harness.lua.eval(
        "function(n, t) return {"
        "  getName = function(self) return n end,"
        "  getTypeName = function(self) return t end,"
        "  getCoalition = function(self) return 1 end,"
        "} end"
    )(name, type_name)


def _kill(harness: DcsPluginHarness, killer: Any, target: Any, weapon: Any) -> None:
    event = {"id": 28, "initiator": killer, "target": target}
    if weapon is not None:
        event["weapon_name"] = weapon
    harness.fire_event(event)
    harness.assert_no_lua_errors()


def test_a_kill_records_who_did_it_and_with_what() -> None:
    harness = _load()
    killer = _unit(harness, "Viper 1-1", "F-16C_50")
    _kill(harness, killer, _unit(harness, "Flanker 2-1", "Su-27"), "AIM-120C")
    causes = harness.to_python(harness.lua.eval("kill_causes"))
    assert causes == [
        {
            "target": "Flanker 2-1",
            "killer": "Viper 1-1",
            "killer_type": "F-16C_50",
            "weapon": "AIM-120C",
        }
    ]
    # The victim is still recorded the way every loss channel records it.
    assert harness.to_python(harness.lua.eval("kill_events")) == ["Flanker 2-1"]


def test_a_kill_with_no_weapon_name_still_names_the_killer() -> None:
    harness = _load()
    _kill(
        harness,
        _unit(harness, "SA-10 #3", "S-300PS 5P85C ln"),
        _unit(harness, "Hornet 1-2"),
        None,
    )
    causes = harness.to_python(harness.lua.eval("kill_causes"))
    assert causes == [
        {
            "target": "Hornet 1-2",
            "killer": "SA-10 #3",
            "killer_type": "S-300PS 5P85C ln",
        }
    ]


def test_a_kill_by_something_with_no_name_is_not_given_a_cause() -> None:
    harness = _load()
    # Scenery reports a number for a name.
    _kill(harness, _unit(harness, 12345), _unit(harness, "Truck 4"), None)
    assert not harness.to_python(harness.lua.eval("kill_causes"))
    assert harness.to_python(harness.lua.eval("kill_events")) == ["Truck 4"]


# --- base capture ignores downed pilots ----------------------------------------

_BLUE, _RED, _GROUND = 2, 1, 2


def _infantry(harness: DcsPluginHarness, name: str, side: int, x: float) -> None:
    harness.add_group(
        {
            "name": name,
            "side": side,
            "category": _GROUND,
            "units": [{"name": f"{name}-1", "type": "Soldier M4", "x": x, "z": 0.0}],
        }
    )


def _taken(harness: DcsPluginHarness, capturing: int, losing: int) -> bool:
    fn = harness.lua.eval("capture_zone_taken")
    return bool(fn(0.0, 0.0, 3000.0, capturing, losing))


def test_a_downed_pilot_does_not_capture_an_empty_base() -> None:
    """Test 59: an ejected F-15E crew landed inside empty Gazipasa and took it."""
    harness = _load()
    _infantry(harness, "CSAR Lt Smith 1a2b3c4d", _BLUE, 2000.0)
    _infantry(harness, "Pilot 260.00kHz-42#001", _BLUE, 1000.0)
    assert _taken(harness, _BLUE, _RED) is False
    harness.assert_no_lua_errors()


def test_ground_troops_capture_an_empty_base() -> None:
    harness = _load()
    _infantry(harness, "Armor 1", _BLUE, 2500.0)
    assert _taken(harness, _BLUE, _RED) is True


def test_a_downed_defender_does_not_hold_a_base() -> None:
    harness = _load()
    _infantry(harness, "Armor 1", _BLUE, 2500.0)
    _infantry(harness, "CSAR Kpt Ivanov 5e6f7a8b", _RED, 100.0)
    assert _taken(harness, _BLUE, _RED) is True


def test_a_live_defender_holds_a_base() -> None:
    harness = _load()
    _infantry(harness, "Armor 1", _BLUE, 2500.0)
    _infantry(harness, "Garrison 1", _RED, 100.0)
    assert _taken(harness, _BLUE, _RED) is False


def test_troops_outside_the_zone_capture_nothing() -> None:
    harness = _load()
    _infantry(harness, "Armor 1", _BLUE, 3500.0)
    assert _taken(harness, _BLUE, _RED) is False
