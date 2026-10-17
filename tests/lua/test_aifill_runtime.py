"""Headless runtime checks for the aifill plugin (aifill-config.lua, §113).

The contract: at the check time a client group with no player in any seat gets
its takeover announced and its AI twin activated at the planned takeoff, or at
once if that has passed; a group with a player in it keeps its twin parked; a
mission with no aiFill node is a clean no-op. Whether DCS flies the activated
twin well is in-game only (checklist B234).
"""

from __future__ import annotations

from typing import Any

from tests.lua.harness import DcsPluginHarness

PLUGIN = "resources/plugins/aifill/aifill-config.lua"
BLUE = 2


def _pair(
    client: str = "Hog 1",
    activate_after: int = 1200,
    side: str = "blue",
    client_activation: int = 0,
    escorts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    pair: dict[str, Any] = {
        "client": client,
        "twin": "AI " + client,
        "coalition": side,
        "activateAfter": str(activate_after),
        "clientActivation": str(client_activation),
        "message": client + " has no players.",
    }
    if escorts is not None:
        pair["escorts"] = escorts
    return pair


def _config(pairs: list[dict[str, Any]], announce: str = "true") -> dict[str, Any]:
    return {"aiFill": {"checkDelay": "300", "announce": announce, "pairs": pairs}}


def _group(
    name: str, player: str | None = None, exists: bool = True, airborne: bool = False
) -> dict[str, Any]:
    return {
        "name": name,
        "id": _id(name),
        "side": BLUE,
        "category": 0,
        "exists": exists,
        "units": [
            {
                "name": name + " Pilot #1",
                "type": "A-10C_2",
                "x": 0,
                "z": 0,
                "exists": exists,
                "airborne": airborne,
                "playerName": player,
            }
        ],
    }


def _id(name: str) -> int:
    return len(name) * 100 + sum(map(ord, name))


def _escort(group: str = "Eagle 1") -> dict[str, Any]:
    return {
        "group": group,
        "engagementDistMax": "37040",
        "targetTypes": ["Fighters", "Multirole fighters"],
        "x": "100.0",
        "y": "609.6",
        "z": "-50.0",
        "splitFlag": "split-42",
    }


def _harness(
    config: dict[str, Any],
    groups: list[dict[str, Any]],
    leash: list[dict[str, Any]] | None = None,
) -> DcsPluginHarness:
    h = DcsPluginHarness()
    h.lua.globals().dcsRetribution = h.to_lua(
        {"plugins": {}, **config, "Escorts": leash or []}
    )
    for spec in groups:
        h.add_group(spec)
    h.load_plugin_script(PLUGIN)
    return h


def test_no_node_is_a_clean_noop() -> None:
    h = DcsPluginHarness()
    h.set_retribution_config()
    h.load_plugin_script(PLUGIN)
    h.advance_to(4000)
    assert h.records("activations") == []
    h.assert_no_lua_errors()


def test_an_empty_flight_is_announced_at_the_check_and_launched_at_takeoff() -> None:
    h = _harness(
        _config([_pair()]),
        [_group("Hog 1", exists=False), _group("AI Hog 1", exists=False)],
    )
    h.advance_to(299)
    assert h.records("texts") == []
    h.advance_to(301)
    texts = h.records("texts")
    assert [t["text"] for t in texts] == ["Hog 1 has no players."]
    assert texts[0]["side"] == BLUE
    assert h.records("activations") == []
    h.advance_to(1201)
    assert h.records("activations") == ["AI Hog 1"]
    h.assert_no_lua_errors()


def test_a_takeoff_before_the_check_launches_at_the_check() -> None:
    h = _harness(
        _config([_pair(activate_after=60)]),
        [_group("AI Hog 1", exists=False)],
    )
    h.advance_to(301)
    assert h.records("activations") == ["AI Hog 1"]
    h.assert_no_lua_errors()


def test_a_flight_with_a_player_keeps_its_twin_parked() -> None:
    h = _harness(
        _config([_pair()]),
        [_group("Hog 1", player="Brady"), _group("AI Hog 1", exists=False)],
    )
    h.advance_to(4000)
    assert h.records("activations") == []
    assert h.records("texts") == []
    h.assert_no_lua_errors()


def test_each_pair_is_decided_on_its_own() -> None:
    h = _harness(
        _config([_pair("Hog 1"), _pair("Hog 2")]),
        [
            _group("Hog 1", player="Brady"),
            _group("AI Hog 1", exists=False),
            _group("AI Hog 2", exists=False),
        ],
    )
    h.advance_to(4000)
    assert h.records("activations") == ["AI Hog 2"]
    h.assert_no_lua_errors()


def test_announce_off_launches_quietly() -> None:
    h = _harness(
        _config([_pair()], announce=""),
        [_group("AI Hog 1", exists=False)],
    )
    h.advance_to(4000)
    assert h.records("texts") == []
    assert h.records("activations") == ["AI Hog 1"]
    h.assert_no_lua_errors()


def test_a_missing_twin_warns_instead_of_erroring() -> None:
    h = _harness(_config([_pair()]), [])
    h.advance_to(4000)
    assert any("not found" in w for w in h.records("warnings"))
    h.assert_no_lua_errors()


def test_a_late_activated_client_is_checked_after_it_appears() -> None:
    # A lone player's group appears at its planned start (should_delay_flight);
    # a check before then finds no seats and launched the twin under the player.
    h = _harness(
        _config([_pair(activate_after=1200, client_activation=1200)]),
        [_group("Hog 1", exists=False), _group("AI Hog 1", exists=False)],
    )
    h.advance_to(1400)
    assert h.records("texts") == []
    assert h.records("activations") == []
    h.update_unit("Hog 1", {"exists": True, "playerName": "Brady"})
    h.advance_to(4000)
    assert h.records("activations") == []
    h.assert_no_lua_errors()


def test_an_empty_late_activated_client_launches_at_its_own_check() -> None:
    h = _harness(
        _config([_pair(activate_after=1200, client_activation=1200)]),
        [_group("AI Hog 1", exists=False)],
    )
    h.advance_to(1499)
    assert h.records("activations") == []
    h.advance_to(1501)
    assert h.records("activations") == ["AI Hog 1"]
    h.assert_no_lua_errors()


def test_the_escorts_are_retasked_onto_the_twin_once_airborne() -> None:
    h = _harness(
        _config([_pair(escorts=[_escort()])]),
        [_group("AI Hog 1", exists=False), _group("Eagle 1")],
    )
    h.advance_to(1201)
    assert h.records("activations") == ["AI Hog 1"]
    assert h.records("pushedTasks") == []  # still on the ground
    h.update_unit("Eagle 1", {"airborne": True})
    h.advance_to(1300)
    pushed = h.records("pushedTasks")
    assert len(pushed) == 1
    task = pushed[0]
    assert task["group"] == "Eagle 1"
    assert (task["taskId"], task["innerId"]) == ("ControlledTask", "Escort")
    assert task["targetGroupId"] == _id("AI Hog 1")
    assert task["engagementDistMax"] == 37040
    assert task["targetTypes"] == ["Fighters", "Multirole fighters"]
    assert task["stopFlag"] == "split-42"
    h.assert_no_lua_errors()


def test_the_escort_leash_follows_the_twin() -> None:
    leash = {
        "escortGroupName": "Eagle 1",
        "escortedGroupName": "Hog 1",
        "escortedGroupId": "7",
    }
    h = _harness(
        _config([_pair()]),
        [_group("AI Hog 1", exists=False), _group("Eagle 1")],
        leash=[leash],
    )
    h.advance_to(1201)
    escorts = h.lua.globals().dcsRetribution.Escorts
    assert escorts[1].escortedGroupName == "AI Hog 1"
    assert escorts[1].escortedGroupId == str(_id("AI Hog 1"))
    h.assert_no_lua_errors()


def test_an_escort_that_never_flies_is_dropped_quietly() -> None:
    h = _harness(
        _config([_pair(escorts=[_escort()])]),
        [_group("AI Hog 1", exists=False), _group("Eagle 1")],
    )
    h.advance_to(1201 + 3700)
    assert h.records("pushedTasks") == []
    assert any("never airborne" in i for i in h.records("infos"))
    h.assert_no_lua_errors()


def test_a_flight_with_a_player_leaves_its_escorts_alone() -> None:
    h = _harness(
        _config([_pair(escorts=[_escort()])]),
        [_group("Hog 1", player="Brady"), _group("Eagle 1", airborne=True)],
    )
    h.advance_to(4000)
    assert h.records("pushedTasks") == []
    h.assert_no_lua_errors()
