from __future__ import annotations

from pathlib import Path

from tools.audit_stale_docs import REMOVAL_WORDS, Removed, scan


def test_a_phrase_split_by_a_line_wrap_is_still_found(tmp_path: Path) -> None:
    # "comms\njamming" sat on a published wiki page past the comms[ -]jam row
    # until 2026-09-22: the rows were matched against the raw, wrapped block.
    page = tmp_path / "page.md"
    page.write_text(
        "Combat SAR, comms\njamming and the briefing cards are cheap.\n",
        encoding="utf-8",
    )
    findings = scan([page])
    assert [entry.what for entry, *_ in findings] == ["enemy comms jamming (S51)"]
    assert findings[0][2] == 1


def test_a_wrapped_removal_notice_is_still_allowed(tmp_path: Path) -> None:
    page = tmp_path / "page.md"
    page.write_text(
        "Enemy comms\njamming was removed on 2026-09-07.\n", encoding="utf-8"
    )
    assert scan([page]) == []


def test_one_bullets_disclaimer_does_not_excuse_its_neighbour(tmp_path: Path) -> None:
    # README's GPS-jamming bullet said "an unscouted one is not" inside a list whose
    # other bullets carried the allow words, so the whole list read as a notice.
    page = tmp_path / "page.md"
    page.write_text(
        "- Enemy comms jamming was removed.\n- An unscouted site stays hidden.\n",
        encoding="utf-8",
    )
    findings = scan([page])
    assert [(entry.what, line) for entry, _path, line, _text in findings] == [
        ("phrasings that outlived their feature", 2)
    ]


def test_a_reversal_row_is_not_excused_by_the_removal_words() -> None:
    # For a reversal, "retired" is the stale claim, not a notice: a strict row takes
    # only its own allow words. (The MIST reversal row this was written for went when
    # MIST was removed for good, 2026-11-12.)
    row = Removed("a reversed removal", "n/a", r"x", allow=("until",), strict=True)
    assert row.allowed == ("until",)
    assert set(REMOVAL_WORDS) <= set(Removed("x", "n/a", r"x").allowed)


def test_a_page_saying_mist_loads_is_flagged(tmp_path: Path) -> None:
    page = tmp_path / "page.md"
    page.write_text("MIST is upstream's own build.\n", encoding="utf-8")
    findings = scan([page])
    assert [entry.what for entry, *_ in findings] == [
        "MIST in the mission (removed 2026-11-12)"
    ]
