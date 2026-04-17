import logging
import uuid
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime

from packages.core.config import settings
from packages.core.exceptions import AuthenticationError, AuthorizationError

logger = logging.getLogger("grantpath.auth")

security = HTTPBearer(auto_error=False)


def _decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=["HS256"],
        )
        return payload
    except JWTError as e:
        raise AuthenticationError(f"Invalid token: {e}")


async def require_auth(request: Request) -> dict:
    """
    Dependency: Require a valid JWT. Injects user payload into request.state.
    Usage: user = Depends(require_auth)
    """
    credentials: HTTPAuthorizationCredentials = await security(request)

    if not credentials or not credentials.credentials:
        raise AuthenticationError("No authentication token provided")

    payload = _decode_token(credentials.credentials)

    # Validate expiry
    exp = payload.get("exp")
    if not exp or datetime.utcnow().timestamp() > exp:
        raise AuthenticationError("Token has expired")

    # Inject into request state for middleware access
    request.state.user_id = payload.get("sub")
    request.state.user_email = payload.get("email")
    request.state.user_role = payload.get("role", "free")

    return payload


async def require_premium(request: Request) -> dict:
    """Dependency: Require premium or admin role."""
    payload = await require_auth(request)
    role = payload.get("role", "free")

    if role not in ("premium", "admin"):
        raise AuthorizationError(
            "This feature requires a premium subscription",
            context={"required_role": "premium", "current_role": role},
        )
    return payload


async def require_admin(request: Request) -> dict:
    """Dependency: Require admin role."""
    payload = await require_auth(request)
    role = payload.get("role", "free")

    if role != "admin":
        raise AuthorizationError(
            "Admin access required",
            context={"required_role": "admin", "current_role": role},
        )
    return payload
