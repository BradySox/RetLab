"""§115: the end-of-turn ping to the host's phone through ntfy."""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from typing import Any

from game.retlab.turn_ping import TurnPing, send_turn_ping, turn_ping, valid_topic


def _game(sitrep: Any = None) -> Any:
    packages = [
        SimpleNamespace(flights=[object(), object()]),
        SimpleNamespace(flights=[object()]),
    ]
    return SimpleNamespace(
        campaign_name="Scenic Route",
        turn=4,
        current_day=date(2004, 6, 12),
        last_sitrep=sitrep,
        blue=SimpleNamespace(ato=SimpleNamespace(packages=packages)),
    )


def test_topic_names_follow_ntfy() -> None:
    assert valid_topic("retlab-brady_7f3k")
    assert not valid_topic("")
    assert not valid_topic("two words")
    assert not valid_topic("a/b")
    assert not valid_topic("x" * 65)


def test_the_ping_names_the_turn_and_the_next_plan() -> None:
    ping = turn_ping(_game())
    assert ping.title == "RetLab: turn 4 is ready"
    assert ping.body.splitlines() == [
        "Scenic Route, turn 4, Jun 12, 2004.",
        "Next turn planned: 3 flights. The map is ready.",
    ]


def test_the_ping_carries_the_sitrep_when_there_is_news() -> None:
    news = SimpleNamespace(has_news=True, kneeboard_lines=lambda: ["Lost: Batumi"])
    assert "Lost: Batumi" in turn_ping(_game(news)).body.splitlines()
    quiet = SimpleNamespace(has_news=False, kneeboard_lines=lambda: ["Lost: Batumi"])
    assert "Lost: Batumi" not in turn_ping(_game(quiet)).body


def test_sending_posts_to_the_topic_in_the_background() -> None:
    sent: list[tuple[str, TurnPing]] = []
    ping = TurnPing("t", "b")
    thread = send_turn_ping("my-topic", ping, post=lambda t, p: sent.append((t, p)))
    assert thread is not None
    thread.join(5)
    assert sent == [("my-topic", ping)]


def test_a_failed_send_is_swallowed() -> None:
    def fail(topic: str, ping: TurnPing) -> None:
        raise OSError("offline")

    thread = send_turn_ping("my-topic", TurnPing("t", "b"), post=fail)
    assert thread is not None
    thread.join(5)
    assert not thread.is_alive()


def test_a_bad_topic_sends_nothing() -> None:
    sent: list[str] = []
    assert (
        send_turn_ping("a b", TurnPing("t", "b"), post=lambda t, p: sent.append(t))
        is None
    )
    assert sent == []
