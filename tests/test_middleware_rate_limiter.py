import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.responses import JSONResponse

from api.middleware.rate_limiter import RateLimitMiddleware, _check_rate_limit, _store
from packages.core.exceptions import RateLimitError


@pytest.fixture(autouse=True)
def clear_store():
    """Reset rate limit store before each test."""
    _store.clear()
    yield
    _store.clear()


class TestCheckRateLimit:

    def test_first_request_allowed(self):
        allowed, remaining, retry = _check_rate_limit("test-key", 10, 60)
        assert allowed is True
        assert remaining == 9
        assert retry == 0

    def test_at_limit_blocked(self):
        for _ in range(10):
            _check_rate_limit("key-limit", 10, 60)
        allowed, remaining, retry = _check_rate_limit("key-limit", 10, 60)
        assert allowed is False
        assert remaining == 0
        assert retry > 0

    def test_window_reset(self):
        # Simulate expired window
        _store["key-reset"] = (10, time.time() - 120)
        allowed, remaining, retry = _check_rate_limit("key-reset", 10, 60)
        assert allowed is True
        assert remaining == 9

    def test_different_keys_independent(self):
        for _ in range(10):
            _check_rate_limit("key-a", 10, 60)
        allowed_b, _, _ = _check_rate_limit("key-b", 10, 60)
        assert allowed_b is True


class TestRateLimitMiddleware:

    def make_request(self, path="/api/grants", user_id=None, role="default"):
        request = MagicMock()
        request.url.path = path
        request.client.host = "127.0.0.1"
        request.state.user_id = user_id
        request.state.user_role = role
        return request

    @pytest.mark.asyncio
    async def test_health_path_skipped(self):
        middleware = RateLimitMiddleware(app=MagicMock())
        request = self.make_request(path="/health")
        call_next = AsyncMock(return_value=MagicMock(headers={}))
        await middleware.dispatch(request, call_next)
        call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_rate_limit_headers_added(self):
        middleware = RateLimitMiddleware(app=MagicMock())
        request = self.make_request(user_id="user-1", role="free")
        response = MagicMock()
        response.headers = {}
        call_next = AsyncMock(return_value=response)
        await middleware.dispatch(request, call_next)
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers

    @pytest.mark.asyncio
    async def test_exceeding_limit_raises(self):
        middleware = RateLimitMiddleware(app=MagicMock())
        request = self.make_request(user_id="user-over", role="free")
        _store["user:user-over"] = (30, time.time())  # already at free limit
        call_next = AsyncMock(return_value=MagicMock(headers={}))
        with pytest.raises(RateLimitError):
            await middleware.dispatch(request, call_next)

    @pytest.mark.asyncio
    async def test_unauthenticated_uses_ip(self):
        middleware = RateLimitMiddleware(app=MagicMock())
        request = self.make_request(user_id=None)
        response = MagicMock()
        response.headers = {}
        call_next = AsyncMock(return_value=response)
        await middleware.dispatch(request, call_next)
        assert "ip:127.0.0.1" in _store
