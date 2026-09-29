from pathlib import Path

import pytest

from tools.checklist_rows import CHECKLIST, ROWS_DIR, checklist_text, move, stub

MAIN = (
    "# Checklist\r\n\r\n"
    "### B1 — first · §1 · ☐ UNTESTED\r\n\r\nbody one\r\n\r\n"
    "### B2 — second · §2 · ◐ PARTIAL\r\n\r\nbody two\r\n"
)


@pytest.fixture
def tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / CHECKLIST).parent.mkdir(parents=True)
    (tmp_path / CHECKLIST).write_bytes(MAIN.encode("utf-8"))
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_move_cuts_one_row_and_keeps_the_main_files_line_endings(tree: Path) -> None:
    target = move("B1")
    assert target.read_text(encoding="utf-8") == (
        "### B1 — first · §1 · ☐ UNTESTED\n\nbody one\n"
    )
    assert (tree / CHECKLIST).read_bytes().decode("utf-8") == (
        "# Checklist\r\n\r\n### B2 — second · §2 · ◐ PARTIAL\r\n\r\nbody two\r\n"
    )


def test_the_combined_text_reads_row_files_in_id_order(tree: Path) -> None:
    for row in ("B10", "B9"):
        stub(row)
    headings = [
        line.split(" — ")[0]
        for line in checklist_text().splitlines()
        if line.startswith("### ")
    ]
    assert headings == ["### B1", "### B2", "### B9", "### B10"]


def test_stub_never_overwrites_a_row(tree: Path) -> None:
    path = stub("B3")
    path.write_text("### B3 — written · §3 · ☐ UNTESTED\n", encoding="utf-8")
    stub("B3")
    assert "written" in (tree / ROWS_DIR / "B3.md").read_text(encoding="utf-8")
