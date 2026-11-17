"""
Phase 5 API Integration Tests — Local AI Infrastructure.
Covers GET /api/v1/ai/status, POST /api/v1/ai/documents/{id}/summarize,
invocation telemetry logging, and graceful 503 degradation when Ollama is offline.
"""
from __future__ import annotations

import io
import uuid
from pathlib import Path

import httpx
import pymupdf
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mediflow.ai.models import AIInvocationLog
from mediflow.ai.providers.mock import MockAIProvider
from mediflow.ai.providers.ollama import OllamaProvider
from mediflow.ai.providers.router import ProviderRouter


def _lab_pdf_bytes() -> bytes:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    lines = [
        "DIAGNOSTIC LABORATORY REPORT",
        "Report Date: 12/11/2026",
        "Hemoglobin   13.4   g/dL   12.0 - 16.0",
        "Fasting Blood Glucose   108   mg/dL   70 - 100",
    ]
    y = 55
    for ln in lines:
        page.insert_text((45, y), ln, fontsize=11, fontname="helv")
        y += 20
    raw = doc.tobytes()
    doc.close()
    return raw


@pytest.mark.asyncio
async def test_get_ai_status_returns_privacy_and_prompt_registry(
    authenticated_client: AsyncClient,
) -> None:
    """AI-001: /api/v1/ai/status reports local-first config, privacy lock, and prompts."""
    res = await authenticated_client.get("/api/v1/ai/status")
    assert res.status_code == 200
    body = res.json()
    assert body["default_provider"] == "ollama"
    assert body["default_model"] == "qwen2.5:1.5b"
    assert body["privacy_policy"]["local_first"] is True
    assert body["privacy_policy"]["allow_external_ai_for_real_data"] is False
    assert body["privacy_policy"]["external_ai_synthetic_only"] is True
    assert len(body["prompt_registry"]) >= 3
    # Ensure no API key fields are ever present in response
    assert "api_key" not in str(body).lower()


@pytest.mark.asyncio
async def test_summarize_document_success_and_logs_invocation(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AI-002: Summarizing a processed document succeeds, validates JSON, and logs metadata."""
    monkeypatch.setattr("mediflow.api.v1.routers.documents._storage_root", lambda: tmp_path)
    monkeypatch.setattr(
        "mediflow.ai.service._default_router",
        lambda: ProviderRouter(override_providers={"ollama": MockAIProvider()}),
    )

    up = await authenticated_client.post(
        "/api/v1/documents",
        files={"file": ("panel.pdf", io.BytesIO(_lab_pdf_bytes()), "application/pdf")},
        data={"title": "November Panel"},
    )
    doc_id = up.json()["id"]

    # Attempting to summarize before processing -> 409 Conflict
    early = await authenticated_client.post(f"/api/v1/ai/documents/{doc_id}/summarize")
    assert early.status_code == 409

    # Process document first
    proc = await authenticated_client.post(f"/api/v1/documents/{doc_id}/process")
    assert proc.status_code == 200

    # Generate AI plain-language summary
    summ = await authenticated_client.post(f"/api/v1/ai/documents/{doc_id}/summarize")
    assert summ.status_code == 200
    body = summ.json()
    assert body["document_id"] == doc_id
    assert body["prompt_id"] == "doc_summary"
    assert body["prompt_version"] == "1.0.0"
    assert "November Panel" in body["summary"]["plain_language_summary"]
    assert len(body["summary"]["informational_disclaimer"]) >= 10

    # Verify anonymized invocation log row persisted
    logs = (
        await db_session.execute(
            select(AIInvocationLog).where(AIInvocationLog.task_type == "document_summary")
        )
    ).scalars().all()
    assert len(logs) == 1
    assert logs[0].status == "succeeded"
    assert logs[0].schema_valid is True


@pytest.mark.asyncio
async def test_summarize_document_graceful_503_when_ollama_offline(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AI-003: When local Ollama is unreachable, returns 503 cleanly and logs telemetry."""
    monkeypatch.setattr("mediflow.api.v1.routers.documents._storage_root", lambda: tmp_path)

    def offline_handler(_req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    offline_ollama = OllamaProvider(transport=httpx.MockTransport(offline_handler))
    monkeypatch.setattr(
        "mediflow.ai.service._default_router",
        lambda: ProviderRouter(override_providers={"ollama": offline_ollama}),
    )

    up = await authenticated_client.post(
        "/api/v1/documents",
        files={"file": ("offline.pdf", io.BytesIO(_lab_pdf_bytes()), "application/pdf")},
        data={"title": "Offline Test"},
    )
    doc_id = up.json()["id"]
    await authenticated_client.post(f"/api/v1/documents/{doc_id}/process")

    res = await authenticated_client.post(f"/api/v1/ai/documents/{doc_id}/summarize")
    assert res.status_code == 503
    assert "unreachable" in res.json()["detail"].lower()

    logs = (
        await db_session.execute(
            select(AIInvocationLog).where(AIInvocationLog.status == "provider_unavailable")
        )
    ).scalars().all()
    assert len(logs) == 1
    assert logs[0].error_code == "provider_unavailable"


@pytest.mark.asyncio
async def test_summarize_nonexistent_document_returns_404(
    authenticated_client: AsyncClient,
) -> None:
    res = await authenticated_client.post(f"/api/v1/ai/documents/{uuid.uuid4()}/summarize")
    assert res.status_code == 404
