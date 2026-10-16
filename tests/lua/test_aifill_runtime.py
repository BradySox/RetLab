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
    client: str = "Hog 1", activate_after: int = 1200, side: str = "blue"
) -> dict[str, Any]:
    return {
        "client": client,
        "twin": "AI " + client,
        "coalition": side,
        "activateAfter": str(activate_after),
        "message": client + " has no players.",
    }


def _config(pairs: list[dict[str, Any]], announce: str = "true") -> dict[str, Any]:
    return {"aiFill": {"checkDelay": "300", "announce": announce, "pairs": pairs}}


def _group(name: str, player: str | None = None, exists: bool = True) -> dict[str, Any]:
    return {
        "name": name,
        "id": len(name) * 100 + sum(map(ord, name)),
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
                "playerName": player,
            }
        ],
    }


def _harness(config: dict[str, Any], groups: list[dict[str, Any]]) -> DcsPluginHarness:
    h = DcsPluginHarness()
    h.lua.globals().dcsRetribution = h.to_lua({"plugins": {}, **config})
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
