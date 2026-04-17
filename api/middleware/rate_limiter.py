import time
import logging
from collections import defaultdict
from typing import Dict, Tuple
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from packages.core.exceptions import RateLimitError

logger = logging.getLogger("grantpath.rate_limiter")

# In-memory store: {key: (request_count, window_start)}
# Replace with Redis for multi-process/production deployments
_store: Dict[str, Tuple[int, float]] = defaultdict(lambda: (0, time.time()))

# Rate limit tiers (requests per window_seconds)
RATE_LIMITS = {
    "free":    {"requests": 30,  "window": 60},   # 30/min
    "premium": {"requests": 120, "window": 60},   # 120/min
    "admin":   {"requests": 1000, "window": 60},  # effectively unlimited
    "default": {"requests": 20,  "window": 60},   # unauthenticated
}


def _get_limit(role: str) -> Tuple[int, int]:
    tier = RATE_LIMITS.get(role, RATE_LIMITS["default"])
    return tier["requests"], tier["window"]


def _check_rate_limit(key: str, max_requests: int, window: int) -> Tuple[bool, int, int]:
    """
    Returns (allowed, remaining, retry_after_seconds).
    """
    count, window_start = _store[key]
    now = time.time()

    if now - window_start > window:
        # Reset window
        _store[key] = (1, now)
        return True, max_requests - 1, 0

    if count >= max_requests:
        retry_after = int(window - (now - window_start))
        return False, 0, retry_after

    _store[key] = (count + 1, window_start)
    return True, max_requests - count - 1, 0


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Per-user (or per-IP for unauthenticated) sliding window rate limiting.
    """

    SKIP_PATHS = {"/health", "/ready", "/live", "/docs", "/openapi.json"}

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        # Identify requester
        user_id = getattr(request.state, "user_id", None)
        role = getattr(request.state, "user_role", "default")
        key = f"user:{user_id}" if user_id else f"ip:{request.client.host}"

        max_requests, window = _get_limit(role)
        allowed, remaining, retry_after = _check_rate_limit(key, max_requests, window)

        if not allowed:
            logger.warning(f"Rate limit exceeded: {key}")
            raise RateLimitError(
                f"Rate limit exceeded. Retry after {retry_after} seconds.",
                context={"retry_after": retry_after, "key": key},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Window"] = str(window)

        return response
