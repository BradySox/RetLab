"""Every route on the map server needs a key, and the AI's key opens only its own.

The map's routes serve blue's plan. Until 2026-10-11 they were open, so anything on
the PC that could reach the port could read it, the outside AI (§109) included.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterator

import pytest
from fastapi import WebSocketException
from fastapi.routing import APIRoute, APIWebSocketRoute

from game import persistency
from game.server.app import app
from game.server.security import ApiKeyManager, TokenRedactingFilter
from tests.server import asgi

AI = "/retribution-ai/"
MAP_HEADER = {"X-API-Key": ApiKeyManager.MAP_KEY}
AI_HEADER = {"X-API-Key": ApiKeyManager.KEY}


@pytest.fixture(autouse=True)
def map_keyed() -> Iterator[None]:
    previous = ApiKeyManager.map_sends_key
    ApiKeyManager.map_sends_key = True
    yield
    ApiKeyManager.map_sends_key = previous


def test_the_app_serves_nothing_but_api_routes() -> None:
    # A mount or a static route would not carry a router's key check.
    kinds = {type(route) for route in app.routes}
    assert kinds == {APIRoute, APIWebSocketRoute}
    assert len(list(asgi.http_routes())) > 60


@pytest.mark.parametrize("method, path", sorted(set(asgi.http_routes())))
def test_no_route_answers_without_a_key(method: str, path: str) -> None:
    status, _ = asgi.request(asgi.concrete(path), method)
    assert status == 403
    status, _ = asgi.request(asgi.concrete(path), method, query="token=wrong")
    assert status == 403


@pytest.mark.parametrize(
    "method, path",
    sorted(r for r in set(asgi.http_routes()) if not r[1].startswith(AI)),
)
def test_the_ais_key_opens_no_map_route(method: str, path: str) -> None:
    if path == "/openapi.json":
        pytest.skip("the schema names routes and serves no campaign data")
    status, _ = asgi.request(asgi.concrete(path), method, headers=AI_HEADER)
    assert status == 403
    query = f"token={ApiKeyManager.KEY}"
    assert asgi.request(asgi.concrete(path), method, query=query)[0] == 403


def test_the_maps_key_opens_no_ai_route() -> None:
    status, _ = asgi.request(f"{AI}capabilities", headers=MAP_HEADER)
    assert status == 403


def test_the_maps_key_opens_a_map_route_by_header_or_query(tmp_path: Path) -> None:
    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16880)
    assert asgi.request("/map-tiles/", headers=MAP_HEADER) == (200, "[]")
    # A tile is an <img>: it can only carry the key in its URL.
    query = f"token={ApiKeyManager.MAP_KEY}"
    assert asgi.request("/map-tiles/", query=query) == (200, "[]")


def test_the_schema_is_keyed_and_its_browser_is_gone() -> None:
    assert asgi.request("/docs")[0] == 404
    assert asgi.request("/redoc")[0] == 404
    status, body = asgi.request("/openapi.json", headers=AI_HEADER)
    assert status == 200 and "/flights/" in body


def test_the_event_stream_refuses_a_connect_without_the_maps_key() -> None:
    assert asgi.websocket_handshake("/eventstream") == "websocket.close"
    wrong = f"token={ApiKeyManager.KEY}"
    assert asgi.websocket_handshake("/eventstream", wrong) == "websocket.close"


class _Socket:
    def __init__(self, token: str) -> None:
        self.query_params = {"token": token}


def test_the_event_stream_check_passes_the_maps_key() -> None:
    ApiKeyManager.verify_map_websocket(_Socket(ApiKeyManager.MAP_KEY))  # type: ignore[arg-type]
    with pytest.raises(WebSocketException):
        ApiKeyManager.verify_map_websocket(_Socket("wrong"))  # type: ignore[arg-type]


def _client_build(root: Path, bundle: str) -> Path:
    scripts = root / "static" / "js"
    scripts.mkdir(parents=True)
    (scripts / "main.abc123.js").write_text(bundle, encoding="utf-8")
    return root


def test_a_client_built_with_the_key_keeps_the_map_routes_closed(
    tmp_path: Path,
) -> None:
    ApiKeyManager.check_map_client(_client_build(tmp_path, 'e={"X-API-Key":t}'))
    assert ApiKeyManager.map_sends_key
    assert asgi.request("/map-tiles/")[0] == 403


def test_a_client_built_before_the_key_still_gets_its_map(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    # client/build is untracked and never rebuilt on launch: refusing an old
    # bundle's requests would blank the map on a source checkout.
    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16880)
    with caplog.at_level(logging.WARNING):
        ApiKeyManager.check_map_client(_client_build(tmp_path / "build", "old"))
    assert not ApiKeyManager.map_sends_key
    assert "Rebuild the client" in caplog.text
    assert asgi.request("/map-tiles/")[0] == 200
    ApiKeyManager.verify_map_websocket(_Socket(""))  # type: ignore[arg-type]
    # The AI's routes never open without the AI's key.
    assert asgi.request(f"{AI}capabilities")[0] == 403


def test_the_key_is_kept_out_of_the_request_log() -> None:
    record = logging.LogRecord(
        "uvicorn.access",
        logging.INFO,
        __file__,
        1,
        '%s - "%s %s HTTP/%s" %d',
        ("::1:5", "GET", "/map-tiles/a/1/2/3.png?token=SECRETKEY&x=1", "1.1", 200),
        None,
    )
    assert TokenRedactingFilter().filter(record)
    line = record.getMessage()
    assert "SECRETKEY" not in line
    assert "/map-tiles/a/1/2/3.png?token=[redacted]&x=1" in line
    assert line.endswith("200")
