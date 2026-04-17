import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock

from main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


class TestHealthEndpoints:

    def test_health_check_healthy(self, client):
        with patch("api.routes.health.db_pool.health_check", new=AsyncMock(return_value=True)):
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["checks"]["database"] == "ok"
            assert "uptime_seconds" in data
            assert "version" in data

    def test_health_check_degraded(self, client):
        with patch("api.routes.health.db_pool.health_check", new=AsyncMock(return_value=False)):
            response = client.get("/health")
            assert response.status_code == 503
            assert response.json()["status"] == "degraded"
            assert response.json()["checks"]["database"] == "unreachable"

    def test_readiness_ready(self, client):
        with patch("api.routes.health.db_pool.health_check", new=AsyncMock(return_value=True)):
            response = client.get("/ready")
            assert response.status_code == 200
            assert response.json()["ready"] is True

    def test_readiness_not_ready(self, client):
        with patch("api.routes.health.db_pool.health_check", new=AsyncMock(return_value=False)):
            response = client.get("/ready")
            assert response.status_code == 503
            assert response.json()["ready"] is False
            assert "reason" in response.json()

    def test_liveness_always_alive(self, client):
        response = client.get("/live")
        assert response.status_code == 200
        assert response.json()["alive"] is True
        assert "uptime_seconds" in response.json()
