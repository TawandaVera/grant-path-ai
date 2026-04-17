import time
import logging
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from packages.core.config import settings
from packages.database.connection import db_pool

logger = logging.getLogger("grantpath.health")

router = APIRouter(tags=["Health"])

_start_time = time.time()


@router.get("/health", summary="Full health check")
async def health_check():
    """
    Returns app info, uptime, and database connectivity status.
    Used by load balancers and monitoring tools.
    """
    db_healthy = await db_pool.health_check()
    uptime_seconds = int(time.time() - _start_time)

    status = "healthy" if db_healthy else "degraded"
    http_code = 200 if db_healthy else 503

    return JSONResponse(
        status_code=http_code,
        content={
            "status": status,
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENV,
            "uptime_seconds": uptime_seconds,
            "checks": {
                "database": "ok" if db_healthy else "unreachable",
            },
        },
    )


@router.get("/ready", summary="Readiness probe")
async def readiness():
    """
    Kubernetes readiness probe — returns 200 only when ready to serve traffic.
    """
    db_healthy = await db_pool.health_check()

    if not db_healthy:
        return JSONResponse(
            status_code=503,
            content={"ready": False, "reason": "database_unavailable"},
        )

    return {"ready": True}


@router.get("/live", summary="Liveness probe")
async def liveness():
    """
    Kubernetes liveness probe — returns 200 if the process is alive.
    Does NOT check external dependencies.
    """
    return {"alive": True, "uptime_seconds": int(time.time() - _start_time)}
