"""A native crash leaves every thread's Python stack in logs/faulthandler.log (§8)."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path
from typing import Any

import pytest

import qt_ui.main as app_main


@pytest.fixture
def enabled(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    # Never replace pytest's own faulthandler.
    monkeypatch.setattr(
        app_main.faulthandler, "enable", lambda **kwargs: calls.append(kwargs)
    )
    monkeypatch.setattr(app_main, "_fault_log", None)
    return calls


def _close() -> None:
    if app_main._fault_log is not None:
        app_main._fault_log.close()


def test_enables_all_threads_into_the_log_with_a_session_header(
    tmp_path: Path, enabled: list[dict[str, Any]]
) -> None:
    path = tmp_path / "logs" / "faulthandler.log"
    path.parent.mkdir()
    path.write_text("earlier session\n", encoding="utf-8")

    app_main.enable_fault_log(path)
    try:
        assert enabled == [{"file": app_main._fault_log, "all_threads": True}]
        assert app_main._fault_log is not None and not app_main._fault_log.closed
    finally:
        _close()
    text = path.read_text(encoding="utf-8")
    assert text.startswith("earlier session\n")
    assert "--- DCS Retribution" in text and "started" in text


def test_starts_over_past_the_size_cap(
    tmp_path: Path, enabled: list[dict[str, Any]]
) -> None:
    path = tmp_path / "faulthandler.log"
    path.write_text("x" * (app_main.FAULT_LOG_MAX_BYTES + 1), encoding="utf-8")

    app_main.enable_fault_log(path)
    _close()

    assert path.read_text(encoding="utf-8").startswith("--- DCS Retribution")


def test_an_unwritable_log_does_not_stop_startup(
    tmp_path: Path, enabled: list[dict[str, Any]]
) -> None:
    blocker = tmp_path / "logs"
    blocker.write_text("a file where the folder should be", encoding="utf-8")

    app_main.enable_fault_log(blocker / "faulthandler.log")

    assert enabled == []
