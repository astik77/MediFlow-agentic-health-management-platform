"""
Medical History & Timeline Database Models
Defines PatientCondition, PatientAllergy, PatientSymptom, HealthObservation,
HealthEvent, and RecordRevision with full provenance and correction history.
"""
from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from mediflow.core.database import Base


def utc_now() -> datetime:
    """Return the current UTC datetime."""
    return datetime.now(UTC)


class PatientCondition(Base):
    """Patient medical condition / diagnosis record with provenance."""

    __tablename__ = "patient_conditions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("patient_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default="active", nullable=False
    )  # active, resolved, remission, inactive
    severity: Mapped[str | None] = mapped_column(String(32), nullable=True)
    onset_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    resolved_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Provenance & governance
    source_type: Mapped[str] = mapped_column(
        String(32), default="patient_reported", nullable=False
    )  # patient_reported, document_extracted, patient_confirmed, ai_proposed
    review_status: Mapped[str] = mapped_column(
        String(32), default="confirmed", nullable=False
    )  # confirmed, candidate, rejected, uncertain
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class PatientAllergy(Base):
    """Patient allergy and adverse reaction record."""

    __tablename__ = "patient_allergies"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("patient_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    allergen: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(
        String(32), default="other", nullable=False
    )  # medication, food, environmental, other
    reaction: Mapped[str | None] = mapped_column(String(500), nullable=True)
    severity: Mapped[str] = mapped_column(
        String(32), default="moderate", nullable=False
    )  # mild, moderate, severe, life_threatening
    status: Mapped[str] = mapped_column(
        String(32), default="active", nullable=False
    )  # active, inactive, resolved
    onset_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Provenance & governance
    source_type: Mapped[str] = mapped_column(
        String(32), default="patient_reported", nullable=False
    )
    review_status: Mapped[str] = mapped_column(
        String(32), default="confirmed", nullable=False
    )
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class PatientSymptom(Base):
    """Patient-reported or extracted symptom record."""

    __tablename__ = "patient_symptoms"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("patient_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[str] = mapped_column(
        String(32), default="moderate", nullable=False
    )  # mild, moderate, severe
    frequency: Mapped[str | None] = mapped_column(String(100), nullable=True)
    body_location: Mapped[str | None] = mapped_column(String(150), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), default="ongoing", nullable=False
    )  # ongoing, resolved, intermittent
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Provenance & governance
    source_type: Mapped[str] = mapped_column(
        String(32), default="patient_reported", nullable=False
    )
    review_status: Mapped[str] = mapped_column(
        String(32), default="confirmed", nullable=False
    )
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class HealthObservation(Base):
    """
    Structured medical observation (lab result, vital sign, clinical measurement).
    Preserves original raw value & unit, optional normalized numeric value & unit,
    reference range, source page, and full extraction provenance.
    Supports both numeric and non-numeric values (e.g., 'Positive', '120/80').
    """

    __tablename__ = "health_observations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("patient_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    observation_type: Mapped[str] = mapped_column(
        String(40), default="vital_sign", nullable=False
    )  # lab_result, vital_sign, measurement, clinical_note
    display_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Values & units (strictly preserved together)
    value_raw: Mapped[str] = mapped_column(String(255), nullable=False)
    unit_raw: Mapped[str | None] = mapped_column(String(64), nullable=True)
    value_numeric: Mapped[float | None] = mapped_column(Float, nullable=True)
    value_normalized: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit_normalized: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reference_range_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    abnormality_flag: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )  # normal, low, high, critical, unknown

    # Clinical occurrence timestamp (distinct from created_at)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Provenance & extraction metadata
    source_type: Mapped[str] = mapped_column(
        String(32), default="patient_reported", nullable=False
    )
    review_status: Mapped[str] = mapped_column(
        String(32), default="confirmed", nullable=False, index=True
    )
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extraction_method: Mapped[str | None] = mapped_column(String(64), nullable=True)
    extraction_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    provenance_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class HealthEvent(Base):
    """
    Unified chronological health event backing the Medical Timeline.
    Preserves event_occurred_at separately from created_at.
    """

    __tablename__ = "health_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("patient_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_category: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
    )  # symptom, condition, allergy, observation, document, correction, summary, general
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )
    source_type: Mapped[str] = mapped_column(
        String(32), default="patient_reported", nullable=False
    )
    review_status: Mapped[str] = mapped_column(
        String(32), default="confirmed", nullable=False
    )
    related_entity_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    related_entity_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True, index=True
    )
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class RecordRevision(Base):
    """
    Immutable audit & correction history log for medical records (SEC-018).
    Prevents silent overwriting of historical facts by recording before/after snapshots.
    """

    __tablename__ = "record_revisions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("patient_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entity_type: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # condition, allergy, symptom, observation
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # created, corrected, archived
    previous_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    new_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    changed_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


# Composite indexes for efficient patient-scoped chronological queries
Index(
    "ix_health_events_patient_occurred",
    HealthEvent.patient_id,
    HealthEvent.event_occurred_at.desc(),
)
Index(
    "ix_record_revisions_entity_lookup",
    RecordRevision.patient_id,
    RecordRevision.entity_type,
    RecordRevision.entity_id,
    RecordRevision.revision_number,
)
Index(
    "ix_health_observations_patient_observed",
    HealthObservation.patient_id,
    HealthObservation.observed_at.desc(),
)
