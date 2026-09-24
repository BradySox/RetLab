"""A plugin loop period cannot be set to 0.

The loader's default minimum is 0, and a Lua loop that reschedules at
``now + 0`` runs on every scheduler pass. Eight such options shipped without a
``minimumValue`` (2026-09-22 UI consistency audit).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from game.plugins.luaplugin import LuaPluginDefinition

PLUGINS = Path("resources/plugins")

# Loop periods only. Graces, delays and dwells also end in S, and 0 is a valid
# value for those.
LOOP_PERIOD = re.compile(r"(IntervalS|RepathS|StepS|tickSec)$")


def test_every_loop_period_has_a_positive_minimum() -> None:
    offenders = []
    checked = 0
    for manifest in sorted(PLUGINS.glob("*/plugin.json")):
        raw = json.loads(manifest.read_text(encoding="utf-8"))
        if not any(
            LOOP_PERIOD.search(o["mnemonic"]) for o in raw.get("specificOptions") or []
        ):
            continue
        definition = LuaPluginDefinition.from_json(manifest.parent.name, manifest)
        for option in definition.options:
            if not LOOP_PERIOD.search(option.identifier):
                continue
            checked += 1
            if option.min is None or option.min <= 0:
                offenders.append(option.identifier)
    assert not offenders, f"loop periods that accept 0: {offenders}"
    assert checked >= 11, "the loop-period pattern no longer matches the tree"
