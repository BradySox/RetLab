"""Debrief, sim and saved-point updates reach Qt on the GUI thread (features doc §8).

The app crashed in PySide's signal code 20-40 s after mission end. The debrief
poll, the game loop timer and the web server all emitted Qt signals carrying
Python objects from their own threads.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import json
import threading
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterator

import pytest
from PySide6.QtWidgets import QApplication

from game.debriefingfilepoller import DebriefingFilePoller
from game.sim.gameupdateevents import GameUpdateEvents
from qt_ui.simcontroller import DebriefingPollTimer, SimController
from qt_ui.windows.GameUpdateSignal import GameUpdateSignal


@pytest.fixture(scope="module")
def qapp() -> Iterator[Any]:
    yield QApplication.instance() or QApplication([])


class _FakeSim:
    def __init__(self, generated_at: float) -> None:
        self.miz_generated_at = generated_at
        self.reads = 0

    def debrief_current_state(self, state_path: Path) -> Any:
        self.reads += 1
        data = json.loads(state_path.read_text(encoding="utf-8"))
        return SimpleNamespace(
            state_data=SimpleNamespace(mission_ended=data["mission_ended"])
        )


def _write_state(path: Path, mtime: float, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    os.utime(path, (mtime, mtime))


def test_poller_ignores_a_state_file_older_than_the_mission(tmp_path: Path) -> None:
    state = tmp_path / "state.json"
    _write_state(state, 1000.0, '{"mission_ended": true}')
    sim = _FakeSim(generated_at=2000.0)
    received: list[Any] = []
    poller = DebriefingFilePoller(received.append, sim, state)  # type: ignore[arg-type]

    poller.poll()

    assert received == []
    assert not poller.stopped()


def test_poller_retries_a_half_written_file_then_stops_at_mission_end(
    tmp_path: Path,
) -> None:
    state = tmp_path / "state.json"
    sim = _FakeSim(generated_at=1000.0)
    received: list[Any] = []
    poller = DebriefingFilePoller(received.append, sim, state)  # type: ignore[arg-type]

    _write_state(state, 2000.0, '{"mission_ended": tr')
    poller.poll()
    assert received == []
    assert poller.last_modified == 1000.0

    poller.poll()
    assert sim.reads == 2, "a failed read is retried on the next poll"

    _write_state(state, 2000.0, '{"mission_ended": false}')
    poller.poll()
    assert len(received) == 1
    assert not poller.stopped()

    poller.poll()
    assert len(received) == 1, "an unchanged file is not read again"

    _write_state(state, 3000.0, '{"mission_ended": true}')
    poller.poll()
    assert len(received) == 2
    assert poller.stopped()

    _write_state(state, 4000.0, '{"mission_ended": true}')
    poller.poll()
    assert len(received) == 2


def test_poll_timer_runs_the_poll_on_the_gui_thread(qapp: Any, tmp_path: Path) -> None:
    state = tmp_path / "state.json"
    _write_state(state, 2000.0, '{"mission_ended": true}')
    threads: list[threading.Thread] = []
    poller = DebriefingFilePoller(
        lambda _d: threads.append(threading.current_thread()),
        _FakeSim(generated_at=1000.0),  # type: ignore[arg-type]
        state,
    )
    timer = DebriefingPollTimer(poller)
    timer.start()
    qapp.processEvents()

    assert threads == [threading.main_thread()]
    assert not timer.is_active(), "the timer stops with the poller at mission end"


def test_poll_timer_stop_ends_polling(qapp: Any, tmp_path: Path) -> None:
    received: list[Any] = []
    poller = DebriefingFilePoller(
        received.append,
        _FakeSim(generated_at=1000.0),  # type: ignore[arg-type]
        tmp_path / "state.json",
    )
    timer = DebriefingPollTimer(poller)
    timer.start()
    timer.stop()

    assert poller.stopped()
    assert not timer.is_active()


def _run_in_thread(target: Any) -> None:
    worker = threading.Thread(target=target)
    worker.start()
    worker.join()


def test_sim_updates_from_the_timer_thread_arrive_on_the_gui_thread(
    qapp: Any,
) -> None:
    controller = SimController(None)
    seen: list[tuple[str, Any, threading.Thread]] = []
    controller.sim_update.connect(
        lambda events: seen.append(("update", events, threading.current_thread()))
    )
    controller.simulation_complete.connect(
        lambda: seen.append(("complete", None, threading.current_thread()))
    )
    first, second = GameUpdateEvents(), GameUpdateEvents()

    def tick() -> None:
        controller._on_loop_update(first)
        controller._on_loop_update(second)
        controller.on_simulation_complete()

    _run_in_thread(tick)
    assert seen == [], "nothing is delivered on the timer thread"

    qapp.processEvents()

    assert [(kind, events) for kind, events, _ in seen] == [
        ("update", first),
        ("update", second),
        ("complete", None),
    ]
    assert all(thread is threading.main_thread() for _, _, thread in seen)


def test_sim_update_on_the_gui_thread_is_immediate_and_after_queued_ones(
    qapp: Any,
) -> None:
    controller = SimController(None)
    seen: list[GameUpdateEvents] = []
    controller.sim_update.connect(seen.append)
    queued, direct = GameUpdateEvents(), GameUpdateEvents()

    _run_in_thread(lambda: controller._on_loop_update(queued))
    controller._on_loop_update(direct)

    assert seen == [queued, direct]
    qapp.processEvents()
    assert seen == [queued, direct]


def test_saved_points_notice_from_the_server_thread_arrives_on_the_gui_thread(
    qapp: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    signal = GameUpdateSignal()
    monkeypatch.setattr(GameUpdateSignal, "instance", signal)
    threads: list[threading.Thread] = []
    signal.saved_points_changed.connect(
        lambda: threads.append(threading.current_thread())
    )

    _run_in_thread(signal.notify_saved_points_changed)
    assert threads == []
    qapp.processEvents()
    assert threads == [threading.main_thread()]

    signal.notify_saved_points_changed()
    assert threads == [threading.main_thread()] * 2
