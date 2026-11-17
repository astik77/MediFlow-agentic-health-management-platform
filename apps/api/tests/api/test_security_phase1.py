"""
Security Test Suite for Phase 1
Implements and verifies:
- SEC-001 / SEC-002: Cross-Patient Data Isolation & Access Rejection
- SEC-004: Authentication Bypass Rejection
- SEC-005: Expired Session Rejection
- SEC-006: Session Revocation & Replay Prevention
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from mediflow.core.dependencies import SESSION_COOKIE_NAME
from mediflow.core.security import generate_session_token
from mediflow.modules.auth.models import Session, User
from mediflow.modules.patients.models import PatientProfile


@pytest.mark.asyncio
class TestSecurityPhase1:
    async def test_sec_004_authentication_bypass_rejected(
        self, test_client: AsyncClient
    ) -> None:
        """
        SEC-004: Unauthenticated requests to protected endpoints must be rejected
        with HTTP 401 Unauthorized.
        """
        # Profile endpoint
        res1 = await test_client.get("/api/v1/patients/profile")
        assert res1.status_code == 401

        # Profile update endpoint
        res2 = await test_client.put("/api/v1/patients/profile", json={"full_name": "Hacker"})
        assert res2.status_code == 401

        # Onboarding endpoint
        res3 = await test_client.post("/api/v1/patients/onboarding", json={})
        assert res3.status_code == 401

        # Session revoke-all endpoint
        res4 = await test_client.post("/api/v1/auth/sessions/revoke-all")
        assert res4.status_code == 401

    async def test_sec_005_expired_session_rejected(
        self,
        test_client: AsyncClient,
        db_session: AsyncSession,
        test_patient: tuple[User, PatientProfile, str],
    ) -> None:
        """
        SEC-005: Expired sessions must be rejected with HTTP 401 Unauthorized.
        """
        user, _, _ = test_patient

        # Create an explicitly expired session (expired 10 minutes ago)
        expired_token = generate_session_token()
        expired_at = datetime.now(UTC) - timedelta(minutes=10)

        expired_session = Session(
            user_id=user.id,
            session_token_hash=expired_token.token_hash,
            expires_at=expired_at,
            is_revoked=False,
        )
        db_session.add(expired_session)
        await db_session.commit()

        # Attempt to use the expired session token
        test_client.cookies.set(SESSION_COOKIE_NAME, expired_token.raw_token)
        response = await test_client.get("/api/v1/patients/profile")

        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()

    async def test_sec_006_session_revocation_and_replay_prevented(
        self,
        test_client: AsyncClient,
        test_patient: tuple[User, PatientProfile, str],
    ) -> None:
        """
        SEC-006: Once a session is revoked or the patient logs out,
        replaying the same session token must be rejected with HTTP 401 Unauthorized.
        """
        _, _, raw_token = test_patient
        test_client.cookies.set(SESSION_COOKIE_NAME, raw_token)

        # Confirm session is valid before logout
        res_valid = await test_client.get("/api/v1/patients/profile")
        assert res_valid.status_code == 200

        # Logout (revokes session)
        logout_res = await test_client.post("/api/v1/auth/logout")
        assert logout_res.status_code == 200

        # Attempt to replay the old session token via Bearer header or cookie
        test_client.cookies.set(SESSION_COOKIE_NAME, raw_token)
        replay_res = await test_client.get("/api/v1/patients/profile")
        assert replay_res.status_code == 401

        # Also test with Bearer header replay
        header_replay_res = await test_client.get(
            "/api/v1/patients/profile",
            headers={"Authorization": f"Bearer {raw_token}"},
        )
        assert header_replay_res.status_code == 401

    async def test_sec_001_002_cross_patient_data_access_strictly_forbidden(
        self,
        test_client: AsyncClient,
        test_patient: tuple[User, PatientProfile, str],
        second_patient: tuple[User, PatientProfile, str],
    ) -> None:
        """
        SEC-001 & SEC-002: A patient (Patient 1) must NEVER be permitted
        to view or access another patient's (Patient 2) record.
        The backend must reject with HTTP 403 Forbidden.
        """
        _, profile_1, token_1 = test_patient
        _, profile_2, _ = second_patient

        # Authenticate as Patient 1
        test_client.cookies.set(SESSION_COOKIE_NAME, token_1)

        # Patient 1 accessing Patient 1's profile by ID -> Allowed (HTTP 200)
        own_res = await test_client.get(f"/api/v1/patients/{profile_1.id}")
        assert own_res.status_code == 200
        assert own_res.json()["id"] == str(profile_1.id)

        # Patient 1 attempting to access Patient 2's profile by ID -> HTTP 403 Forbidden!
        cross_res = await test_client.get(f"/api/v1/patients/{profile_2.id}")
        assert cross_res.status_code == 403
        assert "access denied" in cross_res.json()["detail"].lower()

        # Patient 1 attempting to access a random non-existent patient ID -> HTTP 403 Forbidden
        # (ownership check precedes existence check to avoid ID enumeration)
        random_id = uuid.uuid4()
        random_res = await test_client.get(f"/api/v1/patients/{random_id}")
        assert random_res.status_code == 403
