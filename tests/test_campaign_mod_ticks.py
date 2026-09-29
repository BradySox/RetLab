"""A campaign's mod tick only works if the New Game wizard has a box for it.

`QNewGameWizard.accept()` builds ModSettings from its own fields, so a mod the
wizard has no checkbox for is off in every new game whatever the campaign yaml
says. Anatolian Reach's Turkish BARCAP flew an F-16D gated this way and never
appeared (audit 2026-09-29).
"""

from __future__ import annotations

import re
from dataclasses import fields
from pathlib import Path

import pytest
import yaml

from game.theater.start_generator import ModSettings

WIZARD = Path("qt_ui/windows/newgame/QNewGameWizard.py")
CAMPAIGNS = sorted(Path("resources/campaigns").glob("*.yaml"))
MOD_FIELDS = {field.name for field in fields(ModSettings)}


def _wizard_mods() -> set[str]:
    source = WIZARD.read_text(encoding="utf-8")
    return set(re.findall(r'(\w+)=self\.field\("\1"\)', source)) & MOD_FIELDS


@pytest.mark.parametrize("path", CAMPAIGNS, ids=lambda p: p.stem)
def test_every_ticked_mod_has_a_wizard_box(path: Path) -> None:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    settings = data.get("settings") or {}
    ticked = {key for key in MOD_FIELDS if settings.get(key) is True}
    assert ticked - _wizard_mods() == set()


def test_the_wizard_parse_finds_the_boxes() -> None:
    assert {"iranairdefensepack", "ea6b_prowler"} <= _wizard_mods()
