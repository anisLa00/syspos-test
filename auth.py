import os
from hmac import compare_digest

from fastapi import HTTPException, Security
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class APIKeyError(HTTPException):
    pass


async def api_key_error_response(_request, exc: APIKeyError):
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail,
        headers=exc.headers,
    )


def require_api_key(key: str | None = Security(api_key_header)):
    expected = os.getenv("SYSPOS_API_KEY")

    if not expected:
        raise APIKeyError(
            status_code=503,
            detail={
                "error": "api_key_not_configured",
                "message": "API key is not configured",
            },
        )

    if key is None or not compare_digest(key.encode(), expected.encode()):
        raise APIKeyError(
            status_code=401,
            detail={
                "error": "invalid_api_key",
                "message": "Missing or invalid API key",
            },
            headers={"WWW-Authenticate": "APIKey"},
        )