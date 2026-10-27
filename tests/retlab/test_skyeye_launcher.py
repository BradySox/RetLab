"""Voice bots on Take Off (§120): what starts, what is left alone, what is stopped."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from game.retlab import skyeye_launcher as launcher


class _FakeProcess:
    next_pid = 4242

    def __init__(self) -> None:
        self.pid = _FakeProcess.next_pid
        _FakeProcess.next_pid += 1

    def poll(self) -> None:
        return None

    def wait(self, timeout: float) -> int:
        return 0


@pytest.fixture
def world(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, Any]:
    srs = tmp_path / "srs"
    for sub, exe in (
        ("Server", launcher.SRS_SERVER_EXE),
        ("Client", launcher.SRS_CLIENT_EXE),
    ):
        (srs / sub).mkdir(parents=True)
        (srs / sub / exe).write_text("")
    skyeye = tmp_path / "skyeye"
    skyeye.mkdir()
    (skyeye / launcher.SKYEYE_EXE).write_text("")
    (skyeye / launcher.SKYEYE_CONFIG).write_text("")
    state: dict[str, Any] = {
        "running": set(),
        "started": [],
        "connects": [],
        "skyeye": skyeye,
        # Live processes by PID, with their creation time.
        "alive": {},
        "stops": [],
        # Whether the console's WM_CLOSE closes SkyEye.
        "graceful_works": True,
    }

    def start(
        exe: Path,
        args: list[str],
        minimized: bool = False,
        hidden: bool = False,
        log: Any = None,
    ) -> _FakeProcess:
        window = "hidden" if hidden else "minimized" if minimized else "shown"
        state["started"].append((exe.name, window))
        if log is not None:
            state["log"] = log
        state["running"].add(exe.name)
        process = _FakeProcess()
        if exe.name == launcher.SKYEYE_EXE:
            state["alive"][process.pid] = 1000 + process.pid
        return process

    monkeypatch.setattr(launcher, "srs_dir", lambda: srs)
    monkeypatch.setattr(launcher, "running", lambda image: image in state["running"])
    monkeypatch.setattr(
        launcher,
        "port_open",
        lambda port: launcher.SRS_SERVER_EXE in state["running"]
        and not state.get("stopped"),
    )

    def kill(image: str) -> None:
        state["running"].discard(image)
        state["killed"] = image
        state["stopped"] = False

    monkeypatch.setattr(launcher, "kill", kill)
    monkeypatch.setattr(
        launcher, "_wait", lambda condition, seconds, step=1.0: condition()
    )
    monkeypatch.setattr(launcher, "_start", start)
    monkeypatch.setattr(launcher, "_watch_early_exit", lambda process, log: None)
    monkeypatch.setattr(launcher, "_connect_client", state["connects"].append)
    monkeypatch.setattr(launcher, "record_path", lambda: tmp_path / "record.json")
    monkeypatch.setattr(launcher, "process_started", state["alive"].get)

    def stop(pid: int, force: bool) -> None:
        state["stops"].append((pid, force))
        if force or state["graceful_works"]:
            state["alive"].pop(pid, None)
            state["running"].discard(launcher.SKYEYE_EXE)

    def ask_to_close(pid: int) -> int:
        stop(pid, False)
        return 1

    monkeypatch.setattr(launcher, "_ask_to_close", ask_to_close)
    monkeypatch.setattr(launcher, "_force_kill", lambda pid: stop(pid, True))
    monkeypatch.setattr(launcher, "_starting", False)
    return state


def test_everything_missing_is_started_and_skyeye_hidden(
    world: dict[str, Any],
) -> None:
    launcher._start_voice_bots(world["skyeye"])
    assert world["started"] == [
        (launcher.SRS_SERVER_EXE, "minimized"),
        (launcher.SKYEYE_EXE, "hidden"),
        (launcher.SRS_CLIENT_EXE, "shown"),
    ]
    assert world["connects"] == [True]


def test_what_is_running_is_left_alone(world: dict[str, Any]) -> None:
    world["running"].update(
        {launcher.SRS_SERVER_EXE, launcher.SKYEYE_EXE, launcher.SRS_CLIENT_EXE}
    )
    launcher._start_voice_bots(world["skyeye"])
    assert world["started"] == []
    # A running client still gets one connect message.
    assert world["connects"] == [False]
    launcher.stop_skyeye()  # nothing RetLab started


def test_no_config_starts_no_skyeye(world: dict[str, Any]) -> None:
    (world["skyeye"] / launcher.SKYEYE_CONFIG).unlink()
    launcher._start_voice_bots(world["skyeye"])
    assert (launcher.SKYEYE_EXE, "hidden") not in world["started"]


def test_only_the_skyeye_retlab_started_is_stopped(world: dict[str, Any]) -> None:
    launcher._start_voice_bots(world["skyeye"])
    (pid,) = world["alive"]
    launcher.stop_skyeye()
    assert world["stops"] == [(pid, False)]
    assert pid not in world["alive"]
    assert not launcher.record_path().exists()


def test_a_restart_does_not_orphan_retlabs_skyeye(world: dict[str, Any]) -> None:
    launcher._start_voice_bots(world["skyeye"])
    (pid,) = world["alive"]
    # Nothing in memory survives a restart; only the record file does.
    assert launcher.record_path().exists()
    launcher._start_voice_bots(world["skyeye"])
    assert [s for s in world["started"] if s[0] == launcher.SKYEYE_EXE] == [
        (launcher.SKYEYE_EXE, "hidden")
    ]
    launcher.stop_skyeye()
    assert world["stops"] == [(pid, False)]


def test_a_reused_pid_is_not_retlabs(world: dict[str, Any]) -> None:
    launcher._start_voice_bots(world["skyeye"])
    (pid,) = world["alive"]
    world["alive"][pid] = 1  # the same PID, a different process
    launcher.stop_skyeye()
    assert world["stops"] == []
    assert not launcher.record_path().exists()


def test_the_players_skyeye_is_left_on_debrief(world: dict[str, Any]) -> None:
    world["running"].add(launcher.SKYEYE_EXE)
    launcher._start_voice_bots(world["skyeye"])
    launcher.stop_skyeye()
    assert world["stops"] == []


def test_skyeye_is_forced_only_when_it_will_not_close(
    world: dict[str, Any],
) -> None:
    world["graceful_works"] = False
    launcher._start_voice_bots(world["skyeye"])
    (pid,) = world["alive"]
    launcher.stop_skyeye()
    assert world["stops"] == [(pid, False), (pid, True)]


def test_a_second_take_off_during_a_start_starts_nothing(
    world: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    threads: list[Any] = []

    class _Thread:
        def __init__(self, target: Any, args: Any, **kwargs: Any) -> None:
            threads.append((target, args))

        def start(self) -> None:
            pass

    monkeypatch.setattr(launcher.threading, "Thread", _Thread)
    launcher.start_voice_bots(world["skyeye"])
    launcher.start_voice_bots(world["skyeye"])
    assert len(threads) == 1
    target, args = threads[0]
    target(*args)
    assert not launcher._starting
    launcher.start_voice_bots(world["skyeye"])
    assert len(threads) == 2


def test_skyeye_started_while_waiting_for_srs_is_not_doubled(
    world: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    def wait(condition: Any, seconds: float, step: float = 1.0) -> bool:
        # Someone starts SkyEye while this Take off waits for the SRS port.
        world["running"].add(launcher.SKYEYE_EXE)
        return bool(condition())

    monkeypatch.setattr(launcher, "_wait", wait)
    launcher._start_voice_bots(world["skyeye"])
    assert (launcher.SKYEYE_EXE, "hidden") not in world["started"]


def test_the_early_exit_warning_gives_the_real_time_and_skips_a_stop(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    clock = [100.0, 112.4]
    monkeypatch.setattr(
        launcher.time, "monotonic", lambda: clock.pop(0) if len(clock) > 1 else clock[0]
    )
    ran: list[Any] = []

    class _Thread:
        def __init__(self, target: Any, **kwargs: Any) -> None:
            ran.append(target)

        def start(self) -> None:
            pass

    monkeypatch.setattr(launcher.threading, "Thread", _Thread)
    process: Any = _FakeProcess()
    with caplog.at_level("WARNING"):
        launcher._watch_early_exit(process, tmp_path / "none.log")
        ran[0]()
    assert "quit 12 s after starting" in caplog.text
    caplog.clear()
    stopped: Any = _FakeProcess()
    monkeypatch.setattr(launcher, "_stopped", {stopped.pid})
    with caplog.at_level("WARNING"):
        launcher._watch_early_exit(stopped, tmp_path / "none.log")
        ran[1]()
    assert "quit" not in caplog.text


def test_this_process_is_alive_with_a_fixed_creation_time() -> None:
    import os
    import sys

    if sys.platform != "win32":
        pytest.skip("Windows process times")
    first = launcher.process_started(os.getpid())
    assert first is not None and first == launcher.process_started(os.getpid())


def test_the_connect_message_is_what_srs_sends() -> None:
    assert launcher.autoconnect_message() == b"127.0.0.1:5002\n"


def test_a_stopped_srs_server_is_restarted(world: dict[str, Any]) -> None:
    world["running"].add(launcher.SRS_SERVER_EXE)
    world["stopped"] = True
    launcher._start_voice_bots(world["skyeye"])
    assert world["killed"] == launcher.SRS_SERVER_EXE
    assert world["started"][0] == (launcher.SRS_SERVER_EXE, "minimized")
    assert (launcher.SKYEYE_EXE, "hidden") in world["started"]


def test_a_listening_srs_server_is_left_alone(world: dict[str, Any]) -> None:
    world["running"].add(launcher.SRS_SERVER_EXE)
    launcher._start_voice_bots(world["skyeye"])
    assert "killed" not in world
    assert (launcher.SRS_SERVER_EXE, "minimized") not in world["started"]


def test_skyeye_output_goes_to_its_take_off_log(world: dict[str, Any]) -> None:
    launcher._start_voice_bots(world["skyeye"])
    assert world["log"] == world["skyeye"] / launcher.SKYEYE_LOG


def test_a_real_start_writes_the_log(tmp_path: Path) -> None:
    import sys

    log = tmp_path / "out.log"
    # Hidden: a shown console titled SkyEye popped up on the PC at every test run.
    process = launcher._start(
        Path(sys.executable),
        ["-c", "print('hello from skyeye')"],
        hidden=True,
        log=log,
    )
    process.wait(timeout=30)
    text = log.read_text()
    assert "Take off" in text and "hello from skyeye" in text


def test_the_process_tree_takes_every_descendant_and_nothing_else() -> None:
    # powershell 10 -> conhost 11, skyeye 12 -> 13; 20 is someone else's.
    parents = [(10, 1), (11, 10), (12, 10), (13, 12), (20, 1), (0, 0)]
    assert launcher.process_tree(10, parents) == {10, 11, 12, 13}
    assert launcher.process_tree(99, parents) == {99}


def test_only_console_windows_in_the_tree_are_closed() -> None:
    windows = [
        (1, 10, launcher.CONSOLE_CLASS),  # the hidden SkyEye console
        (2, 10, "IME"),
        (3, 20, launcher.CONSOLE_CLASS),  # the player's own console
    ]
    assert launcher.console_windows({10, 11}, windows) == [1]


def test_the_polite_stop_posts_wm_close_to_the_hidden_console(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    posted: list[int] = []
    monkeypatch.setattr(launcher, "_process_parents", lambda: [(11, 10), (20, 1)])
    monkeypatch.setattr(
        launcher,
        "_top_level_windows",
        lambda: [
            (5, 11, launcher.CONSOLE_CLASS),
            (6, 20, launcher.CONSOLE_CLASS),
            (7, 10, "IME"),
        ],
    )
    monkeypatch.setattr(launcher, "_post_close", posted.append)
    assert launcher._ask_to_close(10) == 1
    assert posted == [5]


def test_a_stop_with_no_console_found_still_forces(
    world: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher._start_voice_bots(world["skyeye"])
    (pid,) = world["alive"]
    forced: list[int] = []
    monkeypatch.setattr(launcher, "_ask_to_close", lambda pid: 0)
    monkeypatch.setattr(launcher, "_force_kill", forced.append)
    launcher.stop_skyeye()
    assert forced == [pid]
