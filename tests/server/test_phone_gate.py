"""The phone map: another device can read the map with the phone key and do nothing else."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Iterator, MutableMapping, Optional

import pytest

from game import persistency
from game.server.app import app
from game.server.phone import PhoneAccess, PhoneGate, phone_url
from game.server.security import ApiKeyManager

PHONE = "192.168.1.20"
PHONE_KEY = "phone-key"


@pytest.fixture
def gate(tmp_path: Path) -> Iterator[PhoneGate]:
    build = tmp_path / "build"
    build.mkdir()
    (build / "index.html").write_text("<html>map</html>", encoding="utf-8")
    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16880)
    previous = (PhoneAccess.enabled, PhoneAccess.key, ApiKeyManager.map_sends_key)
    PhoneAccess.configure(True, PHONE_KEY)
    ApiKeyManager.map_sends_key = True
    yield PhoneGate(app, build)
    PhoneAccess.enabled, PhoneAccess.key, ApiKeyManager.map_sends_key = previous


def _call(
    gate: PhoneGate,
    path: str,
    method: str = "GET",
    query: str = "",
    headers: Optional[dict[str, str]] = None,
    client: str = PHONE,
    kind: str = "http",
) -> tuple[Any, str]:
    scope: dict[str, Any] = {
        "type": kind,
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "scheme": "http" if kind == "http" else "ws",
        "method": method,
        "path": path,
        "raw_path": path.encode(),
        "query_string": query.encode(),
        "root_path": "",
        "headers": [
            (k.lower().encode(), v.encode()) for k, v in (headers or {}).items()
        ],
        "client": (client, 50000),
        "server": ("192.168.1.10", 16880),
        "subprotocols": [],
    }
    sent: list[MutableMapping[str, Any]] = []

    async def receive() -> MutableMapping[str, Any]:
        if kind == "websocket":
            return {"type": "websocket.connect"}
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: MutableMapping[str, Any]) -> None:
        sent.append(message)

    asyncio.run(gate(scope, receive, send))
    if kind == "websocket":
        return sent[0]["type"], ""
    body = b"".join(m.get("body", b"") for m in sent if m["type"].endswith("body"))
    return sent[0]["status"], body.decode("utf-8", errors="ignore")


def test_the_phone_key_reads_a_map_route(gate: PhoneGate) -> None:
    assert _call(gate, "/map-tiles/", headers={"X-API-Key": PHONE_KEY}) == (200, "[]")
    assert _call(gate, "/map-tiles/", query=f"token={PHONE_KEY}") == (200, "[]")


def test_another_device_needs_the_phone_key(gate: PhoneGate) -> None:
    assert _call(gate, "/map-tiles/")[0] == 403
    # The PC's own map key never leaves the PC, and is no use from outside.
    assert (
        _call(gate, "/map-tiles/", headers={"X-API-Key": ApiKeyManager.MAP_KEY})[0]
        == 403
    )


@pytest.mark.parametrize("method", ["POST", "PUT", "DELETE", "PATCH"])
def test_the_phone_cannot_change_anything(gate: PhoneGate, method: str) -> None:
    status, _ = _call(gate, "/map-layers", method, headers={"X-API-Key": PHONE_KEY})
    assert status == 403


def test_the_phone_never_reaches_the_ai_routes(gate: PhoneGate) -> None:
    for path in ("/retribution-ai/capabilities", "/openapi.json"):
        query = f"token={PHONE_KEY}"
        assert _call(gate, path, query=query)[0] == 403


def test_the_page_is_served_without_a_key(gate: PhoneGate) -> None:
    assert _call(gate, "/phone/index.html") == (200, "<html>map</html>")
    assert _call(gate, "/phone/") == (200, "<html>map</html>")
    assert _call(gate, "/phone/index.html", "POST")[0] == 403


def test_turned_off_refuses_every_other_device(gate: PhoneGate) -> None:
    PhoneAccess.configure(False, PHONE_KEY)
    assert _call(gate, "/map-tiles/", query=f"token={PHONE_KEY}")[0] == 403
    assert _call(gate, "/phone/index.html")[0] == 403


def test_the_pc_itself_is_not_gated(gate: PhoneGate) -> None:
    header = {"X-API-Key": ApiKeyManager.MAP_KEY}
    assert _call(gate, "/map-tiles/", headers=header, client="::1") == (200, "[]")
    assert _call(gate, "/map-tiles/", headers=header, client="127.0.0.1")[0] == 200
    # A stale client build leaves the map routes open on the PC, never to the phone.
    ApiKeyManager.map_sends_key = False
    assert _call(gate, "/map-tiles/", client="::1")[0] == 200
    assert _call(gate, "/map-tiles/")[0] == 403


def test_the_event_stream_takes_the_phone_key(gate: PhoneGate) -> None:
    refused, _ = _call(gate, "/eventstream", kind="websocket")
    assert refused == "websocket.close"
    wrong, _ = _call(gate, "/eventstream", query="token=wrong", kind="websocket")
    assert wrong == "websocket.close"


def test_the_link_carries_the_server_and_the_phone_key() -> None:
    url = phone_url("192.168.1.10", 16880, "abc")
    assert url == (
        "http://192.168.1.10:16880/phone/index.html"
        "?server=192.168.1.10%3A16880&key=abc&view=phone"
    )
