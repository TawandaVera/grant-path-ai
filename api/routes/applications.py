import logging
from typing import Optional
from fastapi import APIRouter, Depends, Path, Query, Body

from packages.core.exceptions import NotFoundError, ValidationError, AuthorizationError
from packages.core.security import InputSanitizer
from packages.database.repositories.application_repo import ApplicationRepository
from packages.database.audit import AuditLogger
from api.middleware.auth import require_auth, require_premium

logger = logging.getLogger("grantpath.routes.applications")
router = APIRouter(prefix="/api/applications", tags=["Applications"])

app_repo = ApplicationRepository()

VALID_STATUSES = {"draft", "in_progress", "submitted", "awarded", "rejected", "withdrawn"}


@router.get("/", summary="List user's applications")
async def list_applications(
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: dict = Depends(require_auth),
):
    """List all grant applications for the authenticated user."""
    if status and status not in VALID_STATUSES:
        raise ValidationError(f"Invalid status. Must be one of: {', '.join(VALID_STATUSES)}", field="status")

    offset = (page - 1) * page_size
    applications, total = await app_repo.list_by_user(
        user_id=user["sub"],
        status=status,
        limit=page_size,
        offset=offset,
    )

    return {
        "applications": applications,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": (total + page_size - 1) // page_size,
        },
    }


@router.post("/", summary="Start a new application", status_code=201)
async def create_application(
    grant_id: str = Body(..., embed=True),
    user: dict = Depends(require_auth),
    request=None,
):
    """Create a new grant application (draft)."""
    if not InputSanitizer.validate_id(grant_id):
        raise ValidationError("Invalid grant ID format", field="grant_id")

    application = await app_repo.create(
        user_id=user["sub"],
        grant_id=grant_id,
    )

    await AuditLogger.log(
        action="CREATE",
        resource_type="application",
        resource_id=application["id"],
        user_id=user["sub"],
        new_value={"grant_id": grant_id, "status": "draft"},
    )

    return application


@router.get("/{app_id}", summary="Get application details")
async def get_application(
    app_id: str = Path(...),
    user: dict = Depends(require_auth),
):
    """Retrieve a single application. Users can only access their own."""
    application = await app_repo.get_by_id(app_id)

    if not application:
        raise NotFoundError("Application", app_id)

    if application["user_id"] != user["sub"] and user.get("role") != "admin":
        raise AuthorizationError("You do not have access to this application")

    return application


@router.patch("/{app_id}/status", summary="Update application status")
async def update_status(
    app_id: str = Path(...),
    status: str = Body(..., embed=True),
    user: dict = Depends(require_auth),
):
    """Update the status of an application."""
    if status not in VALID_STATUSES:
        raise ValidationError(
            f"Invalid status '{status}'. Must be one of: {', '.join(VALID_STATUSES)}",
            field="status",
        )

    application = await app_repo.get_by_id(app_id)
    if not application:
        raise NotFoundError("Application", app_id)

    if application["user_id"] != user["sub"] and user.get("role") != "admin":
        raise AuthorizationError("You do not have access to this application")

    updated = await app_repo.update_status(
        app_id=app_id,
        status=status,
        user_id=user["sub"],
    )

    await AuditLogger.log(
        action="UPDATE",
        resource_type="application",
        resource_id=app_id,
        user_id=user["sub"],
        old_value={"status": application["status"]},
        new_value={"status": status},
    )

    return updated


@router.delete("/{app_id}", summary="Delete (withdraw) an application")
async def delete_application(
    app_id: str = Path(...),
    user: dict = Depends(require_auth),
):
    """Soft-delete an application by setting status to 'withdrawn'."""
    application = await app_repo.get_by_id(app_id)

    if not application:
        raise NotFoundError("Application", app_id)

    if application["user_id"] != user["sub"] and user.get("role") != "admin":
        raise AuthorizationError("You do not have access to this application")

    if application["status"] == "submitted":
        raise ValidationError(
            "Cannot delete a submitted application. Update status to 'withdrawn' first.",
            field="status",
        )

    await app_repo.update_status(app_id=app_id, status="withdrawn", user_id=user["sub"])

    await AuditLogger.log(
        action="DELETE",
        resource_type="application",
        resource_id=app_id,
        user_id=user["sub"],
        old_value={"status": application["status"]},
        new_value={"status": "withdrawn"},
    )

    return {"message": "Application withdrawn successfully", "app_id": app_id}
