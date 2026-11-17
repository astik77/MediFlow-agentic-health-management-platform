"""
Phase 7 API Integration Tests — Patient-Specific Hybrid RAG Search, Reindexing,
and AI Health Assistant Document Citation Grounding.
"""
from __future__ import annotations

import io
from pathlib import Path

import pymupdf
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mediflow.ai.providers.mock import MockAIProvider
from mediflow.ai.providers.router import ProviderRouter
from mediflow.modules.documents.models import DocumentEmbedding


def _make_pdf(lines: list[str]) -> bytes:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    y = 55
    for ln in lines:
        page.insert_text((45, y), ln, fontsize=11, fontname="helv")
        y += 20
    raw = doc.tobytes()
    doc.close()
    return raw


@pytest.mark.asyncio
async def test_rag_automatic_indexing_hybrid_search_reindex_and_assistant_citations(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RAG-INT-001: End-to-end document processing -> embeddings -> RAG search -> Assistant cite."""
    monkeypatch.setattr("mediflow.api.v1.routers.documents._storage_root", lambda: tmp_path)
    monkeypatch.setattr(
        "mediflow.ai.agents.health_assistant._assistant_router",
        lambda: ProviderRouter(override_providers={"ollama": MockAIProvider()}),
    )

    # Upload two distinct documents
    lab_pdf = _make_pdf(
        [
            "DIAGNOSTIC LABORATORY REPORT",
            "Report Date: 05/11/2026",
            "Fasting Blood Glucose   124   mg/dL   70 - 100",
            "HbA1c   6.9   %   4.0 - 5.6",
        ]
    )
    xray_pdf = _make_pdf(
        [
            "RADIOLOGY REPORT - CHEST X-RAY PA VIEW",
            "Exam Date: 20/10/2026",
            "Findings: Lung fields are clear. Costophrenic angles are sharp.",
            "Impression: No acute cardiopulmonary abnormality.",
        ]
    )

    r1 = await authenticated_client.post(
        "/api/v1/documents",
        files={"file": ("glucose.pdf", io.BytesIO(lab_pdf), "application/pdf")},
        data={"document_type": "lab_report", "title": "November Blood Sugar Panel"},
    )
    r2 = await authenticated_client.post(
        "/api/v1/documents",
        files={"file": ("chest_xray.pdf", io.BytesIO(xray_pdf), "application/pdf")},
        data={"document_type": "imaging", "title": "October Chest X-Ray"},
    )
    doc_lab_id = r1.json()["id"]
    doc_xray_id = r2.json()["id"]

    # Process both documents -> embeddings automatically created
    p1 = await authenticated_client.post(f"/api/v1/documents/{doc_lab_id}/process")
    p2 = await authenticated_client.post(f"/api/v1/documents/{doc_xray_id}/process")
    assert p1.status_code == 200
    assert p1.json()["metrics_json"]["embeddings_indexed"] >= 1
    assert p2.status_code == 200

    embs = (await db_session.execute(select(DocumentEmbedding))).scalars().all()
    assert len(embs) >= 2

    # Hybrid search for blood sugar / HbA1c ranks Lab Report #1
    s1 = await authenticated_client.post(
        "/api/v1/ai/rag/search",
        json={"query": "What is my blood sugar and HbA1c?", "top_k": 5},
    )
    assert s1.status_code == 200
    body1 = s1.json()
    assert body1["total_hits"] >= 1
    assert body1["hits"][0]["document_id"] == doc_lab_id
    assert body1["hits"][0]["page_start"] == 1

    # Hybrid search filtered by document_type=imaging returns X-Ray only
    s2 = await authenticated_client.post(
        "/api/v1/ai/rag/search",
        json={"query": "chest lung fields impression", "document_type": "imaging"},
    )
    assert s2.status_code == 200
    assert s2.json()["total_hits"] == 1
    assert s2.json()["hits"][0]["document_id"] == doc_xray_id

    # Reindex endpoint succeeds cleanly
    reidx = await authenticated_client.post("/api/v1/ai/rag/reindex")
    assert reidx.status_code == 200
    assert reidx.json()["documents_indexed"] == 2
    assert reidx.json()["chunks_indexed"] >= 2

    # AI Health Assistant automatically retrieves & cites exact document page
    conv_id = (await authenticated_client.post("/api/v1/conversations", json={})).json()["id"]
    turn = await authenticated_client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"content": "What did my chest x-ray impression say?"},
    )
    assert turn.status_code == 201
    cited_records = turn.json()["assistant_message"]["cited_records_json"] or []
    cited_labels = [c["label"] for c in cited_records]
    assert any("October Chest X-Ray (p. 1)" in lbl for lbl in cited_labels)
