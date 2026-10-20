"""Headless runtime checks for the pkgcontrol plugin (pkgcontrol-config.lua, §117).

The contract: while a ABCCC C-130 is alive and airborne it runs each
player package on STRIKE (common): an F10 Check in menu and spoken check-in, ready
to push and push time requests from SkyEye, the push call, up to two holds for a
SEAD or escort on the ground, aborts for a dead target or a lost SEAD, and the
egress call. With no controller airborne nothing is said and the push waits. The
calls go to SkyEye over the UDP link in the controller's voice and are text too.
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
            }
        ],
    }


def _harness(
    flights: list[dict[str, Any]],
    groups: list[dict[str, Any]],
    targets: tuple[str, ...] = ("Bridge #1",),
    link: bool = True,
    controller_airborne: bool = True,
) -> DcsPluginHarness:
    h = DcsPluginHarness()
    h.lua.execute(FAKE_AIRBASE)
    if link:
        h.lua.execute(FAKE_SOCKET)
    h.lua.globals().dcsRetribution = h.to_lua(
        {"plugins": {}, **_config(flights, list(targets))}
    )
    h.add_group(_group("Anvil", x=100 * NM, airborne=controller_airborne))
    h.add_group(_group("Bridge", x=0, category=2))
    for spec in groups:
        h.add_group(spec)
    h.load_plugin_script(PLUGIN)
    return h


def _texts(h: DcsPluginHarness) -> list[str]:
    return [t["text"] for t in h.records("texts")]


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
        "Colt1 1, Anvil, radar contact. Cleared direct hold, angels 20. "
        "Push time 14 10."
    )
    assert _texts(h) == [line]
    assert _said(h) == [
        {"type": "say", "frequency": "264.500AM", "text": line, "voice": "masculine"}
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
        "Colt1 1, Anvil, push time 14 10.",
        "Colt1 1, Anvil, negative, SEAD not airborne. Push time 14 10.",
    ]
    h.assert_no_lua_errors()


def test_ready_to_push_pushes_early_when_everyone_is_up() -> None:
    h = _harness([_flight("Colt", client=True)], [_group("Colt")])
    _request(h, "ready")
    h.advance_to(2)
    assert _texts(h) == ["Package Colt, Anvil, push, push."]
    h.advance_to(PUSH + 10)
    assert _texts(h) == ["Package Colt, Anvil, push, push."]
    h.assert_no_lua_errors()


def test_the_push_is_called_at_the_push_time() -> None:
    h = _harness(
        [_flight("Colt", client=True), _flight("Weasel", role="sead")],
        [_group("Colt"), _group("Weasel")],
    )
    h.advance_to(PUSH - 1)
    assert _texts(h) == []
    h.advance_to(PUSH + 10)
    assert _texts(h) == ["Package Colt, Anvil, push, push."]
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
        "Package Colt, Anvil, hold, hold. SEAD not airborne. New push time 14 13.",
        "Package Colt, Anvil, hold, hold. SEAD not airborne. New push time 14 16.",
        "Package Colt, Anvil, abort, abort, abort. No SEAD. RTB.",
    ]
    h.assert_no_lua_errors()


def test_a_dead_target_aborts() -> None:
    h = _harness([_flight("Colt", client=True)], [_group("Colt")], targets=("Gone #1",))
    h.advance_to(PUSH + 10)
    assert _texts(h) == [
        "Package Colt, Anvil, abort, abort, abort. Target Bridge destroyed. RTB."
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
    assert _texts(h) == ["Package Colt, Anvil, abort, abort, abort. SEAD lost. RTB."]
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
    assert _texts(h)[-1] == "Package Colt, Anvil, push, push."
    h.update_unit("Colt", {"x": 12 * NM})
    h.advance_to(PUSH + 50)
    assert _texts(h)[-1] == "Package Colt, Anvil, all strikers egressed. RTB."
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
    assert _texts(h) == ["Package Colt, Anvil, push, push."]
    h.assert_no_lua_errors()


def test_without_luasocket_the_calls_are_text_only() -> None:
    h = _harness([_flight("Colt", client=True)], [_group("Colt")], link=False)
    h.advance_to(PUSH + 10)
    assert _texts(h) == ["Package Colt, Anvil, push, push."]
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
