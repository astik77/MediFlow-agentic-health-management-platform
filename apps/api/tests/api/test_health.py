"""
API tests for health check endpoints.
These tests use the ASGI test client and do NOT require a live database.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestRootHealthEndpoint:
    """Tests for GET /health"""

    async def test_root_health_returns_200(self, test_client: AsyncClient) -> None:
        response = await test_client.get("/health")
        assert response.status_code == 200

    async def test_root_health_returns_ok_status(self, test_client: AsyncClient) -> None:
        response = await test_client.get("/health")
        data = response.json()
        assert data["status"] == "ok"

    async def test_root_health_returns_service_name(self, test_client: AsyncClient) -> None:
        response = await test_client.get("/health")
        data = response.json()
        assert data["service"] == "mediflow-api"

    async def test_root_health_returns_version(self, test_client: AsyncClient) -> None:
        response = await test_client.get("/health")
        data = response.json()
        assert "version" in data
        assert data["version"] == "0.1.0"

    async def test_root_health_returns_environment(self, test_client: AsyncClient) -> None:
        response = await test_client.get("/health")
        data = response.json()
        assert "environment" in data

    async def test_root_health_returns_uptime(self, test_client: AsyncClient) -> None:
        response = await test_client.get("/health")
        data = response.json()
        assert "uptime_seconds" in data
        assert isinstance(data["uptime_seconds"], (int, float))
        assert data["uptime_seconds"] >= 0

    async def test_root_health_response_time_is_fast(self, test_client: AsyncClient) -> None:
        """Root health check must respond immediately — no DB calls."""
        import time
        start = time.time()
        response = await test_client.get("/health")
        elapsed = time.time() - start
        assert response.status_code == 200
        assert elapsed < 2.0  # Must complete within 2 seconds


@pytest.mark.asyncio
class TestApiV1HealthEndpoint:
    """Tests for GET /api/v1/health (may degrade if DB is unavailable)."""

    async def test_api_health_returns_200_or_200_degraded(
        self, test_client: AsyncClient
    ) -> None:
        """
        The /api/v1/health endpoint always returns 200.
        Status field will be 'ok' or 'degraded' depending on DB connectivity.
        """
        response = await test_client.get("/api/v1/health")
        assert response.status_code == 200

    async def test_api_health_response_has_components(self, test_client: AsyncClient) -> None:
        response = await test_client.get("/api/v1/health")
        data = response.json()
        assert "components" in data
        assert isinstance(data["components"], dict)

    async def test_api_health_response_has_database_component(
        self, test_client: AsyncClient
    ) -> None:
        response = await test_client.get("/api/v1/health")
        data = response.json()
        assert "database" in data["components"]
        db = data["components"]["database"]
        assert "status" in db

    async def test_api_health_response_has_service_name(
        self, test_client: AsyncClient
    ) -> None:
        response = await test_client.get("/api/v1/health")
        data = response.json()
        assert data["service"] == "mediflow-api"

    async def test_api_health_response_has_python_version(
        self, test_client: AsyncClient
    ) -> None:
        response = await test_client.get("/api/v1/health")
        data = response.json()
        assert "python" in data
