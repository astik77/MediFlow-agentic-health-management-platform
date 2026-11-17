"""
API & Database Integration Tests for Medical History Endpoints (/api/v1/health-records).
Covers Conditions, Allergies, Symptoms, Observations, Provenance, Revisions, and Overview.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestConditionsAPI:
    async def test_create_list_correct_archive_condition_with_history(
        self, authenticated_client: AsyncClient
    ) -> None:
        # Create
        create_res = await authenticated_client.post(
            "/api/v1/health-records/conditions",
            json={
                "name": "Essential Hypertension",
                "status": "active",
                "severity": "moderate",
                "onset_date": "2024-03-10",
                "notes": "Diagnosed during annual physical",
            },
        )
        assert create_res.status_code == 201
        created = create_res.json()
        cid = created["id"]
        assert created["name"] == "Essential Hypertension"
        assert created["source_type"] == "patient_reported"
        assert created["review_status"] == "confirmed"
        assert created["onset_date"] == "2024-03-10"

        # List
        list_res = await authenticated_client.get("/api/v1/health-records/conditions")
        assert list_res.status_code == 200
        assert len(list_res.json()) == 1

        # Correct (non-destructive)
        patch_res = await authenticated_client.patch(
            f"/api/v1/health-records/conditions/{cid}",
            json={
                "status": "remission",
                "severity": "mild",
                "correction_reason": "Blood pressure stabilized after lifestyle changes",
            },
        )
        assert patch_res.status_code == 200
        updated = patch_res.json()
        assert updated["status"] == "remission"
        assert updated["severity"] == "mild"

        # Verify revision history preserves original fact + correction
        hist_res = await authenticated_client.get(
            f"/api/v1/health-records/conditions/{cid}/history"
        )
        assert hist_res.status_code == 200
        history = hist_res.json()
        assert len(history) == 2
        assert history[0]["revision_number"] == 1
        assert history[0]["action"] == "created"
        assert history[0]["previous_data"] is None
        assert history[0]["new_data"]["status"] == "active"

        assert history[1]["revision_number"] == 2
        assert history[1]["action"] == "corrected"
        assert history[1]["previous_data"]["status"] == "active"
        assert history[1]["new_data"]["status"] == "remission"
        assert "stabilized" in history[1]["reason"]

        # Archive (soft delete)
        del_res = await authenticated_client.delete(
            f"/api/v1/health-records/conditions/{cid}",
            params={"reason": "Entered in error"},
        )
        assert del_res.status_code == 200
        assert del_res.json()["is_archived"] is True

        # Active list excludes archived item by default
        active_list = await authenticated_client.get("/api/v1/health-records/conditions")
        assert len(active_list.json()) == 0

        # include_archived=true returns it
        all_list = await authenticated_client.get(
            "/api/v1/health-records/conditions", params={"include_archived": "true"}
        )
        assert len(all_list.json()) == 1

        # Revision log now has 3 entries including archival
        hist_after = await authenticated_client.get(
            f"/api/v1/health-records/conditions/{cid}/history"
        )
        assert len(hist_after.json()) == 3
        assert hist_after.json()[2]["action"] == "archived"


@pytest.mark.asyncio
class TestAllergiesAPI:
    async def test_allergy_lifecycle(self, authenticated_client: AsyncClient) -> None:
        create_res = await authenticated_client.post(
            "/api/v1/health-records/allergies",
            json={
                "allergen": "Penicillin",
                "category": "medication",
                "reaction": "Hives and swelling",
                "severity": "severe",
                "status": "active",
            },
        )
        assert create_res.status_code == 201
        aid = create_res.json()["id"]

        patch_res = await authenticated_client.patch(
            f"/api/v1/health-records/allergies/{aid}",
            json={
                "severity": "life_threatening",
                "correction_reason": "Clarified reaction severity with allergist",
            },
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["severity"] == "life_threatening"

        hist_res = await authenticated_client.get(
            f"/api/v1/health-records/allergies/{aid}/history"
        )
        assert len(hist_res.json()) == 2
        assert hist_res.json()[1]["previous_data"]["severity"] == "severe"
        assert hist_res.json()[1]["new_data"]["severity"] == "life_threatening"


@pytest.mark.asyncio
class TestSymptomsAPI:
    async def test_symptom_lifecycle(self, authenticated_client: AsyncClient) -> None:
        create_res = await authenticated_client.post(
            "/api/v1/health-records/symptoms",
            json={
                "name": "Migraine Headache",
                "severity": "severe",
                "frequency": "Twice weekly",
                "body_location": "Right temple",
                "status": "ongoing",
                "started_at": "2026-11-10T08:30:00Z",
            },
        )
        assert create_res.status_code == 201
        created = create_res.json()
        sid = created["id"]
        assert created["started_at"].startswith("2026-11-10T08:30:00")

        patch_res = await authenticated_client.patch(
            f"/api/v1/health-records/symptoms/{sid}",
            json={
                "status": "resolved",
                "ended_at": "2026-11-14T18:00:00Z",
                "correction_reason": "Symptoms subsided",
            },
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["status"] == "resolved"


@pytest.mark.asyncio
class TestObservationsAPI:
    async def test_numeric_and_non_numeric_observations_preserve_units_and_ranges(
        self, authenticated_client: AsyncClient
    ) -> None:
        # Numeric lab result
        lab_res = await authenticated_client.post(
            "/api/v1/health-records/observations",
            json={
                "observation_type": "lab_result",
                "display_name": "Hemoglobin",
                "value_raw": "13.5",
                "unit_raw": "g/dL",
                "reference_range_text": "12.0-16.0 g/dL",
                "abnormality_flag": "normal",
                "observed_at": "2026-10-15T09:00:00Z",
            },
        )
        assert lab_res.status_code == 201
        lab = lab_res.json()
        assert lab["value_raw"] == "13.5"
        assert lab["value_numeric"] == 13.5
        assert lab["unit_raw"] == "g/dL"
        assert lab["reference_range_text"] == "12.0-16.0 g/dL"
        assert lab["observed_at"].startswith("2026-10-15T09:00:00")

        # Non-numeric observation (Blood Pressure / Qualitative)
        qual_res = await authenticated_client.post(
            "/api/v1/health-records/observations",
            json={
                "observation_type": "vital_sign",
                "display_name": "Blood Pressure",
                "value_raw": "122/78",
                "unit_raw": "mmHg",
                "abnormality_flag": "normal",
            },
        )
        assert qual_res.status_code == 201
        qual = qual_res.json()
        assert qual["value_raw"] == "122/78"
        assert qual["value_numeric"] is None
        assert qual["unit_raw"] == "mmHg"

        # Filter by observation_type and display_name
        filtered = await authenticated_client.get(
            "/api/v1/health-records/observations",
            params={"observation_type": "lab_result", "display_name": "Hemo"},
        )
        assert filtered.status_code == 200
        items = filtered.json()
        assert len(items) == 1
        assert items[0]["display_name"] == "Hemoglobin"

        # Correct value and verify numeric updates + history preserved
        patch_res = await authenticated_client.patch(
            f"/api/v1/health-records/observations/{lab['id']}",
            json={
                "value_raw": "13.8",
                "correction_reason": "Corrected typo from printed lab sheet",
            },
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["value_raw"] == "13.8"
        assert patch_res.json()["value_numeric"] == 13.8

        hist = (
            await authenticated_client.get(
                f"/api/v1/health-records/observations/{lab['id']}/history"
            )
        ).json()
        assert len(hist) == 2
        assert hist[1]["previous_data"]["value_raw"] == "13.5"
        assert hist[1]["new_data"]["value_raw"] == "13.8"


@pytest.mark.asyncio
class TestHealthOverviewAPI:
    async def test_overview_counts_and_recent_events(
        self, authenticated_client: AsyncClient
    ) -> None:
        await authenticated_client.post(
            "/api/v1/health-records/conditions",
            json={"name": "Asthma", "status": "active"},
        )
        await authenticated_client.post(
            "/api/v1/health-records/allergies",
            json={"allergen": "Dust Mites", "category": "environmental"},
        )
        await authenticated_client.post(
            "/api/v1/health-records/symptoms",
            json={"name": "Shortness of breath", "status": "ongoing"},
        )
        await authenticated_client.post(
            "/api/v1/health-records/observations",
            json={
                "observation_type": "vital_sign",
                "display_name": "SpO2",
                "value_raw": "98",
                "unit_raw": "%",
            },
        )

        res = await authenticated_client.get("/api/v1/health-records/overview")
        assert res.status_code == 200
        data = res.json()
        assert data["conditions_count"] == 1
        assert data["active_conditions_count"] == 1
        assert data["allergies_count"] == 1
        assert data["symptoms_count"] == 1
        assert data["ongoing_symptoms_count"] == 1
        assert data["observations_count"] == 1
        assert data["timeline_events_count"] == 4
        assert len(data["recent_events"]) == 4
