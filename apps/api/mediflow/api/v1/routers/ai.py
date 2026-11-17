"""
AI Infrastructure API Router (v1).
Exposes local AI runtime/privacy status and schema-validated plain-language
document summarization strictly scoped to the authenticated patient.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from mediflow.ai.schemas import AIStatusResponse, DocumentSummaryApiResponse
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
