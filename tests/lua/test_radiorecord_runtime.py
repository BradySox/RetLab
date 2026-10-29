"""Headless runtime checks for the radiorecord plugin (radiorecord-config.lua, §127).

The contract: with dcsRetribution.radioRecord set, the plugin sends SkyEye one record
message a few seconds in and again every minute, listing each frequency with its label,
recordOnly as a JSON boolean. With no node it sends nothing. What SkyEye records is
in-game only (B301).
"""

from __future__ import annotations

import json
from typing import Any

from tests.lua.harness import DcsPluginHarness
from tests.lua.test_vacuum_runtime import FAKE_SOCKET

PLUGIN = "resources/plugins/radiorecord/radiorecord-config.lua"


def _sent(h: DcsPluginHarness) -> list[dict[str, Any]]:
    sent = h.to_python(h.lua.globals().SENT)
    return [json.loads(s["msg"]) for s in sent] if isinstance(sent, list) else []


def test_no_node_is_a_clean_noop() -> None:
    h = DcsPluginHarness()
    h.lua.execute(FAKE_SOCKET)
    h.set_retribution_config()
    h.load_plugin_script(PLUGIN)
    h.advance_to(600)
    assert _sent(h) == []


def test_the_record_message_lists_every_frequency_and_repeats() -> None:
    h = DcsPluginHarness()
    h.lua.execute(FAKE_SOCKET)
    node = {
        "linkHost": "127.0.0.1",
        "linkPort": "42690",
        "frequencies": [
            {"frequency": "251.000AM", "label": "AWACS", "recordOnly": ""},
            {"frequency": "130.250AM", "label": "Enfield 4", "recordOnly": "true"},
        ],
    }
    h.lua.globals().dcsRetribution = h.to_lua({"plugins": {}, "radioRecord": node})
    h.load_plugin_script(PLUGIN)
    h.advance_to(10)
    sent = _sent(h)
    assert sent == [
        {
            "type": "record",
            "frequencies": [
                {"frequency": "251.000AM", "label": "AWACS", "recordOnly": False},
                {"frequency": "130.250AM", "label": "Enfield 4", "recordOnly": True},
            ],
        }
    ]
    h.advance_to(130)
    assert len(_sent(h)) == 3
