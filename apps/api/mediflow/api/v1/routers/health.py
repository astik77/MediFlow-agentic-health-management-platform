"""
MediFlow Health Check API Router
Provides /health and /api/v1/health endpoints.
"""
from __future__ import annotations

import platform
import time
from typing import Any

from fastapi import APIRouter

from mediflow.core.config import get_settings
from mediflow.core.database import check_database_connection, check_pgvector_extension
from mediflow.core.logging import get_logger

router = APIRouter(tags=["health"])
logger = get_logger(__name__)

_startup_time = time.time()


@router.get("/health")
@router.get("/api/health")
@router.get("/healthz")
async def root_health_check() -> dict[str, Any]:
    """
    Root-level health check — always responds if the server is up.
    Does NOT check database connectivity (fast path for load balancers).
    """
    return {
        "status": "ok",
        "service": "mediflow-api",
        "version": get_settings().app_version,
        "environment": get_settings().app_env,
        "uptime_seconds": round(time.time() - _startup_time, 2),
    }


@router.get("/api/v1/health")
async def api_health_check() -> dict[str, Any]:
    """
    Full API health check including database and extensions.
    """
    settings = get_settings()
    result: dict[str, Any] = {
        "status": "ok",
        "service": "mediflow-api",
        "version": settings.app_version,
        "environment": settings.app_env,
        "uptime_seconds": round(time.time() - _startup_time, 2),
        "python": platform.python_version(),
        "components": {},
    }

    # Check database
    try:
        db_info = await check_database_connection()
        result["components"]["database"] = db_info
    except Exception as exc:
        logger.error("database_health_check_failed", error=str(exc))
        result["components"]["database"] = {"status": "unhealthy", "error": str(exc)}
        result["status"] = "degraded"

    # Check pgvector
    try:
        pgvector_info = await check_pgvector_extension()
        result["components"]["pgvector"] = pgvector_info
    except Exception as exc:
        logger.warning("pgvector_health_check_failed", error=str(exc))
        result["components"]["pgvector"] = {"status": "unknown", "error": str(exc)}

    # Check default AI provider (non-blocking, graceful degradation when offline)
    try:
        if settings.ai_default_provider == "gemini":
            from mediflow.ai.providers.external import GeminiProvider

            gemini = GeminiProvider(
                api_key=settings.gemini_api_key,
                default_model=settings.gemini_model,
                enabled=settings.gemini_enabled,
            )
            ai_health = await gemini.health_check(
                timeout_seconds=min(settings.ai_health_check_timeout_seconds, 0.35)
            )
        else:
            from mediflow.ai.providers.ollama import OllamaProvider

            ollama = OllamaProvider(
                base_url=settings.ollama_base_url,
                default_model=settings.ollama_default_model,
                embedding_model=settings.ollama_embedding_model,
            )
            ai_health = await ollama.health_check(
                timeout_seconds=min(settings.ai_health_check_timeout_seconds, 0.35)
            )
        result["components"]["ai_provider"] = {
            "provider": ai_health.provider,
            "is_local": ai_health.is_local,
            "status": "healthy" if ai_health.available else "offline",
            "default_model": ai_health.default_model,
            "installed_models_count": len(ai_health.installed_models),
        }
    except Exception as exc:
        result["components"]["ai_provider"] = {
            "provider": settings.ai_default_provider,
            "status": "unknown",
            "error": str(exc),
        }

    return result
