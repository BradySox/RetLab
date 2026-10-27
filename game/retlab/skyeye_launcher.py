"""Voice bots on Take Off (§120): start SRS and SkyEye, connect the player's SRS client.

On Take Off, with the preference on: the SRS server starts if it is not running and
RetLab waits for its port, minimized; SkyEye starts from its folder with no window, its
log shown by RetLab's SkyEye log button; the SRS client starts if it is not running and
is told to connect to 127.0.0.1:5002. Anything already running is left alone. On
debrief only the SkyEye that RetLab started is stopped (user call, 2026-10-20), found by
a record file so a Retribution restart in between does not orphan it. docs/dev/retlab-features.md §120.
"""

from __future__ import annotations

import json
import logging
import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Callable, Iterable, Optional

SRS_PORT = 5002
#: The SRS client's auto-connect port (global.cfg DCSAutoConnectUDP). SRS's own hook
#: sends "host:port" here, but only to a server's guests, never to the host.
SRS_AUTOCONNECT_PORT = 5069
SERVER_WAIT_SECONDS = 60
#: How long an open SRS server may take to listen before it counts as stopped.
STOPPED_SERVER_SECONDS = 15
CLIENT_START_SECONDS = 8
SKYEYE_EXE = "skyeye.exe"
SKYEYE_CONFIG = "config.yaml"
#: SkyEye's output when Take off starts it, for working out a failed flight.
SKYEYE_LOG = "skyeye-takeoff.log"
#: A SkyEye that quits this soon after starting is reported in RetLab's log.
EARLY_EXIT_SECONDS = 60
#: How long SkyEye gets to sign off SRS before it is closed by force.
GRACEFUL_STOP_SECONDS = 5
#: The SkyEye Take off started, by PID and process creation time (a reused PID has a
#: different creation time). Kept beside Retribution's preferences.
RECORD_FILE = "skyeye-takeoff.json"
SRS_SERVER_EXE = "SRS-Server.exe"
SRS_CLIENT_EXE = "SR-ClientRadio.exe"
DEFAULT_SRS_DIR = Path(r"C:\ProgramData\DCS-SimpleRadio-Standalone")

_SW_HIDE = 0
WM_CLOSE = 0x0010
#: conhost's window class. A hidden one still answers WM_CLOSE with a close event.
CONSOLE_CLASS = "ConsoleWindowClass"
_SW_SHOWMINNOACTIVE = 7

#: Held while a Take off decides whether to start SkyEye, and while debrief stops it.
_lock = threading.Lock()
_starting = False
#: PIDs stop_skyeye closed, so their exit is not reported as an early quit.
_stopped: set[int] = set()


def record_path() -> Path:
    """The record file, in the folder liberation_install keeps the preferences in."""
    if os.name == "nt":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return root / "DCSRetribution" / RECORD_FILE


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


def kill(image: str) -> None:
    """Close every process with this .exe name."""
    if sys.platform != "win32":
        return
    subprocess.run(
        ["taskkill", "/IM", image, "/F"],
        capture_output=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
        check=False,
    )


def process_started(pid: int) -> Optional[int]:
    """The creation time of a live process with this PID, or None if none is running."""
    if sys.platform != "win32":
        return None
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
    kernel32.GetProcessTimes.argtypes = [wintypes.HANDLE, *[ctypes.c_void_p] * 4]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel32.OpenProcess(0x1000, False, pid)  # QUERY_LIMITED_INFORMATION
    if not handle:
        return None
    try:
        code = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
            return None
        if code.value != 259:  # STILL_ACTIVE
            return None
        times = [wintypes.FILETIME() for _ in range(4)]
        if not kernel32.GetProcessTimes(handle, *(ctypes.byref(t) for t in times)):
            return None
        return (times[0].dwHighDateTime << 32) | times[0].dwLowDateTime
    finally:
        kernel32.CloseHandle(handle)


def _read_record() -> Optional[tuple[int, int]]:
    try:
        data = json.loads(record_path().read_text(encoding="utf-8"))
        return int(data["pid"]), int(data["created"])
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _write_record(pid: int, created: int) -> None:
    path = record_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"pid": pid, "created": created}), encoding="utf-8")
    except OSError:
        logging.exception("Voice bots: could not write %s", path)


def _clear_record() -> None:
    try:
        record_path().unlink()
    except FileNotFoundError:
        pass
    except OSError:
        logging.exception("Voice bots: could not remove %s", record_path())


def _ours() -> Optional[tuple[int, int]]:
    """The SkyEye a Take off started, as (pid, creation time), if it still runs."""
    record = _read_record()
    if record is None:
        return None
    if process_started(record[0]) != record[1]:
        _clear_record()
        return None
    return record


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
    exe: Path,
    args: list[str],
    minimized: bool = False,
    hidden: bool = False,
    log: Optional[Path] = None,
) -> subprocess.Popen[bytes]:
    kwargs: dict[str, object] = {"cwd": str(exe.parent)}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE
        if minimized or hidden:
            info = subprocess.STARTUPINFO()
            info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            info.wShowWindow = _SW_HIDE if hidden else _SW_SHOWMINNOACTIVE
            kwargs["startupinfo"] = info
    if log is None:
        return subprocess.Popen([str(exe), *args], **kwargs)  # type: ignore[call-overload]
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with log.open("ab") as out:
        out.write(f"\n==== {stamp} Take off ====\n".encode())
    if sys.platform != "win32":
        with log.open("ab") as out:
            return subprocess.Popen(  # type: ignore[call-overload]
                [str(exe), *args], stdout=out, stderr=subprocess.STDOUT, **kwargs
            )
    # The log is RetLab's SkyEye log button. PowerShell is the tee. taskkill without /F
    # skips the hidden console, so stop_skyeye posts its WM_CLOSE itself.
    return subprocess.Popen(  # type: ignore[call-overload]
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            tee_command(exe, args, log),
        ],
        **kwargs,
    )


def _ps_quote(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def tee_command(exe: Path, args: list[str], log: Path) -> str:
    """PowerShell that runs exe, shows each line and appends it to log as UTF-8."""
    call = " ".join(["&", _ps_quote(str(exe)), *(_ps_quote(a) for a in args)])
    return (
        f"$Host.UI.RawUI.WindowTitle = {_ps_quote('SkyEye')}; "
        f'{call} 2>&1 | ForEach-Object {{ $line = "$_"; $line; '
        f"Add-Content -LiteralPath {_ps_quote(str(log))} -Value $line -Encoding UTF8 }}"
    )


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
    global _starting
    with _lock:
        # A second Take off while the first still waits for SRS would start a
        # second SkyEye; the start under way covers both.
        if _starting:
            logging.info("Voice bots: a start is already under way")
            return
        _starting = True
    threading.Thread(
        target=_run_start, args=(skyeye_dir,), daemon=True, name="voicebots"
    ).start()


def _run_start(skyeye_dir: Path) -> None:
    global _starting
    try:
        _start_voice_bots(skyeye_dir)
    finally:
        with _lock:
            _starting = False


def _start_skyeye(skyeye_dir: Path) -> None:
    skyeye = skyeye_dir / SKYEYE_EXE
    with _lock:
        if _ours() is not None:
            logging.info("Voice bots: the SkyEye Take off started is still running")
        elif running(SKYEYE_EXE):
            logging.info("Voice bots: SkyEye already running, left alone")
        elif skyeye.exists() and (skyeye_dir / SKYEYE_CONFIG).exists():
            log = skyeye_dir / SKYEYE_LOG
            process = _start(
                skyeye, ["--config-file", SKYEYE_CONFIG], hidden=True, log=log
            )
            created = process_started(process.pid)
            if created is not None:
                _write_record(process.pid, created)
            logging.info(
                "Voice bots: started SkyEye (pid %d), output in %s", process.pid, log
            )
            _watch_early_exit(process, log)
        else:
            logging.warning("Voice bots: no SkyEye or config.yaml in %s", skyeye_dir)


def _start_voice_bots(skyeye_dir: Path) -> None:
    srs = srs_dir()
    server = srs / "Server" / SRS_SERVER_EXE
    client = srs / "Client" / SRS_CLIENT_EXE
    try:
        # An SRS server window whose Stop button was pressed runs without listening;
        # Take off restarts it (user call, 2026-10-21).
        if running(SRS_SERVER_EXE) and not _wait(
            lambda: port_open(SRS_PORT), STOPPED_SERVER_SECONDS
        ):
            logging.info("Voice bots: SRS server is open but stopped; restarting it")
            kill(SRS_SERVER_EXE)
            _wait(lambda: not running(SRS_SERVER_EXE), 10)
        if not running(SRS_SERVER_EXE):
            logging.info("Voice bots: starting the SRS server")
            if not server.exists():
                logging.warning("Voice bots: no SRS server at %s", server)
                return
            _start(server, [], minimized=True)
        if not _wait(lambda: port_open(SRS_PORT), SERVER_WAIT_SECONDS):
            logging.warning("Voice bots: SRS server never opened port %d", SRS_PORT)
            return
        _start_skyeye(skyeye_dir)
        just_started = not running(SRS_CLIENT_EXE)
        if just_started:
            if not client.exists():
                logging.warning("Voice bots: no SRS client at %s", client)
                return
            _start(client, [])
        _connect_client(just_started)
        logging.info("Voice bots: SRS client told to connect to 127.0.0.1:%d", SRS_PORT)
    except OSError:
        logging.exception("Voice bots: could not start SRS or SkyEye")


def _tail(log: Path, lines: int = 15) -> str:
    try:
        text = log.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return "\n".join(text.splitlines()[-lines:])


def _watch_early_exit(process: subprocess.Popen[bytes], log: Path) -> None:
    started = time.monotonic()

    def watch() -> None:
        try:
            code = process.wait(timeout=EARLY_EXIT_SECONDS)
        except subprocess.TimeoutExpired:
            return
        if process.pid in _stopped:
            return
        logging.warning(
            "Voice bots: SkyEye quit %d s after starting (exit %s). Last output:\n%s",
            round(time.monotonic() - started),
            code,
            _tail(log),
        )

    threading.Thread(target=watch, daemon=True, name="skyeye-watch").start()


def process_tree(pid: int, parents: Iterable[tuple[int, int]]) -> set[int]:
    """pid and every process under it, from (pid, parent pid) pairs."""
    children: dict[int, list[int]] = {}
    for child, parent in parents:
        if child != parent:
            children.setdefault(parent, []).append(child)
    tree = {pid}
    todo = [pid]
    while todo:
        for child in children.get(todo.pop(), []):
            if child not in tree:
                tree.add(child)
                todo.append(child)
    return tree


def console_windows(
    tree: set[int], windows: Iterable[tuple[int, int, str]]
) -> list[int]:
    """The console windows, hidden ones too, of (hwnd, pid, class) owned in tree."""
    return [hwnd for hwnd, pid, cls in windows if pid in tree and cls == CONSOLE_CLASS]


def _process_parents() -> list[tuple[int, int]]:
    """Every running process as (pid, parent pid), from a toolhelp snapshot."""
    if sys.platform != "win32":
        return []
    import ctypes
    from ctypes import wintypes

    class Entry(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.c_size_t),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", wintypes.LONG),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", wintypes.WCHAR * 260),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
    kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    snapshot = kernel32.CreateToolhelp32Snapshot(0x2, 0)  # TH32CS_SNAPPROCESS
    if not snapshot or snapshot == wintypes.HANDLE(-1).value:
        return []
    pairs: list[tuple[int, int]] = []
    try:
        entry = Entry()
        entry.dwSize = ctypes.sizeof(Entry)
        more = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
        while more:
            pairs.append((entry.th32ProcessID, entry.th32ParentProcessID))
            more = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snapshot)
    return pairs


def _top_level_windows() -> list[tuple[int, int, str]]:
    """Every top-level window, visible or not, as (hwnd, owning pid, class name)."""
    if sys.platform != "win32":
        return []
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows.argtypes = [proc, wintypes.LPARAM]
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.c_void_p]
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    found: list[tuple[int, int, str]] = []

    def visit(hwnd: int, _: int) -> bool:
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        name = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, name, 256)
        found.append((hwnd, pid.value, name.value))
        return True

    user32.EnumWindows(proc(visit), 0)
    return found


def _post_close(hwnd: int) -> None:
    if sys.platform != "win32":
        return
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.PostMessageW.argtypes = [
        wintypes.HWND,
        wintypes.UINT,
        wintypes.WPARAM,
        wintypes.LPARAM,
    ]
    user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)


def _ask_to_close(pid: int) -> int:
    """Post WM_CLOSE to the console of pid's tree; returns how many windows got it.

    The console host answers WM_CLOSE with a close event to every process on the
    console, shown or hidden, so SkyEye gets its SIGTERM and signs off SRS.
    taskkill without /F never reached the hidden one (Test 65), so it is not used.
    """
    windows = console_windows(
        process_tree(pid, _process_parents()), _top_level_windows()
    )
    for hwnd in windows:
        _post_close(hwnd)
    return len(windows)


def _force_kill(pid: int) -> None:
    if sys.platform != "win32":
        return
    # The process is PowerShell; /T takes SkyEye under it too.
    subprocess.run(
        ["taskkill", "/T", "/F", "/PID", str(pid)],
        capture_output=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
        check=False,
    )


def stop_skyeye() -> None:
    """Stop the SkyEye a Take off started, even before a restart; the player's stays."""
    with _lock:
        ours = _ours()
        if ours is None:
            return
        pid, created = ours
        _stopped.add(pid)
        logging.info("Voice bots: stopping the SkyEye Take off started")
        try:
            if not _ask_to_close(pid):
                logging.info("Voice bots: found no SkyEye console window to close")
            if not _wait(
                lambda: process_started(pid) != created, GRACEFUL_STOP_SECONDS, 0.25
            ):
                logging.info("Voice bots: SkyEye did not close; closing it by force")
                _force_kill(pid)
        except OSError:
            logging.exception("Voice bots: could not stop SkyEye")
        _clear_record()
