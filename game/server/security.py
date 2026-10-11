import logging
import re
import secrets
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, Security, WebSocket, WebSocketException, status
from fastapi.security import APIKeyHeader, APIKeyQuery

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
# A query token lets an outside AI authenticate with nothing but a pasted URL, and
# is the only way a map tile or the event stream can carry one.
API_KEY_QUERY = APIKeyQuery(name="token", auto_error=False)

_TOKEN_IN_URL = re.compile(r"([?&]token=)[^&\s\"']+")


class ApiKeyManager:
    #: The outside AI's key (Copy AI connect link). It opens the AI routes only.
    KEY = secrets.token_urlsafe()
    #: The map page's key, handed to it by Qt. Blue's plan is behind this one, so
    #: the AI's key must never open a map route.
    MAP_KEY = secrets.token_urlsafe()
    #: False for a run whose map client was built before the map sent the key (a
    #: source checkout with a stale ``client/build``). The AI routes ignore it.
    map_sends_key = True

    @classmethod
    def verify(
        cls,
        api_key_header: Optional[str] = Security(API_KEY_HEADER),
        api_key_query: Optional[str] = Security(API_KEY_QUERY),
    ) -> None:
        if cls.KEY not in (api_key_header, api_key_query):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    @classmethod
    def verify_map(
        cls,
        api_key_header: Optional[str] = Security(API_KEY_HEADER),
        api_key_query: Optional[str] = Security(API_KEY_QUERY),
    ) -> None:
        if cls.map_sends_key and cls.MAP_KEY not in (api_key_header, api_key_query):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    @classmethod
    def verify_map_websocket(cls, websocket: WebSocket) -> None:
        if cls.map_sends_key and websocket.query_params.get("token") != cls.MAP_KEY:
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)

    @classmethod
    def check_map_client(cls, client_build: Path) -> None:
        """Leaves the map routes open when the built client cannot send the key.

        ``client/build`` is not tracked and nothing rebuilds it on launch, so a
        source checkout can run a bundle from before the key. Refusing its requests
        would blank the map; the release build always ships a matching bundle."""
        bundles = list((client_build / "static" / "js").glob("main.*.js"))
        cls.map_sends_key = any(
            "X-API-Key" in bundle.read_text(encoding="utf-8", errors="ignore")
            for bundle in bundles
        )
        if not cls.map_sends_key:
            logging.warning(
                "The map client in %s was built before the map sent the API key, "
                "so the map server's routes are open for this run. Rebuild the "
                "client (npm run build in client/) to close them.",
                client_build,
            )


class TokenRedactingFilter(logging.Filter):
    """Keeps the key out of the log: uvicorn logs each request line, query included."""

    @staticmethod
    def _redact(value: object) -> object:
        if isinstance(value, str):
            return _TOKEN_IN_URL.sub(r"\1[redacted]", value)
        return value

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = self._redact(record.msg)
        if isinstance(record.args, tuple):
            record.args = tuple(self._redact(arg) for arg in record.args)
        return True
