import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query, Path

from packages.core.exceptions import NotFoundError, ValidationError
from packages.core.security import InputSanitizer
from packages.database.repositories.grant_repo import GrantRepository
from packages.engines.search_engine import SearchEngine
from api.middleware.auth import require_auth, require_premium

logger = logging.getLogger("grantpath.routes.grants")
router = APIRouter(prefix="/api/grants", tags=["Grants"])

grant_repo = GrantRepository()
search_engine = SearchEngine()


@router.get("/", summary="Search and list grants")
async def list_grants(
    q: Optional[str] = Query(None, max_length=500, description="Search query"),
    category: Optional[str] = Query(None),
    funder_type: Optional[str] = Query(None),
    min_amount: Optional[int] = Query(None, ge=0),
    max_amount: Optional[int] = Query(None, ge=0),
    org_type: Optional[str] = Query(None),
    deadline_within_days: Optional[int] = Query(None, ge=1, le=365),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """
    Public endpoint — search and filter active grants.
    No authentication required.
    """
    # Sanitize search query
    sanitized_q = InputSanitizer.sanitize_search_query(q) if q else None

    offset = (page - 1) * page_size

    grants, total = await grant_repo.search(
        query=sanitized_q,
        category=category,
        funder_type=funder_type,
        min_amount=min_amount,
        max_amount=max_amount,
        org_type=org_type,
        deadline_within_days=deadline_within_days,
        limit=page_size,
        offset=offset,
    )

    return {
        "grants": grants,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": (total + page_size - 1) // page_size,
        },
    }


@router.get("/match", summary="AI-matched grants for user profile")
async def match_grants(
    limit: int = Query(10, ge=1, le=50),
    user: dict = Depends(require_auth),
):
    """
    Authenticated endpoint — returns grants matched to user's org profile
    using the Tier 0 rule-based search engine.
    """
    user_id = user["sub"]

    matched = await search_engine.match_for_user(
        user_id=user_id,
        limit=limit,
    )

    return {
        "matched_grants": matched,
        "count": len(matched),
        "engine": "tier0_rule_based",
    }


@router.get("/{grant_id}", summary="Get a single grant by ID")
async def get_grant(
    grant_id: str = Path(..., min_length=3, max_length=50),
):
    """
    Public endpoint — retrieve full details for a single grant.
    """
    if not InputSanitizer.validate_id(grant_id):
        raise ValidationError("Invalid grant ID format", field="grant_id")

    grant = await grant_repo.get_by_id(grant_id)

    if not grant:
        raise NotFoundError("Grant", grant_id)

    return grant


@router.get("/{grant_id}/eligibility", summary="Check eligibility for a grant")
async def check_eligibility(
    grant_id: str = Path(..., min_length=3, max_length=50),
    user: dict = Depends(require_auth),
):
    """
    Authenticated endpoint — run rule-based eligibility check for the
    authenticated user's organization against a specific grant.
    """
    grant = await grant_repo.get_by_id(grant_id)
    if not grant:
        raise NotFoundError("Grant", grant_id)

    result = await search_engine.check_eligibility(
        user_id=user["sub"],
        grant=grant,
    )

    return {
        "grant_id": grant_id,
        "eligible": result["eligible"],
        "score": result["score"],
        "reasons": result["reasons"],
        "missing_requirements": result.get("missing_requirements", []),
    }
