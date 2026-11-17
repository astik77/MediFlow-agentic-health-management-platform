"""
Phase 7 Security Tests — Zero-Tolerance Cross-Patient RAG Isolation (SEC-003 / RAG-008),
Auth Enforcement (SEC-004), and Vector Deletion Sync on Archive (SEC-016).
"""
from __future__ import annotations

import io
import uuid
from pathlib import Path

import pymupdf
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mediflow.core.dependencies import SESSION_COOKIE_NAME
from mediflow.modules.auth.models import User
from mediflow.modules.documents.models import DocumentEmbedding
from mediflow.modules.patients.models import PatientProfile


def _make_pdf(lines: list[str]) -> bytes:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    y = 55
    for ln in lines:
        page.insert_text((45, y), ln, fontsize=11, fontname="helv")
        y += 20
    data = doc.tobytes()
    doc.close()
    return data


@pytest.mark.asyncio
async def test_sec004_unauthenticated_rag_endpoints_rejected(
    test_client: AsyncClient,
) -> None:
    """SEC-004: Unauthenticated RAG search and reindex return 401."""
    assert (
        await test_client.post("/api/v1/ai/rag/search", json={"query": "hemoglobin"})
    ).status_code == 401
    assert (await test_client.post("/api/v1/ai/rag/reindex")).status_code == 401


@pytest.mark.asyncio
async def test_sec003_rag008_zero_cross_patient_rag_leakage(
    test_client: AsyncClient,
    test_patient: tuple[User, PatientProfile, str],
    second_patient: tuple[User, PatientProfile, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    SEC-003 / RAG-008 (ZERO TOLERANCE):
    Patient A uploads highly distinctive confidential lab reports.
    Patient B runs 10 targeted queries for Patient A's exact unique tokens.
    Expected: ZERO foreign chunks returned (RAG-008 = 0.00).
    """
    monkeypatch.setattr("mediflow.api.v1.routers.documents._storage_root", lambda: tmp_path)
    _, _, token_a = test_patient
    _, _, token_b = second_patient

    # Patient A uploads & processes confidential medical report
    test_client.cookies.set(SESSION_COOKIE_NAME, token_a)
    pdf_a = _make_pdf(
        [
            "CONFIDENTIAL DIAGNOSTIC REPORT - PATIENT ALPHA",
            "UniqueMarkerX99: 42.7 mg/dL (Ref 10 - 30)",
            "Hemoglobin   10.8   g/dL   12.0 - 16.0",
            "RareDiagnosisZeta: Hyperferritinemia evaluation",
        ]
    )
    up_a = await test_client.post(
        "/api/v1/documents",
        files={"file": ("alpha_secret.pdf", io.BytesIO(pdf_a), "application/pdf")},
        data={"title": "Patient Alpha Secret Panel"},
    )
    doc_a_id = up_a.json()["id"]
    await test_client.post(f"/api/v1/documents/{doc_a_id}/process")

    # Sanity: Patient A CAN retrieve their own chunk
    res_a = await test_client.post(
        "/api/v1/ai/rag/search",
        json={"query": "UniqueMarkerX99 Hyperferritinemia"},
    )
    assert res_a.status_code == 200
    assert res_a.json()["total_hits"] == 1

    # Switch to Patient B and run adversarial cross-patient queries
    test_client.cookies.set(SESSION_COOKIE_NAME, token_b)
    adversarial_queries = [
        "UniqueMarkerX99",
        "RareDiagnosisZeta",
        "Hyperferritinemia",
        "Patient Alpha Secret Panel",
        "Hemoglobin 10.8",
        "CONFIDENTIAL DIAGNOSTIC REPORT",
        "42.7 mg/dL",
        "alpha_secret",
        "all patient blood results",
        "show everyone's hemoglobin",
    ]
    for q in adversarial_queries:
        res_b = await test_client.post("/api/v1/ai/rag/search", json={"query": q})
        assert res_b.status_code == 200
        assert res_b.json()["total_hits"] == 0, f"Cross-patient leak on query: {q}"
        assert res_b.json()["hits"] == []


@pytest.mark.asyncio
async def test_sec016_archived_document_embeddings_wiped_and_unretrievable(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    SEC-016 (Vector Sync): Archiving a processed document immediately deletes its
    document_embeddings rows and ensures subsequent RAG queries return 0 hits.
    """
    monkeypatch.setattr("mediflow.api.v1.routers.documents._storage_root", lambda: tmp_path)
    pdf = _make_pdf(
        [
            "LABORATORY REPORT",
            "UniqueDeletedToken777   88.5   U/L   10 - 50",
        ]
    )
    up = await authenticated_client.post(
        "/api/v1/documents",
        files={"file": ("wipe_vec.pdf", io.BytesIO(pdf), "application/pdf")},
        data={"title": "Vector Wipe Test"},
    )
    doc_id = up.json()["id"]
    await authenticated_client.post(f"/api/v1/documents/{doc_id}/process")

    # Confirm retrievable before archival
    before = await authenticated_client.post(
        "/api/v1/ai/rag/search", json={"query": "UniqueDeletedToken777"}
    )
    assert before.json()["total_hits"] == 1

    # Archive document
    arch = await authenticated_client.delete(f"/api/v1/documents/{doc_id}")
    assert arch.status_code == 200

    # Verify DB embeddings wiped
    remaining = (
        await db_session.execute(
            select(DocumentEmbedding).where(DocumentEmbedding.document_id == uuid.UUID(doc_id))
        )
    ).scalars().all()
    assert remaining == []

    # Verify RAG returns 0 hits
    after = await authenticated_client.post(
        "/api/v1/ai/rag/search", json={"query": "UniqueDeletedToken777"}
    )
    assert after.status_code == 200
    assert after.json()["total_hits"] == 0
