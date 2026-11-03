"""Headless runtime checks for Voice ATC step 2 (voiceatc-config.lua, §119): Approach.

The contract: a field's Approach also works departures. Tower's takeoff clearance hands a
departure to it; it gives the chart exit nearest the flight's heading and the altitude, and
approves the frequency change when the flight reports the exit or flies past it. Inbound, it
gives the chart entry nearest the flight that serves the runway in use, and hands the flight to
Tower at the entry; Tower's first answer then needs no repeat. A field without a chart gets a
point 10 NM out. How SkyEye hears and says it is in-game only.
"""

from __future__ import annotations

import json
from typing import Any

from tests.lua.harness import DcsPluginHarness
from tests.lua.test_voiceatc_runtime import (
    FAKE_AIRBASE,
    FAKE_SOCKET,
    GROUND,
    NM,
    PLUGIN,
    TOWER,
    _call,
    _texts,
    _viper,
)

APPROACH = "264.000AM"
DEPARTURE = "266.000AM"


def _points() -> list[dict[str, str]]:
    return [
        {"name": "North", "x": str(7 * NM), "z": "0", "entry": "25", "exit": "true"},
        {"name": "South", "x": str(-7 * NM), "z": "0", "entry": "07", "exit": "true"},
        {"name": "Lake", "x": "0", "z": str(-7 * NM), "entry": "", "exit": "true"},
    ]


def _harness(
    charted: bool = True,
    x: float = 0,
    airborne: bool = False,
    departure: bool = False,
) -> DcsPluginHarness:
    field: dict[str, Any] = {
        "name": "Kobuleti",
        "airbase": "Kobuleti",
        "runway": "25",
        "runways": "07,25",
        "altimeter": "29.92",
        "ground": GROUND,
        "tower": TOWER,
        "approach": APPROACH,
        "groundVoice": "en_US-ryan-medium",
        "towerVoice": "en_US-amy-medium",
        "approachVoice": "en_GB-alan-medium",
    }
    if departure:
        field.update({"departure": DEPARTURE, "departureVoice": "en_US-joe-medium"})
    if charted:
        field.update(
            {"chart": "VAD 01", "maxAltitude": "2000", "patternAltitude": "1500"}
        )
        field["points"] = _points()
    config = {
        "voiceAtc": {
            "linkHost": "127.0.0.1",
            "linkPort": "42690",
            "fields": [field],
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
    h = DcsPluginHarness()
    h.lua.execute(FAKE_AIRBASE)
    h.lua.execute(FAKE_SOCKET)
    h.lua.globals().dcsRetribution = h.to_lua({"plugins": {}, **config})
    h.add_group(_viper(airborne, x))
    h.load_plugin_script(PLUGIN)
    return h


def _move(h: DcsPluginHarness, x: float, z: float = 0, vx: float = 0) -> None:
    h.update_unit(
        "Viper",
        {"x": x, "z": z, "airborne": True, "velocity": {"x": vx, "y": 0, "z": 0}},
    )


def test_skyeye_hears_approach_too() -> None:
    h = _harness()
    h.advance_to(2)
    sent = [m for m in h.to_python(h.lua.globals().SENT) or []]
    assert any(APPROACH in s["msg"] and '"approach"' in s["msg"] for s in sent)


def test_tower_hands_a_departure_to_departure() -> None:
    h = _harness()
    _call(h, "ready", frequency=TOWER)
    h.advance_to(2)
    assert "cleared for takeoff, contact Departure 264.0." in _texts(h)[-1]


def test_departure_gives_the_exit_ahead_and_lets_go_at_the_report() -> None:
    h = _harness()
    _move(h, 2 * NM, vx=150)
    _call(h, "airborne", frequency=APPROACH)
    h.advance_to(2)
    assert _texts(h)[-1] == (
        "Viper 1-1, Kobuleti Departure, radar contact, depart via North exit, "
        "climb and maintain 2,000, report North."
    )
    _call(h, "unknown", frequency=APPROACH, text="Kobuleti Departure, Viper 1-1, North")
    h.advance_to(4)
    assert _texts(h)[-1] == "Viper 1-1, frequency change approved."


def test_a_departure_past_its_exit_is_let_go_unasked() -> None:
    h = _harness()
    _move(h, 2 * NM, vx=150)
    _call(h, "airborne", frequency=APPROACH)
    h.advance_to(2)
    _move(h, 11 * NM, vx=150)
    h.advance_to(6)
    assert _texts(h)[-1] == "Viper 1-1, frequency change approved."


def test_an_arrival_gets_the_entry_for_the_runway_then_tower_needs_no_repeat() -> None:
    h = _harness(x=20 * NM, airborne=True)
    # South-west of the field, but the only entry for runway 25 is North.
    _move(h, -20 * NM, z=-5 * NM)
    _call(
        h, "inbound", frequency=APPROACH, text="Kobuleti Approach, Viper 1-1, 20 miles"
    )
    h.advance_to(2)
    assert _texts(h)[-1].startswith(
        "Viper 1-1, Kobuleti Approach, radar contact, runway 25, "
    )
    assert _texts(h)[-1].endswith("enter via North, maintain 2,000, report North.")
    _move(h, 7.5 * NM)
    h.advance_to(6)
    assert _texts(h)[-1] == "Viper 1-1, contact Tower 262.0."
    _call(h, "inbound", frequency=TOWER, text="Kobuleti Tower, Viper 1-1")
    h.advance_to(8)
    last = _texts(h)[-1]
    assert last.startswith("Viper 1-1, Kobuleti Tower, runway 25, ")
    assert last.endswith("report initial.")


def test_an_entry_reported_by_name_is_handed_to_tower() -> None:
    h = _harness(x=20 * NM, airborne=True)
    _call(h, "inbound", frequency=APPROACH)
    h.advance_to(2)
    _call(h, "unknown", frequency=APPROACH, text="Viper 1-1, North")
    h.advance_to(4)
    assert _texts(h)[-1] == "Viper 1-1, contact Tower 262.0."


def test_no_chart_gives_a_point_10_miles_out() -> None:
    h = _harness(charted=False, airborne=True)
    _move(h, 0, z=20 * NM)
    _call(h, "inbound", frequency=APPROACH)
    h.advance_to(2)
    # The fake field is 10 m up: 33 ft plus 2,000, to the next hundred.
    assert _texts(h)[-1].endswith(
        "proceed 10 miles east of the field, maintain 2,100, report 10 miles."
    )
    said = [m for m in h.to_python(h.lua.globals().SENT) or [] if '"say"' in m["msg"]]
    assert "two thousand one hundred" in said[-1]["msg"]
    assert "ten miles" in said[-1]["msg"]


def test_no_approach_keeps_the_old_takeoff_clearance() -> None:
    from tests.lua.test_voiceatc_runtime import _harness as old_harness

    h = old_harness()
    _call(h, "ready", frequency=TOWER)
    h.advance_to(2)
    assert _texts(h)[-1].endswith("cleared for takeoff, frequency change approved.")


def test_a_ten_mile_report_sent_digit_by_digit_lets_a_departure_go() -> None:
    # SkyEye sends "10" as "1 0"; flown 2026-11-02, the report was missed.
    for text in (
        "Kobuleti Departure, Viper 1-1, outbound, 1 0 miles",
        "Kobuleti Tower, Viper 1 1 0 miles",
    ):
        h = _harness(charted=False)
        _move(h, 2 * NM, vx=150)
        _call(h, "airborne", frequency=APPROACH)
        h.advance_to(2)
        assert _texts(h)[-1].endswith("report 10 miles.")
        _call(h, "inbound", frequency=APPROACH, text=text)
        h.advance_to(4)
        assert _texts(h)[-1] == "Viper 1-1, frequency change approved.", text


def _said_on(h: DcsPluginHarness) -> list[tuple[str, str]]:
    sent = h.to_python(h.lua.globals().SENT) or []
    said = [json.loads(m["msg"]) for m in sent if '"say"' in m["msg"]]
    return [(m["frequency"], m["text"]) for m in said]


def test_with_its_own_frequency_departure_works_the_exits_there() -> None:
    h = _harness(departure=True)
    _call(h, "ready", frequency=TOWER)
    h.advance_to(2)
    assert _texts(h)[-1].endswith("cleared for takeoff, contact Departure 266.0.")
    _move(h, 2 * NM, vx=150)
    _call(h, "airborne", frequency=DEPARTURE)
    h.advance_to(4)
    frequency, text = _said_on(h)[-1]
    assert frequency == DEPARTURE
    assert text.startswith(
        "Viper 1-1, Kobuleti Departure, radar contact, depart via North"
    )
    _call(h, "unknown", frequency=DEPARTURE, text="Viper 1-1, North")
    h.advance_to(6)
    assert _said_on(h)[-1] == (DEPARTURE, "Viper 1-1, frequency change approved.")


def test_a_call_on_the_wrong_one_is_sent_to_the_right_one() -> None:
    h = _harness(departure=True, x=2 * NM, airborne=True)
    _call(h, "airborne", frequency=APPROACH)
    h.advance_to(2)
    assert _said_on(h)[-1] == (APPROACH, "Viper 1-1, contact Departure 266.0.")
    _move(h, 20 * NM)
    _call(h, "inbound", frequency=DEPARTURE)
    h.advance_to(4)
    assert _said_on(h)[-1] == (DEPARTURE, "Viper 1-1, contact Approach 264.0.")
    _call(h, "inbound", frequency=APPROACH)
    h.advance_to(6)
    frequency, text = _said_on(h)[-1]
    assert frequency == APPROACH and "enter via North" in text


def test_skyeye_hears_departure_too() -> None:
    h = _harness(departure=True)
    h.advance_to(2)
    sent = h.to_python(h.lua.globals().SENT) or []
    assert any(DEPARTURE in m["msg"] and '"departure"' in m["msg"] for m in sent)


def _sop_harness(runway: str = "23", exit_name: str = "Lake") -> DcsPluginHarness:
    """Spangdahlem-like: right 280 to the north fixes, left 210 to the south, off 23 only."""
    field: dict[str, Any] = {
        "name": "Kobuleti",
        "airbase": "Kobuleti",
        "runway": runway,
        "runways": "05,23",
        "altimeter": "29.92",
        "ground": GROUND,
        "tower": TOWER,
        "departure": DEPARTURE,
        "approach": APPROACH,
        "chart": "52 TFW SOP",
        "maxAltitude": "2600",
        "patternAltitude": "2600",
        "points": [
            {"name": "Lake", "x": str(7 * NM), "z": "0", "entry": "23", "exit": "true"},
            {
                "name": "Bravo",
                "x": str(-7 * NM),
                "z": "0",
                "entry": "05",
                "exit": "true",
            },
        ],
        "turns": [
            {"runway": "23", "turn": "right", "heading": "280", "exits": "Lake"},
            {"runway": "23", "turn": "left", "heading": "210", "exits": "Bravo"},
        ],
    }
    config = {
        "voiceAtc": {
            "linkHost": "127.0.0.1",
            "linkPort": "42690",
            "fields": [field],
            "flights": [
                {
                    "group": "Viper",
                    "callsign": "Viper 1-1",
                    "departure": "Kobuleti",
                    "arrival": "Kobuleti",
                    "exit": exit_name,
                    "spots": [{"unit": "Viper #1", "spot": "42"}],
                }
            ],
        }
    }
    h = DcsPluginHarness()
    h.lua.execute(FAKE_AIRBASE)
    h.lua.execute(FAKE_SOCKET)
    h.lua.globals().dcsRetribution = h.to_lua({"plugins": {}, **config})
    h.add_group(_viper())
    h.load_plugin_script(PLUGIN)
    return h


def test_taxi_names_the_spawn_spot_and_takeoff_gives_the_sop_turn() -> None:
    h = _sop_harness()
    _call(h, "taxi", text="Kobuleti Ground, Viper 1-1, ready to taxi")
    h.advance_to(2)
    assert _texts(h)[-1].startswith(
        "Viper 1-1, Kobuleti Ground, from spot 42, taxi to runway 23, "
    )
    _call(h, "ready", frequency=TOWER)
    h.advance_to(4)
    assert (
        "cleared for takeoff, right turn 280, contact Departure 266.0." in _texts(h)[-1]
    )


def test_the_south_exit_turns_left_and_runway_05_has_no_turn() -> None:
    h = _sop_harness(exit_name="Bravo")
    _call(h, "ready", frequency=TOWER)
    h.advance_to(2)
    assert "cleared for takeoff, left turn 210, contact Departure" in _texts(h)[-1]
    h = _sop_harness(runway="05")
    _call(h, "ready", frequency=TOWER)
    h.advance_to(2)
    assert "cleared for takeoff, contact Departure" in _texts(h)[-1]


def test_departure_gives_the_planned_exit_whatever_the_heading() -> None:
    h = _sop_harness(exit_name="Bravo")
    # Heading north, but the route leaves by Bravo to the south.
    _move(h, 2 * NM, vx=150)
    _call(h, "airborne", frequency=DEPARTURE)
    h.advance_to(2)
    assert "depart via Bravo exit" in _texts(h)[-1]


def test_after_landing_back_home_it_is_taxi_to_parking_spot_42() -> None:
    h = _sop_harness()
    _call(
        h,
        "clear",
        frequency=TOWER,
        text="Kobuleti Tower, Viper 1-1, clear of runway 23",
    )
    h.advance_to(2)
    assert _texts(h)[-1] == "Viper 1-1, taxi to parking, spot 42."
