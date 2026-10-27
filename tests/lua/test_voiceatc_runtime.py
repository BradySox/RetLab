"""Headless runtime checks for the voiceatc plugin (voiceatc-config.lua, §119).

The contract: SkyEye passes each call heard on a field's Ground or Tower frequency;
the plugin answers on that frequency in that position's voice, with no on-screen
text (text only without LuaSocket). Military calls (no squawk): altimeter with taxi, wind and
the frequency change with takeoff, report initial inbound, cleared to land at base with the gear
down; a strict readback missing
an item gets "readback incomplete"; a rule bust gets one scolding call. How SkyEye
hears and says it is in-game only (B261).
"""

from __future__ import annotations

import json
from typing import Any

from tests.lua.harness import DcsPluginHarness

PLUGIN = "resources/plugins/voiceatc/voiceatc-config.lua"
BLUE = 2
NM = 1852
GROUND = "260.000AM"
TOWER = "262.000AM"

FAKE_AIRBASE = """
Airbase = Airbase or {}
Airbase.getByName = function(name)
    return { getPoint = function() return { x = 0, y = 10, z = 0 } end }
end
"""

# A LuaSocket stand-in: sendto() is recorded, receivefrom() pops INBOX.
FAKE_SOCKET = """
SENT = {}
INBOX = {}
package.preload["socket"] = function()
    return {
        udp = function()
            return {
                settimeout = function() end,
                setsockname = function() end,
                sendto = function(self, msg, host, port)
                    table.insert(SENT, { msg = msg, host = host, port = port })
                end,
                receivefrom = function(self)
                    return table.remove(INBOX, 1)
                end,
            }
        end,
    }
end
"""


def _config() -> dict[str, Any]:
    return {
        "voiceAtc": {
            "linkHost": "127.0.0.1",
            "linkPort": "42690",
            "fields": [
                {
                    "name": "Kobuleti",
                    "airbase": "Kobuleti",
                    "runway": "25",
                    "runways": "07,25",
                    "altimeter": "29.92",
                    "ground": GROUND,
                    "tower": TOWER,
                    "groundVoice": "en_US-ryan-medium",
                    "towerVoice": "en_US-amy-medium",
                }
            ],
            "flights": [
                {
                    "group": "Viper",
                    "callsign": "Viper 1-1",
                    "departure": "Kobuleti",
                    "arrival": "Kobuleti",
                }
            ],
        }
    }


def _viper(airborne: bool = False, x: float = 0, ships: int = 1) -> dict[str, Any]:
    return {
        "name": "Viper",
        "id": 77,
        "side": BLUE,
        "category": 0,
        "units": [
            {
                "name": f"Viper #{i}",
                "type": "F-16C_50",
                "x": x,
                "z": 0,
                "airborne": airborne,
                "playerName": f"Flash{i}",
            }
            for i in range(1, ships + 1)
        ],
    }


def _harness(
    discipline: str = "strict",
    airborne: bool = False,
    x: float = 0,
    ships: int = 1,
    link: bool = True,
) -> DcsPluginHarness:
    h = DcsPluginHarness()
    h.lua.execute(FAKE_AIRBASE)
    if link:
        h.lua.execute(FAKE_SOCKET)
    h.lua.globals().dcsRetribution = h.to_lua(
        {"plugins": {}, "radioDiscipline": discipline, **_config()}
    )
    h.add_group(_viper(airborne, x, ships))
    h.load_plugin_script(PLUGIN)
    return h


def _sent(h: DcsPluginHarness) -> list[dict[str, Any]]:
    sent = h.to_python(h.lua.globals().SENT)
    return [json.loads(s["msg"]) for s in sent] if isinstance(sent, list) else []


def _said(h: DcsPluginHarness) -> list[dict[str, Any]]:
    return [m for m in _sent(h) if m["type"] == "say"]


def _texts(h: DcsPluginHarness) -> list[str]:
    # A spoken call is never on-screen text too.
    assert h.records("texts") == []
    return [m["text"] for m in _said(h)]


def _call(
    h: DcsPluginHarness,
    kind: str,
    frequency: str = GROUND,
    callsign: str = "viper 1 1",
    numbers: str = "",
    text: str = "",
    detail: str = "",
) -> None:
    message = json.dumps(
        {
            "type": "atcRequest",
            "kind": kind,
            "callsign": callsign,
            "numbers": numbers,
            "text": text,
            "detail": detail,
            "frequency": frequency,
        }
    )
    h.lua.execute(f"table.insert(INBOX, {json.dumps(message)})")


def _event(h: DcsPluginHarness, event_id: int, ship: int = 1) -> None:
    h.lua.execute(
        "DcsHarness.fireEvent({ id = %d, initiator = Group.getByName('Viper'):getUnit(%d) })"
        % (event_id, ship)
    )


def test_no_node_is_a_clean_noop() -> None:
    h = DcsPluginHarness()
    h.set_retribution_config()
    h.load_plugin_script(PLUGIN)
    h.advance_to(100)
    h.assert_no_lua_errors()


def test_skyeye_is_told_the_field_frequencies() -> None:
    h = _harness()
    h.advance_to(2)
    atc = [m for m in _sent(h) if m["type"] == "atc"][0]
    assert atc["fields"] == [
        {
            "name": "Kobuleti",
            "positions": [
                {"position": "ground", "frequency": GROUND},
                {"position": "tower", "frequency": TOWER},
            ],
        }
    ]
    h.assert_no_lua_errors()


def test_a_sortie_from_taxi_to_parking() -> None:
    h = _harness()
    _call(h, "taxi")
    _call(h, "readback", numbers="25", text="hold short 2 5 viper 1 1")
    _call(h, "ready", TOWER)
    _call(h, "readback", TOWER, numbers="25")
    h.advance_to(2)
    assert _texts(h) == [
        "Viper 1-1, runway 25, altimeter 29.92, taxi, hold short runway 25, contact Tower 262.0.",
        "Viper 1-1, runway 25, cleared for takeoff, frequency change approved.",
    ]
    said = _said(h)
    assert [m["frequency"] for m in said] == [GROUND, TOWER]
    assert [m["voice"] for m in said] == ["en_US-ryan-medium", "en_US-amy-medium"]
    assert [m["speaker"] for m in said] == ["Kobuleti Ground", "Kobuleti Tower"]
    assert said[0]["speech"] == (
        "Viper one one, runway two five, altimeter two niner niner two, taxi, "
        "hold short runway two five, contact Tower two six two decimal zero."
    )

    _event(h, 3)
    h.update_unit("Viper", {"airborne": True, "x": 10 * NM})
    _call(h, "inbound", TOWER, numbers="10", text="viper 1 1 10 miles full stop")
    _call(h, "inbound", TOWER, detail="initial")
    h.update_unit("Viper", {"x": 2 * NM})
    _call(h, "inbound", TOWER, detail="geardown")
    _call(h, "readback", TOWER, numbers="25")
    h.advance_to(4)
    assert _texts(h)[2:] == [
        "Viper 1-1, runway 25, report initial.",
        "Viper 1-1, roger.",
        "Viper 1-1, runway 25, cleared to land.",
    ]
    h.update_unit("Viper", {"airborne": False, "x": 0})
    _event(h, 4)
    h.advance_to(6)
    assert _texts(h)[5:] == ["Viper 1-1, clear the runway, taxi to parking."]
    h.assert_no_lua_errors()


def test_a_strict_readback_missing_an_item_is_incomplete() -> None:
    h = _harness()
    _call(h, "taxi")
    _call(h, "readback", text="viper 1 1")
    _call(h, "readback", numbers="25")
    h.advance_to(2)
    assert _texts(h)[1:] == ["Viper 1-1, readback incomplete, hold short runway 25."]
    assert _said(h)[1]["speech"] == (
        "Viper one one, readback incomplete, hold short runway two five."
    )
    h.assert_no_lua_errors()


def test_no_squawk_is_given_or_needed_but_one_read_back_is_fine() -> None:
    # User call, 2026-10-22: no squawk codes. A pilot who still says one is not corrected.
    for discipline in ("strict", "relaxed"):
        h = _harness(discipline=discipline)
        _call(h, "taxi")
        _call(h, "readback", numbers="4101 25", text="squawk 4 1 0 1 hold short 2 5")
        h.advance_to(60)
        assert len(_texts(h)) == 1
        assert "squawk" not in _texts(h)[0].lower()
        assert "squawk" not in _said(h)[0]["speech"].lower()
        h.assert_no_lua_errors()


def test_relaxed_lets_an_item_go_but_corrects_a_wrong_number() -> None:
    h = _harness(discipline="relaxed")
    _call(h, "taxi")
    _call(h, "readback")
    _call(h, "taxi")
    _call(h, "readback", numbers="52")
    h.advance_to(2)
    assert _texts(h)[1:] == [
        _texts(h)[0],
        "Viper 1-1, negative, hold short runway 25.",
    ]
    h.assert_no_lua_errors()


def test_relaxed_and_casual_never_scold() -> None:
    for discipline in ("relaxed", "casual"):
        h = _harness(discipline=discipline)
        h.update_unit("Viper", {"velocity": {"x": 5, "y": 0, "z": 0}})
        h.advance_to(10)
        _event(h, 3)
        h.update_unit("Viper", {"velocity": {"x": 0, "y": 0, "z": 0}})
        _event(h, 4)
        h.advance_to(12)
        expected = (
            []
            if discipline == "casual"
            else ["Viper 1-1, clear the runway, taxi to parking."]
        )
        assert _texts(h) == expected, discipline
        h.assert_no_lua_errors()


def test_casual_takes_any_readback_and_answers_whoever_was_called() -> None:
    h = _harness(discipline="casual")
    _call(h, "taxi", TOWER)
    _call(h, "readback", TOWER, numbers="9999")
    h.advance_to(2)
    said = _said(h)
    assert [m["text"] for m in said] == [
        "Viper 1-1, runway 25, altimeter 29.92, taxi, hold short runway 25, contact Tower 262.0."
    ]
    assert said[0]["frequency"] == TOWER
    h.assert_no_lua_errors()


def test_casual_matches_a_misheard_or_missing_callsign() -> None:
    h = _harness(discipline="casual")
    _call(h, "radiocheck", callsign="cobra 1 1")
    _call(h, "radiocheck", callsign="")
    h.advance_to(2)
    assert _texts(h) == ["Viper 1-1, Kobuleti Ground, read you 5 by 5."] * 2
    h.assert_no_lua_errors()


def test_the_discipline_goes_to_skyeye() -> None:
    h = _harness(discipline="casual")
    h.advance_to(2)
    atc = [m for m in _sent(h) if m["type"] == "atc"][0]
    assert atc["discipline"] == "casual"
    h.assert_no_lua_errors()


def test_skyeye_is_told_the_player_flight_callsigns() -> None:
    h = _harness()
    h.advance_to(2)
    atc = [m for m in _sent(h) if m["type"] == "atc"][0]
    assert atc["callsigns"] == ["Viper 1-1"]
    h.assert_no_lua_errors()


def test_a_call_to_the_wrong_position_is_sent_to_the_right_one() -> None:
    h = _harness()
    _call(h, "taxi", TOWER)
    _call(h, "ready", GROUND)
    h.advance_to(2)
    assert _texts(h) == [
        "Viper 1-1, contact Ground 260.0.",
        "Viper 1-1, contact Tower 262.0.",
    ]
    h.assert_no_lua_errors()


def test_rule_busts_get_one_scolding_call_each() -> None:
    h = _harness()
    h.update_unit("Viper", {"velocity": {"x": 5, "y": 0, "z": 0}})
    h.advance_to(10)
    _event(h, 3)
    _event(h, 3)
    h.update_unit("Viper", {"airborne": False, "velocity": {"x": 0, "y": 0, "z": 0}})
    _event(h, 4)
    h.advance_to(12)
    assert _texts(h) == [
        "Viper 1-1, not cleared for taxi.",
        "Viper 1-1, you were not cleared for takeoff.",
        "Viper 1-1, you landed without clearance.",
        "Viper 1-1, clear the runway, taxi to parking.",
    ]
    h.assert_no_lua_errors()


def test_a_gear_down_call_far_out_is_answered_as_inbound() -> None:
    h = _harness(airborne=True, x=40 * NM)
    _call(h, "inbound", TOWER, detail="geardown")
    h.advance_to(2)
    assert _texts(h) == ["Viper 1-1, runway 25, report initial."]
    h.assert_no_lua_errors()


def test_inbound_is_never_a_landing_clearance() -> None:
    for detail in ("", "overhead"):
        h = _harness(airborne=True, x=4 * NM)
        _call(h, "inbound", TOWER, numbers="5", detail=detail)
        h.advance_to(30)
        # Not a clearance: no readback is asked for.
        assert _texts(h) == ["Viper 1-1, runway 25, report initial."], detail
        h.assert_no_lua_errors()


def test_a_straight_in_reports_3_mile_final() -> None:
    h = _harness(airborne=True, x=10 * NM)
    _call(h, "inbound", TOWER, detail="straightin")
    h.advance_to(2)
    assert _texts(h) == ["Viper 1-1, runway 25, make straight-in, report 3-mile final."]
    assert _said(h)[0]["speech"] == (
        "Viper one one, runway two five, make straight-in, report three-mile final."
    )
    h.assert_no_lua_errors()


def test_a_wingman_gets_their_own_landing_clearance() -> None:
    h = _harness(airborne=True, x=2 * NM, ships=2)
    _call(h, "inbound", TOWER, detail="geardown")
    _call(h, "inbound", TOWER, callsign="viper 1 2", detail="geardown")
    h.advance_to(2)
    assert _texts(h) == [
        "Viper 1-1, runway 25, cleared to land.",
        "Viper 1-2, runway 25, cleared to land.",
    ]
    h.assert_no_lua_errors()


def test_a_formation_is_cleared_to_land_as_a_flight() -> None:
    h = _harness(airborne=True, x=2 * NM, ships=2)
    _call(
        h, "inbound", TOWER, detail="geardown", text="viper 1 1 flight base gear down"
    )
    h.advance_to(2)
    assert _texts(h) == ["Viper 1-1 flight, runway 25, cleared to land."]
    assert _said(h)[0]["speech"].startswith("Viper one one flight, runway two five")
    h.update_unit("Viper", {"airborne": False, "x": 0})
    _event(h, 4, ship=2)
    h.advance_to(4)
    assert "landed without clearance" not in " ".join(_texts(h))
    h.assert_no_lua_errors()


def test_initial_is_rogered_or_asked_for_the_break_with_traffic() -> None:
    h = DcsPluginHarness()
    h.lua.execute(FAKE_AIRBASE)
    h.lua.execute(FAKE_SOCKET)
    config = _config()
    lead = dict(config["voiceAtc"]["flights"][0])
    config["voiceAtc"]["flights"].append(
        dict(lead, group="Cobra", callsign="Cobra 2-1")
    )
    h.lua.globals().dcsRetribution = h.to_lua({"plugins": {}, **config})
    h.add_group(_viper(airborne=True, x=5 * NM))
    cobra = _viper(airborne=True, x=8 * NM)
    cobra.update(name="Cobra", id=78)
    cobra["units"][0]["name"] = "Cobra #1"
    h.add_group(cobra)
    h.load_plugin_script(PLUGIN)
    _call(h, "inbound", TOWER, detail="initial")
    _call(h, "inbound", TOWER, callsign="cobra 2 1")
    _call(h, "inbound", TOWER, detail="initial")
    _call(h, "inbound", TOWER, detail="break")
    h.advance_to(2)
    assert _texts(h) == [
        "Viper 1-1, roger.",
        "Cobra 2-1, runway 25, report initial.",
        "Viper 1-1, report break.",
        "Viper 1-1, roger.",
    ]
    h.assert_no_lua_errors()


def test_the_flight_callsign_alone_is_the_lead() -> None:
    h = _harness()
    _call(h, "radiocheck", callsign="viper 1")
    h.advance_to(2)
    assert _texts(h) == ["Viper 1-1, Kobuleti Ground, read you 5 by 5."]
    h.assert_no_lua_errors()


def test_an_unknown_callsign_is_asked_again() -> None:
    h = _harness()
    _call(h, "taxi", callsign="cobra 2 1")
    h.advance_to(2)
    assert _texts(h) == ["Station calling Kobuleti Ground, say again your callsign."]
    h.assert_no_lua_errors()


def test_say_again_repeats_the_last_call_and_radio_check_answers() -> None:
    h = _harness()
    _call(h, "taxi")
    _call(h, "sayagain")
    _call(h, "radiocheck", TOWER)
    h.advance_to(2)
    assert _texts(h) == [
        "Viper 1-1, runway 25, altimeter 29.92, taxi, hold short runway 25, contact Tower 262.0.",
        "Viper 1-1, runway 25, altimeter 29.92, taxi, hold short runway 25, contact Tower 262.0.",
        "Viper 1-1, Kobuleti Tower, read you 5 by 5.",
    ]
    h.assert_no_lua_errors()


def test_a_mayday_is_cleared_to_land_any_runway() -> None:
    h = _harness(airborne=True, x=20 * NM)
    _call(h, "emergency", TOWER)
    h.advance_to(2)
    assert _texts(h) == ["Viper 1-1, cleared to land any runway."]
    h.assert_no_lua_errors()


def _menu(h: DcsPluginHarness, label: str) -> None:
    menus = h.lua.globals().DcsHarness.records.menus
    for i in range(1, len(menus) + 1):
        if menus[i].path == label:
            menus[i].fn(menus[i].arg)
            return
    raise AssertionError(f"no menu {label}")


def test_the_f10_menu_makes_the_same_requests() -> None:
    h = _harness()
    paths = [m["path"] for m in h.records("menus")]
    assert not any("engine start" in p for p in paths)
    assert paths[0] == "ATC"
    assert "Ground: request taxi" in paths and "Mayday" in paths
    _menu(h, "Ground: request taxi")
    _menu(h, "Read back")
    _menu(h, "Tower: holding short, ready")
    h.advance_to(2)
    assert _texts(h) == [
        "Viper 1-1, runway 25, altimeter 29.92, taxi, hold short runway 25, contact Tower 262.0.",
        "Viper 1-1, runway 25, cleared for takeoff, frequency change approved.",
    ]
    h.assert_no_lua_errors()


def test_without_luasocket_the_menu_answers_in_text() -> None:
    h = _harness(link=False)
    _menu(h, "Ground: request taxi")
    h.advance_to(10)
    assert [t["text"] for t in h.records("texts")] == [
        "Kobuleti Ground: Viper 1-1, runway 25, altimeter 29.92, taxi, "
        "hold short runway 25, contact Tower 262.0."
    ]
    h.assert_no_lua_errors()


def test_landing_at_the_divert_is_answered_by_its_tower() -> None:
    h = DcsPluginHarness()
    h.lua.execute(
        "Airbase = Airbase or {} "
        "Airbase.getByName = function(name) "
        "  local x = name == 'Batumi' and 50000 or 0 "
        "  return { getPoint = function() return { x = x, y = 10, z = 0 } end } "
        "end"
    )
    h.lua.execute(FAKE_SOCKET)
    config = _config()
    batumi = dict(config["voiceAtc"]["fields"][0], name="Batumi", airbase="Batumi")
    batumi.update(ground="126.000AM", tower="127.000AM")
    config["voiceAtc"]["fields"].append(batumi)
    config["voiceAtc"]["flights"][0]["divert"] = "Batumi"
    h.lua.globals().dcsRetribution = h.to_lua({"plugins": {}, **config})
    h.add_group(_viper(airborne=True, x=49000))
    h.load_plugin_script(PLUGIN)
    _call(h, "emergency", "127.000AM")
    h.advance_to(2)
    h.update_unit("Viper", {"airborne": False})
    _event(h, 4)
    h.advance_to(4)
    said = _said(h)
    assert [m["frequency"] for m in said] == ["127.000AM", "127.000AM"]
    assert said[-1]["text"] == "Viper 1-1, clear the runway, taxi to parking."
    h.assert_no_lua_errors()


def _ai_takeoff(h: DcsPluginHarness, name: str, x: float, heading: float) -> None:
    h.add_group(
        {
            "name": name,
            "id": sum(map(ord, name)),
            "side": BLUE,
            "category": 0,
            "units": [
                {
                    "name": name + " #1",
                    "type": "F-15C",
                    "x": x,
                    "z": 0,
                    "airborne": True,
                }
            ],
        }
    )
    h.lua.execute(
        "local u = Group.getByName('%s'):getUnit(1) "
        "u.getPosition = function(self) local r = math.rad(%f) "
        "return { x = { x = math.cos(r), y = 0, z = math.sin(r) } } end "
        "DcsHarness.fireEvent({ id = 3, initiator = u })" % (name, heading)
    )


def test_the_first_ai_takeoff_sets_the_runway_in_use() -> None:
    h = _harness()
    _ai_takeoff(h, "Eagle", 1000, 72)
    # A later AI on the other end does not flip it back and forth.
    _ai_takeoff(h, "Hawk", 1000, 252)
    _call(h, "ready", TOWER)
    h.advance_to(2)
    assert _texts(h) == [
        "Viper 1-1, runway 07, cleared for takeoff, frequency change approved."
    ]
    h.assert_no_lua_errors()


def test_an_ai_takeoff_elsewhere_changes_nothing() -> None:
    h = _harness()
    _ai_takeoff(h, "Eagle", 40 * NM, 72)
    _call(h, "ready", TOWER)
    h.advance_to(2)
    assert _texts(h) == [
        "Viper 1-1, runway 25, cleared for takeoff, frequency change approved."
    ]
    h.assert_no_lua_errors()


def test_the_briefed_strip_wins_between_parallels() -> None:
    h = DcsPluginHarness()
    h.lua.execute(FAKE_AIRBASE)
    h.lua.execute(FAKE_SOCKET)
    config = _config()
    config["voiceAtc"]["fields"][0].update(runway="28L", runways="10R,28L,10L,28R")
    h.lua.globals().dcsRetribution = h.to_lua({"plugins": {}, **config})
    h.add_group(_viper())
    h.load_plugin_script(PLUGIN)
    _ai_takeoff(h, "Eagle", 1000, 100)
    _call(h, "ready", TOWER)
    h.advance_to(2)
    assert _texts(h) == [
        "Viper 1-1, runway 10R, cleared for takeoff, frequency change approved."
    ]
    h.assert_no_lua_errors()


def test_startup_and_airborne_get_a_short_answer_not_say_again() -> None:
    h = _harness()
    _call(h, "startup")
    _call(h, "airborne", TOWER)
    h.advance_to(2)
    assert _texts(h) == [
        "Viper 1-1, start at your discretion. Call ready to taxi.",
        "Viper 1-1, frequency change approved.",
    ]
    h.assert_no_lua_errors()


def test_a_respawn_in_the_same_slot_is_a_new_sortie() -> None:
    h = _harness()
    h.update_unit("Viper", {"velocity": {"x": 5, "y": 0, "z": 0}})
    h.advance_to(4)
    _event(h, 3)
    h.update_unit("Viper", {"airborne": False, "velocity": {"x": 0, "y": 0, "z": 0}})
    _event(h, 4)
    h.advance_to(6)
    first = list(_texts(h))
    assert first[0] == "Viper 1-1, not cleared for taxi."
    _event(h, 15)
    h.update_unit("Viper", {"velocity": {"x": 5, "y": 0, "z": 0}})
    h.advance_to(10)
    assert _texts(h)[len(first) :] == ["Viper 1-1, not cleared for taxi."]
    h.assert_no_lua_errors()


def test_a_wingman_respawn_leaves_the_flight_sequence_alone() -> None:
    h = _harness(ships=2)
    _call(h, "taxi")
    h.advance_to(2)
    _event(h, 15, ship=2)
    h.update_unit("Viper", {"velocity": {"x": 5, "y": 0, "z": 0}})
    h.advance_to(6)
    assert "Viper 1-1, not cleared for taxi." not in _texts(h)
    h.assert_no_lua_errors()


def _menu_items(h: DcsPluginHarness, label: str) -> list[Any]:
    menus = h.lua.globals().DcsHarness.records.menus
    return [menus[i] for i in range(1, len(menus) + 1) if menus[i].path == label]


def test_the_f10_menu_speaks_for_a_lone_wingman() -> None:
    h = _harness(ships=2)
    h.lua.execute("Group.getByName('Viper'):getUnit(1).playerName = nil")
    item = _menu_items(h, "Ground: request taxi")[0]
    item.fn(item.arg)
    h.advance_to(2)
    assert _texts(h) == [
        "Viper 1-2, runway 25, altimeter 29.92, taxi, hold short runway 25, "
        "contact Tower 262.0."
    ]
    h.assert_no_lua_errors()


def test_a_ship_submenu_speaks_for_that_seat() -> None:
    h = _harness(airborne=True, x=2 * NM, ships=2)
    paths = [m["path"] for m in h.records("menus")]
    assert "Ship 2" in paths and "Ship 3" not in paths
    lead, ship2 = _menu_items(h, "Tower: base, gear down")
    lead.fn(lead.arg)
    ship2.fn(ship2.arg)
    h.advance_to(2)
    assert _texts(h) == [
        "Viper 1-1, runway 25, cleared to land.",
        "Viper 1-2, runway 25, cleared to land.",
    ]
    h.assert_no_lua_errors()


def test_a_three_digit_flight_number_is_its_own_flight() -> None:
    h = DcsPluginHarness()
    h.lua.execute(FAKE_AIRBASE)
    h.lua.execute(FAKE_SOCKET)
    config = _config()
    lead = dict(config["voiceAtc"]["flights"][0])
    config["voiceAtc"]["flights"] = [
        dict(lead, group="Short", callsign="Flight 12-1"),
        dict(lead, group="Long", callsign="Flight 123-1"),
    ]
    h.lua.globals().dcsRetribution = h.to_lua({"plugins": {}, **config})
    h.load_plugin_script(PLUGIN)
    _call(h, "radiocheck", callsign="flight 1 2 3")
    _call(h, "radiocheck", callsign="flight 1 2 3 2")
    _call(h, "radiocheck", callsign="flight 1 2 3 1")
    _call(h, "radiocheck", callsign="flight 1 2 2")
    h.advance_to(2)
    assert _texts(h) == [
        "Flight 123-1, Kobuleti Ground, read you 5 by 5.",
        "Flight 123-2, Kobuleti Ground, read you 5 by 5.",
        "Flight 123-1, Kobuleti Ground, read you 5 by 5.",
        "Flight 12-2, Kobuleti Ground, read you 5 by 5.",
    ]
    assert _said(h)[0]["speech"].startswith("Flight one two three one,")
    h.assert_no_lua_errors()


def test_strict_asks_once_for_a_readback_that_never_came() -> None:
    h = _harness()
    _call(h, "taxi")
    h.advance_to(15)
    assert len(_texts(h)) == 1
    h.advance_to(30)
    assert _texts(h)[1:] == ["Viper 1-1, read back."]
    assert _said(h)[1]["speech"] == "Viper one one, read back."
    assert _said(h)[1]["frequency"] == GROUND
    h.advance_to(80)
    assert len(_texts(h)) == 2
    h.assert_no_lua_errors()


def test_a_heard_readback_needs_no_prompt() -> None:
    h = _harness()
    _call(h, "taxi")
    _call(h, "readback", numbers="25")
    h.advance_to(60)
    assert len(_texts(h)) == 1
    h.assert_no_lua_errors()


def test_relaxed_never_prompts_for_a_readback() -> None:
    h = _harness("relaxed")
    _call(h, "taxi")
    h.advance_to(60)
    assert len(_texts(h)) == 1
    h.assert_no_lua_errors()


FAKE_WIND = """
atmosphere = { getWind = function(p) return { x = -2.6, y = 0, z = 0 } end }
"""


def test_formation_taxi_and_takeoff_with_the_numbers() -> None:
    h = _harness(ships=2)
    h.lua.execute(FAKE_WIND)
    _call(
        h, "taxi", detail="numbers", text="viper 1 1 flight of 2 have the numbers taxi"
    )
    _call(h, "ready", TOWER)
    h.advance_to(2)
    assert _texts(h) == [
        "Viper 1-1 flight, runway 25, taxi, hold short runway 25, contact Tower 262.0.",
        "Viper 1-1 flight, runway 25, cleared for takeoff, frequency change approved.",
    ]
    h.assert_no_lua_errors()


def test_takeoff_gives_the_wind_and_landing_too() -> None:
    h = _harness()
    h.lua.execute(FAKE_WIND)
    _call(h, "ready", TOWER)
    h.advance_to(2)
    # 5 kt from 360 true; the harness has no declination.
    assert _texts(h) == [
        "Viper 1-1, runway 25, wind 360 at 5, cleared for takeoff, frequency change approved."
    ]
    assert _said(h)[0]["speech"] == (
        "Viper one one, runway two five, wind three six zero at 5, "
        "cleared for takeoff, frequency change approved."
    )
    h.assert_no_lua_errors()


def test_reading_back_the_wind_altimeter_or_frequency_is_never_wrong() -> None:
    h = _harness(discipline="relaxed")
    h.lua.execute(FAKE_WIND)
    _call(h, "taxi")
    _call(h, "readback", numbers="25 2992 25 262.0")
    _call(h, "ready", TOWER)
    _call(h, "readback", TOWER, numbers="25 360 5")
    h.advance_to(2)
    assert len(_texts(h)) == 2
    h.assert_no_lua_errors()


def test_strict_still_needs_the_runway_in_the_takeoff_readback() -> None:
    h = _harness()
    _call(h, "ready", TOWER)
    _call(h, "readback", TOWER, text="cleared for takeoff viper 1 1")
    h.advance_to(2)
    assert _texts(h)[1:] == [
        "Viper 1-1, readback incomplete, cleared for takeoff runway 25."
    ]
    h.assert_no_lua_errors()


def test_relaxed_matches_a_misheard_callsign_by_flight_name() -> None:
    # Test 65: Whisper heard "Enfield 4" as "Enfield 2" and Relaxed asked again each time.
    h = DcsPluginHarness()
    h.lua.execute(FAKE_AIRBASE)
    h.lua.execute(FAKE_SOCKET)
    config = _config()
    lead = dict(config["voiceAtc"]["flights"][0])
    config["voiceAtc"]["flights"] = [
        dict(lead, group="Viper", callsign="Enfield 4-1"),
        dict(lead, group="Cobra", callsign="Colt 1-1"),
    ]
    h.lua.globals().dcsRetribution = h.to_lua(
        {"plugins": {}, "radioDiscipline": "relaxed", **config}
    )
    h.add_group(_viper())
    h.load_plugin_script(PLUGIN)
    _call(h, "radiocheck", callsign="enfield 2")
    _call(h, "radiocheck", callsign="cobra 7")
    h.advance_to(2)
    assert _texts(h) == [
        "Enfield 4-1, Kobuleti Ground, read you 5 by 5.",
        "Station calling Kobuleti Ground, say again your callsign.",
    ]
    h.assert_no_lua_errors()


def test_relaxed_matches_the_only_flight_at_the_field_and_strict_does_not() -> None:
    for discipline, expected in (
        ("relaxed", "Viper 1-1, Kobuleti Ground, read you 5 by 5."),
        ("strict", "Station calling Kobuleti Ground, say again your callsign."),
    ):
        h = _harness(discipline=discipline)
        _call(h, "radiocheck", callsign="enfield 2")
        h.advance_to(2)
        assert _texts(h) == [expected], discipline
        h.assert_no_lua_errors()


def test_runway_in_use_gives_the_runway_and_wind() -> None:
    h = _harness()
    h.lua.execute(FAKE_WIND)
    _call(h, "runway", TOWER)
    _call(h, "runway")
    h.advance_to(2)
    assert _texts(h) == ["Viper 1-1, runway 25, wind 360 at 5."] * 2
    assert [m["frequency"] for m in _said(h)] == [TOWER, GROUND]
    h.assert_no_lua_errors()
