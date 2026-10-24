"""Headless runtime checks for the pkgcontrol plugin (pkgcontrol-config.lua, §117).

The contract: while a ABCCC C-130 is alive and airborne it runs each
player package on STRIKE (common): an F10 Check in menu and spoken check-in, ready
to push and push time requests from SkyEye, the push to join, up to two holds for a
SEAD or escort on the ground, aborts for a dead target or a lost SEAD, the execute
call once the strikers and escorts are at the join point, and the egress call. With no controller airborne nothing is said and the push waits. The
calls go to SkyEye over the UDP link in the controller's voice, with no on-screen
text; without LuaSocket they are text only.
How SkyEye says them is in-game only (checklist B258).
"""

from __future__ import annotations

import json
from typing import Any

from tests.lua.harness import DcsPluginHarness

PLUGIN = "resources/plugins/pkgcontrol/pkgcontrol-config.lua"
BLUE = 2
NM = 1852
PUSH = 600

FAKE_AIRBASE = """
Airbase = Airbase or {}
Airbase.getByName = function(name)
    return {
        getPoint = function() return { x = 5, y = 30, z = 7 } end,
        getID = function() return 42 end,
    }
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


def _flight(
    group: str, role: str = "strike", client: bool = False, push: int = PUSH
) -> dict[str, Any]:
    return {
        "group": group,
        "callsign": group + "1-1",
        "role": role,
        "client": "true" if client else "",
        "pushAfter": str(push),
        "holdX": "1000",
        "holdY": "2000",
        "holdAngels": "20",
        "holdIndex": "3",
        "home": "Incirlik",
    }


def _config(flights: list[dict[str, Any]], targets: list[str]) -> dict[str, Any]:
    return {
        "packageControl": {
            "startSeconds": str(14 * 3600),
            "linkHost": "127.0.0.1",
            "linkPort": "42690",
            "strikeFreq": "264.500",
            "strikeModulation": "AM",
            "awacsVoice": "feminine",
            "controllerVoice": "masculine",
            "controllers": [{"group": "Anvil", "callsign": "Anvil"}],
            "packages": [
                {
                    "name": "Colt",
                    "totAfter": "1500",
                    "targetName": "Bridge",
                    "targetX": "0",
                    "targetY": "0",
                    "targetUnits": targets,
                    "flights": flights,
                }
            ],
        }
    }


def _group(
    name: str,
    x: float = 50 * NM,
    airborne: bool = True,
    exists: bool = True,
    category: int = 0,
    player: str | None = None,
) -> dict[str, Any]:
    return {
        "name": name,
        "id": len(name) * 100 + sum(map(ord, name)),
        "side": BLUE,
        "category": category,
        "exists": exists,
        "units": [
            {
                "name": name + " #1",
                "type": "F-16C_50",
                "x": x,
                "z": 0,
                "exists": exists,
                "airborne": airborne,
                "playerName": player,
            }
        ],
    }


def _harness(
    flights: list[dict[str, Any]],
    groups: list[dict[str, Any]],
    targets: tuple[str, ...] = ("Bridge #1",),
    link: bool = True,
    controller_airborne: bool = True,
    discipline: str = "strict",
) -> DcsPluginHarness:
    h = DcsPluginHarness()
    h.lua.execute(FAKE_AIRBASE)
    if link:
        h.lua.execute(FAKE_SOCKET)
    h.lua.globals().dcsRetribution = h.to_lua(
        {
            "plugins": {},
            "radioDiscipline": discipline,
            **_config(flights, list(targets)),
        }
    )
    h.add_group(_group("Anvil", x=100 * NM, airborne=controller_airborne))
    h.add_group(_group("Bridge", x=0, category=2))
    for spec in groups:
        h.add_group(spec)
    h.load_plugin_script(PLUGIN)
    return h


def _all_texts(h: DcsPluginHarness) -> list[str]:
    # Spoken calls when the link is up (they are never on-screen text then); else the
    # text fallback, texted to every player group in the package, one copy kept.
    if h.lua.globals().SENT is not None:
        assert h.records("texts") == []
        return [m["text"] for m in _said(h)]
    out: list[str] = []
    for t in h.records("texts"):
        if not out or out[-1] != t["text"]:
            out.append(t["text"])
    return out


def _texts(h: DcsPluginHarness) -> list[str]:
    # The roll call and its AI read-out have their own tests below.
    return [
        t
        for t in _all_texts(h)
        if "check in. Push in" not in t and not t.endswith(" airborne.")
    ]


def _sent(h: DcsPluginHarness) -> list[dict[str, Any]]:
    sent = h.to_python(h.lua.globals().SENT)
    return [json.loads(s["msg"]) for s in sent] if isinstance(sent, list) else []


def _said(h: DcsPluginHarness) -> list[dict[str, Any]]:
    return [m for m in _sent(h) if m["type"] == "say"]


def _request(h: DcsPluginHarness, kind: str, callsign: str = "colt 1 1") -> None:
    message = json.dumps(
        {"type": "request", "kind": kind, "callsign": callsign, "controller": "x"}
    )
    h.lua.execute(f"table.insert(INBOX, {json.dumps(message)})")


def test_no_node_is_a_clean_noop() -> None:
    h = DcsPluginHarness()
    h.set_retribution_config()
    h.load_plugin_script(PLUGIN)
    h.advance_to(4000)
    assert h.records("texts") == []
    h.assert_no_lua_errors()


def test_skyeye_is_told_the_controllers_strike_and_awacs_voice() -> None:
    h = _harness([_flight("Colt", client=True)], [_group("Colt")])
    h.advance_to(2)
    packages = [m for m in _sent(h) if m["type"] == "packages"][0]
    assert packages["controllers"] == ["Anvil"]
    assert packages["strike"] == "264.500AM"
    assert packages["gciVoice"] == "feminine"
    assert packages["packages"] == [{"name": "Colt", "frequency": "264.500AM"}]
    h.assert_no_lua_errors()


def test_the_f10_check_in_answers_on_strike_in_the_controller_voice() -> None:
    h = _harness([_flight("Colt", client=True)], [_group("Colt")])
    assert [m["path"] for m in h.records("menus")] == ["Package control", "Check in"]
    check_in = h.lua.globals().DcsHarness.records.menus[2]
    check_in.fn(check_in.arg)
    line = (
        "Colt1-1, Anvil, radar contact. Cleared direct hold, angels 20. "
        "Push time 1410."
    )
    assert _texts(h) == [line]
    assert _said(h) == [
        {
            "type": "say",
            "frequency": "264.500AM",
            "text": line,
            "speech": "Colt one one, Anvil, radar contact. Cleared direct hold, "
            "angels two zero. Push time one four one zero.",
            "voice": "masculine",
            "speaker": "Anvil",
        }
    ]
    h.assert_no_lua_errors()


def test_spoken_requests_from_skyeye_are_answered() -> None:
    h = _harness(
        [_flight("Colt", client=True), _flight("Weasel", role="sead")],
        [_group("Colt"), _group("Weasel", airborne=False)],
    )
    _request(h, "pushtime")
    _request(h, "ready")
    h.advance_to(2)
    assert _texts(h) == [
        "Colt1-1, Anvil, push time 1410.",
        "Colt1-1, Anvil, negative, SEAD not airborne. Push time 1410.",
    ]
    h.assert_no_lua_errors()


def test_ready_to_push_pushes_early_when_everyone_is_up() -> None:
    h = _harness([_flight("Colt", client=True)], [_group("Colt")])
    _request(h, "ready")
    h.advance_to(2)
    assert _texts(h) == ["Colt package, Anvil, execute."]
    h.advance_to(PUSH + 10)
    assert _texts(h) == ["Colt package, Anvil, execute."]
    h.assert_no_lua_errors()


def test_the_push_is_called_at_the_push_time() -> None:
    h = _harness(
        [_flight("Colt", client=True), _flight("Weasel", role="sead")],
        [_group("Colt"), _group("Weasel")],
    )
    h.advance_to(PUSH - 1)
    assert _texts(h) == []
    h.advance_to(PUSH + 10)
    assert _texts(h) == ["Colt package, Anvil, execute."]
    h.assert_no_lua_errors()


def test_a_sead_on_the_ground_holds_twice_then_aborts() -> None:
    h = _harness(
        [_flight("Colt", client=True), _flight("Weasel", role="sead")],
        [_group("Colt"), _group("Weasel", airborne=False)],
    )
    h.advance_to(PUSH + 10)
    h.advance_to(PUSH + 190)
    h.advance_to(PUSH + 370)
    assert _texts(h) == [
        "Colt package, Anvil, hold, hold. SEAD not airborne. New push time 1413.",
        "Colt package, Anvil, hold, hold. SEAD not airborne. New push time 1416.",
        "Colt package, Anvil, abort, abort, abort. No SEAD. RTB.",
    ]
    h.assert_no_lua_errors()


def test_a_dead_target_aborts() -> None:
    h = _harness([_flight("Colt", client=True)], [_group("Colt")], targets=("Gone #1",))
    h.advance_to(PUSH + 10)
    assert _texts(h) == [
        "Colt package, Anvil, abort, abort, abort. Target Bridge destroyed. RTB."
    ]
    h.assert_no_lua_errors()


def test_a_lost_sead_aborts() -> None:
    h = _harness(
        [_flight("Colt", client=True), _flight("Weasel", role="sead")],
        [_group("Colt"), _group("Weasel")],
    )
    h.advance_to(20)
    h.update_unit("Weasel", {"exists": False})
    h.advance_to(PUSH + 10)
    assert _texts(h) == ["Colt package, Anvil, abort, abort, abort. SEAD lost. RTB."]
    h.assert_no_lua_errors()


def test_egress_is_called_when_the_strikers_open_from_the_target() -> None:
    h = _harness([_flight("Colt", client=True)], [_group("Colt", x=50 * NM)])
    h.advance_to(PUSH + 10)
    h.update_unit("Colt", {"x": 8 * NM})
    h.advance_to(PUSH + 20)
    h.update_unit("Colt", {"x": 5 * NM})
    h.advance_to(PUSH + 30)
    h.update_unit("Colt", {"x": 9 * NM})
    h.advance_to(PUSH + 40)
    assert _texts(h)[-1] == "Colt package, Anvil, execute."
    h.update_unit("Colt", {"x": 12 * NM})
    h.advance_to(PUSH + 50)
    assert _texts(h)[-1] == "Colt package, Anvil, all strikers egressed. RTB."
    h.assert_no_lua_errors()


def test_no_controller_airborne_means_no_package_control() -> None:
    h = _harness(
        [_flight("Colt", client=True)], [_group("Colt")], controller_airborne=False
    )
    _request(h, "checkin")
    h.advance_to(PUSH + 300)
    assert _texts(h) == []
    assert _said(h) == []
    h.update_unit("Anvil", {"airborne": True})
    h.advance_to(PUSH + 320)
    assert _texts(h) == ["Colt package, Anvil, execute."]
    h.assert_no_lua_errors()


def test_without_luasocket_the_calls_are_text_only() -> None:
    h = _harness([_flight("Colt", client=True)], [_group("Colt")], link=False)
    h.advance_to(PUSH + 10)
    assert _texts(h) == ["Colt package, Anvil, execute."]
    assert any("LuaSocket" in w for w in h.records("warnings"))
    h.assert_no_lua_errors()


def test_ai_flights_orbit_on_a_hold_and_go_home_on_an_abort() -> None:
    h = _harness(
        [
            _flight("Colt", client=True),
            _flight("Weasel", role="sead"),
            _flight("Hawg"),
        ],
        [_group("Colt"), _group("Weasel", airborne=False), _group("Hawg")],
    )
    h.advance_to(PUSH + 10)
    pushed = h.records("pushedTasks")
    assert {p["group"] for p in pushed} == {"Hawg"}
    h.advance_to(PUSH + 190)
    h.advance_to(PUSH + 370)
    homes = [t for t in h.records("controllerTasks") if t["taskId"] == "Mission"]
    assert {t["group"] for t in homes} == {"Hawg"}
    h.assert_no_lua_errors()


def test_an_early_push_releases_the_ai_from_hold() -> None:
    h = _harness(
        [_flight("Colt", client=True), _flight("Hawg")],
        [_group("Colt"), _group("Hawg")],
    )
    _request(h, "ready")
    h.advance_to(2)
    commands = h.records("controllerCommands")
    assert [(c["group"], c["commandId"]) for c in commands] == [
        ("Hawg", "SwitchWaypoint")
    ]
    h.assert_no_lua_errors()


def test_the_roll_call_goes_out_three_minutes_before_the_push() -> None:
    h = _harness(
        [_flight("Colt", client=True), _flight("Hawg"), _flight("Weasel", role="sead")],
        [
            _group("Colt", player="Flash"),
            _group("Hawg"),
            _group("Weasel", airborne=False),
        ],
    )
    h.advance_to(PUSH - 190)
    assert _all_texts(h) == []
    h.advance_to(PUSH - 170)
    assert _all_texts(h) == [
        "Colt package, Anvil, check in. Push in 3 minutes."
        " Hawg1-1 airborne. Weasel1-1 not airborne."
    ]
    h.assert_no_lua_errors()


def test_the_roll_call_and_its_ai_read_out_are_one_transmission() -> None:
    # Flown 2026-10-22: the read-out sent as a second say right behind the roll call
    # was transmitted and never heard.
    h = _harness(
        [_flight("Colt", client=True), _flight("Hawg"), _flight("Weasel", role="sead")],
        [
            _group("Colt", player="Flash"),
            _group("Hawg"),
            _group("Weasel", airborne=False),
        ],
    )
    h.advance_to(PUSH - 170)
    said = _said(h)
    assert len(said) == 1
    assert said[0]["speech"] == (
        "Colt package, Anvil, check in. Push in three minutes."
        " Hawg one one airborne. Weasel one one not airborne."
    )
    assert said[0]["frequency"] == "264.500AM"
    h.assert_no_lua_errors()


def test_a_checked_in_player_pushes_on_time() -> None:
    h = _harness([_flight("Colt", client=True)], [_group("Colt", player="Flash")])
    h.advance_to(PUSH - 170)
    _request(h, "checkin")
    h.advance_to(PUSH - 160)
    assert _texts(h) == ["Colt1-1, Anvil, copy ready. Push time 1410."]
    h.advance_to(PUSH + 10)
    assert _texts(h)[-1] == "Colt package, Anvil, execute."
    h.assert_no_lua_errors()


def test_a_silent_striker_is_left_behind_when_another_striker_is_up() -> None:
    h = _harness(
        [_flight("Colt", client=True), _flight("Hawg")],
        [_group("Colt", player="Flash"), _group("Hawg")],
    )
    h.advance_to(PUSH + 10)
    assert _texts(h)[-2:] == [
        "Colt1-1, Anvil, not checked in. Package pushing without you.",
        "Colt package, Anvil, execute.",
    ]
    h.assert_no_lua_errors()


def test_a_lone_silent_striker_holds_once_then_aborts() -> None:
    h = _harness([_flight("Colt", client=True)], [_group("Colt", player="Flash")])
    h.advance_to(PUSH + 10)
    h.advance_to(PUSH + 190)
    assert _texts(h) == [
        "Colt package, Anvil, hold, hold. Colt1-1 not checked in. New push time 1413.",
        "Colt package, Anvil, abort, abort, abort. No strikers checked in. RTB.",
    ]
    h.assert_no_lua_errors()


def test_a_silent_escort_gets_one_hold_then_the_package_pushes() -> None:
    h = _harness(
        [_flight("Colt", client=True), _flight("Eagle", role="escort", client=True)],
        [_group("Colt", player="Flash"), _group("Eagle", player="Joe")],
    )
    h.advance_to(PUSH - 170)
    _request(h, "checkin")
    h.advance_to(PUSH + 10)
    h.advance_to(PUSH + 190)
    assert _texts(h)[-2:] == [
        "Colt package, Anvil, hold, hold. Eagle1-1 not checked in. New push time 1413.",
        "Colt package, Anvil, execute.",
    ]
    h.assert_no_lua_errors()


def test_a_silent_sead_holds_twice_then_aborts() -> None:
    h = _harness(
        [_flight("Colt", client=True), _flight("Weasel", role="sead", client=True)],
        [_group("Colt", player="Flash"), _group("Weasel", player="Joe")],
    )
    h.advance_to(PUSH - 170)
    _request(h, "checkin")
    h.advance_to(PUSH + 10)
    h.advance_to(PUSH + 190)
    h.advance_to(PUSH + 370)
    assert _texts(h)[-3:] == [
        "Colt package, Anvil, hold, hold. Weasel1-1 not checked in. New push time 1413.",
        "Colt package, Anvil, hold, hold. Weasel1-1 not checked in. New push time 1416.",
        "Colt package, Anvil, abort, abort, abort. Weasel1-1 not checked in. RTB.",
    ]
    h.assert_no_lua_errors()


def test_an_empty_player_slot_is_not_waited_for() -> None:
    h = _harness([_flight("Colt", client=True)], [_group("Colt")])
    h.advance_to(PUSH + 10)
    assert _texts(h) == ["Colt package, Anvil, execute."]
    h.assert_no_lua_errors()


def _strike_on_the_ramp() -> DcsPluginHarness:
    # Test 64: the only striker, an AI flight, never got airborne.
    return _harness(
        [_flight("Colt", role="escort", client=True), _flight("Ford")],
        [_group("Colt"), _group("Ford", airborne=False)],
    )


def test_a_strike_never_airborne_holds_twice_then_aborts() -> None:
    h = _strike_on_the_ramp()
    h.advance_to(PUSH + 370)
    assert _texts(h) == [
        "Colt package, Anvil, hold, hold. Ford1-1 not airborne. New push time 1413.",
        "Colt package, Anvil, hold, hold. Ford1-1 not airborne. New push time 1416.",
        "Colt package, Anvil, abort, abort, abort. No strikers airborne. RTB.",
    ]
    h.assert_no_lua_errors()


def test_a_striker_up_after_one_hold_still_pushes() -> None:
    h = _strike_on_the_ramp()
    h.advance_to(PUSH + 10)
    h.update_unit("Ford", {"airborne": True})
    h.advance_to(PUSH + 190)
    assert _texts(h) == [
        "Colt package, Anvil, hold, hold. Ford1-1 not airborne. New push time 1413.",
        "Colt package, Anvil, execute.",
    ]
    h.assert_no_lua_errors()


def test_the_hold_names_the_striker_on_the_ground_in_words() -> None:
    h = _strike_on_the_ramp()
    h.advance_to(PUSH + 10)
    holds = [t for t in _speech(h) if "hold, hold" in t]
    assert holds == [
        "Colt package, Anvil, hold, hold. Ford one one not airborne. "
        "New push time one four one three."
    ]
    h.assert_no_lua_errors()


def test_ready_to_push_with_no_striker_up_is_a_negative() -> None:
    h = _strike_on_the_ramp()
    _request(h, "ready")
    h.advance_to(2)
    assert _texts(h) == [
        "Colt1-1, Anvil, negative, Ford1-1 not airborne. Push time 1410."
    ]
    h.assert_no_lua_errors()


def test_the_hold_reason_starts_a_sentence() -> None:
    h = _harness(
        [_flight("Colt", client=True), _flight("Uzi", role="escort")],
        [_group("Colt"), _group("Uzi", airborne=False)],
    )
    h.advance_to(PUSH + 10)
    assert _texts(h) == [
        "Colt package, Anvil, hold, hold. Escort not airborne. New push time 1413."
    ]
    h.assert_no_lua_errors()


def _holds(h: DcsPluginHarness) -> list[str]:
    return [t for t in _texts(h) if "hold, hold" in t or "abort" in t]


def test_skyeye_is_told_how_loose_the_calls_may_be() -> None:
    for discipline, loose, threats_only in (
        ("strict", False, False),
        ("relaxed", True, False),
        ("casual", True, True),
    ):
        h = _harness(
            [_flight("Colt", client=True)], [_group("Colt")], discipline=discipline
        )
        h.advance_to(2)
        packages = [m for m in _sent(h) if m["type"] == "packages"][0]
        assert packages["looseCalls"] is loose
        assert packages["strikeThreatsOnly"] is threats_only


def test_relaxed_never_holds_for_a_silent_player() -> None:
    h = _harness(
        [_flight("Colt", client=True), _flight("Weasel", role="sead", client=True)],
        [_group("Colt", player="Flash"), _group("Weasel", player="Joe")],
        discipline="relaxed",
    )
    h.advance_to(PUSH + 10)
    assert any("Anvil, check in. Push in" in t for t in _all_texts(h))
    assert _holds(h) == []
    assert "execute" in _texts(h)[-1]
    h.assert_no_lua_errors()


def test_casual_has_no_roll_call_and_no_hold_for_the_escort() -> None:
    h = _harness(
        [_flight("Colt", client=True), _flight("Uzi", role="escort")],
        [_group("Colt", player="Flash"), _group("Uzi", airborne=False)],
        discipline="casual",
    )
    h.advance_to(PUSH + 10)
    assert not any("check in" in t for t in _all_texts(h))
    assert _holds(h) == []
    assert "execute" in _texts(h)[-1]


def test_casual_still_holds_for_sead_on_the_ground() -> None:
    h = _harness(
        [_flight("Colt", client=True), _flight("Weasel", role="sead")],
        [_group("Colt", player="Flash"), _group("Weasel", airborne=False)],
        discipline="casual",
    )
    h.advance_to(PUSH + 10)
    assert _holds(h) == [
        "Colt package, Anvil, hold, hold. SEAD not airborne. New push time 1413."
    ]


def test_off_strict_a_close_enough_callsign_finds_the_flight() -> None:
    for discipline, answered in (("strict", False), ("relaxed", True)):
        h = _harness(
            [_flight("Colt", client=True)], [_group("Colt")], discipline=discipline
        )
        _request(h, "pushtime", callsign="colt")
        h.advance_to(2)
        assert bool(_texts(h)) is answered, discipline


def test_a_seat_callsign_finds_its_flight_on_strict() -> None:
    flight = _flight("Ford", client=True)
    flight["callsign"] = "Ford 5-1"
    for heard in ("ford 5 1", "ford 5", "ford 5 2"):
        h = _harness([flight], [_group("Ford")])
        _request(h, "pushtime", callsign=heard)
        h.advance_to(2)
        assert _texts(h) == ["Ford 5-1, Anvil, push time 1410."], heard
        h.assert_no_lua_errors()
    h = _harness([flight], [_group("Ford")])
    _request(h, "pushtime", callsign="ford 6 1")
    h.advance_to(2)
    assert _texts(h) == []


def test_a_three_digit_flight_number_finds_its_flight() -> None:
    # Non-Western callsigns are "Flight 123-1"; "flight 1 2 3" is that flight's lead.
    flight = _flight("Ford", client=True)
    flight["callsign"] = "Flight 123-1"
    for heard in ("flight 1 2 3 1", "flight 1 2 3", "flight 1 2 3 2"):
        h = _harness([flight], [_group("Ford")])
        _request(h, "pushtime", callsign=heard)
        h.advance_to(2)
        assert _texts(h) == ["Flight 123-1, Anvil, push time 1410."], heard
        h.assert_no_lua_errors()


# Spoken lines (2026-10-21 phrasing review): "Ford package", digits as words, "airborne",
# a roll call that names the package, text and speech sent apart.


def _speech(h: DcsPluginHarness) -> list[str]:
    return [m["speech"] for m in _said(h)]


def test_the_push_names_the_package_and_speaks_digits_as_words() -> None:
    flight = _flight("Ford", client=True)
    flight["callsign"] = "Ford 9-1"
    h = _harness([flight], [_group("Ford")])
    _request(h, "pushtime", callsign="ford 9 1")
    h.advance_to(2)
    assert _texts(h) == ["Ford 9-1, Anvil, push time 1410."]
    assert _speech(h) == ["Ford niner one, Anvil, push time one four one zero."]
    h.advance_to(PUSH + 10)
    assert _said(h)[-1]["text"] == "Colt package, Anvil, execute."
    assert _said(h)[-1]["speech"] == "Colt package, Anvil, execute."
    h.assert_no_lua_errors()


def test_a_dead_target_is_named_in_text_only() -> None:
    h = _harness([_flight("Colt", client=True)], [_group("Colt")], targets=("Gone #1",))
    h.advance_to(PUSH + 10)
    assert _said(h)[-1]["speech"] == (
        "Colt package, Anvil, abort, abort, abort. Target destroyed. RTB."
    )


def test_the_roll_call_names_every_package_due_together() -> None:
    h = DcsPluginHarness()
    h.lua.execute(FAKE_AIRBASE)
    h.lua.execute(FAKE_SOCKET)
    config = _config([_flight("Colt", client=True)], ["Bridge #1"])
    second = dict(config["packageControl"]["packages"][0])
    second["name"] = "Ford"
    second["flights"] = [_flight("Ford", client=True)]
    config["packageControl"]["packages"].append(second)
    h.lua.globals().dcsRetribution = h.to_lua(
        {"plugins": {}, "radioDiscipline": "strict", **config}
    )
    h.add_group(_group("Anvil", x=100 * NM))
    h.add_group(_group("Bridge", x=0, category=2))
    h.add_group(_group("Colt", player="Flash"))
    h.add_group(_group("Ford", player="Joe"))
    h.load_plugin_script(PLUGIN)
    h.advance_to(PUSH - 170)
    roll_calls = [t for t in _speech(h) if "check in" in t]
    assert roll_calls == [
        "Colt and Ford packages, Anvil, check in. Push in three minutes."
    ]
    h.assert_no_lua_errors()


def test_ready_to_push_answering_the_roll_call_is_a_check_in() -> None:
    h = _harness([_flight("Colt", client=True)], [_group("Colt", player="Flash")])
    h.advance_to(PUSH - 170)
    _request(h, "ready")
    h.advance_to(PUSH - 160)
    assert _texts(h) == ["Colt1-1, Anvil, copy ready. Push time 1410."]
    _request(h, "ready")
    h.advance_to(PUSH - 150)
    assert _texts(h)[-1] == "Colt package, Anvil, execute."
    h.assert_no_lua_errors()


def test_an_unreadable_call_gets_a_say_again_in_the_controller_voice() -> None:
    h = _harness([_flight("Colt", client=True)], [_group("Colt")])
    _request(h, "unknown")
    _request(h, "unknown", callsign="ford 9 1")
    _request(h, "unknown", callsign="")
    h.advance_to(2)
    said = _said(h)
    assert [m["text"] for m in said] == [
        "Colt1-1, Anvil, say again.",
        "Ford 9 1, Anvil, say again.",
        "Station calling Anvil, say again your callsign.",
    ]
    assert said[1]["speech"] == "Ford niner one, Anvil, say again."
    assert {m["voice"] for m in said} == {"masculine"}
    h.assert_no_lua_errors()


def test_an_airborne_report_checks_in_once_then_is_copied() -> None:
    # Test 64: "Ramrod, Chevy 2, flight is airborne" got a say again.
    h = _harness([_flight("Colt", client=True)], [_group("Colt")])
    _request(h, "airborne")
    h.advance_to(2)
    _request(h, "airborne")
    h.advance_to(3)
    assert _all_texts(h)[-2:] == [
        "Colt1-1, Anvil, radar contact. Cleared direct hold, angels 20. "
        "Push time 1410.",
        "Colt1-1, Anvil, copy airborne.",
    ]
    h.assert_no_lua_errors()


def test_an_airborne_report_after_a_check_in_is_only_copied() -> None:
    h = _harness([_flight("Colt", client=True)], [_group("Colt")])
    _request(h, "checkin")
    _request(h, "airborne")
    h.advance_to(2)
    assert _all_texts(h)[-1] == "Colt1-1, Anvil, copy airborne."
    assert len([t for t in _all_texts(h) if "radar contact" in t]) == 1
    h.assert_no_lua_errors()


def test_skyeye_is_told_which_player_flies_which_seat() -> None:
    h = DcsPluginHarness()
    h.lua.execute(FAKE_AIRBASE)
    h.lua.execute(FAKE_SOCKET)
    config = _config([_flight("Colt", client=True)], ["Bridge #1"])
    config["packageControl"]["players"] = [{"group": "Viper", "callsign": "Ford 9-1"}]
    h.lua.globals().dcsRetribution = h.to_lua(
        {"plugins": {}, "radioDiscipline": "strict", **config}
    )
    h.add_group(_group("Anvil", x=100 * NM))
    h.add_group(_group("Viper", player="Flash"))
    h.load_plugin_script(PLUGIN)
    h.advance_to(2)
    packages = [m for m in _sent(h) if m["type"] == "packages"][0]
    assert packages["pilots"] == [
        {"name": "Flash", "callsign": "Ford 9-1"},
        {"name": "Flash", "callsign": "Ford 9"},
    ]
    h.assert_no_lua_errors()


def test_a_late_activated_flight_not_yet_active_is_not_airborne() -> None:
    # Test 63: an inactive late-activation unit reads isExist and inAir true.
    h = _harness(
        [_flight("Colt", client=True), _flight("Weasel", role="sead")],
        [_group("Colt"), _group("Weasel")],
    )
    h.lua.execute(
        "Group.getByName('Weasel'):getUnit(1).isActive = function() return false end"
    )
    h.advance_to(PUSH + 10)
    assert _texts(h) == [
        "Colt package, Anvil, hold, hold. SEAD not airborne. New push time 1413."
    ]
    h.lua.execute("Group.getByName('Weasel'):getUnit(1).isActive = nil")
    h.advance_to(PUSH + 190)
    assert _texts(h)[-1] == "Colt package, Anvil, execute."
    h.assert_no_lua_errors()


JOIN_X = 30 * NM
JOIN = PUSH + 300


def _joining(group: str, role: str = "strike", client: bool = False) -> dict[str, Any]:
    return {
        **_flight(group, role=role, client=client),
        "joinAfter": str(JOIN),
        "joinX": str(JOIN_X),
        "joinY": "0",
        "joinAngels": "22",
    }


def test_the_push_sends_the_package_to_the_join_and_execute_waits_for_it() -> None:
    h = _harness(
        [_joining("Colt", client=True), _joining("Hawg"), _joining("Eagle", "escort")],
        [_group("Colt"), _group("Hawg"), _group("Eagle")],
    )
    h.advance_to(PUSH + 10)
    assert _texts(h) == ["Colt package, Anvil, push to join."]
    h.update_unit("Hawg", {"x": JOIN_X + 2 * NM})
    h.advance_to(PUSH + 20)
    assert _texts(h) == ["Colt package, Anvil, push to join."]
    h.update_unit("Eagle", {"x": JOIN_X - 3 * NM})
    h.advance_to(PUSH + 30)
    assert _texts(h)[-1] == "Colt package, Anvil, execute."
    assert [f["flag"] for f in h.records("userFlags")] == ["pkgcontrol_execute_1"]
    h.assert_no_lua_errors()


def test_an_ai_flight_early_at_the_join_orbits_until_execute() -> None:
    h = _harness(
        [_joining("Colt", client=True), _joining("Hawg"), _joining("Eagle", "escort")],
        [_group("Colt"), _group("Hawg", x=JOIN_X), _group("Eagle")],
    )
    h.advance_to(PUSH + 20)
    orbits = [p for p in h.records("pushedTasks") if p["innerId"] == "Orbit"]
    assert [(p["group"], p["stopFlag"]) for p in orbits] == [
        ("Hawg", "pkgcontrol_execute_1")
    ]
    h.advance_to(PUSH + 40)
    assert len([p for p in h.records("pushedTasks") if p["innerId"] == "Orbit"]) == 1
    h.update_unit("Eagle", {"x": JOIN_X})
    h.advance_to(PUSH + 50)
    assert _texts(h)[-1] == "Colt package, Anvil, execute."
    assert h.records("userFlags")[0]["value"] is True
    h.assert_no_lua_errors()


def test_sead_is_not_waited_for_at_the_join() -> None:
    h = _harness(
        [_joining("Colt", client=True), _joining("Hawg"), _joining("Weasel", "sead")],
        [_group("Colt"), _group("Hawg", x=JOIN_X), _group("Weasel")],
    )
    h.advance_to(PUSH + 20)
    assert _texts(h) == [
        "Colt package, Anvil, push to join.",
        "Colt package, Anvil, execute.",
    ]
    h.assert_no_lua_errors()


def test_a_late_flight_gets_three_minutes_then_the_package_executes() -> None:
    h = _harness(
        [_joining("Colt", client=True), _joining("Hawg"), _joining("Eagle", "escort")],
        [_group("Colt"), _group("Hawg", x=JOIN_X), _group("Eagle")],
    )
    h.advance_to(JOIN + 170)
    assert _texts(h) == ["Colt package, Anvil, push to join."]
    h.advance_to(JOIN + 190)
    assert _texts(h)[-2:] == [
        "Eagle1-1, Anvil, not at join. Package executing without you.",
        "Colt package, Anvil, execute.",
    ]
    h.assert_no_lua_errors()


def test_no_striker_at_the_join_aborts_after_the_wait() -> None:
    h = _harness(
        [_joining("Colt", client=True), _joining("Hawg"), _joining("Eagle", "escort")],
        [_group("Colt"), _group("Hawg"), _group("Eagle", x=JOIN_X)],
    )
    h.advance_to(JOIN + 190)
    assert _texts(h)[-1] == (
        "Colt package, Anvil, abort, abort, abort. No strikers at join. RTB."
    )
    h.assert_no_lua_errors()


def test_no_striker_up_on_the_way_to_the_join_aborts_at_once() -> None:
    h = _harness(
        [_joining("Colt", role="escort", client=True), _joining("Hawg")],
        [_group("Colt"), _group("Hawg")],
    )
    h.advance_to(PUSH + 10)
    assert _texts(h) == ["Colt package, Anvil, push to join."]
    h.update_unit("Hawg", {"airborne": False})
    h.advance_to(PUSH + 20)
    assert _texts(h)[-1] == (
        "Colt package, Anvil, abort, abort, abort. No strikers airborne. RTB."
    )
    h.assert_no_lua_errors()


def test_a_slipped_push_moves_the_join_wait_with_it() -> None:
    h = _harness(
        [
            _joining("Colt", client=True),
            _joining("Hawg"),
            _joining("Eagle", "escort"),
            _flight("Weasel", role="sead"),
        ],
        [
            _group("Colt"),
            _group("Hawg", x=JOIN_X),
            _group("Eagle"),
            _group("Weasel", airborne=False),
        ],
    )
    h.advance_to(PUSH + 10)
    h.update_unit("Weasel", {"airborne": True})
    h.advance_to(PUSH + 190)
    assert _texts(h)[-1] == "Colt package, Anvil, push to join."
    h.advance_to(JOIN + 190)
    assert _texts(h)[-1] == "Colt package, Anvil, push to join."
    h.advance_to(JOIN + 370)
    assert _texts(h)[-1] == "Colt package, Anvil, execute."
    h.assert_no_lua_errors()


def test_a_check_in_on_the_way_to_the_join_is_told_to_proceed() -> None:
    h = _harness(
        [_joining("Colt", client=True), _joining("Hawg"), _joining("Eagle", "escort")],
        [_group("Colt"), _group("Hawg"), _group("Eagle")],
    )
    h.advance_to(PUSH + 10)
    _request(h, "checkin")
    _request(h, "pushtime")
    h.advance_to(PUSH + 12)
    assert _texts(h)[1:] == [
        "Colt1-1, Anvil, radar contact. Colt package has pushed, proceed to join.",
        "Colt1-1, Anvil, Colt package has pushed.",
    ]
    h.assert_no_lua_errors()
