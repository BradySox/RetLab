import secrets
from typing import Optional

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader, APIKeyQuery

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
# A query token lets an outside AI authenticate with nothing but a pasted URL.
API_KEY_QUERY = APIKeyQuery(name="token", auto_error=False)


class ApiKeyManager:
    KEY = secrets.token_urlsafe()

    @classmethod
    def verify(
        cls,
        api_key_header: Optional[str] = Security(API_KEY_HEADER),
        api_key_query: Optional[str] = Security(API_KEY_QUERY),
    ) -> None:
        if cls.KEY not in (api_key_header, api_key_query):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
