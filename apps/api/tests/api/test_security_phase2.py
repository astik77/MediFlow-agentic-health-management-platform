"""
Security & Isolation Test Suite for Phase 2 (Medical History & Timeline).
Verifies:
- Strict cross-patient isolation across conditions, allergies, symptoms, observations,
  revision histories, overview, and timeline.
- SEC-018: Unauthorized historical record modification & immutable provenance preservation.
- SEC-004: Unauthenticated rejection on all Phase 2 endpoints.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from mediflow.core.dependencies import SESSION_COOKIE_NAME
from mediflow.modules.auth.models import User
from mediflow.modules.patients.models import PatientProfile


@pytest.mark.asyncio
class TestPhase2SecurityAndIsolation:
    async def test_sec_004_unauthenticated_rejected_on_health_records_and_timeline(
        self, test_client: AsyncClient
    ) -> None:
        endpoints = [
            ("GET", "/api/v1/health-records/overview"),
            ("GET", "/api/v1/health-records/conditions"),
            ("GET", "/api/v1/health-records/allergies"),
            ("GET", "/api/v1/health-records/symptoms"),
            ("GET", "/api/v1/health-records/observations"),
            ("GET", "/api/v1/timeline"),
        ]
        for method, path in endpoints:
            res = await test_client.request(method, path)
            assert res.status_code == 401, f"{method} {path} should require authentication"

    async def test_cross_patient_medical_history_and_sec_018_isolation(
        self,
        test_client: AsyncClient,
        test_patient: tuple[User, PatientProfile, str],
        second_patient: tuple[User, PatientProfile, str],
    ) -> None:
        _, _, token_p1 = test_patient
        _, _, token_p2 = second_patient

        # Patient 1 creates records across all medical history categories
        test_client.cookies.set(SESSION_COOKIE_NAME, token_p1)
        cond_id = (
            await test_client.post(
                "/api/v1/health-records/conditions",
                json={"name": "Patient 1 Private Condition"},
            )
        ).json()["id"]
        allergy_id = (
            await test_client.post(
                "/api/v1/health-records/allergies",
                json={"allergen": "Patient 1 Private Allergen"},
            )
        ).json()["id"]
        symptom_id = (
            await test_client.post(
                "/api/v1/health-records/symptoms",
                json={"name": "Patient 1 Private Symptom"},
            )
        ).json()["id"]
        obs_id = (
            await test_client.post(
                "/api/v1/health-records/observations",
                json={
                    "display_name": "Patient 1 Glucose",
                    "value_raw": "95",
                    "unit_raw": "mg/dL",
                },
            )
        ).json()["id"]

        # Switch to Patient 2
        test_client.cookies.set(SESSION_COOKIE_NAME, token_p2)

        # Patient 2 list endpoints must NOT return any of Patient 1's records
        assert (await test_client.get("/api/v1/health-records/conditions")).json() == []
        assert (await test_client.get("/api/v1/health-records/allergies")).json() == []
        assert (await test_client.get("/api/v1/health-records/symptoms")).json() == []
        assert (await test_client.get("/api/v1/health-records/observations")).json() == []
        assert (await test_client.get("/api/v1/timeline")).json()["total"] == 0
        overview_p2 = (await test_client.get("/api/v1/health-records/overview")).json()
        assert overview_p2["timeline_events_count"] == 0

        # Direct access, modification (SEC-018), archive, and history lookup -> 403 Forbidden
        targets = [
            ("conditions", cond_id, {"status": "resolved"}),
            ("allergies", allergy_id, {"severity": "mild"}),
            ("symptoms", symptom_id, {"status": "resolved"}),
            ("observations", obs_id, {"value_raw": "999"}),
        ]
        for resource, rec_id, patch_body in targets:
            assert (
                await test_client.get(f"/api/v1/health-records/{resource}/{rec_id}")
            ).status_code == 403
            assert (
                await test_client.patch(
                    f"/api/v1/health-records/{resource}/{rec_id}", json=patch_body
                )
            ).status_code == 403
            assert (
                await test_client.delete(f"/api/v1/health-records/{resource}/{rec_id}")
            ).status_code == 403
            assert (
                await test_client.get(f"/api/v1/health-records/{resource}/{rec_id}/history")
            ).status_code == 403

        # Switch back to Patient 1 and confirm records remain completely untouched
        test_client.cookies.set(SESSION_COOKIE_NAME, token_p1)
        obs_after = (
            await test_client.get(f"/api/v1/health-records/observations/{obs_id}")
        ).json()
        assert obs_after["value_raw"] == "95"
        hist_after = (
            await test_client.get(f"/api/v1/health-records/observations/{obs_id}/history")
        ).json()
        assert len(hist_after) == 1  # No unauthorized revision recorded
