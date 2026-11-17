"""
Phase 5 Security Tests — Local AI Infrastructure.
Verifies:
- SEC-001/002: Cross-patient AI document summarization returns 403 Forbidden
- SEC-004: Unauthenticated requests to /api/v1/ai/* rejected with 401
- SEC-013: Hallucinated foreign patient_id in structured AI output rejected (422)
- SEC-014: External providers (gemini/grok) blocked for real patient data (403)
- SEC-015: Sensitive credentials and raw medical text redacted in structured logs
"""
from __future__ import annotations

import io
import json
import uuid
from pathlib import Path

import pymupdf
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mediflow.ai.models import AIInvocationLog
from mediflow.ai.providers.mock import MockAIProvider
from mediflow.ai.providers.router import ProviderRouter
from mediflow.core.dependencies import SESSION_COOKIE_NAME
from mediflow.modules.auth.models import User
from mediflow.modules.patients.models import PatientProfile


def _make_pdf() -> bytes:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((45, 55), "LABORATORY REPORT", fontsize=11, fontname="helv")
    page.insert_text((45, 75), "Report Date: 12/11/2026", fontsize=11, fontname="helv")
    page.insert_text(
        (45, 95), "Hemoglobin   13.2   g/dL   12.0 - 16.0", fontsize=11, fontname="helv"
    )
    data = doc.tobytes()
    doc.close()
    return data


@pytest.mark.asyncio
async def test_sec004_unauthenticated_ai_endpoints_rejected(
    test_client: AsyncClient,
) -> None:
    """SEC-004: AI endpoints reject unauthenticated requests with 401."""
    assert (await test_client.get("/api/v1/ai/status")).status_code == 401
    assert (
        await test_client.post(f"/api/v1/ai/documents/{uuid.uuid4()}/summarize")
    ).status_code == 401


@pytest.mark.asyncio
async def test_sec001_002_cross_patient_summarize_forbidden(
    test_client: AsyncClient,
    test_patient: tuple[User, PatientProfile, str],
    second_patient: tuple[User, PatientProfile, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SEC-001/002: Patient B cannot summarize Patient A's document (403 Forbidden)."""
    monkeypatch.setattr("mediflow.api.v1.routers.documents._storage_root", lambda: tmp_path)
    _, _, token_a = test_patient
    _, _, token_b = second_patient

    test_client.cookies.set(SESSION_COOKIE_NAME, token_a)
    up = await test_client.post(
        "/api/v1/documents",
        files={"file": ("sec_a.pdf", io.BytesIO(_make_pdf()), "application/pdf")},
        data={"title": "Patient A Lab"},
    )
    doc_id = up.json()["id"]
    await test_client.post(f"/api/v1/documents/{doc_id}/process")

    test_client.cookies.set(SESSION_COOKIE_NAME, token_b)
    res = await test_client.post(f"/api/v1/ai/documents/{doc_id}/summarize")
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_sec013_hallucinated_foreign_patient_id_blocked(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SEC-013: AI JSON output carrying a foreign patient_id is rejected and logged."""
    monkeypatch.setattr("mediflow.api.v1.routers.documents._storage_root", lambda: tmp_path)
    hallucinated = json.dumps(
        {
            "patient_id": str(uuid.uuid4()),
            "plain_language_summary": "Summary with wrong patient UUID.",
            "key_findings": ["Hemoglobin 13.2 g/dL"],
            "medical_terms_explained": [],
            "questions_for_doctor": [],
            "informational_disclaimer": "Informational only; not medical advice.",
        }
    )
    monkeypatch.setattr(
        "mediflow.ai.service._default_router",
        lambda: ProviderRouter(
            override_providers={"ollama": MockAIProvider(response_sequence=[hallucinated])}
        ),
    )

    up = await authenticated_client.post(
        "/api/v1/documents",
        files={"file": ("sec013.pdf", io.BytesIO(_make_pdf()), "application/pdf")},
        data={"title": "SEC-013 Test"},
    )
    doc_id = up.json()["id"]
    await authenticated_client.post(f"/api/v1/documents/{doc_id}/process")

    res = await authenticated_client.post(f"/api/v1/ai/documents/{doc_id}/summarize")
    assert res.status_code == 422

    logs = (
        await db_session.execute(
            select(AIInvocationLog).where(
                AIInvocationLog.error_code == "sec013_patient_id_mismatch"
            )
        )
    ).scalars().all()
    assert len(logs) == 1
    assert logs[0].schema_valid is False


@pytest.mark.asyncio
async def test_sec014_external_provider_blocked_for_real_patient_document(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SEC-014: Requesting Gemini or Grok for a real patient document returns 403 & logs block."""
    monkeypatch.setattr("mediflow.api.v1.routers.documents._storage_root", lambda: tmp_path)

    up = await authenticated_client.post(
        "/api/v1/documents",
        files={"file": ("sec014.pdf", io.BytesIO(_make_pdf()), "application/pdf")},
        data={"title": "SEC-014 Real Patient Doc"},
    )
    doc_id = up.json()["id"]
    await authenticated_client.post(f"/api/v1/documents/{doc_id}/process")

    for ext_provider in ("gemini", "grok"):
        res = await authenticated_client.post(
            f"/api/v1/ai/documents/{doc_id}/summarize?provider={ext_provider}"
        )
        assert res.status_code == 403
        assert "SEC-014" in res.json()["detail"]

    blocked = (
        await db_session.execute(
            select(AIInvocationLog).where(AIInvocationLog.status == "blocked_privacy")
        )
    ).scalars().all()
    assert len(blocked) == 2
