"""
AI Subsystem Database Models (Phase 5).
Tracks anonymized AI invocation telemetry (latency, token usage, schema validity,
privacy policy enforcement) without ever storing raw prompts or raw medical transcripts.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from mediflow.core.database import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class AIInvocationLog(Base):
    """
    Observability & audit record for AI provider calls (AIR-001, SEC-013, SEC-014).
    Strictly metadata-only — raw prompts, responses, and clinical text are NEVER persisted here.
    """

    __tablename__ = "ai_invocation_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("patient_profiles.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_id: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(32), nullable=False)
    task_type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
    )  # succeeded | failed | blocked_privacy | schema_invalid | provider_unavailable
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    schema_valid: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )


Index("ix_ai_logs_patient_created", AIInvocationLog.patient_id, AIInvocationLog.created_at.desc())
