"""Headless runtime checks for the vacuum plugin (vacuum-config.lua, §118).

The contract: while a Vacuum is alive and airborne, each red radar in range is called
once each time it comes on, on Vacuum's own frequency, and on STRIKE too only when it
covers a player package. A radar must stay off a minute to count as a new on-cycle.
Nothing is said with no Vacuum airborne. Each radar Vacuum locates is remembered:
awake while on, asleep while off; its fix is loose until heard long enough, added up
across blinks, to be tight. A player's call that SkyEye passes on (check in, emitters,
target status, mud, say again) is answered with a say line on the frequency it came
in on. How SkyEye hears and says it is in-game only (B260).
"""

from __future__ import annotations

import json
from typing import Any, Optional

from tests.lua.harness import DcsPluginHarness

PLUGIN = "resources/plugins/vacuum/vacuum-config.lua"
BLUE, RED = 2, 1
NM = 1852

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


def _emitter(
    label: str, unit: str, strike: bool = False, known: str = "tight"
) -> dict[str, Any]:
    # Known tight by default: the called spot is the radar's own, so positions are exact.
    return {
        "label": label,
        "units": [unit],
        "strike": "true" if strike else "",
        "known": known,
    }


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
    flights: Optional[list[dict[str, Any]]] = None,
    blue: Optional[list[dict[str, Any]]] = None,
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
        "flights": flights or [],
    }
    if strike:
        node["strike"] = "264.500AM"
    h.lua.globals().dcsRetribution = h.to_lua({"plugins": {}, "vacuum": node})
    h.add_group(_group("Vacuum", BLUE, 0, airborne=airborne))
    for spec in red + (blue or []):
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
        {
            "type": "tune",
            "frequencies": ["262.000AM", "264.500AM"],
            "callsign": "Vacuum",
            "frequency": "262.000AM",
        }
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


def test_casual_calls_only_radars_over_a_player_package() -> None:
    h = DcsPluginHarness()
    h.lua.execute(FAKE_SOCKET)
    node = {
        "callsign": "Vacuum",
        "frequency": "262.000AM",
        "strike": "264.500AM",
        "linkHost": "127.0.0.1",
        "linkPort": "42690",
        "rangeMeters": str(250 * NM),
        "groups": ["Vacuum"],
        "emitters": [
            _emitter("SA-6", "Kub #1", strike=True),
            _emitter("EWR", "Ewr #1"),
        ],
    }
    h.lua.globals().dcsRetribution = h.to_lua(
        {"plugins": {}, "radioDiscipline": "casual", "vacuum": node}
    )
    h.add_group(_group("Vacuum", BLUE, 0, airborne=True))
    h.add_group(_group("Kub", RED, 50 * NM, radar=True))
    h.add_group(_group("Ewr", RED, 60 * NM, radar=True))
    h.load_plugin_script(PLUGIN)
    h.advance_to(60)
    assert [c["label"] for c in _sent(h, "emitter")] == ["SA-6"]
    h.assert_no_lua_errors()


def test_luasocket_is_looked_for_in_the_dcs_folder() -> None:
    # Single backslashes in the path read as ".LuaSocket?.lua" in Lua 5.1, so the
    # require only worked where something had already put LuaSocket on the path.
    h = DcsPluginHarness()
    h.lua.globals().dcsRetribution = h.to_lua(
        {"plugins": {}, "vacuum": {"callsign": "Vacuum", "groups": ["Vacuum"]}}
    )
    h.load_plugin_script(PLUGIN)
    assert ";.\\LuaSocket\\?.lua;" in h.lua.eval("package.path")
    assert ";.\\LuaSocket\\?.dll;" in h.lua.eval("package.cpath")


def test_a_label_with_a_backslash_or_control_character_is_valid_json() -> None:
    label = 'SA-6 "Kub"\\1\tB'
    h = _harness([_emitter(label, "Kub #1")], [_group("Kub", RED, 50 * NM, radar=True)])
    h.advance_to(60)
    assert [c["label"] for c in _sent(h, "emitter")] == [label]
    h.assert_no_lua_errors()


# --- Answers to players -----------------------------------------------------------------

OWN = "262.000AM"
STRIKE = "264.500AM"
FORD = {
    "group": "Ford",
    "callsign": "Ford 9-1",
    "targetX": str(60 * NM),
    "targetY": "0",
}
BULLSEYE = (
    "coalition.getMainRefPoint = function(side) "
    "return { x = 0, y = 0, z = -20 * 1852 } end"
)


def _ford(x: float = 0, z: float = 0) -> dict[str, Any]:
    return {
        "name": "Ford",
        "id": 99,
        "side": BLUE,
        "category": 0,
        "units": [
            {
                "name": "Ford #1",
                "type": "F-16C_50",
                "x": x,
                "z": z,
                "airborne": True,
                "playerName": "Ford 9-1 | Joe",
            }
        ],
    }


def _site(name: str, x: float, z: float, radar: bool = True) -> dict[str, Any]:
    spec = _group(name, RED, x, radar=radar)
    spec["units"][0]["z"] = z
    return spec


def _commands(
    sites: list[dict[str, Any]],
    emitters: list[dict[str, Any]],
    flights: Optional[list[dict[str, Any]]] = None,
    airborne: bool = True,
) -> DcsPluginHarness:
    h = _harness(
        emitters, sites, airborne=airborne, flights=flights or [FORD], blue=[_ford()]
    )
    h.lua.execute(BULLSEYE)
    h.advance_to(5)
    return h


def _ask(
    h: DcsPluginHarness,
    kind: str,
    callsign: str = "ford 9",
    frequency: str = OWN,
    bearing: str = "",
) -> list[dict[str, Any]]:
    before = len(_sent(h, "say"))
    request = {
        "type": "elintRequest",
        "kind": kind,
        "callsign": callsign,
        "speaker": "vacuum",
        "frequency": frequency,
    }
    if bearing:
        request["bearing"] = bearing
    h.lua.globals().INBOX[1] = json.dumps(request)
    h.advance_to(h.lua.eval("timer.getTime()") + 2)
    h.assert_no_lua_errors()
    assert h.records("texts") == []
    return _sent(h, "say")[before:]


# A Kub due north 50 NM, a Buk due east 30 NM, both radiating, and a dark Osa.
SITES = [
    _site("Kub", 50 * NM, 0),
    _site("Buk", 0, 30 * NM),
    _site("Osa", 0, -10 * NM, radar=False),
]
EMITTERS = [
    {**_emitter("SA-6", "Kub #1"), "reach": str(int(13 * NM))},
    {**_emitter("SA-11", "Buk #1"), "reach": str(int(19 * NM))},
    {**_emitter("SA-8", "Osa #1"), "reach": str(int(6 * NM))},
]


def test_check_in_counts_awake_and_asleep_and_names_the_nearest_awake() -> None:
    h = _commands(SITES, EMITTERS)
    [reply] = _ask(h, "checkin")
    assert reply["frequency"] == OWN
    assert reply["voice"] == "en_GB-alan-medium"
    assert reply["speaker"] == "Vacuum"
    assert reply["text"] == (
        "Ford 9, Vacuum, two awake, one asleep, nearest SA-11 awake, "
        "bullseye 090/50, tight."
    )
    assert reply["speech"] == (
        "Ford 9, Vacuum, two awake, one asleep, nearest S-A-11 awake, "
        "bullseye 0 9 0, 50, tight."
    )


def test_emitters_are_bearing_and_range_from_the_caller_awake_first() -> None:
    h = _commands(SITES, EMITTERS)
    [reply] = _ask(h, "emitters")
    # The asleep Osa is nearest but comes after the awake radars.
    assert reply["text"] == (
        "Ford 9, Vacuum, SA-11 awake 090, 30, tight; SA-6 awake 360, 50, tight; "
        "SA-8 asleep 270, 10, tight."
    )
    assert reply["speech"].startswith("Ford 9, Vacuum, S-A-11 awake 0 9 0, 30, tight; ")


def test_nothing_located_is_blank() -> None:
    h = _commands(
        [_site("Kub", 50 * NM, 0, radar=False)],
        [_emitter("SA-6", "Kub #1", known="")],
    )
    assert [r["text"] for r in _ask(h, "emitters")] == ["Ford 9, Vacuum, blank."]
    assert [r["text"] for r in _ask(h, "checkin")] == ["Ford 9, Vacuum, blank."]


def test_target_status_names_radars_on_around_the_package_target() -> None:
    h = _commands(SITES, EMITTERS)
    # The target is 60 NM north: the Kub 10 NM from it is inside its 13 NM ring.
    [reply] = _ask(h, "target")
    assert reply["text"] == (
        "Ford 9, Vacuum, target area, SA-6 awake, bullseye 022/54, tight."
    )
    h.update_unit("Kub", {"radar": False})
    assert [r["text"] for r in _ask(h, "target")] == [
        "Ford 9, Vacuum, target area, SA-6 asleep, bullseye 022/54, tight."
    ]
    h.update_unit("Kub", {"life": 0})
    assert [r["text"] for r in _ask(h, "target")] == [
        "Ford 9, Vacuum, target area blank."
    ]


def test_mud_names_the_radar_on_that_bearing() -> None:
    h = _commands(SITES, EMITTERS)
    assert [r["text"] for r in _ask(h, "mud", bearing="080")] == [
        "Ford 9, Vacuum, mud 080 is SA-11 awake, bullseye 090/50, tight."
    ]
    assert [r["speech"] for r in _ask(h, "mud", bearing="005")] == [
        "Ford 9, Vacuum, mud 0 0 5 is S-A-6 awake, bullseye 0 2 2, 54, tight."
    ]
    # The Osa is at 270 but asleep: an RWR spike is a radar on.
    assert [r["text"] for r in _ask(h, "mud", bearing="270")] == [
        "Ford 9, Vacuum, no emitter 270."
    ]
    assert [r["text"] for r in _ask(h, "mud")] == ["Ford 9, Vacuum, say mud bearing."]


def test_say_again_repeats_the_last_reply_then_the_last_call() -> None:
    h = _commands(SITES, EMITTERS)
    first = _ask(h, "emitters")
    assert [r["text"] for r in _ask(h, "sayagain")] == [first[0]["text"]]
    # Another seat that has asked nothing hears the last unprompted call.
    h2 = _commands(SITES, EMITTERS)
    h2.advance_to(40)
    said = [r["text"] for r in _ask(h2, "sayagain", callsign="ford 9 2")]
    assert len(said) == 1 and said[0].startswith("Vacuum, SA-")
    assert said[0].endswith(" awake, bullseye 090/50, tight.")


def test_a_call_on_strike_is_answered_on_strike() -> None:
    h = _commands(SITES, EMITTERS)
    [reply] = _ask(h, "checkin", frequency=STRIKE)
    assert reply["frequency"] == STRIKE


def test_an_unknown_caller_is_asked_for_a_callsign() -> None:
    h = _commands(SITES, EMITTERS)
    assert [r["text"] for r in _ask(h, "emitters", callsign="dodge 3")] == [
        "Station calling Vacuum, say again your callsign."
    ]
    assert [r["text"] for r in _ask(h, "unknown")] == ["Ford 9, Vacuum, say again."]


def test_a_viper_seat_is_named_as_said() -> None:
    h = _commands(SITES, EMITTERS, flights=[{**FORD, "callsign": "Viper 1-1"}])
    [reply] = _ask(h, "emitters", callsign="viper 1 1")
    assert reply["text"].startswith("Viper 1-1, Vacuum, ")
    assert reply["speech"].startswith("Viper 1 1, Vacuum, ")


def test_no_answer_with_no_vacuum_airborne() -> None:
    h = _commands(SITES, EMITTERS, airborne=False)
    assert _ask(h, "emitters") == []


def test_a_socket_without_receivefrom_is_harmless() -> None:
    h = DcsPluginHarness()
    h.lua.execute(FAKE_SOCKET.replace("receivefrom", "unused"))
    h.lua.globals().dcsRetribution = h.to_lua(
        {
            "plugins": {},
            "vacuum": {"callsign": "Vacuum", "frequency": OWN, "groups": ["Vacuum"]},
        }
    )
    h.add_group(_group("Vacuum", BLUE, 0, airborne=True))
    h.load_plugin_script(PLUGIN)
    h.advance_to(120)
    h.assert_no_lua_errors()


def test_a_late_activated_vacuum_is_silent_until_it_activates() -> None:
    # Test 63: the air start existed and read inAir 7 minutes before activation.
    h = _harness(
        [_emitter("SA-6", "Kub #1")], [_group("Kub", RED, 50 * NM, radar=True)]
    )
    h.update_unit("Vacuum", {"active": False})
    h.advance_to(300)
    assert _sent(h, "emitter") == []
    assert _sent(h, "tune") == []
    h.update_unit("Vacuum", {"active": True})
    h.advance_to(360)
    assert len(_sent(h, "emitter")) == 1


# --- Fixes: awake, asleep, tight and loose -----------------------------------------------


def _off_nm(call: dict[str, Any], x: float, z: float = 0) -> float:
    """How far a call puts the radar from its real spot, in NM (the stub's LOtoLL)."""
    dx, dz = call["lat"] * 111000 - x, call["lon"] * 111000 - z
    return float((dx * dx + dz * dz) ** 0.5 / NM)


def test_a_first_fix_is_loose_and_off_then_called_again_once_tight() -> None:
    h = _harness(
        [_emitter("SA-6", "Kub #1", known="")],
        [_group("Kub", RED, 50 * NM, radar=True)],
    )
    h.advance_to(15)
    [first] = _sent(h, "emitter")
    assert (first["status"], first["fix"]) == ("awake", "loose")
    # 50 NM out the first fix is about 6 NM off, already closing.
    assert 1 < _off_nm(first, 50 * NM) <= 6
    h.advance_to(120)
    calls = _sent(h, "emitter")
    assert len(calls) == 2
    assert (calls[1]["status"], calls[1]["fix"]) == ("awake", "tight")
    assert _off_nm(calls[1], 50 * NM) <= 1
    h.advance_to(600)
    assert len(_sent(h, "emitter")) == 2
    h.assert_no_lua_errors()


def test_listening_adds_up_across_blinks() -> None:
    # On for one poll in every three, never off a full minute: one on-cycle, and the
    # blinks together make the fix tight.
    h = _harness(
        [_emitter("SA-6", "Kub #1", known="")],
        [_group("Kub", RED, 50 * NM, radar=True)],
    )
    for start in range(0, 200, 30):
        h.update_unit("Kub", {"radar": True})
        h.advance_to(start + 12)
        h.update_unit("Kub", {"radar": False})
        h.advance_to(start + 30)
    h.update_unit("Kub", {"radar": True})
    h.advance_to(225)
    assert [c["fix"] for c in _sent(h, "emitter")] == ["loose", "tight"]


def test_a_far_radar_starts_at_most_15_nm_off() -> None:
    h = _harness(
        [_emitter("SA-10", "Kub #1", known="")],
        [_group("Kub", RED, 200 * NM, radar=True)],
    )
    h.advance_to(15)
    [first] = _sent(h, "emitter")
    assert first["fix"] == "loose"
    assert 10 < _off_nm(first, 200 * NM) <= 15


def test_a_site_blue_knows_starts_asleep_and_loose() -> None:
    sites = [_site("Kub", 50 * NM, 0, radar=False)]
    h = _commands(sites, [_emitter("SA-6", "Kub #1", known="loose")])
    [reply] = _ask(h, "checkin")
    assert reply["text"].startswith(
        "Ford 9, Vacuum, none awake, one asleep, nearest SA-6 asleep, bullseye "
    )
    assert reply["text"].endswith(", loose.")
    assert _sent(h, "emitter") == []


def test_fixes_are_kept_when_vacuum_lands() -> None:
    h = _harness(
        [_emitter("SA-6", "Kub #1", known="")],
        [_group("Kub", RED, 50 * NM, radar=True)],
    )
    h.advance_to(120)
    assert [c["fix"] for c in _sent(h, "emitter")] == ["loose", "tight"]
    h.update_unit("Vacuum", {"airborne": False})
    h.advance_to(200)
    h.update_unit("Vacuum", {"airborne": True})
    h.advance_to(240)
    assert [c["fix"] for c in _sent(h, "emitter")] == ["loose", "tight", "tight"]


def test_every_radar_heard_is_written_for_the_debrief() -> None:
    h = _harness(
        [
            _emitter("SA-6", "Kub #1", known=""),
            _emitter("SA-8", "Osa #1", known="loose"),
        ],
        [
            _group("Kub", RED, 50 * NM, radar=True),
            _group("Osa", RED, 30 * NM),
        ],
    )
    h.advance_to(15)
    [first] = h.to_python(h.lua.globals().vacuum_fixes)
    assert first["unit"] == "Kub #1" and first["error"] > NM
    assert h.lua.globals().dirty_state is True
    h.advance_to(120)
    # Tight by now; the never-heard Osa is not written.
    [fix] = h.to_python(h.lua.globals().vacuum_fixes)
    assert fix["error"] <= NM


def test_a_site_starts_from_the_fix_an_earlier_vacuum_left() -> None:
    sites = [_site("Kub", 50 * NM, 0, radar=False)]
    known = {**_emitter("SA-6", "Kub #1", known="loose"), "knownError": str(4 * NM)}
    h = _commands(sites, [known])
    [reply] = _ask(h, "emitters")
    assert reply["text"].endswith(", loose.")
    # 4 NM off the 50 NM-north site: the range from the caller reads 46 to 54.
    rng = int(reply["text"].split(", ")[3])
    assert 46 <= rng <= 54
