from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import settings

# Counts requests per IP address. Each route sets its own limit with @limiter.limit(...)
limiter = Limiter(key_func=get_remote_address, storage_uri=settings.rate_limit_storage_uri)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Answer with 429 in the same {"detail": ...} shape as our other errors."""
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please wait a minute and try again."},
    )
