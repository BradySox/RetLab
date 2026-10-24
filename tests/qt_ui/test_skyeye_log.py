"""The SkyEye log button shows the end of Take off's SkyEye log (§120)."""

from __future__ import annotations

from pathlib import Path

from qt_ui.windows.SkyEyeLogDialog import log_tail


def test_the_last_lines_are_shown(tmp_path: Path) -> None:
    log = tmp_path / "skyeye-takeoff.log"
    log.write_text("\n".join(f"line {n}" for n in range(10)), encoding="utf-8")
    assert log_tail(log, lines=3) == "line 7\nline 8\nline 9"


def test_a_missing_log_says_so(tmp_path: Path) -> None:
    assert "No SkyEye log yet" in log_tail(tmp_path / "missing.log")
