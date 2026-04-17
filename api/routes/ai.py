import logging
from typing import Optional
from fastapi import APIRouter, Depends, Path, Query, Body

from packages.core.exceptions import NotFoundError, ValidationError
from packages.core.security import InputSanitizer
from packages.engines.ai_engine import ai_engine
from packages.engines.token_budget import TokenBudgetManager
from packages.database.repositories.grant_repo import GrantRepository
from packages.database.repositories.user_repo import UserRepository
from packages.database.repositories.application_repo import ApplicationRepository
from packages.database.audit import AuditLogger
from api.middleware.auth import require_auth, require_premium

logger = logging.getLogger("grantpath.routes.ai")
router = APIRouter(prefix="/api/ai", tags=["AI"])

grant_repo = GrantRepository()
user_repo = UserRepository()
app_repo = ApplicationRepository()


# ─── Helper ───────────────────────────────────────────────────────────────────

async def _get_org_profile(user_id: str) -> dict:
    """Fetch user's org profile, raise if incomplete."""
    user = await user_repo.get_by_id(user_id)
    if not user or not user.get("org_profile"):
        raise ValidationError(
            "Please complete your organization profile before using AI features.",
            field="org_profile",
        )
    return user["org_profile"]


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("/match", summary="AI-powered grant matching")
async def ai_match_grants(
    limit: int = Query(10, ge=1, le=25),
    category: Optional[str] = Query(None),
    user: dict = Depends(require_premium),
):
    """
    Premium — Uses Gemini to semantically match and rank grants
    against the user's organization profile.
    Returns top matches with AI confidence scores and explanations.
    """
    user_id = user["sub"]
    role = user.get("role", "premium")

    # Check token budget
    await TokenBudgetManager.check_and_reserve(user_id, role, "match")

    # Get org profile
    org_profile = await _get_org_profile(user_id)

    # Fetch candidate grants (rule-based pre-filter first — saves tokens)
    candidates, _ = await grant_repo.search(
        category=category,
        limit=50,
        offset=0,
    )

    if not candidates:
        return {"matches": [], "count": 0, "note": "No active grants found matching your filters."}

    # Run AI matching
    matches = await ai_engine.match_grants(
        org_profile=org_profile,
        grants=candidates,
        top_n=limit,
    )

    # Record token usage
    await TokenBudgetManager.record_usage(user_id, "match", 500)

    # Audit
    await AuditLogger.log(
        action="AI_GENERATE",
        resource_type="grant_match",
        user_id=user_id,
        details={"task": "match", "candidates": len(candidates), "returned": len(matches)},
    )

    budget = await TokenBudgetManager.get_budget_status(user_id, role)

    return {
        "matches": matches,
        "count": len(matches),
        "engine": "gemini_semantic",
        "budget": budget,
    }


@router.post("/draft/{grant_id}", summary="AI draft a grant section")
async def ai_draft_section(
    grant_id: str = Path(..., min_length=3, max_length=50),
    section: str = Body(..., embed=True),
    existing_content: Optional[str] = Body(None, embed=True),
    word_limit: int = Body(500, ge=50, le=2000, embed=True),
    user: dict = Depends(require_premium),
):
    """
    Premium — Drafts or improves a single section of a grant application
    using the user's org profile and grant requirements.
    Sanitizes all user-provided content before passing to AI.
    """
    user_id = user["sub"]
    role = user.get("role", "premium")

    # Validate section name
    sanitized_section = InputSanitizer.sanitize_text(section, max_length=100)
    if not sanitized_section:
        raise ValidationError("Section name is required", field="section")

    # Check token budget
    await TokenBudgetManager.check_and_reserve(user_id, role, "draft")

    # Fetch grant
    grant = await grant_repo.get_by_id(grant_id)
    if not grant:
        raise NotFoundError("Grant", grant_id)

    # Get org profile
    org_profile = await _get_org_profile(user_id)

    # Sanitize existing content
    safe_existing = ""
    if existing_content:
        safe_existing, _ = InputSanitizer.sanitize_for_llm(
            existing_content, max_length=3000
        )

    # Generate draft
    result = await ai_engine.draft_section(
        grant=grant,
        section=sanitized_section,
        org_profile=org_profile,
        existing_content=safe_existing,
        word_limit=word_limit,
    )

    # Record usage
    actual_tokens = min(result["word_count"] * 2, 4000)  # Approx token count
    await TokenBudgetManager.record_usage(user_id, "draft", actual_tokens)

    await AuditLogger.log(
        action="AI_GENERATE",
        resource_type="draft_section",
        resource_id=grant_id,
        user_id=user_id,
        details={"section": sanitized_section, "word_count": result["word_count"]},
    )

    budget = await TokenBudgetManager.get_budget_status(user_id, role)

    return {**result, "grant_id": grant_id, "budget": budget}


@router.post("/review/{app_id}", summary="AI review a full application")
async def ai_review_application(
    app_id: str = Path(...),
    user: dict = Depends(require_premium),
):
    """
    Premium — Reviews a complete application draft with scored feedback,
    strengths/weaknesses, and recommended actions.
    """
    user_id = user["sub"]
    role = user.get("role", "premium")

    # Fetch application
    application = await app_repo.get_by_id(app_id)
    if not application:
        raise NotFoundError("Application", app_id)

    # Authorization check
    if application["user_id"] != user_id and role != "admin":
        from packages.core.exceptions import AuthorizationError
        raise AuthorizationError("You do not have access to this application")

    # Validate there's content to review
    sections = application.get("sections", {})
    if not sections:
        raise ValidationError(
            "Application has no draft content to review. "
            "Add sections using the /ai/draft endpoint first.",
            field="sections",
        )

    # Check budget
    await TokenBudgetManager.check_and_reserve(user_id, role, "review")

    # Fetch grant for context
    grant = await grant_repo.get_by_id(application["grant_id"])
    if not grant:
        raise NotFoundError("Grant", application["grant_id"])

    # Run AI review
    review = await ai_engine.review_application(
        grant=grant,
        sections=sections,
        scoring_criteria=grant.get("scoring_criteria"),
    )

    await TokenBudgetManager.record_usage(user_id, "review", 2000)

    await AuditLogger.log(
        action="AI_GENERATE",
        resource_type="application_review",
        resource_id=app_id,
        user_id=user_id,
        details={"overall_score": review.get("overall_score")},
    )

    budget = await TokenBudgetManager.get_budget_status(user_id, role)

    return {
        "app_id": app_id,
        "review": review,
        "budget": budget,
    }


@router.get("/summarize/{grant_id}", summary="AI plain-language grant summary")
async def ai_summarize_grant(
    grant_id: str = Path(..., min_length=3, max_length=50),
    user: dict = Depends(require_auth),
):
    """
    Authenticated (free tier) — Returns a plain-language 3-sentence summary
    of any grant. Lower token cost, available to all logged-in users.
    """
    user_id = user["sub"]
    role = user.get("role", "free")

    await TokenBudgetManager.check_and_reserve(user_id, role, "summarize")

    grant = await grant_repo.get_by_id(grant_id)
    if not grant:
        raise NotFoundError("Grant", grant_id)

    summary = await ai_engine.summarize_grant(grant)

    await TokenBudgetManager.record_usage(user_id, "summarize", 600)

    return {
        "grant_id": grant_id,
        "grant_title": grant["title"],
        "summary": summary,
    }


@router.get("/budget", summary="Get AI token budget status")
async def get_budget_status(user: dict = Depends(require_auth)):
    """
    Authenticated — Returns the user's current daily AI token usage and limits.
    """
    user_id = user["sub"]
    role = user.get("role", "free")
    budget = await TokenBudgetManager.get_budget_status(user_id, role)
    return {"user_id": user_id, "role": role, **budget}
