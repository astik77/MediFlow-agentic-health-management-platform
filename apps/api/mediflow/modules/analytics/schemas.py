"""
Pydantic Schemas for Phase 8: Dashboard Analytics, Biomarker Trends & 7-Day Summaries.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

TrendDirection = Literal["increasing", "decreasing", "stable", "insufficient_data"]
TrendWindow = Literal["30d", "90d", "1y", "all"]
SummaryGenerationMode = Literal["local_ai", "deterministic_fallback"]

DEFAULT_SUMMARY_DISCLAIMER = (
    "This longitudinal health summary is strictly informational and does not constitute "
    "medical advice, diagnosis, or treatment. Always consult a qualified healthcare "
    "professional regarding your health records."
)


class TrendDataPoint(BaseModel):
    """Single confirmed numeric observation plotted on a biomarker trend chart."""

    observation_id: uuid.UUID
    observed_at: datetime
    value: float
    unit: str | None = None
    value_raw: str
    unit_raw: str | None = None
    reference_range_text: str | None = None
    abnormality_flag: str | None = None
    source_document_id: uuid.UUID | None = None


class BiomarkerTrendSeries(BaseModel):
    """Unit-safe longitudinal time-series and deterministic stats for one biomarker."""

    biomarker_key: str
    display_name: str
    unit: str | None = None
    observation_type: str
    point_count: int
    latest_value: float
    latest_observed_at: datetime
    latest_abnormality_flag: str | None = None
    previous_value: float | None = None
    delta_absolute: float | None = None
    delta_percent: float | None = None
    direction: TrendDirection
    min_value: float
    max_value: float
    mean_value: float
    reference_low: float | None = None
    reference_high: float | None = None
    reference_range_text: str | None = None
    points: list[TrendDataPoint]


class BiomarkerTrendsResponse(BaseModel):
    """Response for GET /api/v1/analytics/trends."""

    window: TrendWindow
    biomarker_filter: str | None = None
    series_count: int
    series: list[BiomarkerTrendSeries]


class DashboardKPIs(BaseModel):
    """Top-level longitudinal health counters strictly scoped to the authenticated patient."""

    active_conditions_count: int
    active_allergies_count: int
    ongoing_symptoms_count: int
    confirmed_observations_count: int
    abnormal_observations_count: int
    documents_count: int
    pending_candidates_count: int
    pending_symptom_proposals_count: int


class AbnormalObservationAlert(BaseModel):
    """Confirmed out-of-range observation surfaced on the dashboard."""

    id: uuid.UUID
    display_name: str
    value_raw: str
    unit_raw: str | None = None
    reference_range_text: str | None = None
    abnormality_flag: str
    observed_at: datetime
    source_document_id: uuid.UUID | None = None


class PendingReviewItem(BaseModel):
    """Document with unconfirmed extracted candidate observations awaiting patient review."""

    document_id: uuid.UUID
    document_title: str
    document_type: str
    pending_count: int
    uploaded_at: datetime


class AvailableBiomarkerItem(BaseModel):
    """Lightweight biomarker metadata for dashboard selector pills."""

    biomarker_key: str
    display_name: str
    unit: str | None = None
    point_count: int
    latest_value: float
    latest_abnormality_flag: str | None = None
    direction: TrendDirection


class HealthSummaryMetricsSnapshot(BaseModel):
    """Exact deterministic counts for the summary's time window."""

    observations_in_window: int
    abnormal_observations_in_window: int
    symptoms_logged_in_window: int
    ongoing_symptoms_total: int
    documents_uploaded_in_window: int
    active_conditions_total: int
    pending_candidates_excluded: int


class NotableTrendItem(BaseModel):
    """Abnormal or moving biomarker highlighted inside a health summary."""

    biomarker: str
    latest_value: float
    unit: str | None = None
    direction: TrendDirection
    delta_percent: float | None = None
    abnormality_flag: str | None = None
    reference_range_text: str | None = None


class HealthSummaryAIOutput(BaseModel):
    """
    Schema-validated JSON payload returned by local AI for health_summary_7d@1.0.0.
    Includes patient_id for SEC-013 output identity verification.
    """

    patient_id: uuid.UUID
    headline: str = Field(..., min_length=3, max_length=255)
    summary_text: str = Field(..., min_length=10, max_length=4000)
    highlights: list[str] = Field(default_factory=list, max_length=10)
    questions_for_doctor: list[str] = Field(default_factory=list, max_length=8)
    informational_disclaimer: str = Field(default=DEFAULT_SUMMARY_DISCLAIMER, max_length=500)


class HealthSummaryCreateRequest(BaseModel):
    """Request body for POST /api/v1/analytics/summaries."""

    window_days: int = Field(default=7, ge=7, le=90)


class HealthSummaryResponse(BaseModel):
    """Persisted longitudinal health summary returned by API endpoints."""

    id: uuid.UUID
    window_days: int
    period_start: datetime
    period_end: datetime
    headline: str
    summary_text: str
    highlights: list[str]
    notable_trends: list[NotableTrendItem]
    questions_for_doctor: list[str]
    metrics_snapshot: HealthSummaryMetricsSnapshot
    generation_mode: SummaryGenerationMode
    model_name: str | None = None
    prompt_version: str | None = None
    informational_disclaimer: str = DEFAULT_SUMMARY_DISCLAIMER
    created_at: datetime


class HealthSummaryListResponse(BaseModel):
    """List of patient's persisted historical health summaries."""

    items: list[HealthSummaryResponse]
    total: int


class DashboardResponse(BaseModel):
    """Unified patient dashboard payload for GET /api/v1/analytics/dashboard."""

    kpis: DashboardKPIs
    recent_abnormal_observations: list[AbnormalObservationAlert]
    pending_review_documents: list[PendingReviewItem]
    available_biomarkers: list[AvailableBiomarkerItem]
    latest_summary: HealthSummaryResponse | None = None
    generated_at: datetime
