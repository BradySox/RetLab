"""A mod that a shipped campaign preseeds must have a New Game toggle.

Without one, ModSettings leaves the mod off and the faction strips its units, so
the campaign's preseed is silently ignored. UH-60L was preseeded by 13 campaigns
and stripped from every new game until 2026-09-22.
"""

from __future__ import annotations

import re
from dataclasses import fields
from pathlib import Path

import yaml

from game.theater.start_generator import ModSettings

MODS_PAGE = Path("qt_ui/windows/newgame/WizardPages/QGeneratorSettings.py")
WIZARD = Path("qt_ui/windows/newgame/QNewGameWizard.py")


def _mod_flags() -> set[str]:
    return {f.name for f in fields(ModSettings) if f.type in ("bool", bool)}


def _toggles() -> set[str]:
    source = MODS_PAGE.read_text(encoding="utf-8")
    return set(re.findall(r'registerField\("(\w+)"', source)) & _mod_flags()


def test_every_mod_a_campaign_preseeds_has_a_toggle() -> None:
    preseeded: dict[str, list[str]] = {}
    for path in sorted(Path("resources/campaigns").glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for name, value in (data.get("settings") or {}).items():
            if name in _mod_flags() and value is True:
                preseeded.setdefault(name, []).append(path.stem)
    toggles = _toggles()
    assert {n: c for n, c in preseeded.items() if n not in toggles} == {}


def test_every_toggle_reaches_mod_settings() -> None:
    passed = set(
        re.findall(r'(\w+)=self\.field\("(\w+)"\)', WIZARD.read_text(encoding="utf-8"))
    )
    assert _toggles() - {name for name, field in passed if name == field} == set()
