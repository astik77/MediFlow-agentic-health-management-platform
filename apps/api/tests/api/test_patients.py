"""
API integration tests for patient profile and onboarding (/api/v1/patients).
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestPatientProfileAPI:
    async def test_get_profile_authenticated(
        self, authenticated_client: AsyncClient
    ) -> None:
        response = await authenticated_client.get("/api/v1/patients/profile")
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Jane Doe"
        assert "id" in data
        assert "user_id" in data
        assert data["is_onboarded"] is False

    async def test_update_profile_demographics(
        self, authenticated_client: AsyncClient
    ) -> None:
        update_payload = {
            "full_name": "Jane Doe Updated",
            "blood_group": "O+",
            "height_cm": 168.5,
            "weight_kg": 62.0,
            "biological_sex": "female",
        }
        response = await authenticated_client.put(
            "/api/v1/patients/profile",
            json=update_payload,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Jane Doe Updated"
        assert data["blood_group"] == "O+"
        assert data["height_cm"] == 168.5
        assert data["weight_kg"] == 62.0
        assert data["biological_sex"] == "female"

    async def test_complete_onboarding_workflow(
        self, authenticated_client: AsyncClient
    ) -> None:
        onboarding_payload = {
            "date_of_birth": "1994-05-15",
            "biological_sex": "female",
            "blood_group": "A+",
            "height_cm": 165.0,
            "weight_kg": 58.0,
            "emergency_contact": {
                "name": "Mark Doe",
                "relationship": "Spouse",
                "phone_number": "+91-9876543210",
            },
            "existing_conditions": ["Hypertension", "Asthma"],
            "known_allergies": ["Penicillin", "Peanuts"],
        }
        response = await authenticated_client.post(
            "/api/v1/patients/onboarding",
            json=onboarding_payload,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_onboarded"] is True
        assert data["blood_group"] == "A+"
        assert data["emergency_contact"]["name"] == "Mark Doe"
        assert "Hypertension" in data["medical_baseline"]["existing_conditions"]
        assert "Penicillin" in data["medical_baseline"]["known_allergies"]
