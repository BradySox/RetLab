"""Calls the server app as uvicorn would, without a socket or an HTTP client.

The other server tests call route functions directly, which skips the key check on
the router. These go through the app, so a route's dependencies run.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any, Iterable, MutableMapping, Optional

from game.server.app import app

_PATH_PARAM = re.compile(r"\{[^}]+\}")


def concrete(path: str) -> str:
    """A route path with every parameter filled in."""
    return _PATH_PARAM.sub("1", path)


def _scope(kind: str, path: str, query: str, headers: dict[str, str]) -> dict[str, Any]:
    return {
        "type": kind,
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "scheme": "http" if kind == "http" else "ws",
        "path": path,
        "raw_path": path.encode(),
        "query_string": query.encode(),
        "root_path": "",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "client": ("::1", 50000),
        "server": ("::1", 16880),
        "subprotocols": [],
    }


def request(
    path: str,
    method: str = "GET",
    query: str = "",
    headers: Optional[dict[str, str]] = None,
) -> tuple[int, str]:
    """(status, body text) for one HTTP request."""
    scope = _scope("http", path, query, headers or {})
    scope["method"] = method
    sent: list[MutableMapping[str, Any]] = []

    async def receive() -> MutableMapping[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: MutableMapping[str, Any]) -> None:
        sent.append(message)

    asyncio.run(app(scope, receive, send))
    body = b"".join(m.get("body", b"") for m in sent if m["type"].endswith("body"))
    return sent[0]["status"], body.decode("utf-8", errors="ignore")


def websocket_handshake(path: str, query: str = "") -> str:
    """The first message the server answers a websocket connect with."""
    sent: list[MutableMapping[str, Any]] = []

    async def receive() -> MutableMapping[str, Any]:
        return {"type": "websocket.connect"}

    async def send(message: MutableMapping[str, Any]) -> None:
        sent.append(message)

    asyncio.run(app(_scope("websocket", path, query, {}), receive, send))
    return str(sent[0]["type"])


def http_routes() -> Iterable[tuple[str, str]]:
    """Every (method, path) the app serves over HTTP."""
    for route in app.routes:
        for method in sorted(getattr(route, "methods", None) or ()):
            if method not in ("HEAD", "OPTIONS"):
                yield method, getattr(route, "path")
