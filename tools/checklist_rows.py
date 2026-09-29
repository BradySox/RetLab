"""The in-game-pass checklist: the main file plus one file per new row.

Every PR used to append its new ``### B###`` row at the bottom of
``docs/dev/retlab-ingame-pass-checklist.md``, so any two PRs adding rows met on
the same last lines. A new row now lives in ``docs/dev/checklist-rows/<ID>.md``,
named by its claimed id, so two PRs never touch the same file. Rows already in
the main file stay there; readers take both.

    python tools/checklist_rows.py new B173     # write the stub file for a claimed id
    python tools/checklist_rows.py move B170    # move a row out of the main file

Every reader of the checklist (the board, the claim tool, the session-start hook,
the tests) goes through ``checklist_text()`` or the same two paths.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

CHECKLIST = Path("docs/dev/retlab-ingame-pass-checklist.md")
ROWS_DIR = Path("docs/dev/checklist-rows")
ROW_ID = re.compile(r"[A-Z]+[0-9]+")
ROW_HEADING = re.compile(r"^### (?P<row>[A-Z]+[0-9]+) ")


def _natural(path: Path) -> tuple[str, int]:
    block = path.stem.rstrip("0123456789")
    return block, int(path.stem[len(block) :])


def row_files(root: Path = Path(".")) -> list[Path]:
    """Every ``<ID>.md`` in the rows directory, in id order (B9 before B10)."""
    folder = root / ROWS_DIR
    if not folder.is_dir():
        return []
    found = [p for p in folder.glob("*.md") if ROW_ID.fullmatch(p.stem)]
    return sorted(found, key=_natural)


def checklist_text(root: Path = Path(".")) -> str:
    """The main file followed by every row file, as one document."""
    parts = [(root / CHECKLIST).read_text(encoding="utf-8")]
    parts += [p.read_text(encoding="utf-8") for p in row_files(root)]
    return "\n".join(part.rstrip("\n") + "\n" for part in parts)


def stub(row: str) -> Path:
    """Write the heading template for a freshly claimed row; never overwrites."""
    path = ROWS_DIR / f"{row}.md"
    if not path.exists():
        ROWS_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"### {row} — <what it checks> · <feature or §N> · ☐ UNTESTED\n\n"
            "**Pass:** \n\n**Fail signature:** \n",
            encoding="utf-8",
            newline="\n",
        )
    return path


def move(row: str) -> Path:
    """Cut one row's block out of the main file into its own file.

    The block runs from its ``### <ID> `` heading to the next ``### `` or ``## ``
    heading, or a ``---`` rule. The main file keeps its line endings.
    """
    raw = CHECKLIST.read_bytes().decode("utf-8")
    lines = raw.splitlines(keepends=True)
    start = next(
        (i for i, line in enumerate(lines) if line.startswith(f"### {row} ")), None
    )
    if start is None:
        raise SystemExit(f"{row} has no heading in {CHECKLIST}")
    end = start + 1
    while end < len(lines) and not (
        lines[end].startswith(("### ", "## ")) or lines[end].strip() == "---"
    ):
        end += 1
    target = ROWS_DIR / f"{row}.md"
    if target.exists():
        raise SystemExit(f"{target} already exists")
    block = "".join(lines[start:end]).replace("\r\n", "\n").rstrip("\n") + "\n"
    ROWS_DIR.mkdir(parents=True, exist_ok=True)
    target.write_text(block, encoding="utf-8", newline="\n")
    CHECKLIST.write_bytes("".join(lines[:start] + lines[end:]).encode("utf-8"))
    return target


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[0] not in {"new", "move"}:
        print(__doc__)
        return 2
    for row in argv[1:]:
        if not ROW_ID.fullmatch(row):
            raise SystemExit(f"not a row id: {row!r}")
        print(stub(row) if argv[0] == "new" else move(row))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
