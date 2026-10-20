"""Headless runtime checks for the pkgcontrol plugin (pkgcontrol-config.lua, §117).

The contract: a player flight gets an AWACS > Check in menu; at the package push
time the AWACS calls push, holds up to twice for a SEAD or escort still on the
ground, and aborts for a dead target or a lost SEAD; once every striker has
reached the target and opened past 10 NM it calls egress. Each call is text to
the package's player groups and, when MSRS is loaded, speech on the package
frequency. With no AWACS alive nothing is said. Whether SRS speaks it, and how it
sounds, is in-game only (checklist B258).
"""

from __future__ import annotations

from typing import Any

from tests.lua.harness import DcsPluginHarness

PLUGIN = "resources/plugins/pkgcontrol/pkgcontrol-config.lua"
BLUE = 2
NM = 1852
PUSH = 600

FAKE_MSRS = """
radio = { modulation = { AM = 0, FM = 1 } }
SPOKEN = {}
MSRS = {}
function MSRS:New(path, freq, mod)
    local s = { path = path, freq = freq, mod = mod }
    function s:SetCoalition() end
    function s:SetPort() end
    function s:SetGender(g) self.gender = g end
    function s:SetCulture() end
    function s:SetLabel(l) self.label = l end
    function s:PlayText(text)
        table.insert(SPOKEN, { text = text, freq = self.freq, label = self.label,
                               gender = self.gender })
    end
    return s
end
"""


def _flight(
    group: str, role: str = "strike", client: bool = False, push: int = PUSH
) -> dict[str, Any]:
    return {
        "group": group,
        "callsign": group.replace(" ", "") + "-1",
        "role": role,
        "client": "true" if client else "",
        "pushAfter": str(push),
        "holdAngels": "20",
    }


def _config(flights: list[dict[str, Any]], targets: list[str]) -> dict[str, Any]:
    return {
        "packageControl": {
            "startSeconds": str(14 * 3600),
            "srsPath": "C:\\SRS",
            "port": "5002",
            "gender": "male",
            "culture": "en-US",
            "awacs": [{"group": "Darkstar", "callsign": "Darkstar"}],
            "packages": [
                {
                    "name": "Colt",
                    "freq": "251.250",
                    "modulation": "AM",
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
    msrs: bool = True,
    awacs: bool = True,
) -> DcsPluginHarness:
    h = DcsPluginHarness()
    if msrs:
        h.lua.execute(FAKE_MSRS)
    h.lua.globals().dcsRetribution = h.to_lua(
        {"plugins": {}, **_config(flights, list(targets))}
    )
    if awacs:
        h.add_group(_group("Darkstar", x=100 * NM))
    h.add_group(_group("Bridge", x=0, category=2))
    for spec in groups:
        h.add_group(spec)
    h.load_plugin_script(PLUGIN)
    return h


def _texts(h: DcsPluginHarness) -> list[str]:
    return [t["text"] for t in h.records("texts")]


def _spoken(h: DcsPluginHarness) -> list[dict[str, Any]]:
    spoken = h.to_python(h.lua.globals().SPOKEN)
    return spoken if isinstance(spoken, list) else []


def test_no_node_is_a_clean_noop() -> None:
    h = DcsPluginHarness()
    h.set_retribution_config()
    h.load_plugin_script(PLUGIN)
    h.advance_to(4000)
    assert h.records("texts") == []
    h.assert_no_lua_errors()


def test_a_player_flight_gets_a_check_in_menu_that_answers() -> None:
    h = _harness([_flight("Colt", client=True)], [_group("Colt")])
    menus = h.records("menus")
    assert [m["path"] for m in menus] == ["AWACS", "Check in"]
    check_in = h.lua.globals().DcsHarness.records.menus[2]
    check_in.fn(check_in.arg)
    assert _texts(h) == [
        "Colt 1, Darkstar, radar contact. Cleared direct hold, angels 20. "
        "Push time 14 10."
    ]
    spoken = _spoken(h)
    assert spoken[0]["freq"] == 251.25
    assert spoken[0]["gender"] == "male"
    assert spoken[0]["label"] == "Darkstar"
    h.assert_no_lua_errors()


def test_the_push_is_called_at_the_push_time() -> None:
    h = _harness(
        [_flight("Colt", client=True), _flight("Weasel", role="sead")],
        [_group("Colt"), _group("Weasel")],
    )
    h.advance_to(PUSH - 1)
    assert _texts(h) == []
    h.advance_to(PUSH + 10)
    assert _texts(h) == ["Package Colt, Darkstar, push, push."]
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
        "Package Colt, Darkstar, hold, hold. SEAD not airborne. New push time 14 13.",
        "Package Colt, Darkstar, hold, hold. SEAD not airborne. New push time 14 16.",
        "Package Colt, Darkstar, abort, abort, abort. No SEAD. RTB.",
    ]
    h.assert_no_lua_errors()


def test_a_sead_that_gets_airborne_during_the_hold_pushes() -> None:
    h = _harness(
        [_flight("Colt", client=True), _flight("Weasel", role="sead")],
        [_group("Colt"), _group("Weasel", airborne=False)],
    )
    h.advance_to(PUSH + 10)
    h.update_unit("Weasel", {"airborne": True})
    h.advance_to(PUSH + 190)
    assert _texts(h)[-1] == "Package Colt, Darkstar, push, push."
    h.assert_no_lua_errors()


def test_a_dead_target_aborts() -> None:
    h = _harness(
        [_flight("Colt", client=True)],
        [_group("Colt")],
        targets=("Gone #1",),
    )
    h.advance_to(PUSH + 10)
    assert _texts(h) == [
        "Package Colt, Darkstar, abort, abort, abort. Target Bridge destroyed. RTB."
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
    assert _texts(h) == ["Package Colt, Darkstar, abort, abort, abort. SEAD lost. RTB."]
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
    assert _texts(h)[-1] == "Package Colt, Darkstar, push, push."
    h.update_unit("Colt", {"x": 12 * NM})
    h.advance_to(PUSH + 50)
    assert _texts(h)[-1] == "Package Colt, Darkstar, all strikers egressed. RTB."
    h.assert_no_lua_errors()


def test_without_an_awacs_nothing_is_said() -> None:
    h = _harness([_flight("Colt", client=True)], [_group("Colt")], awacs=False)
    h.advance_to(PUSH + 10)
    assert _texts(h) == []
    h.assert_no_lua_errors()


def test_without_msrs_the_calls_are_text_only() -> None:
    h = _harness([_flight("Colt", client=True)], [_group("Colt")], msrs=False)
    h.advance_to(PUSH + 10)
    assert _texts(h) == ["Package Colt, Darkstar, push, push."]
    h.assert_no_lua_errors()
