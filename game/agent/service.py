"""The one layer every transport calls; behaviour lives here so transports cannot drift.

Ported from juanjux/dcs-escalation `game/agent/service.py` (LGPL-3). Reads only: the
outside AI reads red's turn and reports what looks wrong. Every function that takes
``side`` refuses anything but red, here rather than in a router, so a second
transport cannot forget the rule: blue's ATO is the human's private side of the board.
Design note: docs/dev/design/retlab-llm-opfor-notes.md.
"""

from __future__ import annotations

import functools
import inspect
import re
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar, TYPE_CHECKING, cast

from game.agent import views

if TYPE_CHECKING:
    from game import Game

OPFOR_SIDE = "red"

_F = TypeVar("_F", bound=Callable[..., Any])


class SideNotAllowedError(PermissionError):
    """Raised when the reader asks for a side other than red."""


def opfor_only(fn: _F) -> _F:
    signature = inspect.signature(fn)

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        bound = signature.bind(*args, **kwargs)
        bound.apply_defaults()
        side = str(bound.arguments.get("side", OPFOR_SIDE)).lower()
        if side != OPFOR_SIDE:
            raise SideNotAllowedError(
                f"this API reads {OPFOR_SIDE} only; {side!r} is the human player's "
                f"own side and is not readable through it"
            )
        return fn(*args, **kwargs)

    return cast(_F, wrapper)


def _require_game() -> Game:
    from game.server import GameContext

    return GameContext.require()


@opfor_only
def turn_context(side: str = OPFOR_SIDE) -> views.TurnContextView:
    return views.build_turn_context(_require_game(), side)


def settings() -> views.SettingsView:
    return views.build_settings(_require_game())


@opfor_only
def packages(side: str = OPFOR_SIDE) -> list[views.PackageView]:
    return views.build_packages(_require_game(), side)


@opfor_only
def waypoints(side: str = OPFOR_SIDE, flight_id: str = "") -> dict[str, Any]:
    """A red flight's route. Scoped to red: an id alone would reach blue's flights."""
    game = _require_game()
    coalition = views.coalition_for_side(game, side)
    for package in coalition.ato.packages:
        for flight in package.flights:
            if str(flight.id) == flight_id:
                return {
                    "flight_id": flight_id,
                    "waypoints": views.build_waypoints(game, flight),
                }
    raise KeyError(f"no {side} flight with id {flight_id!r}")


@opfor_only
def iads(side: str = OPFOR_SIDE) -> views.IadsView:
    return views.build_iads(_require_game(), side)


def prev_turns(n: int = 3) -> views.PrevTurnsView:
    return views.build_prev_turns(_require_game(), n)


@opfor_only
def map_image(side: str = OPFOR_SIDE, bbox: Optional[str] = None) -> bytes:
    from game.agent import mapimage

    game = _require_game()
    return mapimage.render(
        views.build_turn_context(game, side),
        bbox,
        own_sams=views.build_own_sams(game, side),
    )


def human_notes() -> dict[str, str]:
    """The campaign's Notes window: guidance the human left, read-only."""
    return {"notes": getattr(_require_game(), "notes", "") or ""}


def capabilities() -> dict[str, Any]:
    return {
        "name": "RetLab OPFOR AI",
        "mode": "read and report",
        "side": OPFOR_SIDE,
        "docs": "GET /retribution-ai/start, then /retribution-ai/howtoplay",
        "reads": [
            "turn_context",
            "settings",
            "packages",
            "waypoints/{flight_id}",
            "iads",
            "prev_turns",
            "map/image",
            "human_notes",
        ],
        "writes": [],
    }


# --- connect URL and briefings ---


def _server_base() -> str:
    from game import persistency
    from game.server.settings import ServerSettings

    try:
        s = ServerSettings.get(persistency.server_port())
    except Exception:  # persistency not set up (tests)
        s = ServerSettings.get()
    host = str(s.server_bind_address)
    # "[::1]" reads as broken and trips clients that assume IPv4.
    if host in ("::1", "::", "0.0.0.0", "127.0.0.1", ""):
        host = "localhost"
    elif ":" in host:
        host = f"[{host}]"
    return f"http://{host}:{s.server_port}"


def connect_url() -> str:
    from game.server.security import ApiKeyManager

    return f"{_server_base()}/retribution-ai/start?token={ApiKeyManager.KEY}"


# Under resources/ so the PyInstaller build ships them; read relative to the cwd,
# as resources/whatsnew is.
_DOCS_DIR = Path("resources/agent")
_LEADING_COMMENT = re.compile(r"\A\s*<!--.*?-->\s*", re.DOTALL)


def _render_doc(name: str, subs: dict[str, str]) -> str:
    text = (_DOCS_DIR / name).read_text(encoding="utf-8")
    text = _LEADING_COMMENT.sub("", text, count=1)
    for key, value in subs.items():
        text = text.replace("{" + key + "}", value)
    return text


def start_doc(base_url: str) -> str:
    from game.server.security import ApiKeyManager

    return _render_doc(
        "start.md",
        {"BASE_URL": base_url.rstrip("/"), "TOKEN": ApiKeyManager.KEY},
    )


def howtoplay_doc() -> str:
    subs: dict[str, str] = {}
    try:
        game: Optional[Game] = _require_game()
    except Exception:
        game = None
    if game is not None:
        subs["RED_FACTION"] = game.red.faction.name
        subs["BLUE_FACTION"] = game.blue.faction.name
        subs["CAMPAIGN"] = game.campaign_name or "this campaign"
    return _render_doc("howtoplay.md", subs)
