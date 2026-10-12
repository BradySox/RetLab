"""The in-game-pass checklist: the main file, the archive, and one file per new row.

Every PR used to append its new ``### B###`` row at the bottom of
``docs/dev/retlab-ingame-pass-checklist.md``, so any two PRs adding rows met on
the same last lines. A new row now lives in ``docs/dev/checklist-rows/<ID>.md``,
named by its claimed id, so two PRs never touch the same file. Rows already in
the main file stay there. A settled row (verified, retired, removed or closed)
moves to the archive file, so the main file holds the rows that still owe a
flight. Readers take all three.

    python tools/checklist_rows.py new B173     # write the stub file for a claimed id
    python tools/checklist_rows.py move B170    # move a row out of the main file
    python tools/checklist_rows.py archive      # move settled rows to the archive
    python tools/checklist_rows.py archive --keep B41 S3   # ...but leave these

Every reader of the checklist (the board, the claim tool, the tests) goes
through ``checklist_text()`` or the same paths.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

CHECKLIST = Path("docs/dev/retlab-ingame-pass-checklist.md")
ARCHIVE = Path("docs/dev/retlab-ingame-pass-checklist-archive.md")
ROWS_DIR = Path("docs/dev/checklist-rows")
ROW_ID = re.compile(r"[A-Z]+[0-9]+")
ROW_HEADING = re.compile(r"^### (?P<row>[A-Z]+[0-9]+) ")
#: A row's status is the first symbol and word pair on its heading, as the board reads it.
STATUS = re.compile(
    r"[☐☑☒⊘✖✗◐✅] "
    r"(?P<word>VERIFIED|UNTESTED|PARTIAL|REGRESSED|RETIRED|REMOVED|CLOSED)"
)
#: Statuses that owe no flight.
SETTLED = frozenset({"VERIFIED", "RETIRED", "REMOVED", "CLOSED"})
ARCHIVE_HEADER = (
    "# RetLab In-Game Pass Checklist: archive\n\n"
    "Rows that owe no flight: verified, retired, removed or closed. Moved here from\n"
    "`retlab-ingame-pass-checklist.md` by `python tools/checklist_rows.py archive`, text\n"
    "unchanged. A row that regresses is moved back by hand and re-marked.\n"
)


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
    """The main file, the archive, then every row file, as one document."""
    parts = [(root / CHECKLIST).read_text(encoding="utf-8")]
    if (root / ARCHIVE).is_file():
        parts.append((root / ARCHIVE).read_text(encoding="utf-8"))
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


def _block_end(lines: list[str], start: int) -> int:
    """A row's block runs to the next ``### `` or ``## `` heading, or a ``---`` rule."""
    end = start + 1
    while end < len(lines) and not (
        lines[end].startswith(("### ", "## ")) or lines[end].strip() == "---"
    ):
        end += 1
    return end


def move(row: str) -> Path:
    """Cut one row's block out of the main file into its own file.

    The main file keeps its line endings.
    """
    raw = CHECKLIST.read_bytes().decode("utf-8")
    lines = raw.splitlines(keepends=True)
    start = next(
        (i for i, line in enumerate(lines) if line.startswith(f"### {row} ")), None
    )
    if start is None:
        raise SystemExit(f"{row} has no heading in {CHECKLIST}")
    end = _block_end(lines, start)
    target = ROWS_DIR / f"{row}.md"
    if target.exists():
        raise SystemExit(f"{target} already exists")
    block = "".join(lines[start:end]).replace("\r\n", "\n").rstrip("\n") + "\n"
    ROWS_DIR.mkdir(parents=True, exist_ok=True)
    target.write_text(block, encoding="utf-8", newline="\n")
    CHECKLIST.write_bytes("".join(lines[:start] + lines[end:]).encode("utf-8"))
    return target


def archive(keep: frozenset[str] = frozenset()) -> list[str]:
    """Move every settled row out of the main file and append it to the archive.

    ``keep`` names rows to leave where they are, for a row another branch is
    editing. The main file keeps its line endings; the archive is written with LF.
    """
    lines = CHECKLIST.read_bytes().decode("utf-8").splitlines(keepends=True)
    kept: list[str] = []
    blocks: list[str] = []
    moved: list[str] = []
    i = 0
    while i < len(lines):
        heading = ROW_HEADING.match(lines[i])
        status = STATUS.search(lines[i]) if heading else None
        if not heading or not status:
            kept.append(lines[i])
            i += 1
            continue
        end = _block_end(lines, i)
        if status["word"] in SETTLED and heading["row"] not in keep:
            block = "".join(lines[i:end]).replace("\r\n", "\n")
            blocks.append(block.rstrip("\n") + "\n")
            moved.append(heading["row"])
        else:
            kept.extend(lines[i:end])
        i = end
    if not moved:
        return []
    old = ARCHIVE.read_text(encoding="utf-8") if ARCHIVE.is_file() else ARCHIVE_HEADER
    text = "\n".join([old.rstrip("\n") + "\n", *blocks])
    ARCHIVE.write_text(text, encoding="utf-8", newline="\n")
    CHECKLIST.write_bytes("".join(kept).encode("utf-8"))
    return moved


def main(argv: list[str]) -> int:
    if argv and argv[0] == "archive":
        keep = frozenset(argv[2:]) if argv[1:2] == ["--keep"] else frozenset()
        if (argv[1:] and argv[1] != "--keep") or not all(map(ROW_ID.fullmatch, keep)):
            print(__doc__)
            return 2
        moved = archive(keep)
        print(f"{len(moved)} rows moved to {ARCHIVE}")
        return 0
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
