"""Headless runtime checks for the vacuum plugin (vacuum-config.lua, §118).

The contract: while a Vacuum is alive and airborne, each red radar in range is called
once each time it comes on, on Vacuum's own frequency, and on STRIKE too only when it
covers a player package. A radar must stay off a minute to count as a new on-cycle.
Nothing is said with no Vacuum airborne. How SkyEye says it is in-game only (B260).
"""

from __future__ import annotations

import json
from typing import Any

from tests.lua.harness import DcsPluginHarness

PLUGIN = "resources/plugins/vacuum/vacuum-config.lua"
BLUE, RED = 2, 1
NM = 1852

FAKE_SOCKET = """
SENT = {}
package.preload["socket"] = function()
    return {
        udp = function()
            return {
                settimeout = function() end,
                setsockname = function() end,
                sendto = function(self, msg, host, port)
                    table.insert(SENT, { msg = msg, host = host, port = port })
                end,
            }
        end,
    }
end
"""


def _emitter(label: str, unit: str, strike: bool = False) -> dict[str, Any]:
    return {"label": label, "units": [unit], "strike": "true" if strike else ""}


def _group(
    name: str, side: int, x: float, airborne: bool = False, radar: bool = False
) -> dict[str, Any]:
    return {
        "name": name,
        "id": sum(map(ord, name)),
        "side": side,
        "category": 0 if side == BLUE else 2,
        "units": [
            {
                "name": name + " #1",
                "type": "C-130J-30" if side == BLUE else "Kub 1S91 str",
                "x": x,
                "z": 0,
                "airborne": airborne,
                "radar": radar,
            }
        ],
    }


def _harness(
    emitters: list[dict[str, Any]],
    red: list[dict[str, Any]],
    airborne: bool = True,
    strike: bool = True,
) -> DcsPluginHarness:
    h = DcsPluginHarness()
    h.lua.execute(FAKE_SOCKET)
    node: dict[str, Any] = {
        "callsign": "Vacuum",
        "frequency": "262.000AM",
        "voice": "en_GB-alan-medium",
        "linkHost": "127.0.0.1",
        "linkPort": "42690",
        "rangeMeters": str(250 * NM),
        "groups": ["Vacuum"],
        "emitters": emitters,
    }
    if strike:
        node["strike"] = "264.500AM"
    h.lua.globals().dcsRetribution = h.to_lua({"plugins": {}, "vacuum": node})
    h.add_group(_group("Vacuum", BLUE, 0, airborne=airborne))
    for spec in red:
        h.add_group(spec)
    h.load_plugin_script(PLUGIN)
    return h


def _sent(h: DcsPluginHarness, kind: str) -> list[dict[str, Any]]:
    sent = h.to_python(h.lua.globals().SENT)
    messages = [json.loads(s["msg"]) for s in sent] if isinstance(sent, list) else []
    return [m for m in messages if m["type"] == kind]


def test_no_node_is_a_clean_noop() -> None:
    h = DcsPluginHarness()
    h.set_retribution_config()
    h.load_plugin_script(PLUGIN)
    h.advance_to(600)
    h.assert_no_lua_errors()


def test_a_radar_coming_on_is_called_once_on_vacuums_frequency() -> None:
    h = _harness([_emitter("SA-6", "Kub #1")], [_group("Kub", RED, 50 * NM)])
    h.advance_to(30)
    assert _sent(h, "tune") == [
        {"type": "tune", "frequencies": ["262.000AM", "264.500AM"]}
    ]
    assert _sent(h, "emitter") == []
    h.update_unit("Kub", {"radar": True})
    h.advance_to(120)
    calls = _sent(h, "emitter")
    assert len(calls) == 1
    call = calls[0]
    assert call["frequencies"] == ["262.000AM"]
    assert call["label"] == "SA-6"
    assert call["callsign"] == "Vacuum"
    assert call["voice"] == "en_GB-alan-medium"
    assert abs(call["lat"] - 50 * NM / 111000) < 0.001
    h.assert_no_lua_errors()


def test_a_radar_over_a_player_package_also_goes_on_strike() -> None:
    h = _harness(
        [_emitter("SA-6", "Kub #1", strike=True)],
        [_group("Kub", RED, 50 * NM, radar=True)],
    )
    h.advance_to(60)
    assert [c["frequencies"] for c in _sent(h, "emitter")] == [
        ["262.000AM", "264.500AM"]
    ]


def test_no_strike_frequency_keeps_the_call_on_vacuums_own() -> None:
    h = _harness(
        [_emitter("SA-6", "Kub #1", strike=True)],
        [_group("Kub", RED, 50 * NM, radar=True)],
        strike=False,
    )
    h.advance_to(60)
    assert [c["frequencies"] for c in _sent(h, "emitter")] == [["262.000AM"]]


def test_a_blink_is_one_call_and_a_minute_off_is_a_new_cycle() -> None:
    h = _harness(
        [_emitter("SA-6", "Kub #1")], [_group("Kub", RED, 50 * NM, radar=True)]
    )
    h.advance_to(40)
    assert len(_sent(h, "emitter")) == 1
    h.update_unit("Kub", {"radar": False})
    h.advance_to(70)
    h.update_unit("Kub", {"radar": True})
    h.advance_to(120)
    assert len(_sent(h, "emitter")) == 1
    h.update_unit("Kub", {"radar": False})
    h.advance_to(220)
    h.update_unit("Kub", {"radar": True})
    h.advance_to(260)
    assert len(_sent(h, "emitter")) == 2


def test_out_of_range_radars_are_not_called() -> None:
    h = _harness(
        [_emitter("SA-6", "Kub #1")], [_group("Kub", RED, 300 * NM, radar=True)]
    )
    h.advance_to(120)
    assert _sent(h, "emitter") == []


def test_nothing_is_said_with_no_vacuum_airborne() -> None:
    h = _harness(
        [_emitter("SA-6", "Kub #1")],
        [_group("Kub", RED, 50 * NM, radar=True)],
        airborne=False,
    )
    h.advance_to(300)
    assert _sent(h, "emitter") == []
    assert _sent(h, "tune") == []
    h.update_unit("Vacuum", {"airborne": True})
    h.advance_to(360)
    assert len(_sent(h, "emitter")) == 1


def test_calls_are_spaced_out() -> None:
    red = [_group(f"Site{i}", RED, (40 + i) * NM, radar=True) for i in range(3)]
    h = _harness([_emitter(f"SA-{i}", f"Site{i} #1") for i in range(3)], red)
    h.advance_to(15)
    assert len(_sent(h, "emitter")) == 1
    h.advance_to(30)
    assert len(_sent(h, "emitter")) == 3
    h.assert_no_lua_errors()
