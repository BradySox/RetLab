"""Claim the next checklist row id or features-doc section number, race-free.

Two parallel branches used to pick the same next ``B###`` or ``§N`` by reading
their own copy of the docs, and one had to renumber by hand. A claim is a ref on
GitHub, ``refs/retlab-claims/<kind>/<id>``, pointing at a root commit made just
for it. Pushing a ref that already exists is rejected as a non-fast-forward, so
two sessions can never both win the same number. No workflow triggers on these
refs; they are never merged and cost nothing to leave behind.

    python tools/claim_id.py row          # next B row, prints e.g. B158
    python tools/claim_id.py row G        # next row in another letter block
    python tools/claim_id.py section      # next features-doc §N, prints e.g. 108
    python tools/claim_id.py list         # every claim on the remote

The next id is one past the highest of: origin/main's docs, this checkout's docs,
and every existing claim. Claim once per new row or section, then write it.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable

REMOTE = "origin"
CLAIM_PREFIX = "refs/retlab-claims"
CHECKLIST = "docs/dev/retlab-ingame-pass-checklist.md"
FEATURES_DOC = "docs/dev/retlab-features.md"
REGISTRY = "game/retlab/features.py"
MAX_ATTEMPTS = 25


def _git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        input="",
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=check,
    )


def _texts(path: str) -> Iterable[str]:
    """The file as origin/main has it, and as this checkout has it."""
    shown = _git("show", f"{REMOTE}/main:{path}", check=False)
    if shown.returncode == 0:
        yield shown.stdout
    local = Path(path)
    if local.is_file():
        yield local.read_text(encoding="utf-8")


def _claimed(kind: str) -> list[str]:
    listing = _git("ls-remote", REMOTE, f"{CLAIM_PREFIX}/{kind}/*").stdout
    return [line.rsplit("/", 1)[1] for line in listing.splitlines() if "/" in line]


def _highest_row(block: str) -> int:
    pattern = re.compile(rf"^### {block}([0-9]+) ", re.M)
    found = [int(n) for text in _texts(CHECKLIST) for n in pattern.findall(text)]
    claimed = [
        int(row[len(block) :])
        for row in _claimed("rows")
        if re.fullmatch(rf"{block}[0-9]+", row)
    ]
    return max(found + claimed, default=0)


def _highest_section() -> int:
    heading = re.compile(r"^## (?:§)?([0-9]+)[. ]", re.M)
    registered = re.compile(r"^\s+([0-9]+),\s*$", re.M)
    found = [int(n) for text in _texts(FEATURES_DOC) for n in heading.findall(text)]
    found += [int(n) for text in _texts(REGISTRY) for n in registered.findall(text)]
    claimed = [int(n) for n in _claimed("sections") if n.isdigit()]
    return max(found + claimed, default=0)


def _try_claim(kind: str, ident: str) -> bool:
    branch = _git("branch", "--show-current", check=False).stdout.strip() or "detached"
    empty_tree = _git("hash-object", "-t", "tree", "--stdin").stdout.strip()
    message = f"claim {kind}/{ident} for {branch}"
    commit = _git("commit-tree", empty_tree, "-m", message).stdout.strip()
    pushed = _git(
        "push", REMOTE, f"{commit}:{CLAIM_PREFIX}/{kind}/{ident}", check=False
    )
    return pushed.returncode == 0


def claim(kind: str, block: str = "B") -> str:
    _git("fetch", "--quiet", REMOTE, "main", check=False)
    if kind == "rows":
        start = _highest_row(block) + 1
        candidates = [f"{block}{n}" for n in range(start, start + MAX_ATTEMPTS)]
    else:
        start = _highest_section() + 1
        candidates = [str(n) for n in range(start, start + MAX_ATTEMPTS)]
    for ident in candidates:
        if _try_claim(kind, ident):
            return ident
    raise SystemExit(f"could not claim a {kind} id after {MAX_ATTEMPTS} tries")


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in {"row", "section", "list"}:
        print(__doc__)
        return 2
    if argv[0] == "list":
        for kind in ("rows", "sections"):
            print(f"{kind}: {', '.join(sorted(_claimed(kind))) or '(none)'}")
        return 0
    if argv[0] == "row":
        block = argv[1] if len(argv) > 1 else "B"
        if not re.fullmatch(r"[A-Z]+", block):
            raise SystemExit(f"row block must be capital letters, not {block!r}")
        print(claim("rows", block))
    else:
        print(claim("sections"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
