"""Headless runtime check for the ballistic missile strike plugin (bmstrike).

Pins that both scripts load on Lua 5.1 and that a player's call-for-fire does
what the menu says: one FireAtPoint at the marker for the rounds asked, wrapped so
it ends on its own; a refusal with a reason outside the launcher's range window;
a reload timer after the mission; and that only the player's own launchers are
woken and cleared of their generated fire task.
"""

from __future__ import annotations

from typing import Any

from tests.lua.harness import DcsPluginHarness

SCRIPT = "resources/plugins/bmstrike/BallisticMissileStrike.lua"
CONFIG = "resources/plugins/bmstrike/bmstrike-config.lua"

MISSILE = 1  # Weapon.Category.MISSILE
BATTERY = "0001 | Scud Site"
PLAYER = "Viper 1-1"


def _launcher(
    name: str, side: int, unit_type: str = "Scud_B", rounds: int = 1
) -> dict[str, Any]:
    return {
        "name": name,
        "id": abs(hash(name)) % 10000 + 10,
        "side": side,
        "category": 2,  # GROUND
        "units": [
            {
                "name": name + "-1",
                "type": unit_type,
                "x": 0.0,
                "z": 0.0,
                "ammo": [
                    {
                        "count": rounds,
                        "desc": {"category": MISSILE, "displayName": "R-17"},
                    }
                ],
            }
        ],
    }


def _player(side: int) -> dict[str, Any]:
    return {
        "name": "Viper 1",
        "id": 1,
        "side": side,
        "category": 0,  # AIRPLANE
        "units": [
            {
                "name": PLAYER,
                "type": "F-16C_50",
                "x": 1000.0,
                "z": 0.0,
                "playerName": "Brady",
            }
        ],
    }


def _start(
    h: DcsPluginHarness,
    batteries: list[dict[str, Any]],
    options: dict[str, Any] | None = None,
) -> None:
    h.lua.globals().dcsRetribution = h.to_lua(
        {
            "plugins": {"bmstrike": options or {}},
            "artilleryGroups": {"ballisticMissiles": batteries},
            "forwardObserverUnits": [],
        }
    )
    h.load_plugin_script(SCRIPT)
    h.load_plugin_script(CONFIG)
    # The player poll runs at 3 s, the menu poll two seconds behind it.
    h.advance_to(8)


def _entry(group: str = BATTERY, max_range: int = 300000) -> dict[str, Any]:
    return {
        "groupName": group,
        "callsign": "Scud Site",
        "maxRangeMeters": str(max_range),
    }


def _mark(h: DcsPluginHarness, x: float, text: str = "TGT") -> None:
    h.fire_event(
        {
            "id": 25,  # S_EVENT_MARK_ADDED
            "idx": 1,
            "coalition": int(h.side.BLUE),
            "text": text,
            "pos": {"x": x, "y": 0.0, "z": 0.0},
        }
    )


def _call(h: DcsPluginHarness, label: str) -> None:
    """Press the newest radio menu command with this label."""
    for record in reversed(h.records("menus")):
        if isinstance(record, dict) and record.get("path") == label and "fn" in record:
            record["fn"](h.to_lua(record.get("arg")))
            return
    raise AssertionError(f"menu command {label!r} not found")


def _fire_tasks(h: DcsPluginHarness) -> list[dict[str, Any]]:
    return [
        task
        for task in h.records("controllerTasks")
        if task["innerId"] == "FireAtPoint"
    ]


def _said(h: DcsPluginHarness, fragment: str) -> bool:
    return any(fragment in text["text"] for text in h.records("texts"))


def test_scripts_load_with_no_launchers() -> None:
    h = DcsPluginHarness()
    h.add_group(_player(int(h.side.BLUE)))
    _start(h, [])
    assert _fire_tasks(h) == []
    h.assert_no_lua_errors()


def test_scripts_load_outside_a_retribution_mission() -> None:
    h = DcsPluginHarness()
    h.load_plugin_script(SCRIPT)
    h.load_plugin_script(CONFIG)
    h.advance_to(30)
    h.assert_no_lua_errors()


def test_a_player_calls_one_round_onto_a_marker() -> None:
    h = DcsPluginHarness()
    h.add_group(_launcher(BATTERY, int(h.side.BLUE), rounds=1))
    h.add_group(_player(int(h.side.BLUE)))
    _start(h, [_entry()])

    _mark(h, x=100000.0)
    _call(h, "Refresh target list")
    _call(h, "1 round(s)")

    tasks = _fire_tasks(h)
    assert len(tasks) == 1
    task = tasks[0]
    assert task["group"] == BATTERY
    # Wrapped, so the fire task ends by itself if the launcher never fires.
    assert task["taskId"] == "ControlledTask"
    assert task["innerX"] == 100000.0 and task["innerY"] == 0.0
    assert task["expendQty"] == 1
    assert _said(h, "fire mission acknowledged")
    assert _said(h, "53 NM")

    # The round leaves the rail: the ammo count is what ends the mission.
    h.update_unit(BATTERY, {"ammo": []})
    h.advance_to(30)
    assert _said(h, "rounds complete, 1 away")
    h.assert_no_lua_errors()


def test_a_battery_reloads_before_the_next_mission() -> None:
    h = DcsPluginHarness()
    h.add_group(_launcher(BATTERY, int(h.side.BLUE), rounds=2))
    h.add_group(_player(int(h.side.BLUE)))
    _start(h, [_entry()])
    _mark(h, x=100000.0)
    _call(h, "Refresh target list")
    _call(h, "1 round(s)")
    h.update_unit(
        BATTERY,
        {"ammo": [{"count": 1, "desc": {"category": MISSILE, "displayName": "R-17"}}]},
    )
    h.advance_to(30)
    assert _said(h, "rounds complete, 1 away")

    _call(h, "1 round(s)")

    assert len(_fire_tasks(h)) == 1
    assert _said(h, "negative, reloading")
    h.assert_no_lua_errors()


def test_a_target_inside_minimum_range_is_refused() -> None:
    h = DcsPluginHarness()
    h.add_group(_launcher(BATTERY, int(h.side.BLUE), unit_type="CHAP_9K720_HE"))
    h.add_group(_player(int(h.side.BLUE)))
    _start(h, [_entry(max_range=400000)])
    _mark(h, x=50000.0)  # the 9M723 will not fire inside 75 km
    _call(h, "Refresh target list")
    _call(h, "1 round(s)")

    assert _fire_tasks(h) == []
    assert _said(h, "target inside minimum range")
    h.assert_no_lua_errors()


def test_a_target_past_maximum_range_is_refused() -> None:
    h = DcsPluginHarness()
    h.add_group(_launcher(BATTERY, int(h.side.BLUE)))
    h.add_group(_player(int(h.side.BLUE)))
    _start(h, [_entry(max_range=300000)])
    _mark(h, x=350000.0)
    _call(h, "Refresh target list")
    _call(h, "1 round(s)")

    assert _fire_tasks(h) == []
    assert _said(h, "target out of range")
    h.assert_no_lua_errors()


def test_only_the_players_launchers_are_woken_and_reserved() -> None:
    h = DcsPluginHarness()
    enemy = "0002 | Enemy Scud Site"
    h.add_group(_launcher(BATTERY, int(h.side.BLUE)))
    h.add_group(_launcher(enemy, int(h.side.RED)))
    h.add_group(_player(int(h.side.BLUE)))
    _start(h, [_entry(), _entry(enemy)])

    woken = {record["group"] for record in h.records("options")}
    cleared = {record["group"] for record in h.records("controllerResets")}
    assert woken == {BATTERY}
    assert cleared == {BATTERY}
    h.assert_no_lua_errors()


def test_the_enemys_launchers_are_not_on_the_players_menu() -> None:
    h = DcsPluginHarness()
    enemy = "0002 | Enemy Scud Site"
    h.add_group(_launcher(enemy, int(h.side.RED)))
    h.add_group(_player(int(h.side.BLUE)))
    _start(h, [_entry(enemy)])

    labels = [record.get("path") for record in h.records("menus")]
    assert "No ballistic missile batteries available" in labels
    assert not any("Scud Site (" in str(label) for label in labels)
    h.assert_no_lua_errors()
