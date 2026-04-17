from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from packages.core.config import settings
from packages.database.connection import db_pool
from api.middleware.rate_limiter import RateLimitMiddleware
from api.middleware.error_handler import register_exception_handlers
from api.routes.health import router as health_router
# from api.routes.grants import router as grants_router  # add as built


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await db_pool.initialize()
    yield
    # Shutdown
    await db_pool.close()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.is_development else None,
    redoc_url=None,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting
app.add_middleware(RateLimitMiddleware)

# Exception handlers
register_exception_handlers(app)

# Routes
app.include_router(health_router)
