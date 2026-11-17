"""
Phase 8 Security Regression Tests:
- SEC-004: Unauthenticated requests to /api/v1/analytics/* return 401.
- SEC-001 / SEC-002: Strict cross-patient isolation across dashboard, trends, and summaries.
- SEC-013: AI output with mismatched patient_id is blocked, logged, and never persisted.
"""
from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mediflow.ai.models import AIInvocationLog
from mediflow.ai.providers.mock import MockAIProvider
from mediflow.ai.providers.router import ProviderRouter
from mediflow.core.config import Settings
from mediflow.core.dependencies import SESSION_COOKIE_NAME
from mediflow.modules.analytics import service as analytics_service_module
from mediflow.modules.auth.models import User
from mediflow.modules.health_records.models import HealthObservation, PatientCondition
from mediflow.modules.patients.models import PatientProfile


@pytest.mark.asyncio
async def test_phase8_unauthenticated_rejected_sec004(test_client: AsyncClient) -> None:
    assert (await test_client.get("/api/v1/analytics/dashboard")).status_code == 401
    assert (await test_client.get("/api/v1/analytics/trends")).status_code == 401
    assert (await test_client.get("/api/v1/analytics/summaries")).status_code == 401
    assert (
        await test_client.post("/api/v1/analytics/summaries", json={"window_days": 7})
    ).status_code == 401


@pytest.mark.asyncio
async def test_phase8_cross_patient_isolation_sec001_sec002(
    test_client: AsyncClient,
    db_session: AsyncSession,
    test_patient: tuple[User, PatientProfile, str],
    second_patient: tuple[User, PatientProfile, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, patient_a, token_a = test_patient
    _, _, token_b = second_patient

    # Seed Patient A with conditions, abnormal observations, and a persisted summary
    db_session.add(
        PatientCondition(
            id=uuid.uuid4(),
            patient_id=patient_a.id,
            name="Confidential Patient A Condition",
            status="active",
            review_status="confirmed",
        )
    )
    db_session.add(
        HealthObservation(
            id=uuid.uuid4(),
            patient_id=patient_a.id,
            observation_type="lab_result",
            display_name="Patient A Secret Biomarker",
            value_raw="240",
            unit_raw="mg/dL",
            value_numeric=240.0,
            abnormality_flag="high",
            observed_at=datetime.now(UTC),
            review_status="confirmed",
        )
    )
    await db_session.commit()

    mock_router = ProviderRouter(
        settings=Settings(ai_default_provider="ollama"),
        override_providers={"ollama": MockAIProvider()},
    )
    monkeypatch.setattr(analytics_service_module, "_default_router", lambda: mock_router)

    # Patient A generates a summary
    test_client.cookies.set(SESSION_COOKIE_NAME, token_a)
    sum_a = await test_client.post("/api/v1/analytics/summaries", json={"window_days": 7})
    assert sum_a.status_code == 201

    # Switch to Patient B — must see strictly ZERO of Patient A's data
    test_client.cookies.set(SESSION_COOKIE_NAME, token_b)

    dash_b = await test_client.get("/api/v1/analytics/dashboard")
    assert dash_b.status_code == 200
    body_b = dash_b.json()
    assert body_b["kpis"]["active_conditions_count"] == 0
    assert body_b["kpis"]["confirmed_observations_count"] == 0
    assert body_b["recent_abnormal_observations"] == []
    assert body_b["available_biomarkers"] == []
    assert body_b["latest_summary"] is None

    trends_b = await test_client.get("/api/v1/analytics/trends")
    assert trends_b.status_code == 200
    assert trends_b.json()["series_count"] == 0

    summaries_b = await test_client.get("/api/v1/analytics/summaries")
    assert summaries_b.status_code == 200
    assert summaries_b.json()["total"] == 0


@pytest.mark.asyncio
async def test_phase8_summary_sec013_patient_mismatch_never_persisted(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wrong_patient_id = str(uuid.uuid4())
    spoofed_payload = json.dumps(
        {
            "patient_id": wrong_patient_id,
            "headline": "SPOOFED OTHER PATIENT SUMMARY",
            "summary_text": "This spoofed text must never be persisted or returned.",
            "highlights": ["Leaked bullet"],
            "questions_for_doctor": ["Leaked question"],
            "informational_disclaimer": "Informational only.",
        }
    )
    rogue_provider = MockAIProvider(responder=lambda _req: spoofed_payload)
    rogue_router = ProviderRouter(
        settings=Settings(ai_default_provider="ollama"),
        override_providers={"ollama": rogue_provider},
    )
    monkeypatch.setattr(analytics_service_module, "_default_router", lambda: rogue_router)

    resp = await authenticated_client.post("/api/v1/analytics/summaries", json={"window_days": 7})
    assert resp.status_code == 201
    summary = resp.json()

    # Must fall back cleanly to deterministic summary — zero spoofed text persisted!
    assert summary["generation_mode"] == "deterministic_fallback"
    assert "SPOOFED" not in summary["headline"]
    assert "Leaked" not in summary["summary_text"]

    # Verify SEC-013 violation was recorded in AIInvocationLog
    logs = list((await db_session.execute(select(AIInvocationLog))).scalars().all())
    assert any(
        log.status == "schema_invalid" and log.error_code == "sec013_patient_id_mismatch"
        for log in logs
    )
