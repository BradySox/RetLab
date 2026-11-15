"""Every MOOSE class a plugin calls is still in the bundled Moose.lua.

MOOSE develop deleted its AI/ and Tasking/ folders on 2026-02-06. The 2026-11-12
bundle bump (#1501) pulled that build, so AI_A2A_DISPATCHER and
DETECTION_MANAGER vanished and the QRA plugin died on its first line in every
mission. The plugin harness missed it because its fakes define the classes
themselves. This scan reads the real bundle instead.

A name counts as used when a plugin calls ``NAME:method`` or reads ``NAME.field``
outside a comment, and as defined when Moose.lua or any plugin assigns it.
"""

from __future__ import annotations

import re
from pathlib import Path

from tests.lua.harness import REPO_ROOT

PLUGINS = REPO_ROOT / "resources" / "plugins"
MOOSE = PLUGINS / "base" / "Moose.lua"

_ASSIGNED = re.compile(r"^\s*(?:local\s+)?([A-Z][A-Z0-9_]{2,})\s*=(?!=)", re.MULTILINE)
_USED = re.compile(r"(?<![\w.])([A-Z][A-Z0-9_]{2,})\s*[:.]\s*[A-Za-z_]")
_BLOCK_COMMENT = re.compile(r"--\[(=*)\[.*?\]\1\]", re.DOTALL)
_LINE_COMMENT = re.compile(r"--[^\n]*")
_STRING = re.compile(r"\"(?:\\.|[^\"\\\n])*\"|'(?:\\.|[^'\\\n])*'")


def _code(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="ignore")
    text = _BLOCK_COMMENT.sub("", text)
    text = _STRING.sub('""', text)
    return _LINE_COMMENT.sub("", text)


def _plugin_files() -> list[Path]:
    return [p for p in sorted(PLUGINS.rglob("*.lua")) if p != MOOSE]


def test_every_moose_class_a_plugin_uses_is_defined() -> None:
    defined = set(_ASSIGNED.findall(_code(MOOSE)))
    sources = {path: _code(path) for path in _plugin_files()}
    for code in sources.values():
        defined.update(_ASSIGNED.findall(code))

    missing: dict[str, list[str]] = {}
    for path, code in sources.items():
        for name in set(_USED.findall(code)) - defined:
            missing.setdefault(name, []).append(str(path.relative_to(REPO_ROOT)))

    assert not missing, (
        "plugins use MOOSE names the bundle no longer defines (a bundle bump "
        f"dropped them?): {missing}"
    )


def test_the_scan_sees_the_classes_qra_needs() -> None:
    """Guard the scan itself: if these stop matching, the test above is inert."""
    defined = set(_ASSIGNED.findall(_code(MOOSE)))
    for name in ("EASYGCICAP", "SQUADRON", "AIRWING", "AUFTRAG", "STATIC"):
        assert name in defined, f"{name} not found in Moose.lua"
    qra = _code(PLUGINS / "intercept" / "intercept-config.lua")
    assert "EASYGCICAP" in set(_USED.findall(qra))
