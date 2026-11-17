"""
Shared pytest fixtures for the MediFlow test suite.
Configures an isolated in-memory database and test client overrides.
"""
from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Point to test environment settings before importing the app
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("LOG_FORMAT", "console")

from mediflow.core.database import Base, get_db
from mediflow.core.dependencies import SESSION_COOKIE_NAME
from mediflow.main import app
from mediflow.modules.auth.models import User
from mediflow.modules.auth.service import AuthService
from mediflow.modules.patients.models import PatientProfile

# In-memory async SQLite for hermetic, ultra-fast test execution
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

TestAsyncSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provides a clean in-memory database session for each test."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestAsyncSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def test_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP test client with database dependency override."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def test_patient(
    db_session: AsyncSession,
) -> tuple[User, PatientProfile, str]:
    """
    Creates a test patient account with an active session.
    Returns (User, PatientProfile, raw_session_token).
    """
    user, profile = await AuthService.register_patient_user(
        db=db_session,
        email="patient1@example.com",
        password="SecurePassword123!",
        full_name="Jane Doe",
    )
    raw_token, _ = await AuthService.create_session(
        db=db_session,
        user_id=user.id,
    )
    return user, profile, raw_token


@pytest_asyncio.fixture(scope="function")
async def second_patient(
    db_session: AsyncSession,
) -> tuple[User, PatientProfile, str]:
    """
    Creates a second, distinct test patient account for cross-patient isolation tests.
    Returns (User, PatientProfile, raw_session_token).
    """
    user, profile = await AuthService.register_patient_user(
        db=db_session,
        email="patient2@example.com",
        password="DifferentPassword456!",
        full_name="John Smith",
    )
    raw_token, _ = await AuthService.create_session(
        db=db_session,
        user_id=user.id,
    )
    return user, profile, raw_token


@pytest_asyncio.fixture(scope="function")
async def authenticated_client(
    test_client: AsyncClient,
    test_patient: tuple[User, PatientProfile, str],
) -> AsyncClient:
    """Test client with patient 1 session cookie pre-configured."""
    _, _, token = test_patient
    test_client.cookies.set(SESSION_COOKIE_NAME, token)
    return test_client
