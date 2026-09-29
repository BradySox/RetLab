"""Print the in-game-pass checklist's outstanding rows, read from the row headings.

The checklist used to carry this as a hand-kept "at a glance" table with a stated
count. Every PR that added or re-graded a row edited both, so parallel PRs
conflicted there even when their rows were unrelated. The row heading is the
record; this derives the summary from it instead.

    python tools/checklist_board.py          # outstanding rows only
    python tools/checklist_board.py --all    # every row, any status
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

CHECKLIST = Path("docs/dev/retlab-ingame-pass-checklist.md")

# Same pairing as tests/test_flycard_board.py and .claude/hooks/session-start.sh.
STATUS = re.compile(
    r"(?P<symbol>[☐☑☒⊘✖✗◐✅]) "
    r"(?P<word>VERIFIED|UNTESTED|PARTIAL|REGRESSED|RETIRED|REMOVED|CLOSED)"
)
ROW = re.compile(r"^### (?P<row>[A-Z]+[0-9]+) — (?P<rest>.*)$")
OUTSTANDING = {"UNTESTED", "PARTIAL", "REGRESSED"}


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    text = CHECKLIST.read_text(encoding="utf-8")
    everything = "--all" in argv
    table = []
    for line in text.splitlines():
        heading = ROW.match(line)
        status = STATUS.search(line) if heading else None
        if not heading or not status:
            continue
        if not everything and status["word"] not in OUTSTANDING:
            continue
        parts = [p.strip() for p in heading["rest"].split(" · ")]
        feature = parts[1] if len(parts) > 2 else ""
        table.append(
            f"| {heading['row']} | {parts[0]} | {feature} | {status['symbol']} |"
        )
    label = "rows" if everything else "rows need a live pass"
    print(f"{len(table)} {label}.\n")
    print("| Row | What it checks | Feature | |\n|---|---|---|---|")
    print("\n".join(table))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
