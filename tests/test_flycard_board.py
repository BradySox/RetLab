"""The session-start board must agree with the documents it summarises.

Everything here is a defect that actually shipped. The board is read at the top of
every session and is the only surface that routes cockpit time, so a board that
lies costs flights: six rows closed with a marker the parser did not know were
briefed as outstanding work for two weeks, and two crossed-off fly-card items were
briefed as live for two days after they were closed.

The rules mirror `.claude/hooks/session-start.sh`. Keep the two in step.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from checklist_board import (  # type: ignore[import-not-found]  # noqa: E402
    ROW_DIR,
    checklist_text,
    row_files,
)

CHECKLIST = Path("docs/dev/retlab-ingame-pass-checklist.md")
WATCH = Path("docs/dev/flycards/WATCH.md")
LOCAL = Path("docs/dev/flycards/LOCAL.md")

#: A row's status is the first `<symbol> <WORD>` pair on its heading line. Pairing
#: the symbol with the word is what survives someone inventing a marker; matching
#: whole fixed strings is what let `✅ CLOSED` fall through to the "(was ☐ UNTESTED"
#: that every re-verified row quotes.
STATUS = re.compile(
    r"(?P<symbol>[\u2610\u2611\u2612\u2298\u2716\u2717\u25d0\u2705]) "
    r"(?P<word>VERIFIED|UNTESTED|PARTIAL|REGRESSED|RETIRED|REMOVED|CLOSED)"
)

#: Row ids are a letter block plus a number: B6, G19, S2, C9. The `### Session 1 —`
#: headings under "Drain order" are prose, not rows, and carry no status.
ROW_HEADING = re.compile(r"^### (?P<row>[A-Z]+[0-9]+) ")

#: A card section holding history rather than work. Matches the hook's list.
DEAD_SECTION = re.compile(
    r"^## *(Done|Archive|Archived|Closed|Dropped|Superseded|Parking)", re.I
)

#: An item crossed off in place still says so in its own heading.
CLOSED_ITEM = re.compile(r"CLOSED|OFF THE CARD|DONE|VERIFIED")


def _legend() -> dict[str, str]:
    """The `Status legend` table: symbol -> word.

    Scanned line by line and stopped at the section's closing rule. Slicing to the
    next ``---`` instead lands on the table's own ``|---|---|`` separator, which
    yields an empty legend and makes every check below pass vacuously.
    """
    lines = CHECKLIST.read_text(encoding="utf-8").splitlines()
    start = next(
        i for i, line in enumerate(lines) if line.startswith("## Status legend")
    )
    marks = {}
    for line in lines[start + 1 :]:
        if line.strip() == "---":
            break
        found = STATUS.search(line)
        if found:
            marks[found["symbol"]] = found["word"]
    assert marks, "Status legend table parsed empty"
    return marks


def _row_statuses() -> dict[str, str]:
    """Row id -> status word, taken from the `### ` headings."""
    statuses = {}
    for line in checklist_text().splitlines():
        heading = ROW_HEADING.match(line)
        if not heading:
            continue
        found = STATUS.search(line)
        if found:
            statuses[heading["row"]] = found["word"]
    return statuses


def _live_card_items(path: Path) -> list[str]:
    """The `### ` items a reader is actually being asked to do."""
    items: list[str] = []
    live = True
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            live = not DEAD_SECTION.match(line)
        elif line.startswith("### ") and live:
            items.append(line[4:])
    return items


def test_no_two_rows_share_an_id() -> None:
    """A long-lived branch and main allocate row ids from the same end.

    Four collisions on the §98 branch alone -- B100/B101, then B106/B107, then
    B110/B111 twice. `_row_statuses()` keys by id, so a duplicate silently
    overwrites its twin and the board under-reports outstanding work; the
    count test catches that only indirectly, and only when the two rows differ
    in status. The fourth collision landed on a row already marked VERIFIED,
    so being closed is no protection either.
    """
    from collections import Counter

    ids = [
        heading["row"]
        for line in checklist_text().splitlines()
        if (heading := ROW_HEADING.match(line))
    ]
    repeated = sorted(row for row, n in Counter(ids).items() if n > 1)
    assert not repeated, (
        f"row id(s) used twice: {', '.join(repeated)}. Claim a free id for YOUR "
        "row with `python tools/claim_id.py row`, never renumber main's, and "
        "update the features doc, the design note and any `row:` in "
        "resources/whatsnew/."
    )


#: The last row written into the checklist file itself. Every row after it has its
#: own file in docs/dev/checklist-rows/, because rows appended at the end of one
#: file conflicted between every pair of PRs that each added one.
LAST_ROW_IN_THE_CHECKLIST_FILE = 172


def test_new_rows_get_their_own_file() -> None:
    late = [
        heading["row"]
        for line in CHECKLIST.read_text(encoding="utf-8").splitlines()
        if (heading := ROW_HEADING.match(line))
        and heading["row"].startswith("B")
        and int(heading["row"][1:]) > LAST_ROW_IN_THE_CHECKLIST_FILE
    ]
    assert not late, (
        f"row(s) {late} were added to the checklist file; move each to "
        f"{ROW_DIR}/<id>.md (see its README)"
    )


def test_each_row_file_holds_one_row_named_for_its_id() -> None:
    for path in row_files():
        rows = [
            heading["row"]
            for line in path.read_text(encoding="utf-8").splitlines()
            if (heading := ROW_HEADING.match(line))
        ]
        assert rows == [path.stem], f"{path} must hold exactly row {path.stem}"


def test_row_files_are_read_with_the_checklist(tmp_path: Path) -> None:
    checklist = tmp_path / "checklist.md"
    checklist.write_text("### B1 — old · x · ☑ VERIFIED\n", encoding="utf-8")
    rows = tmp_path / "rows"
    rows.mkdir()
    (rows / "B2.md").write_text("### B2 — new · y · ☐ UNTESTED\n", encoding="utf-8")
    (rows / "README.md").write_text("### not a row\n", encoding="utf-8")
    text = checklist_text(checklist, rows)
    assert "### B1 " in text and "### B2 " in text and "not a row" not in text


def test_every_row_heading_carries_a_legend_marker() -> None:
    # A row whose marker is not in the legend is invisible to the board: it is
    # dropped from the counts, and the parser falls through to whatever marker the
    # row's prose quotes next -- which is how a CLOSED row gets briefed as work.
    legend = _legend()
    unmarked = []
    unknown = []
    for line in checklist_text().splitlines():
        heading = ROW_HEADING.match(line)
        if not heading:
            continue
        found = STATUS.search(line)
        if not found:
            unmarked.append(heading["row"])
        elif legend.get(found["symbol"]) != found["word"]:
            unknown.append(f"{heading['row']}: {found['symbol']} {found['word']}")
    assert not unmarked, f"checklist row heading(s) with no status marker: {unmarked}"
    assert not unknown, (
        "checklist row heading(s) using a symbol/word pair the Status legend does "
        f"not list: {unknown}"
    )


def test_the_checklist_keeps_no_hand_written_summary() -> None:
    # The at-a-glance table and its "N rows need a live pass" count were edited by
    # every PR that touched a row, so parallel PRs conflicted there, and they drifted
    # from the headings on four rows. `tools/checklist_board.py` derives both now.
    legend = _legend()
    text = CHECKLIST.read_text(encoding="utf-8")
    assert not re.search(r"^\d+ rows need a live pass", text, re.M), (
        "the checklist states an outstanding count again; "
        "`python tools/checklist_board.py` prints it"
    )
    summary = [
        line
        for line in text.splitlines()
        if (cells := [c.strip() for c in line.split("|")])
        and len(cells) == 6
        and re.fullmatch(r"[A-Z]+[0-9]+", cells[1])
        and cells[4] in legend
    ]
    assert not summary, (
        "the checklist carries a hand-kept summary table again: "
        f"{summary[:3]}; `python tools/checklist_board.py` prints it"
    )


def test_the_board_tool_counts_what_the_headings_say() -> None:
    import subprocess
    import sys

    printed = subprocess.run(
        [sys.executable, "tools/checklist_board.py"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout
    open_now = sum(
        1 for w in _row_statuses().values() if w in {"UNTESTED", "PARTIAL", "REGRESSED"}
    )
    assert printed.startswith(f"{open_now} rows need a live pass.")


def test_fly_cards_hold_no_closed_items_in_their_live_section() -> None:
    # `G29` and the `B25` follow-on were both crossed off on 2026-08-20 and both kept
    # being briefed, because the hook read every heading in the file rather than only
    # the live section. Closing an item has to actually take it off the board.
    for path in (WATCH, LOCAL):
        stale = [i for i in _live_card_items(path) if CLOSED_ITEM.search(i)]
        assert not stale, f"{path} briefs closed item(s) as live work: {stale}"


def test_fly_card_items_name_a_checklist_row_that_is_still_open() -> None:
    # Seeding a card from a stale checklist inherits the staleness: the parking lot
    # carried `Q3` after it was VERIFIED, and a loadout watch for RETIRED `B42`.
    rows = _row_statuses()
    for path in (WATCH, LOCAL):
        for item in _live_card_items(path):
            ids = re.findall(r"`([A-Z]+[0-9]+)`", item)
            assert ids, f"{path} item names no checklist row: {item}"
            for row in ids:
                assert row in rows, f"{path} names unknown checklist row {row}"
                assert rows[row] in {
                    "UNTESTED",
                    "PARTIAL",
                    "REGRESSED",
                }, f"{path} asks for {row}, which is already {rows[row]}"


def test_watch_card_respects_its_five_slot_cap() -> None:
    # "A watch list of twenty items is a watch list of zero." The cap is the card's
    # own rule and the reason it gets read at all.
    items = _live_card_items(WATCH)
    assert len(items) <= 5, f"WATCH.md has {len(items)} items, cap is 5"
