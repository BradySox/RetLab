"""Voice bots on Take Off (§120): start SRS and SkyEye, connect the player's SRS client.

On Take Off, with the preference on: the SRS server starts if it is not running and
RetLab waits for its port; SkyEye starts minimized from its folder; the SRS client
starts if it is not running and is told to connect to 127.0.0.1:5002. Anything already
running is left alone. On debrief only the SkyEye that RetLab started is stopped (user
call, 2026-10-20). docs/dev/retlab-features.md §120.
"""

from __future__ import annotations

import logging
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Callable, Optional

SRS_PORT = 5002
#: The SRS client's auto-connect port (global.cfg DCSAutoConnectUDP). SRS's own hook
#: sends "host:port" here, but only to a server's guests, never to the host.
SRS_AUTOCONNECT_PORT = 5069
SERVER_WAIT_SECONDS = 60
CLIENT_START_SECONDS = 8
SKYEYE_EXE = "skyeye.exe"
SKYEYE_CONFIG = "config.yaml"
SRS_SERVER_EXE = "SRS-Server.exe"
SRS_CLIENT_EXE = "SR-ClientRadio.exe"
DEFAULT_SRS_DIR = Path(r"C:\ProgramData\DCS-SimpleRadio-Standalone")

_SW_SHOWMINNOACTIVE = 7

_skyeye: Optional[subprocess.Popen[bytes]] = None


def srs_dir() -> Path:
    """Where SRS is installed: the installer's registry key, else its default."""
    if sys.platform == "win32":
        import winreg

        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, r"Software\DCS-SR-Standalone"
            ) as key:
                value, _ = winreg.QueryValueEx(key, "SRPathStandalone")
                return Path(value)
        except OSError:
            pass
    return DEFAULT_SRS_DIR


def running(image: str) -> bool:
    """Whether a process with this .exe name is running."""
    if sys.platform != "win32":
        return False
    try:
        out = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {image}", "/NH"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            check=False,
        ).stdout
    except OSError:
        return False
    return image.lower() in out.lower()


def port_open(port: int, host: str = "127.0.0.1") -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def _wait(condition: Callable[[], bool], seconds: float, step: float = 1.0) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(step)
    return condition()


def _start(
    exe: Path, args: list[str], minimized: bool = False
) -> subprocess.Popen[bytes]:
    kwargs: dict[str, object] = {"cwd": str(exe.parent)}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE
        if minimized:
            info = subprocess.STARTUPINFO()
            info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            info.wShowWindow = _SW_SHOWMINNOACTIVE
            kwargs["startupinfo"] = info
    return subprocess.Popen([str(exe), *args], **kwargs)  # type: ignore[call-overload]


def autoconnect_message(port: int = SRS_PORT) -> bytes:
    """What SRS's DCS hook sends its client: the server address and a newline."""
    return f"127.0.0.1:{port}\n".encode()


def _connect_client(just_started: bool) -> None:
    # A client that just started opens its listener a few seconds later. Twice at
    # most: each message can make a connected client reconnect.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
        for delay in (CLIENT_START_SECONDS, 10) if just_started else (0,):
            time.sleep(delay)
            udp.sendto(autoconnect_message(), ("127.0.0.1", SRS_AUTOCONNECT_PORT))


def start_voice_bots(skyeye_dir: Path) -> None:
    """Start what is missing, on a background thread so Take Off never waits."""
    threading.Thread(
        target=_start_voice_bots, args=(skyeye_dir,), daemon=True, name="voicebots"
    ).start()


def _start_voice_bots(skyeye_dir: Path) -> None:
    global _skyeye
    srs = srs_dir()
    server = srs / "Server" / SRS_SERVER_EXE
    client = srs / "Client" / SRS_CLIENT_EXE
    try:
        if not running(SRS_SERVER_EXE):
            if not server.exists():
                logging.warning("Voice bots: no SRS server at %s", server)
                return
            _start(server, [])
        if not _wait(lambda: port_open(SRS_PORT), SERVER_WAIT_SECONDS):
            logging.warning("Voice bots: SRS server never opened port %d", SRS_PORT)
            return
        skyeye = skyeye_dir / SKYEYE_EXE
        if running(SKYEYE_EXE):
            logging.info("Voice bots: SkyEye already running, left alone")
        elif skyeye.exists() and (skyeye_dir / SKYEYE_CONFIG).exists():
            _skyeye = _start(skyeye, ["--config-file", SKYEYE_CONFIG], minimized=True)
        else:
            logging.warning("Voice bots: no SkyEye or config.yaml in %s", skyeye_dir)
        just_started = not running(SRS_CLIENT_EXE)
        if just_started:
            if not client.exists():
                logging.warning("Voice bots: no SRS client at %s", client)
                return
            _start(client, [])
        _connect_client(just_started)
    except OSError:
        logging.exception("Voice bots: could not start SRS or SkyEye")


def stop_skyeye() -> None:
    """Stop the SkyEye RetLab started; one the player started is left running."""
    global _skyeye
    process, _skyeye = _skyeye, None
    if process is None or process.poll() is not None:
        return
    try:
        process.terminate()
        process.wait(timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        logging.exception("Voice bots: could not stop SkyEye")
