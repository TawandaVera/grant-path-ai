"""
Complete exception hierarchy.
Every error is typed, coded, and carries context for debugging.
"""

from typing import Optional
from datetime import datetime
import uuid


class GrantPathError(Exception):
    """Base exception for all Grant Path AI errors."""

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, detail: str = None, context: dict = None):
        self.message = message
        self.detail = detail or message
        self.context = context or {}
        self.error_id = str(uuid.uuid4())[:8]
        self.timestamp = datetime.utcnow().isoformat()
        super().__init__(self.message)

    def to_dict(self) -> dict:
        return {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "error_id": self.error_id,
                "timestamp": self.timestamp,
            }
        }


# ─── Client Errors (4xx) ─────────────

class ValidationError(GrantPathError):
    status_code = 422
    error_code = "VALIDATION_ERROR"

    def __init__(self, message: str, field: str = None, **kwargs):
        super().__init__(message, **kwargs)
        if field:
            self.context["field"] = field


class BadRequestError(GrantPathError):
    status_code = 400
    error_code = "BAD_REQUEST"


class AuthenticationError(GrantPathError):
    status_code = 401
    error_code = "AUTHENTICATION_REQUIRED"

    def __init__(self, message: str = "Authentication required", **kwargs):
        super().__init__(message, **kwargs)


class AuthorizationError(GrantPathError):
    status_code = 403
    error_code = "FORBIDDEN"

    def __init__(self, message: str = "Insufficient permissions", **kwargs):
        super().__init__(message, **kwargs)


class NotFoundError(GrantPathError):
    status_code = 404
    error_code = "NOT_FOUND"

    def __init__(self, resource: str, resource_id: str = None, **kwargs):
        msg = f"{resource} '{resource_id}' not found" if resource_id else f"{resource} not found"
        super().__init__(msg, **kwargs)
        self.context["resource"] = resource


class RateLimitError(GrantPathError):
    status_code = 429
    error_code = "RATE_LIMIT_EXCEEDED"

    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = 60,
                 limit: int = None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after
        self.limit = limit


class PayloadTooLargeError(GrantPathError):
    status_code = 413
    error_code = "PAYLOAD_TOO_LARGE"


# ─── AI/Token Errors ─────────────────

class TokenBudgetExhaustedError(GrantPathError):
    status_code = 429
    error_code = "TOKEN_BUDGET_EXHAUSTED"

    def __init__(self, budget_used: int = None, budget_limit: int = None,
                 resets_at: str = None, **kwargs):
        msg = "Daily AI token budget exhausted. Try standard quality or wait until tomorrow."
        super().__init__(msg, **kwargs)
        self.context.update({
            "budget_used": budget_used,
            "budget_limit": budget_limit,
            "resets_at": resets_at,
        })


class AIServiceError(GrantPathError):
    status_code = 502
    error_code = "AI_SERVICE_UNAVAILABLE"

    def __init__(self, provider: str, message: str = None, **kwargs):
        super().__init__(message or f"AI service '{provider}' unavailable", **kwargs)
        self.context["provider"] = provider


# ─── Server Errors (5xx) ─────────────

class DatabaseError(GrantPathError):
    status_code = 503
    error_code = "DATABASE_ERROR"


class ExternalServiceError(GrantPathError):
    status_code = 502
    error_code = "EXTERNAL_SERVICE_ERROR"
