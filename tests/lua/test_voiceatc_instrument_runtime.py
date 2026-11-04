"""Headless runtime checks for Voice ATC step 3 (voiceatc-config.lua, §119): instrument
approaches.

The contract: in low weather, or when the pilot asks for an ILS, TACAN or LOC, Approach clears
the best instrument approach to the runway in use (ILS first) via its start fix, with the
altitude to keep until established and where to call Tower. Tower then clears the flight to land
on its first call. A field with no approach to the runway keeps the visual entry.
"""

from __future__ import annotations

from typing import Any, Optional

from tests.lua.harness import DcsPluginHarness
from tests.lua.test_voiceatc_approach_runtime import APPROACH, _move
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


def _approaches() -> list[dict[str, str]]:
    return [
        {
            "kind": "LOC",
            "runway": "25",
            "nav": "109.35",
            "startName": "NEPKO",
            "startDme": "",
            "startFeet": "4000",
            "finalName": "",
            "finalDme": "9.2",
            "finalFeet": "3200",
            "generated": "",
        },
        {
            "kind": "ILS",
            "runway": "25",
            "nav": "108.70",
            "startName": "TAKUP",
            "startDme": "",
            "startFeet": "3500",
            "finalName": "",
            "finalDme": "8",
            "finalFeet": "3000",
            "generated": "",
        },
    ]


def _harness(
    instrument: bool = False,
    approaches: Optional[list[dict[str, str]]] = None,
) -> DcsPluginHarness:
    field: dict[str, Any] = {
        "name": "Bodo",
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
        "instrument": "true" if instrument else "",
        "approaches": _approaches() if approaches is None else approaches,
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
                    "departure": "Bodo",
                    "arrival": "Bodo",
                }
            ],
        }
    }
    h = DcsPluginHarness()
    h.lua.execute(FAKE_AIRBASE)
    h.lua.execute(FAKE_SOCKET)
    h.lua.globals().dcsRetribution = h.to_lua({"plugins": {}, **config})
    h.add_group(_viper(True, 20 * NM))
    h.load_plugin_script(PLUGIN)
    _move(h, 20 * NM)
    return h


def test_low_weather_gets_the_ils_via_its_start_fix() -> None:
    h = _harness(instrument=True)
    _call(h, "inbound", frequency=APPROACH, text="Bodo Approach, Viper 1-1, 20 miles")
    h.advance_to(2)
    assert _texts(h)[-1] == (
        "Viper 1-1, Bodo Approach, radar contact, cleared ILS runway 25, via TAKUP, "
        "maintain 3,500 until established, at 8 DME contact Tower 262.0."
    )


def test_tower_clears_an_instrument_arrival_to_land_on_its_first_call() -> None:
    h = _harness(instrument=True)
    _call(h, "inbound", frequency=APPROACH)
    h.advance_to(2)
    _call(h, "inbound", frequency=TOWER, text="Bodo Tower, Viper 1-1, 8 DME")
    h.advance_to(4)
    text = _texts(h)[-1]
    assert text.startswith("Viper 1-1, Bodo Tower, runway 25, ")
    assert text.endswith("cleared to land.")


def test_good_weather_stays_visual_until_the_pilot_asks() -> None:
    h = _harness()
    _call(h, "inbound", frequency=APPROACH)
    h.advance_to(2)
    assert "cleared ILS" not in _texts(h)[-1]
    _call(
        h,
        "unknown",
        frequency=APPROACH,
        text="Bodo Approach, Viper 1-1, request I.L.S. approach",
    )
    h.advance_to(4)
    assert "cleared ILS runway 25, via TAKUP" in _texts(h)[-1]


def test_an_unnamed_fix_is_said_by_its_dme_and_a_generated_one_in_miles() -> None:
    loc = _approaches()[0]
    h = _harness(instrument=True, approaches=[loc])
    _call(h, "inbound", frequency=APPROACH)
    h.advance_to(2)
    assert (
        "cleared LOC runway 25, via NEPKO, maintain 4,000 until established, at 9.2 DME"
        in _texts(h)[-1]
    )
    generated = {
        **loc,
        "kind": "ILS",
        "startName": "",
        "startDme": "12",
        "startFeet": "3100",
        "finalDme": "5",
        "generated": "true",
    }
    h = _harness(instrument=True, approaches=[generated])
    _call(h, "inbound", frequency=APPROACH)
    h.advance_to(2)
    assert (
        "cleared ILS runway 25, proceed to a 12 mile final, maintain 3,100 until "
        "established, at 5 miles contact Tower" in _texts(h)[-1]
    )


def test_no_approach_to_the_runway_keeps_the_visual_entry() -> None:
    other_end = [{**_approaches()[1], "runway": "07"}]
    h = _harness(instrument=True, approaches=other_end)
    _call(h, "inbound", frequency=APPROACH)
    h.advance_to(2)
    text = _texts(h)[-1]
    assert "cleared ILS" not in text
    assert "radar contact, runway 25" in text
