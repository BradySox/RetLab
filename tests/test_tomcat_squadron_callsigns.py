"""Every Tomcat squadron file carries a one-word radio callsign.

The name is written straight into each unit's DCS callsign, and every stock DCS
callsign is a single word, so a space or punctuation is not risked.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

SQUADRONS = Path("resources/squadrons")
#: Fictional squadron, left on stock callsigns.
EXEMPT = {"VMF-29"}

TOMCAT_FILES = sorted(
    path
    for folder in SQUADRONS.glob("F-14*")
    for path in folder.glob("*.yaml")
    if path.stem not in EXEMPT
)


def test_the_tomcat_squadron_files_are_found() -> None:
    assert len(TOMCAT_FILES) == 18


@pytest.mark.parametrize(
    "path", TOMCAT_FILES, ids=lambda p: f"{p.parent.name}/{p.stem}"
)
def test_tomcat_squadron_has_a_one_word_callsign(path: Path) -> None:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    callsign = data.get("callsign")
    assert isinstance(callsign, str) and callsign
    assert callsign.isalpha()
    assert len(callsign) <= 12


def test_a_squadron_keeps_one_callsign_across_airframes() -> None:
    by_squadron: dict[str, set[str]] = {}
    for path in TOMCAT_FILES:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        by_squadron.setdefault(path.stem, set()).add(data["callsign"])
    assert all(len(names) == 1 for names in by_squadron.values()), by_squadron
