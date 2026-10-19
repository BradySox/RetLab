"""The end-of-turn ping to the host's phone through ntfy (§115).

ntfy is a free push service: the phone app subscribes to a topic name and
anything posted to ``https://ntfy.sh/<topic>`` arrives as a notification. The
topic is the only secret, so the host picks a hard-to-guess one. Off until a
topic is set. See docs/dev/design/retlab-phone-map-notes.md.
"""

from __future__ import annotations

import logging
import re
import threading
import urllib.request
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    from game import Game

NTFY_SERVER = "https://ntfy.sh"
SEND_TIMEOUT_SECONDS = 10
# ntfy's own rule for a topic name.
_TOPIC = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def valid_topic(topic: str) -> bool:
    return bool(_TOPIC.match(topic))


@dataclass(frozen=True)
class TurnPing:
    title: str
    body: str


def turn_ping(game: Game) -> TurnPing:
    """What the phone shows once a mission's results are in."""
    campaign = game.campaign_name or "Campaign"
    lines = [f"{campaign}, turn {game.turn}, {game.current_day:%b %d, %Y}."]
    sitrep = game.last_sitrep
    if sitrep is not None and sitrep.has_news:
        lines.extend(sitrep.kneeboard_lines())
    flights = sum(len(package.flights) for package in game.blue.ato.packages)
    lines.append(f"Next turn planned: {flights} flights. The map is ready.")
    return TurnPing(f"RetLab: turn {game.turn} is ready", "\n".join(lines))


def _post(topic: str, ping: TurnPing) -> None:
    request = urllib.request.Request(
        f"{NTFY_SERVER}/{topic}",
        data=ping.body.encode("utf-8"),
        method="POST",
        # ntfy reads header values as latin-1; the body carries the unicode.
        headers={
            "Title": ping.title.encode("ascii", "replace").decode(),
            "Tags": "airplane",
        },
    )
    with urllib.request.urlopen(request, timeout=SEND_TIMEOUT_SECONDS):
        pass


def send_turn_ping(
    topic: str,
    ping: TurnPing,
    post: Callable[[str, TurnPing], None] = _post,
) -> Optional[threading.Thread]:
    """Sends in the background; a ping never holds up or fails the turn."""
    if not valid_topic(topic):
        return None

    def run() -> None:
        try:
            post(topic, ping)
        except Exception:
            logging.exception("The end-of-turn ping did not send")

    thread = threading.Thread(target=run, name="turn-ping", daemon=True)
    thread.start()
    return thread
