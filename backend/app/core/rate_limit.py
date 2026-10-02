"""Per-user rate limiting (slowapi). Protects the free-tier LLM quota from abuse.

Key = user id from the JWT when present, otherwise the client IP.
Storage = Redis when REDIS_URL is set (shared across API replicas), else in-memory.
"""

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings


def _rate_limit_key(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        from app.core.security import decode_access_token

        try:
            return f"user:{decode_access_token(auth[7:])['sub']}"
        except Exception:  # invalid token: fall back to IP; auth will reject it anyway
            pass
    return f"ip:{get_remote_address(request)}"


def _build_limiter() -> Limiter:
    settings = get_settings()
    return Limiter(
        key_func=_rate_limit_key,
        storage_uri=settings.redis_url or "memory://",
        enabled=settings.rate_limit_enabled,
        headers_enabled=False,
        in_memory_fallback_enabled=True,  # if Redis is down, limit per-process instead
    )


limiter = _build_limiter()
