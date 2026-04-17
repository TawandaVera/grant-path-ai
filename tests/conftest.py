import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta
from jose import jwt

from packages.core.config import settings
from main import app


def make_token(user_id="user-123", role="free", email="test@example.com"):
    exp = datetime.utcnow() + timedelta(minutes=15)
    return jwt.encode(
        {"sub": user_id, "email": email, "role": role, "exp": exp},
        settings.JWT_SECRET,
        algorithm="HS256",
    )


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_headers():
    return {"Authorization": f"Bearer {make_token()}"}


@pytest.fixture
def premium_headers():
    return {"Authorization": f"Bearer {make_token(role='premium')}"}


@pytest.fixture
def admin_headers():
    return {"Authorization": f"Bearer {make_token(role='admin')}"}


@pytest.fixture
def mock_db():
    with patch("packages.database.connection.db_pool") as mock:
        mock.health_check = AsyncMock(return_value=True)
        mock.connection = AsyncMock()
        mock.transaction = AsyncMock()
        yield mock
