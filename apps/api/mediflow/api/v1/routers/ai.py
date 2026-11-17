"""
AI Infrastructure API Router (v1).
Exposes local AI runtime/privacy status and schema-validated plain-language
document summarization strictly scoped to the authenticated patient.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from mediflow.ai.rag.service import RagService
from mediflow.ai.schemas import (
    AIStatusResponse,
    DocumentSummaryApiResponse,
    RagReindexResponse,
    RagSearchHitResponse,
    RagSearchRequest,
    RagSearchResponse,
)
from mediflow.ai.service import AIService
from mediflow.core.database import get_db
from mediflow.core.dependencies import get_current_patient
from mediflow.modules.patients.models import PatientProfile

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get(
    "/status",
    response_model=AIStatusResponse,
    summary="Inspect local AI provider availability, privacy firewall, and prompt versions",
)
async def get_ai_status(
    _current_patient: PatientProfile = Depends(get_current_patient),
) -> AIStatusResponse:
    """Return safe AI infrastructure status without ever exposing API keys."""
    return await AIService.get_status()


@router.post(
    "/documents/{document_id}/summarize",
    response_model=DocumentSummaryApiResponse,
    summary="Generate a plain-language informational summary of an extracted document",
)
async def summarize_document(
    document_id: uuid.UUID,
    provider: str | None = Query(
        default=None,
        description="Optional provider override (external providers blocked for real data)",
    ),
    db: AsyncSession = Depends(get_db),
    current_patient: PatientProfile = Depends(get_current_patient),
) -> DocumentSummaryApiResponse:
    """
    Generate a plain-language, strictly informational summary of a processed
    medical document owned by the authenticated patient.
    """
    return await AIService.summarize_document(
        db=db,
        document_id=document_id,
        patient=current_patient,
        provider_name=provider,
        is_synthetic_data=False,
    )


@router.post(
    "/rag/search",
    response_model=RagSearchResponse,
    summary="Hybrid semantic + lexical search across authenticated patient's documents",
)
async def rag_search_documents(
    payload: RagSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_patient: PatientProfile = Depends(get_current_patient),
) -> RagSearchResponse:
    """
    Strictly patient-scoped hybrid RAG search (SEC-003, RAG-008 = 0.00).
    Combines Okapi BM25 lexical scoring with cosine vector similarity via RRF.
    """
    hits, active_model = await RagService.search(
        db=db,
        patient=current_patient,
        query=payload.query,
        top_k=payload.top_k,
        document_type=payload.document_type,
    )
    return RagSearchResponse(
        query=payload.query,
        embedding_model=active_model,
        total_hits=len(hits),
        hits=[
            RagSearchHitResponse(
                chunk_id=h.chunk_id,
                document_id=h.document_id,
                document_title=h.document_title,
                document_type=h.document_type,
                document_date=h.document_date,
                page_start=h.page_start,
                page_end=h.page_end,
                section_heading=h.section_heading,
                snippet=h.snippet,
                score=h.score,
                lexical_score=h.lexical_score,
                vector_score=h.vector_score,
                match_type=h.match_type,
            )
            for h in hits
        ],
    )


@router.post(
    "/rag/reindex",
    response_model=RagReindexResponse,
    summary="Re-index RAG embeddings for all active processed documents of the patient",
)
async def rag_reindex_documents(
    db: AsyncSession = Depends(get_db),
    current_patient: PatientProfile = Depends(get_current_patient),
) -> RagReindexResponse:
    """Recompute local embeddings for all active chunks belonging to the authenticated patient."""
    result = await RagService.reindex_patient_documents(
        db=db,
        patient=current_patient,
    )
    return RagReindexResponse(**result)
