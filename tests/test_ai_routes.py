import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from main import app
from tests.conftest import make_token


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def premium_headers():
    return {"Authorization": f"Bearer {make_token(role='premium')}"}


@pytest.fixture
def free_headers():
    return {"Authorization": f"Bearer {make_token(role='free')}"}


MOCK_GRANT = {
    "id": "grant-001",
    "title": "Climate Innovation Fund",
    "funder_name": "Green Foundation",
    "funding_amount_min": 50000,
    "funding_amount_max": 250000,
    "deadline": "2026-12-01",
    "category_tags": ["climate", "innovation"],
    "description": "Funding for climate solutions.",
    "eligibility_criteria": {"org_types": ["nonprofit"]},
    "scoring_criteria": [{"name": "Impact", "weight": 40}],
    "section_limits": {"project_narrative": "500 words"},
    "status": "active",
}

MOCK_ORG = {
    "name": "Green Future Org",
    "mission": "Advancing climate solutions",
    "org_type": "nonprofit",
    "location": "Phoenix, AZ",
    "focus_areas": ["climate", "sustainability"],
    "annual_budget_min": 100000,
    "annual_budget_max": 500000,
}


class TestAIMatch:

    def test_requires_premium(self, client, free_headers):
        with patch("api.routes.ai.TokenBudgetManager.check_and_reserve", new=AsyncMock(return_value=500)):
            response = client.get("/api/ai/match", headers=free_headers)
            assert response.status_code == 403

    def test_match_returns_results(self, client, premium_headers):
        with (
            patch("api.routes.ai.TokenBudgetManager.check_and_reserve", new=AsyncMock(return_value=500)),
            patch("api.routes.ai.TokenBudgetManager.record_usage", new=AsyncMock()),
            patch("api.routes.ai.TokenBudgetManager.get_budget_status", new=AsyncMock(return_value={})),
            patch("api.routes.ai._get_org_profile", new=AsyncMock(return_value=MOCK_ORG)),
            patch("api.routes.ai.grant_repo.search", new=AsyncMock(return_value=([MOCK_GRANT], 1))),
            patch("api.routes.ai.ai_engine.match_grants", new=AsyncMock(return_value=[
                {**MOCK_GRANT, "ai_score": 0.92, "ai_reason": "Strong mission alignment"}
            ])),
            patch("api.routes.ai.AuditLogger.log", new=AsyncMock()),
        ):
            response = client.get("/api/ai/match", headers=premium_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 1
            assert data["matches"][0]["ai_score"] == 0.92
            assert data["engine"] == "gemini_semantic"

    def test_no_grants_returns_empty(self, client, premium_headers):
        with (
            patch("api.routes.ai.TokenBudgetManager.check_and_reserve", new=AsyncMock(return_value=500)),
            patch("api.routes.ai._get_org_profile", new=AsyncMock(return_value=MOCK_ORG)),
            patch("api.routes.ai.grant_repo.search", new=AsyncMock(return_value=([], 0))),
        ):
            response = client.get("/api/ai/match", headers=premium_headers)
            assert response.status_code == 200
            assert response.json()["count"] == 0


class TestAIDraft:

    def test_draft_section_success(self, client, premium_headers):
        with (
            patch("api.routes.ai.TokenBudgetManager.check_and_reserve", new=AsyncMock(return_value=4000)),
            patch("api.routes.ai.TokenBudgetManager.record_usage", new=AsyncMock()),
            patch("api.routes.ai.TokenBudgetManager.get_budget_status", new=AsyncMock(return_value={})),
            patch("api.routes.ai._get_org_profile", new=AsyncMock(return_value=MOCK_ORG)),
            patch("api.routes.ai.grant_repo.get_by_id", new=AsyncMock(return_value=MOCK_GRANT)),
            patch("api.routes.ai.ai_engine.draft_section", new=AsyncMock(return_value={
                "section": "project_narrative",
                "content": "Our organization will...",
                "word_count": 120,
                "within_limit": True,
                "was_sanitized": False,
            })),
            patch("api.routes.ai.AuditLogger.log", new=AsyncMock()),
        ):
            response = client.post(
                "/api/ai/draft/grant-001",
                json={"section": "project_narrative", "word_limit": 500},
                headers=premium_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["section"] == "project_narrative"
            assert data["within_limit"] is True
            assert data["grant_id"] == "grant-001"

    def test_invalid_grant_raises_404(self, client, premium_headers):
        with (
            patch("api.routes.ai.TokenBudgetManager.check_and_reserve", new=AsyncMock(return_value=4000)),
            patch("api.routes.ai._get_org_profile", new=AsyncMock(return_value=MOCK_ORG)),
            patch("api.routes.ai.grant_repo.get_by_id", new=AsyncMock(return_value=None)),
        ):
            response = client.post(
                "/api/ai/draft/nonexistent",
                json={"section": "narrative"},
                headers=premium_headers,
            )
            assert response.status_code == 404


class TestAIReview:

    def test_review_success(self, client, premium_headers):
        mock_app = {
            "id": "app-001",
            "user_id": "user-123",
            "grant_id": "grant-001",
            "status": "draft",
            "sections": {"project_narrative": "Our project will..."},
        }
        with (
            patch("api.routes.ai.TokenBudgetManager.check_and_reserve", new=AsyncMock(return_value=2000)),
            patch("api.routes.ai.TokenBudgetManager.record_usage", new=AsyncMock()),
            patch("api.routes.ai.TokenBudgetManager.get_budget_status", new=AsyncMock(return_value={})),
            patch("api.routes.ai.app_repo.get_by_id", new=AsyncMock(return_value=mock_app)),
            patch("api.routes.ai.grant_repo.get_by_id", new=AsyncMock(return_value=MOCK_GRANT)),
            patch("api.routes.ai.ai_engine.review_application", new=AsyncMock(return_value={
                "overall_score": 78,
                "overall_assessment": "Strong proposal with minor gaps.",
                "strengths": ["Clear mission alignment"],
                "weaknesses": ["Budget justification thin"],
                "critical_gaps": [],
                "section_scores": {"project_narrative": {"score": 80, "feedback": "Good"}},
                "recommended_actions": ["Expand budget section"],
            })),
            patch("api.routes.ai.AuditLogger.log", new=AsyncMock()),
        ):
            response = client.post("/api/ai/review/app-001", headers=premium_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["review"]["overall_score"] == 78
            assert len(data["review"]["strengths"]) > 0

    def test_empty_sections_raises_400(self, client, premium_headers):
        mock_app = {
            "id": "app-002",
            "user_id": "user-123",
            "grant_id": "grant-001",
            "status": "draft",
            "sections": {},
        }
        with (
            patch("api.routes.ai.TokenBudgetManager.check_and_reserve", new=AsyncMock(return_value=2000)),
            patch("api.routes.ai.app_repo.get_by_id", new=AsyncMock(return_value=mock_app)),
        ):
            response = client.post("/api/ai/review/app-002", headers=premium_headers)
            assert response.status_code == 422


class TestAISummarize:

    def test_summarize_free_tier(self, client, free_headers):
        with (
            patch("api.routes.ai.TokenBudgetManager.check_and_reserve", new=AsyncMock(return_value=600)),
            patch("api.routes.ai.TokenBudgetManager.record_usage", new=AsyncMock()),
            patch("api.routes.ai.grant_repo.get_by_id", new=AsyncMock(return_value=MOCK_GRANT)),
            patch("api.routes.ai.ai_engine.summarize_grant", new=AsyncMock(
                return_value="This grant funds climate innovation. Nonprofits may apply. Deadline is December 2026."
            )),
        ):
            response = client.get("/api/ai/summarize/grant-001", headers=free_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["grant_id"] == "grant-001"
            assert "summary" in data

    def test_budget_exhausted_raises_429(self, client, free_headers):
        from packages.core.exceptions import RateLimitError
        with patch(
            "api.routes.ai.TokenBudgetManager.check_and_reserve",
            new=AsyncMock(side_effect=RateLimitError("Budget exceeded")),
        ):
            response = client.get("/api/ai/summarize/grant-001", headers=free_headers)
            assert response.status_code == 429


class TestAIBudget:

    def test_budget_status_authenticated(self, client, free_headers):
        with patch(
            "api.routes.ai.TokenBudgetManager.get_budget_status",
            new=AsyncMock(return_value={
                "tokens_used": 1200,
                "tokens_budget": 5000,
                "tokens_remaining": 3800,
                "tasks_run_today": 2,
                "percentage_used": 24.0,
                "resets": "midnight UTC",
            }),
        ):
            response = client.get("/api/ai/budget", headers=free_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["tokens_remaining"] == 3800
            assert data["percentage_used"] == 24.0
