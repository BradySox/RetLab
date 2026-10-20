"""Voice bots on Take Off (§120): what starts, what is left alone, what is stopped."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from game.retlab import skyeye_launcher as launcher


class _FakeProcess:
    def __init__(self) -> None:
        self.terminated = False

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

    def start(exe: Path, args: list[str], minimized: bool = False) -> _FakeProcess:
        state["started"].append((exe.name, minimized))
        state["running"].add(exe.name)
        return _FakeProcess()

    monkeypatch.setattr(launcher, "srs_dir", lambda: srs)
    monkeypatch.setattr(launcher, "running", lambda image: image in state["running"])
    monkeypatch.setattr(
        launcher, "port_open", lambda port: launcher.SRS_SERVER_EXE in state["running"]
    )
    monkeypatch.setattr(launcher, "_start", start)
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
