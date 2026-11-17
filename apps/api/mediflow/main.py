"""
MediFlow FastAPI Application Factory
"""
from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from mediflow.api.v1.routers import ai as ai_router
from mediflow.api.v1.routers import auth as auth_router
from mediflow.api.v1.routers import documents as documents_router
from mediflow.api.v1.routers import health as health_router
from mediflow.api.v1.routers import health_records as health_records_router
from mediflow.api.v1.routers import patients as patients_router
from mediflow.api.v1.routers import timeline as timeline_router
from mediflow.core.config import get_settings
from mediflow.core.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown."""
    settings = get_settings()
    logger.info(
        "mediflow_starting",
        version=settings.app_version,
        environment=settings.app_env,
    )
    yield
    logger.info("mediflow_shutdown")


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="MediFlow API",
        description=(
            "AI-powered longitudinal personal healthcare management platform. "
            "Patient-facing API — MVP."
        ),
        version=settings.app_version,
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        openapi_url="/openapi.json" if settings.is_development else None,
        lifespan=lifespan,
    )

    # ---- Rate Limiter ----
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    # ---- CORS ----
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # ---- Global Exception Handler ----
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.error(
            "unhandled_exception",
            path=request.url.path,
            method=request.method,
            error=str(exc),
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "internal_server_error",
                "message": "An unexpected error occurred.",
            },
        )

    # ---- Routers ----
    app.include_router(health_router.router)
    app.include_router(auth_router.router, prefix=settings.api_prefix)
    app.include_router(patients_router.router, prefix=settings.api_prefix)
    app.include_router(health_records_router.router, prefix=settings.api_prefix)
    app.include_router(timeline_router.router, prefix=settings.api_prefix)
    app.include_router(documents_router.router, prefix=settings.api_prefix)
    app.include_router(ai_router.router, prefix=settings.api_prefix)

    return app


app = create_application()
