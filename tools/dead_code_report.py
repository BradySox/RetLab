"""Report dead Python code: unused imports and high-confidence unused names.

Two checks, both cheap and both near-zero on a clean tree:

- pyflakes' "imported but unused", skipping ``__init__.py`` (re-exports) and any
  line marked ``noqa`` (a deliberate side-effect import).
- vulture at >= 80 % confidence: unused imports, unused variables, unreachable
  code. ``tools/vulture_whitelist.py`` lists the names a signature requires but
  the body never reads.

Exit 1 when either finds anything. Run from the repo root:

    python tools/dead_code_report.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOTS = ["game", "qt_ui", "tools"]
WHITELIST = "tools/vulture_whitelist.py"


def unused_imports() -> list[str]:
    result = subprocess.run(
        [sys.executable, "-m", "pyflakes", *ROOTS],
        capture_output=True,
        text=True,
    )
    findings = []
    for line in result.stdout.splitlines():
        if "imported but unused" not in line:
            continue
        path, lineno = line.split(":")[:2]
        path = path.replace("\\", "/")
        if path.endswith("__init__.py") or path == WHITELIST:
            continue
        source = Path(path).read_text(encoding="utf-8").splitlines()
        if "noqa" in source[int(lineno) - 1]:
            continue
        findings.append(line)
    return findings


def unused_names() -> list[str]:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "vulture",
            *ROOTS,
            WHITELIST,
            "--min-confidence",
            "80",
            "--exclude",
            "*/tests/*",
        ],
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def main() -> int:
    imports = unused_imports()
    names = unused_names()
    for line in imports + names:
        print(line)
    print(f"{len(imports)} unused import(s), {len(names)} unused name(s)")
    return 1 if imports or names else 0


if __name__ == "__main__":
    sys.exit(main())
