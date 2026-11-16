"""
Shared pytest fixtures for the MediFlow test suite.
"""
from __future__ import annotations

import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Point to test environment settings before importing the app
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("LOG_FORMAT", "console")

from mediflow.main import app

# Use an in-memory SQLite-compatible URL for unit tests when possible
# For integration tests that need pgvector, use the real DB
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://mediflow:mediflow_dev_password@localhost:5432/mediflow_test_db",
)


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest_asyncio.fixture(scope="function")
async def test_client() -> AsyncClient:
    """Async HTTP client wired to the FastAPI app (no real HTTP calls)."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        yield client
