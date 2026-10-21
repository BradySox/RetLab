"""Voice bots on Take Off (§120): what starts, what is left alone, what is stopped."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from game.retlab import skyeye_launcher as launcher


class _FakeProcess:
    def __init__(self) -> None:
        self.terminated = False
        self.pid = 4242

    def poll(self) -> None:
        return None

    def terminate(self) -> None:
        self.terminated = True

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
    }

    def start(
        exe: Path, args: list[str], minimized: bool = False, log: Any = None
    ) -> _FakeProcess:
        state["started"].append((exe.name, minimized))
        if log is not None:
            state["log"] = log
        state["running"].add(exe.name)
        return _FakeProcess()

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
    monkeypatch.setattr(launcher, "_kill_tree", lambda process: process.terminate())
    monkeypatch.setattr(launcher, "_connect_client", state["connects"].append)
    monkeypatch.setattr(launcher, "_skyeye", None)
    return state


def test_everything_missing_is_started_and_skyeye_minimized(
    world: dict[str, Any],
) -> None:
    launcher._start_voice_bots(world["skyeye"])
    assert world["started"] == [
        (launcher.SRS_SERVER_EXE, False),
        (launcher.SKYEYE_EXE, True),
        (launcher.SRS_CLIENT_EXE, False),
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
    assert (launcher.SKYEYE_EXE, True) not in world["started"]


def test_only_the_skyeye_retlab_started_is_stopped(world: dict[str, Any]) -> None:
    launcher._start_voice_bots(world["skyeye"])
    process: Any = launcher._skyeye
    assert isinstance(process, _FakeProcess)
    launcher.stop_skyeye()
    assert process.terminated
    assert launcher._skyeye is None


def test_the_connect_message_is_what_srs_sends() -> None:
    assert launcher.autoconnect_message() == b"127.0.0.1:5002\n"


def test_a_stopped_srs_server_is_restarted(world: dict[str, Any]) -> None:
    world["running"].add(launcher.SRS_SERVER_EXE)
    world["stopped"] = True
    launcher._start_voice_bots(world["skyeye"])
    assert world["killed"] == launcher.SRS_SERVER_EXE
    assert world["started"][0] == (launcher.SRS_SERVER_EXE, False)
    assert (launcher.SKYEYE_EXE, True) in world["started"]


def test_a_listening_srs_server_is_left_alone(world: dict[str, Any]) -> None:
    world["running"].add(launcher.SRS_SERVER_EXE)
    launcher._start_voice_bots(world["skyeye"])
    assert "killed" not in world
    assert (launcher.SRS_SERVER_EXE, False) not in world["started"]


def test_skyeye_output_goes_to_its_take_off_log(world: dict[str, Any]) -> None:
    launcher._start_voice_bots(world["skyeye"])
    assert world["log"] == world["skyeye"] / launcher.SKYEYE_LOG


def test_a_real_start_writes_the_log(tmp_path: Path) -> None:
    import sys

    log = tmp_path / "out.log"
    process = launcher._start(
        Path(sys.executable), ["-c", "print('hello from skyeye')"], log=log
    )
    process.wait(timeout=30)
    text = log.read_text()
    assert "Take off" in text and "hello from skyeye" in text
