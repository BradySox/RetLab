"""Changelog entries are files in `changelog.d/`, rendered into `changelog.md`.

Every PR used to add its line at the top of the same changelog section, so any two
open PRs conflicted there. The files must stay well-formed, because the release
build renders them and a bad one would ship as a broken line.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import changelog  # type: ignore[import-not-found]  # noqa: E402


def test_every_changelog_entry_file_is_well_formed() -> None:
    assert changelog.problems() == []


def test_the_shipped_changelog_renders() -> None:
    text = changelog.render()
    assert text.splitlines()[0].startswith("# Retribution")


def test_entries_land_at_the_top_of_their_section(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "changelog.md").write_text(
        "﻿# v2\n\n## Features/Improvements\n* **[UI]** old\n\n"
        "# v1\n\n## Fixes\n* **[UI]** older\n",
        encoding="utf-8",
    )
    fragments = tmp_path / "changelog.d"
    fragments.mkdir()
    (fragments / "a.feature.md").write_text("* **[UI]** new\n", encoding="utf-8")
    (fragments / "b.fix.md").write_text("* **[Campaign]** fixed\n", encoding="utf-8")
    (fragments / "README.md").write_text("ignored", encoding="utf-8")
    monkeypatch.setattr(changelog, "CHANGELOG", tmp_path / "changelog.md")
    monkeypatch.setattr(changelog, "FRAGMENTS", fragments)

    lines = changelog.render().splitlines()
    assert lines[:5] == [
        "# v2",
        "",
        "## Features/Improvements",
        "* **[UI]** new",
        "* **[UI]** old",
    ]
    # v2 has no Fixes section, so one is added to v2, not appended to v1's.
    v1 = lines.index("# v1")
    fixes = lines.index("## Fixes")
    assert fixes < v1 and lines[fixes + 1] == "* **[Campaign]** fixed"


def test_a_malformed_entry_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "Bad Name.md").write_text("* **[UI]** x\n", encoding="utf-8")
    (tmp_path / "prose.fix.md").write_text("Fixed a thing.\n", encoding="utf-8")
    monkeypatch.setattr(changelog, "FRAGMENTS", tmp_path)
    assert len(changelog.problems()) == 2
