"""Changelog entries live in ``changelog.d/``, one file per change.

Every PR used to add its line at the top of the same section of ``changelog.md``,
so any two open PRs conflicted there. A new entry is now its own file:

    changelog.d/<short-slug>.feature.md   -> "## Features/Improvements"
    changelog.d/<short-slug>.fix.md       -> "## Fixes"

holding one or more ``* **[Area]** ...`` lines, written exactly as they would read
in the changelog. The build renders them into the top version block of the
shipped ``changelog.md``; ``fold`` writes them into the file for good.

    python tools/changelog.py render     # the full changelog, entries folded in
    python tools/changelog.py check      # exit 1 on a malformed entry file
    python tools/changelog.py fold       # write changelog.md, delete the files
    python tools/changelog.py render --out dist/changelog.md

Fold only when cutting a version, from one session, on a fresh ``main``.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

CHANGELOG = Path("changelog.md")
FRAGMENTS = Path("changelog.d")
SECTIONS = {
    "feature": "## Features/Improvements",
    "fix": "## Fixes",
}
FRAGMENT_NAME = re.compile(r"^[a-z0-9][a-z0-9-]*\.(feature|fix)\.md$")
ENTRY_LINE = re.compile(r"^\* \*\*\[[^\]]+\]\*\* \S")


def fragments() -> list[Path]:
    if not FRAGMENTS.is_dir():
        return []
    return sorted(p for p in FRAGMENTS.iterdir() if p.name != "README.md")


def problems() -> list[str]:
    found = []
    for path in fragments():
        if not FRAGMENT_NAME.match(path.name):
            found.append(f"{path}: name it <slug>.feature.md or <slug>.fix.md")
            continue
        lines = [ln for ln in _lines(path) if ln.strip()]
        if not lines:
            found.append(f"{path}: empty")
        for line in lines:
            if not ENTRY_LINE.match(line):
                found.append(f"{path}: not a '* **[Area]** ...' line: {line[:60]}")
    return found


def _lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8-sig").splitlines()


def render() -> str:
    """changelog.md with every fragment inserted at the top of its section in the
    first version block. A section the block lacks is added at its end."""
    lines = CHANGELOG.read_text(encoding="utf-8-sig").splitlines()
    block_end = next(
        (i for i, ln in enumerate(lines) if i > 0 and ln.startswith("# ")),
        len(lines),
    )
    for kind in ("fix", "feature"):
        entries = [
            ln
            for path in fragments()
            if path.name.endswith(f".{kind}.md")
            for ln in _lines(path)
            if ln.strip()
        ]
        if not entries:
            continue
        header = SECTIONS[kind]
        at = next((i for i in range(block_end) if lines[i].strip() == header), None)
        if at is None:
            lines[block_end:block_end] = [header] + entries + [""]
            block_end += len(entries) + 2
        else:
            lines[at + 1 : at + 1] = entries
            block_end += len(entries)
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    command = argv[0] if argv else ""
    if command == "check":
        bad = problems()
        print("\n".join(bad) or f"{len(fragments())} changelog entries OK")
        return 1 if bad else 0
    if command not in {"render", "fold"}:
        print(__doc__)
        return 2
    bad = problems()
    if bad:
        print("\n".join(bad), file=sys.stderr)
        return 1
    text = render()
    if command == "fold":
        CHANGELOG.write_text(text, encoding="utf-8-sig")
        for path in fragments():
            path.unlink()
        print(f"folded into {CHANGELOG}")
    elif "--out" in argv:
        out = Path(argv[argv.index("--out") + 1])
        out.write_text(text, encoding="utf-8-sig")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
