"""
Analytics & Longitudinal Health Summaries Database Models (Phase 8).
Persists patient-scoped 7-day (or custom window) longitudinal health summaries
with exact window boundaries, structured counts, notable trends, and audit metadata.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from mediflow.core.database import Base


def utc_now() -> datetime:
    """Return the current timezone-aware UTC datetime."""
    return datetime.now(UTC)


class HealthSummary(Base):
    """
    Patient-scoped persisted longitudinal health summary (default 7-day window).
    Strictly scoped to patient_id (SEC-001/SEC-002) with CASCADE deletion.
    """

    __tablename__ = "health_summaries"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("patient_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    window_days: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    headline: Mapped[str] = mapped_column(String(255), nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    highlights_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    notable_trends_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    questions_for_doctor_json: Mapped[list[str]] = mapped_column(
        JSON, default=list, nullable=False
    )
    metrics_snapshot_json: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )

    generation_mode: Mapped[str] = mapped_column(
        String(32), default="deterministic_fallback", nullable=False
    )  # local_ai | deterministic_fallback
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(32), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )


Index(
    "ix_health_summaries_patient_created",
    HealthSummary.patient_id,
    HealthSummary.created_at.desc(),
)
