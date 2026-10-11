"""Headless runtime check for the ballistic missile strike plugin (bmstrike).

Pins that both scripts load on Lua 5.1 and that a player's call-for-fire does
what the menu says: one FireAtPoint at the marker for the rounds asked, wrapped so
it ends on its own; a refusal with a reason outside the launcher's range window;
a reload timer after the mission; and that only the player's own launchers are
woken and cleared of their generated fire task. Also: rounds are counted from
launchers still alive, the menu outlives the pilot it was built for, a renamed
marker shows its name, script-made marks are left out, and no menu passes ten items.
"""

from __future__ import annotations

from typing import Any

import pytest

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


def _mark(
    h: DcsPluginHarness,
    x: float,
    text: str = "TGT",
    idx: int = 1,
    event_id: int = 25,  # S_EVENT_MARK_ADDED; 26 is S_EVENT_MARK_CHANGE
    by_player: bool = True,
) -> None:
    event: dict[str, Any] = {
        "id": event_id,
        "idx": idx,
        "coalition": int(h.side.BLUE),
        "text": text,
        "pos": {"x": x, "y": 0.0, "z": 0.0},
    }
    if by_player:
        event["initiator"] = {"name": PLAYER}
    h.fire_event(event)


def _rounds(count: int) -> list[dict[str, Any]]:
    if count == 0:
        return []
    return [{"count": count, "desc": {"category": MISSILE, "displayName": "R-17"}}]


def _labels(h: DcsPluginHarness) -> list[str]:
    return [str(record.get("path")) for record in h.records("menus")]


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


def test_a_salvo_is_counted_round_by_round() -> None:
    h = DcsPluginHarness()
    h.add_group(_launcher(BATTERY, int(h.side.BLUE), rounds=2))
    h.add_group(_player(int(h.side.BLUE)))
    _start(h, [_entry()])
    _mark(h, x=100000.0)
    _call(h, "Refresh target list")
    _call(h, "2 round(s) - full salvo")

    h.update_unit(BATTERY, {"ammo": _rounds(1)})
    h.advance_to(30)
    assert not _said(h, "end of mission")
    h.update_unit(BATTERY, {"ammo": _rounds(0)})
    h.advance_to(50)

    assert _said(h, "rounds complete, 2 away")
    h.assert_no_lua_errors()


def _two_launchers(side: int) -> dict[str, Any]:
    spec = _launcher(BATTERY, side, rounds=1)
    second = dict(spec["units"][0], name=BATTERY + "-2")
    spec["units"].append(second)
    return spec


def test_a_destroyed_launcher_is_not_counted_as_rounds_fired() -> None:
    h = DcsPluginHarness()
    h.add_group(_two_launchers(int(h.side.BLUE)))
    h.add_group(_player(int(h.side.BLUE)))
    _start(h, [_entry()], {"maxRoundsPerMission": 2})
    _mark(h, x=100000.0)
    _call(h, "Refresh target list")
    _call(h, "2 round(s) - full salvo")

    h.update_unit(BATTERY, {"ammo": _rounds(0)}, unit_index=1)  # fired
    h.update_unit(BATTERY, {"exists": False}, unit_index=2)  # destroyed
    h.advance_to(30)

    assert _said(h, "1 of 2 rounds away")
    assert not _said(h, "2 away")
    h.assert_no_lua_errors()


def test_a_battery_destroyed_before_it_fires_reports_no_rounds_away() -> None:
    h = DcsPluginHarness()
    spec = _launcher(BATTERY, int(h.side.BLUE), rounds=1)
    # The battery's support truck keeps the group alive after the launcher dies.
    spec["units"].append(
        {"name": BATTERY + "-truck", "type": "Ural-375", "x": 0.0, "z": 0.0}
    )
    h.add_group(spec)
    h.add_group(_player(int(h.side.BLUE)))
    _start(h, [_entry()])
    _mark(h, x=100000.0)
    _call(h, "Refresh target list")
    _call(h, "1 round(s)")

    h.update_unit(BATTERY, {"exists": False}, unit_index=1)
    h.advance_to(30)

    assert _said(h, "battery is out of action, no rounds away")
    assert not _said(h, "rounds complete")
    h.assert_no_lua_errors()


def _two_ship(side: int) -> dict[str, Any]:
    flight = _player(side)
    flight["units"].append(
        dict(flight["units"][0], name="Viper 1-2", playerName="Dash 2")
    )
    return flight


@pytest.mark.parametrize("leaver", [1, 2])
def test_the_menu_works_after_either_pilot_of_a_flight_leaves(leaver: int) -> None:
    h = DcsPluginHarness()
    h.add_group(_launcher(BATTERY, int(h.side.BLUE)))
    h.add_group(_two_ship(int(h.side.BLUE)))
    _start(h, [_entry()])
    _mark(h, x=100000.0)

    # DCS hands back nil for the unit of a pilot who died or left the slot.
    h.update_unit("Viper 1", {"exists": False}, unit_index=leaver)
    h.harness.unitsByName[[PLAYER, "Viper 1-2"][leaver - 1]] = None
    h.advance_to(20)
    _call(h, "Refresh target list")
    _call(h, "1 round(s)")

    assert len(_fire_tasks(h)) == 1
    assert _said(h, "fire mission acknowledged")
    h.assert_no_lua_errors()


def test_a_flight_gets_one_menu_not_one_per_pilot() -> None:
    h = DcsPluginHarness()
    h.add_group(_two_ship(int(h.side.BLUE)))
    _start(h, [])

    assert _labels(h).count("Ballistic Missile Strike") == 1


def test_the_name_typed_on_a_marker_is_its_menu_label() -> None:
    h = DcsPluginHarness()
    h.add_group(_launcher(BATTERY, int(h.side.BLUE)))
    h.add_group(_player(int(h.side.BLUE)))
    _start(h, [_entry()])

    _mark(h, x=100000.0, text="")  # DCS adds the mark empty
    _mark(h, x=120000.0, text="BRIDGE", event_id=26)  # then the typed text
    _call(h, "Refresh target list")

    assert "BRIDGE" in _labels(h)
    _call(h, "1 round(s)")
    assert _fire_tasks(h)[0]["innerX"] == 120000.0
    h.assert_no_lua_errors()


def test_a_mark_drawn_by_a_script_is_not_a_target() -> None:
    h = DcsPluginHarness()
    h.add_group(_launcher(BATTERY, int(h.side.BLUE)))
    h.add_group(_player(int(h.side.BLUE)))
    _start(h, [_entry()])

    _mark(h, x=100000.0, text="Tanker Shell 1", by_player=False)
    _mark(h, x=100000.0, text="Tanker Shell 1", event_id=26, by_player=False)
    _call(h, "Refresh target list")

    assert "Tanker Shell 1" not in _labels(h)
    assert _labels(h)[-1] == "Mark a target on the F10 map first"
    h.assert_no_lua_errors()


def _many_batteries(h: DcsPluginHarness, count: int) -> list[dict[str, Any]]:
    entries = []
    for n in range(1, count + 1):
        name = f"00{n:02d} | Scud Site"
        h.add_group(_launcher(name, int(h.side.BLUE)))
        entries.append(dict(_entry(name), callsign=f"Scud Site {n:02d}"))
    return entries


def test_eight_batteries_fill_the_menu_without_a_second_page() -> None:
    h = DcsPluginHarness()
    entries = _many_batteries(h, 8)
    h.add_group(_player(int(h.side.BLUE)))
    _start(h, entries)

    assert "More batteries" not in _labels(h)


def test_a_ninth_battery_goes_on_a_second_page() -> None:
    h = DcsPluginHarness()
    entries = _many_batteries(h, 9)
    h.add_group(_player(int(h.side.BLUE)))
    _start(h, entries)

    labels = _labels(h)
    root = labels[labels.index("Ballistic Missile Strike") + 1 :]
    # Refresh, status and seven batteries, then the tenth slot pages on.
    assert root[:2] == ["Refresh target list", "Battery status"]
    assert root.index("More batteries") == 2 + 2 * 7
    assert root[-4] == "Scud Site 08 (1)"
    assert root[-2] == "Scud Site 09 (1)"
    h.assert_no_lua_errors()


def test_the_round_choices_stop_at_ten() -> None:
    h = DcsPluginHarness()
    h.add_group(_launcher(BATTERY, int(h.side.BLUE), rounds=12))
    h.add_group(_player(int(h.side.BLUE)))
    _start(h, [_entry()], {"maxRoundsPerMission": 12})
    _mark(h, x=100000.0)
    _call(h, "Refresh target list")

    assert "10 round(s)" in _labels(h)
    assert "11 round(s)" not in _labels(h)
