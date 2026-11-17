"""
Analytics, Biomarker Trends & 7-Day Health Summaries API Endpoints (v1 — Phase 8).
All endpoints derive identity strictly from the authenticated patient session (SEC-001/002/004).
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from mediflow.core.database import get_db
from mediflow.core.dependencies import get_current_patient
from mediflow.modules.analytics.schemas import (
    BiomarkerTrendsResponse,
    DashboardResponse,
    HealthSummaryCreateRequest,
    HealthSummaryListResponse,
    HealthSummaryResponse,
    TrendWindow,
)
from mediflow.modules.analytics.service import AnalyticsService
from mediflow.modules.patients.models import PatientProfile

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    current_patient: PatientProfile = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Return aggregated patient KPIs, recent confirmed abnormal observations,
    pending document candidate review queue, available biomarker trends,
    and latest persisted longitudinal summary.
    """
    return await AnalyticsService.get_dashboard(db=db, patient=current_patient)


@router.get("/trends", response_model=BiomarkerTrendsResponse)
async def get_biomarker_trends(
    window: TrendWindow = Query("all", description="Time window: 30d | 90d | 1y | all"),
    biomarker: str | None = Query(
        None, description="Optional case-insensitive biomarker display_name filter"
    ),
    current_patient: PatientProfile = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Return chronological, unit-safe longitudinal time-series and statistics for
    the authenticated patient's confirmed numeric biomarkers.
    Unconfirmed candidates and archived observations are strictly excluded.
    """
    return await AnalyticsService.get_trends(
        db=db,
        patient=current_patient,
        window=window,
        biomarker=biomarker,
    )


@router.post(
    "/summaries",
    response_model=HealthSummaryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_health_summary(
    payload: HealthSummaryCreateRequest | None = None,
    current_patient: PatientProfile = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Generate and persist a 7-day (or custom 7-90 day) longitudinal health summary
    for the authenticated patient and record a 'summary' event on their timeline.
    Uses local AI when available, falling back cleanly to deterministic statistics.
    """
    req = payload or HealthSummaryCreateRequest()
    return await AnalyticsService.generate_summary(
        db=db,
        patient=current_patient,
        window_days=req.window_days,
    )


@router.get("/summaries", response_model=HealthSummaryListResponse)
async def list_health_summaries(
    limit: int = Query(20, ge=1, le=100),
    current_patient: PatientProfile = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """List persisted historical longitudinal health summaries for the authenticated patient."""
    return await AnalyticsService.list_summaries(
        db=db,
        patient=current_patient,
        limit=limit,
    )
