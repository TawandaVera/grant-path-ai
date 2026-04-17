import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from jose import jwt

from packages.core.config import settings
from packages.core.exceptions import AuthenticationError, AuthorizationError
from api.middleware.auth import require_auth, require_premium, require_admin


def make_token(sub="user-123", role="free", expired=False):
    exp = datetime.utcnow() + (timedelta(minutes=-5) if expired else timedelta(minutes=15))
    return jwt.encode(
        {"sub": sub, "email": "test@example.com", "role": role, "exp": exp},
        settings.JWT_SECRET,
        algorithm="HS256",
    )


def mock_request(token=None, user_id=None, role="free"):
    request = MagicMock()
    request.state.user_id = user_id
    request.state.user_role = role
    creds = MagicMock()
    creds.credentials = token
    request._creds = creds
    return request


class TestRequireAuth:

    @pytest.mark.asyncio
    async def test_valid_token_succeeds(self):
        token = make_token()
        request = mock_request(token)
        with patch("api.middleware.auth.security", return_value=AsyncMock(
            return_value=MagicMock(credentials=token)
        )):
            payload = await require_auth(request)
            assert payload["sub"] == "user-123"

    @pytest.mark.asyncio
    async def test_missing_token_raises(self):
        request = mock_request(token=None)
        with patch("api.middleware.auth.security", return_value=AsyncMock(
            return_value=MagicMock(credentials=None)
        )):
            with pytest.raises(AuthenticationError, match="No authentication token"):
                await require_auth(request)

    @pytest.mark.asyncio
    async def test_expired_token_raises(self):
        token = make_token(expired=True)
        request = mock_request(token)
        with patch("api.middleware.auth.security", return_value=AsyncMock(
            return_value=MagicMock(credentials=token)
        )):
            with pytest.raises(AuthenticationError, match="expired"):
                await require_auth(request)

    @pytest.mark.asyncio
    async def test_invalid_token_raises(self):
        request = mock_request("not.a.valid.token")
        with patch("api.middleware.auth.security", return_value=AsyncMock(
            return_value=MagicMock(credentials="not.a.valid.token")
        )):
            with pytest.raises(AuthenticationError):
                await require_auth(request)


class TestRequirePremium:

    @pytest.mark.asyncio
    async def test_premium_role_allowed(self):
        token = make_token(role="premium")
        request = mock_request(token)
        with patch("api.middleware.auth.require_auth", return_value=AsyncMock(
            return_value={"sub": "user-123", "role": "premium"}
        )):
            payload = await require_premium(request)
            assert payload["role"] == "premium"

    @pytest.mark.asyncio
    async def test_free_role_blocked(self):
        token = make_token(role="free")
        request = mock_request(token)
        with patch("api.middleware.auth.require_auth", new=AsyncMock(
            return_value={"sub": "user-123", "role": "free"}
        )):
            with pytest.raises(AuthorizationError, match="premium"):
                await require_premium(request)

    @pytest.mark.asyncio
    async def test_admin_role_allowed(self):
        with patch("api.middleware.auth.require_auth", new=AsyncMock(
            return_value={"sub": "admin-1", "role": "admin"}
        )):
            payload = await require_premium(MagicMock())
            assert payload["role"] == "admin"


class TestRequireAdmin:

    @pytest.mark.asyncio
    async def test_admin_role_allowed(self):
        with patch("api.middleware.auth.require_auth", new=AsyncMock(
            return_value={"sub": "admin-1", "role": "admin"}
        )):
            payload = await require_admin(MagicMock())
            assert payload["role"] == "admin"

    @pytest.mark.asyncio
    async def test_premium_role_blocked(self):
        with patch("api.middleware.auth.require_auth", new=AsyncMock(
            return_value={"sub": "user-1", "role": "premium"}
        )):
            with pytest.raises(AuthorizationError, match="Admin"):
                await require_admin(MagicMock())
