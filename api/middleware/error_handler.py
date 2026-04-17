import logging
import uuid
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from packages.core.exceptions import (
    GrantPathError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ValidationError,
    RateLimitError,
    DatabaseError,
)
from packages.core.config import settings

logger = logging.getLogger("grantpath.errors")


def _error_response(
    status_code: int,
    error_code: str,
    message: str,
    error_id: str,
    debug: dict = None,
) -> JSONResponse:
    body = {
        "error": {
            "code": error_code,
            "message": message,
            "error_id": error_id,
        }
    }
    if settings.is_development and debug:
        body["error"]["debug"] = debug

    return JSONResponse(status_code=status_code, content=body)


async def grantpath_exception_handler(request: Request, exc: GrantPathError) -> JSONResponse:
    error_id = exc.error_id

    # Structured log
    logger.error(
        f"[{error_id}] {exc.error_code}: {exc.message}",
        extra=exc.log_dict(),
        exc_info=exc.cause,
    )

    return _error_response(
        status_code=exc.status_code,
        error_code=exc.error_code,
        message=exc.message,
        error_id=error_id,
        debug=exc.context if settings.is_development else None,
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    error_id = str(uuid.uuid4())[:8]
    logger.warning(f"[{error_id}] HTTP {exc.status_code}: {exc.detail}")

    return _error_response(
        status_code=exc.status_code,
        error_code=f"HTTP_{exc.status_code}",
        message=str(exc.detail),
        error_id=error_id,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    error_id = str(uuid.uuid4())[:8]
    errors = exc.errors()

    # Flatten to human-readable
    messages = [
        f"{' → '.join(str(loc) for loc in e['loc'])}: {e['msg']}"
        for e in errors
    ]

    logger.info(f"[{error_id}] Validation error: {messages}")

    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "error_id": error_id,
                "fields": messages,
            }
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    error_id = str(uuid.uuid4())[:8]
    logger.critical(
        f"[{error_id}] Unhandled exception on {request.method} {request.url.path}",
        exc_info=exc,
    )

    return _error_response(
        status_code=500,
        error_code="INTERNAL_ERROR",
        message="An unexpected error occurred. Please try again later.",
        error_id=error_id,
    )


def register_exception_handlers(app):
    """Register all exception handlers on the FastAPI app."""
    app.add_exception_handler(GrantPathError, grantpath_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
