"""
API integration tests for Phase 8: Dashboard Analytics, Biomarker Trends & 7-Day Summaries.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from mediflow.ai.providers.base import ProviderUnavailableError
from mediflow.ai.providers.mock import MockAIProvider
from mediflow.ai.providers.router import ProviderRouter
from mediflow.core.config import Settings
from mediflow.modules.analytics import service as analytics_service_module
from mediflow.modules.auth.models import User
from mediflow.modules.conversations.models import Conversation, Message
from mediflow.modules.documents.models import Document
from mediflow.modules.health_records.models import (
    HealthObservation,
    PatientAllergy,
    PatientCondition,
    PatientSymptom,
)
from mediflow.modules.patients.models import PatientProfile


class _OfflineProvider(MockAIProvider):
    """Test stub simulating an offline local Ollama server."""

    async def generate(self, request):  # type: ignore[override]
        raise ProviderUnavailableError("Ollama is offline")


async def _seed_patient_analytics_data(
    db: AsyncSession, patient: PatientProfile, user: User
) -> Document:
    now = datetime.now(UTC)

    db.add(
        PatientCondition(
            id=uuid.uuid4(),
            patient_id=patient.id,
            name="Type 2 Diabetes",
            status="active",
            review_status="confirmed",
        )
    )
    db.add(
        PatientAllergy(
            id=uuid.uuid4(),
            patient_id=patient.id,
            allergen="Penicillin",
            category="medication",
            severity="severe",
            status="active",
            review_status="confirmed",
        )
    )
    db.add(
        PatientSymptom(
            id=uuid.uuid4(),
            patient_id=patient.id,
            name="Fatigue",
            severity="mild",
            status="ongoing",
            started_at=now - timedelta(days=2),
            review_status="confirmed",
        )
    )

    doc = Document(
        id=uuid.uuid4(),
        patient_id=patient.id,
        uploader_user_id=user.id,
        original_filename="lipid_panel.pdf",
        stored_filename=f"{uuid.uuid4()}.pdf",
        file_path=f"/private/{uuid.uuid4()}.pdf",
        mime_type="application/pdf",
        file_size_bytes=2048,
        sha256_hash="a" * 64,
        document_type="lab_report",
        title="Quarterly Lab Panel",
        uploaded_at=now - timedelta(days=1),
    )
    db.add(doc)
    await db.flush()

    # 3 confirmed HbA1c observations (two in last 30d, one 60d ago)
    db.add_all(
        [
            HealthObservation(
                id=uuid.uuid4(),
                patient_id=patient.id,
                observation_type="lab_result",
                display_name="HbA1c",
                value_raw="7.1",
                unit_raw="%",
                value_numeric=7.1,
                value_normalized=7.1,
                unit_normalized="%",
                reference_range_text="4.0 - 5.6 %",
                abnormality_flag="high",
                observed_at=now - timedelta(days=60),
                review_status="confirmed",
                source_document_id=doc.id,
            ),
            HealthObservation(
                id=uuid.uuid4(),
                patient_id=patient.id,
                observation_type="lab_result",
                display_name="HbA1c",
                value_raw="6.8",
                unit_raw="%",
                value_numeric=6.8,
                value_normalized=6.8,
                unit_normalized="%",
                reference_range_text="4.0 - 5.6 %",
                abnormality_flag="high",
                observed_at=now - timedelta(days=20),
                review_status="confirmed",
                source_document_id=doc.id,
            ),
            HealthObservation(
                id=uuid.uuid4(),
                patient_id=patient.id,
                observation_type="lab_result",
                display_name="HbA1c",
                value_raw="6.2",
                unit_raw="%",
                value_numeric=6.2,
                value_normalized=6.2,
                unit_normalized="%",
                reference_range_text="4.0 - 5.6 %",
                abnormality_flag="high",
                observed_at=now - timedelta(days=2),
                review_status="confirmed",
                source_document_id=doc.id,
            ),
            # 1 confirmed normal Hemoglobin
            HealthObservation(
                id=uuid.uuid4(),
                patient_id=patient.id,
                observation_type="lab_result",
                display_name="Hemoglobin",
                value_raw="14.2",
                unit_raw="g/dL",
                value_numeric=14.2,
                value_normalized=14.2,
                unit_normalized="g/dL",
                reference_range_text="12.0 - 16.0 g/dL",
                abnormality_flag="normal",
                observed_at=now - timedelta(days=2),
                review_status="confirmed",
                source_document_id=doc.id,
            ),
            # 2 unconfirmed candidate observations (must NEVER contaminate trends/confirmed KPIs)
            HealthObservation(
                id=uuid.uuid4(),
                patient_id=patient.id,
                observation_type="lab_result",
                display_name="HbA1c",
                value_raw="12.5",
                unit_raw="%",
                value_numeric=12.5,
                value_normalized=12.5,
                unit_normalized="%",
                abnormality_flag="critical",
                observed_at=now - timedelta(hours=2),
                review_status="candidate",
                source_document_id=doc.id,
            ),
            HealthObservation(
                id=uuid.uuid4(),
                patient_id=patient.id,
                observation_type="lab_result",
                display_name="LDL Cholesterol",
                value_raw="145",
                unit_raw="mg/dL",
                value_numeric=145.0,
                abnormality_flag="high",
                observed_at=now - timedelta(hours=2),
                review_status="candidate",
                source_document_id=doc.id,
            ),
        ]
    )

    # 1 pending AI-proposed symptom draft in conversations
    conv = Conversation(
        id=uuid.uuid4(),
        patient_id=patient.id,
        title="Fatigue discussion",
    )
    db.add(conv)
    await db.flush()
    db.add(
        Message(
            id=uuid.uuid4(),
            conversation_id=conv.id,
            patient_id=patient.id,
            role="assistant",
            content="Would you like me to save this symptom?",
            proposed_action_json={
                "proposal_type": "symptom",
                "status": "pending",
                "payload": {"name": "Dizziness", "severity": "mild"},
            },
        )
    )

    await db.commit()
    return doc


@pytest.mark.asyncio
async def test_dashboard_aggregates_kpis_abnormal_alerts_and_review_queue(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
    test_patient: tuple[User, PatientProfile, str],
) -> None:
    user, patient, _ = test_patient
    doc = await _seed_patient_analytics_data(db_session, patient, user)

    resp = await authenticated_client.get("/api/v1/analytics/dashboard")
    assert resp.status_code == 200
    data = resp.json()

    kpis = data["kpis"]
    assert kpis["active_conditions_count"] == 1
    assert kpis["active_allergies_count"] == 1
    assert kpis["ongoing_symptoms_count"] == 1
    assert kpis["confirmed_observations_count"] == 4
    assert kpis["abnormal_observations_count"] == 3
    assert kpis["documents_count"] == 1
    assert kpis["pending_candidates_count"] == 2
    assert kpis["pending_symptom_proposals_count"] == 1

    # Pending review queue links back to the source document
    assert len(data["pending_review_documents"]) == 1
    assert data["pending_review_documents"][0]["document_id"] == str(doc.id)
    assert data["pending_review_documents"][0]["pending_count"] == 2

    # Recent abnormal alerts strictly exclude candidate "12.5"
    abnormal_values = [a["value_raw"] for a in data["recent_abnormal_observations"]]
    assert "12.5" not in abnormal_values
    assert "6.2" in abnormal_values

    # Available biomarkers strictly exclude candidate-only "LDL Cholesterol"
    biomarker_keys = {b["biomarker_key"] for b in data["available_biomarkers"]}
    assert biomarker_keys == {"hba1c", "hemoglobin"}
    assert data["latest_summary"] is None


@pytest.mark.asyncio
async def test_trends_endpoint_chronological_and_filtered(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
    test_patient: tuple[User, PatientProfile, str],
) -> None:
    user, patient, _ = test_patient
    await _seed_patient_analytics_data(db_session, patient, user)

    # All-time HbA1c series
    resp_all = await authenticated_client.get(
        "/api/v1/analytics/trends", params={"window": "all", "biomarker": "hba1c"}
    )
    assert resp_all.status_code == 200
    payload = resp_all.json()
    assert payload["window"] == "all"
    assert payload["series_count"] == 1
    hba1c = payload["series"][0]
    assert hba1c["display_name"] == "HbA1c"
    assert [p["value"] for p in hba1c["points"]] == [7.1, 6.8, 6.2]
    assert hba1c["latest_value"] == 6.2
    assert hba1c["previous_value"] == 6.8
    assert hba1c["direction"] == "decreasing"
    assert hba1c["reference_low"] == 4.0
    assert hba1c["reference_high"] == 5.6
    assert hba1c["min_value"] == 6.2
    assert hba1c["max_value"] == 7.1

    # 30-day window excludes the 60-day-old 7.1 point
    resp_30d = await authenticated_client.get(
        "/api/v1/analytics/trends", params={"window": "30d", "biomarker": "HbA1c"}
    )
    assert resp_30d.status_code == 200
    hba1c_30d = resp_30d.json()["series"][0]
    assert [p["value"] for p in hba1c_30d["points"]] == [6.8, 6.2]


@pytest.mark.asyncio
async def test_generate_and_list_summaries_local_ai_and_timeline_event(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
    test_patient: tuple[User, PatientProfile, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user, patient, _ = test_patient
    await _seed_patient_analytics_data(db_session, patient, user)

    mock_router = ProviderRouter(
        settings=Settings(ai_default_provider="mock"),
        override_providers={"mock": MockAIProvider(), "ollama": MockAIProvider()},
    )
    monkeypatch.setattr(analytics_service_module, "_default_router", lambda: mock_router)

    create_resp = await authenticated_client.post(
        "/api/v1/analytics/summaries", json={"window_days": 7}
    )
    assert create_resp.status_code == 201
    summary = create_resp.json()
    assert summary["window_days"] == 7
    assert summary["generation_mode"] == "local_ai"
    assert summary["model_name"] == "mock-mediflow-v1"
    assert summary["prompt_version"] == "1.0.0"
    assert summary["metrics_snapshot"]["observations_in_window"] == 2
    assert summary["metrics_snapshot"]["abnormal_observations_in_window"] == 1
    assert summary["metrics_snapshot"]["pending_candidates_excluded"] == 2
    assert summary["metrics_snapshot"]["documents_uploaded_in_window"] == 1
    assert len(summary["notable_trends"]) >= 1

    # Persisted in GET /summaries
    list_resp = await authenticated_client.get("/api/v1/analytics/summaries")
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] == 1
    assert list_resp.json()["items"][0]["id"] == summary["id"]

    # Surfaced as latest_summary on /dashboard
    dash_resp = await authenticated_client.get("/api/v1/analytics/dashboard")
    assert dash_resp.status_code == 200
    assert dash_resp.json()["latest_summary"]["id"] == summary["id"]

    # Logged as a 'summary' event on Medical Timeline
    tl_resp = await authenticated_client.get("/api/v1/timeline", params={"category": "summary"})
    assert tl_resp.status_code == 200
    assert tl_resp.json()["total"] == 1
    assert tl_resp.json()["items"][0]["related_entity_id"] == summary["id"]


@pytest.mark.asyncio
async def test_generate_summary_graceful_deterministic_fallback_when_ai_offline(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
    test_patient: tuple[User, PatientProfile, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user, patient, _ = test_patient
    await _seed_patient_analytics_data(db_session, patient, user)

    offline_router = ProviderRouter(
        settings=Settings(ai_default_provider="ollama"),
        override_providers={"ollama": _OfflineProvider()},
    )
    monkeypatch.setattr(analytics_service_module, "_default_router", lambda: offline_router)

    resp = await authenticated_client.post("/api/v1/analytics/summaries", json={"window_days": 14})
    assert resp.status_code == 201
    summary = resp.json()
    assert summary["window_days"] == 14
    assert summary["generation_mode"] == "deterministic_fallback"
    assert summary["model_name"] is None
    assert "Out-of-Range" in summary["headline"]
    assert summary["metrics_snapshot"]["pending_candidates_excluded"] == 2
    assert len(summary["highlights"]) >= 3
    assert len(summary["questions_for_doctor"]) >= 1
    assert "informational" in summary["informational_disclaimer"].lower()
