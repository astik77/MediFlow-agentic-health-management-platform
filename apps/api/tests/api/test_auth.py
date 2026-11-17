"""
API integration tests for authentication endpoints (/api/v1/auth).
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from mediflow.core.dependencies import SESSION_COOKIE_NAME


@pytest.mark.asyncio
class TestRegistrationAPI:
    async def test_register_success(self, test_client: AsyncClient) -> None:
        payload = {
            "email": "newpatient@example.com",
            "password": "ValidPassword123!",
            "full_name": "Alice Springs",
        }
        response = await test_client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newpatient@example.com"
        assert "id" in data
        assert data["is_active"] is True

    async def test_register_duplicate_email_fails(self, test_client: AsyncClient) -> None:
        payload = {
            "email": "duplicate@example.com",
            "password": "ValidPassword123!",
            "full_name": "Bob Builder",
        }
        res1 = await test_client.post("/api/v1/auth/register", json=payload)
        assert res1.status_code == 201

        res2 = await test_client.post("/api/v1/auth/register", json=payload)
        assert res2.status_code == 400
        assert "already exists" in res2.json()["detail"].lower()

    async def test_register_short_password_fails_validation(
        self, test_client: AsyncClient
    ) -> None:
        payload = {
            "email": "shortpw@example.com",
            "password": "short",
            "full_name": "Charlie Chaplin",
        }
        response = await test_client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 422  # Pydantic validation error


@pytest.mark.asyncio
class TestLoginAPI:
    async def test_login_success_sets_http_only_cookie(
        self, test_client: AsyncClient
    ) -> None:
        # Register user first
        await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "loginuser@example.com",
                "password": "SecretPassword123!",
                "full_name": "Login Tester",
            },
        )

        # Login
        response = await test_client.post(
            "/api/v1/auth/login",
            json={
                "email": "loginuser@example.com",
                "password": "SecretPassword123!",
            },
        )
        assert response.status_code == 200
        assert SESSION_COOKIE_NAME in response.cookies
        cookie_value = response.cookies[SESSION_COOKIE_NAME]
        assert len(cookie_value) > 20

    async def test_login_wrong_password_returns_401(
        self, test_client: AsyncClient
    ) -> None:
        await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "wrongpw@example.com",
                "password": "SecretPassword123!",
                "full_name": "Wrong Tester",
            },
        )
        response = await test_client.post(
            "/api/v1/auth/login",
            json={
                "email": "wrongpw@example.com",
                "password": "IncorrectPassword999!",
            },
        )
        assert response.status_code == 401
        assert "invalid email or password" in response.json()["detail"].lower()

    async def test_login_nonexistent_user_returns_401(
        self, test_client: AsyncClient
    ) -> None:
        response = await test_client.post(
            "/api/v1/auth/login",
            json={
                "email": "doesnotexist@example.com",
                "password": "SomePassword123!",
            },
        )
        assert response.status_code == 401


@pytest.mark.asyncio
class TestAuthMeAndLogoutAPI:
    async def test_me_unauthenticated(self, test_client: AsyncClient) -> None:
        response = await test_client.get("/api/v1/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is False
        assert data["user"] is None

    async def test_me_authenticated(
        self, authenticated_client: AsyncClient
    ) -> None:
        response = await authenticated_client.get("/api/v1/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True
        assert data["user"] is not None
        assert data["user"]["email"] == "patient1@example.com"
        assert data["patient_id"] is not None

    async def test_logout_clears_cookie_and_invalidates_session(
        self, authenticated_client: AsyncClient
    ) -> None:
        # Check active session
        res_before = await authenticated_client.get("/api/v1/auth/me")
        assert res_before.json()["authenticated"] is True

        # Perform logout
        logout_res = await authenticated_client.post("/api/v1/auth/logout")
        assert logout_res.status_code == 200

        # Subsequent check should report unauthenticated
        res_after = await authenticated_client.get("/api/v1/auth/me")
        assert res_after.json()["authenticated"] is False


@pytest.mark.asyncio
class TestPasswordResetWorkflow:
    async def test_password_reset_full_flow(
        self, test_client: AsyncClient
    ) -> None:
        # Register user
        email = "resetflow@example.com"
        await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "OldPassword123!",
                "full_name": "Reset User",
            },
        )

        # Request password reset
        req_res = await test_client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": email},
        )
        assert req_res.status_code == 200
        token = req_res.json().get("dev_reset_token")
        assert token is not None

        # Confirm password reset with token
        confirm_res = await test_client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "token": token,
                "new_password": "BrandNewPassword456!",
            },
        )
        assert confirm_res.status_code == 200

        # Verify old password fails
        old_login = await test_client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "OldPassword123!"},
        )
        assert old_login.status_code == 401

        # Verify new password succeeds
        new_login = await test_client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "BrandNewPassword456!"},
        )
        assert new_login.status_code == 200
