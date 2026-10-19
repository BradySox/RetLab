"""The phone map: the map page and a read-only view of its routes, on home Wi-Fi.

Off by default. When the host turns it on, the server also listens on the PC's
home-network address, and every request from another device goes through
``PhoneGate``: it must carry the phone key, it may only read, and it never reaches
the outside AI's routes. Requests from the PC itself pass through untouched.
See docs/dev/design/retlab-phone-map-notes.md.
"""

from __future__ import annotations

import ipaddress
import secrets
import socket
from pathlib import Path
from typing import Any, Awaitable, Callable, MutableMapping, Optional
from urllib.parse import parse_qsl, urlencode

from starlette.staticfiles import StaticFiles

from .security import ApiKeyManager

Scope = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[MutableMapping[str, Any]]]
Send = Callable[[MutableMapping[str, Any]], Awaitable[None]]
Asgi = Callable[[Scope, Receive, Send], Awaitable[None]]

PAGE_PREFIX = "/phone"
_READ_METHODS = frozenset({"GET", "HEAD"})
# The outside AI's routes and the schema stay on the PC.
_PC_ONLY_PREFIXES = ("/retribution-ai", "/openapi.json")


class PhoneAccess:
    """Whether other devices may connect, and the key they must carry.

    The home-network socket opens only at launch, so turning this on takes a
    restart; turning it off or changing the key holds at once."""

    enabled = False
    key = ""
    #: True once the server is listening on the home network.
    listening = False

    @classmethod
    def configure(cls, enabled: bool, key: str) -> None:
        cls.enabled = enabled and bool(key)
        cls.key = key


def new_phone_key() -> str:
    return secrets.token_urlsafe()


def _is_loopback(host: Optional[str]) -> bool:
    if not host:
        return False
    try:
        return ipaddress.ip_address(host.split("%")[0]).is_loopback
    except ValueError:
        return host == "localhost"


def lan_address() -> Optional[str]:
    """The PC's address on its home network, or None when it has none.

    Connecting a UDP socket sends nothing; it only makes the OS pick the interface
    it would route through."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("192.0.2.1", 9))
            address = str(probe.getsockname()[0])
    except OSError:
        return None
    if _is_loopback(address) or address == "0.0.0.0":
        return None
    return address


def phone_url(address: str, port: int, key: str) -> str:
    server = f"{address}:{port}"
    query = urlencode({"server": server, "key": key, "view": "phone"})
    return f"http://{server}{PAGE_PREFIX}/index.html?{query}"


class PhoneGate:
    """Wraps the server app; applies the phone rules to anything not from this PC."""

    def __init__(self, app: Asgi, client_build: Path) -> None:
        self.app = app
        self.page = StaticFiles(directory=client_build, html=True, check_dir=False)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        kind = scope["type"]
        if kind not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return
        client = scope.get("client")
        if _is_loopback(client[0] if client else None):
            await self.app(scope, receive, send)
            return
        if not PhoneAccess.enabled:
            await _refuse(scope, receive, send)
            return

        path: str = scope["path"]
        if path == PAGE_PREFIX or path.startswith(f"{PAGE_PREFIX}/"):
            if kind == "http" and scope["method"] in _READ_METHODS:
                # The page itself is the client bundle; the data behind it is keyed.
                page_scope = dict(scope)
                page_scope["path"] = path[len(PAGE_PREFIX) :] or "/"
                page_scope["root_path"] = scope.get("root_path", "") + PAGE_PREFIX
                await self.page(page_scope, receive, send)
            else:
                await _refuse(scope, receive, send)
            return

        if (
            (kind == "http" and scope["method"] not in _READ_METHODS)
            or path.startswith(_PC_ONLY_PREFIXES)
            or not _carries_phone_key(scope)
        ):
            await _refuse(scope, receive, send)
            return
        await self.app(_with_map_key(scope), receive, send)


def _carries_phone_key(scope: Scope) -> bool:
    key = PhoneAccess.key.encode()
    for name, value in scope.get("headers", []):
        if name == b"x-api-key" and secrets.compare_digest(value, key):
            return True
    for name, value in parse_qsl(scope.get("query_string", b"").decode("latin-1")):
        if name == "token" and secrets.compare_digest(value.encode(), key):
            return True
    return False


def _with_map_key(scope: Scope) -> Scope:
    """The same request as the map page would send it, so the routes' own key
    checks stay the only ones they have."""
    map_key = ApiKeyManager.MAP_KEY
    gated = dict(scope)
    gated["headers"] = [
        (name, value)
        for name, value in scope.get("headers", [])
        if name != b"x-api-key"
    ] + [(b"x-api-key", map_key.encode())]
    query = [
        (name, map_key if name == "token" else value)
        for name, value in parse_qsl(
            scope.get("query_string", b"").decode("latin-1"), keep_blank_values=True
        )
    ]
    gated["query_string"] = urlencode(query).encode("latin-1")
    return gated


async def _refuse(scope: Scope, receive: Receive, send: Send) -> None:
    if scope["type"] == "websocket":
        await send({"type": "websocket.close", "code": 1008})
        return
    await send(
        {
            "type": "http.response.start",
            "status": 403,
            "headers": [(b"content-type", b"text/plain")],
        }
    )
    await send({"type": "http.response.body", "body": b"Forbidden"})
