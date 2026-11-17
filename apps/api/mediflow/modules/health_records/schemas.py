"""
Medical History & Timeline Pydantic Schemas
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

SourceType = Literal[
    "patient_reported",
    "document_extracted",
    "patient_confirmed",
    "ai_proposed",
]
ReviewStatus = Literal["confirmed", "candidate", "rejected", "uncertain"]
ConditionStatus = Literal["active", "resolved", "remission", "inactive"]
AllergyCategory = Literal["medication", "food", "environmental", "other"]
AllergySeverity = Literal["mild", "moderate", "severe", "life_threatening"]
AllergyStatus = Literal["active", "inactive", "resolved"]
SymptomSeverity = Literal["mild", "moderate", "severe"]
SymptomStatus = Literal["ongoing", "resolved", "intermittent"]
ObservationType = Literal["lab_result", "vital_sign", "measurement", "clinical_note"]
AbnormalityFlag = Literal["normal", "low", "high", "critical", "unknown"]
EventCategory = Literal[
    "symptom",
    "condition",
    "allergy",
    "observation",
    "document",
    "correction",
    "summary",
    "general",
]


# ---- Conditions ----


class ConditionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    status: ConditionStatus = "active"
    severity: str | None = Field(None, max_length=32)
    onset_date: date | None = None
    resolved_date: date | None = None
    notes: str | None = None


class ConditionUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    status: ConditionStatus | None = None
    severity: str | None = Field(None, max_length=32)
    onset_date: date | None = None
    resolved_date: date | None = None
    notes: str | None = None
    review_status: ReviewStatus | None = None
    correction_reason: str | None = Field(None, max_length=500)


class ConditionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    name: str
    status: str
    severity: str | None
    onset_date: date | None
    resolved_date: date | None
    notes: str | None
    source_type: str
    review_status: str
    source_document_id: uuid.UUID | None
    is_archived: bool
    created_at: datetime
    updated_at: datetime


# ---- Allergies ----


class AllergyCreate(BaseModel):
    allergen: str = Field(..., min_length=1, max_length=255)
    category: AllergyCategory = "other"
    reaction: str | None = Field(None, max_length=500)
    severity: AllergySeverity = "moderate"
    status: AllergyStatus = "active"
    onset_date: date | None = None
    notes: str | None = None


class AllergyUpdate(BaseModel):
    allergen: str | None = Field(None, min_length=1, max_length=255)
    category: AllergyCategory | None = None
    reaction: str | None = Field(None, max_length=500)
    severity: AllergySeverity | None = None
    status: AllergyStatus | None = None
    onset_date: date | None = None
    notes: str | None = None
    review_status: ReviewStatus | None = None
    correction_reason: str | None = Field(None, max_length=500)


class AllergyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    allergen: str
    category: str
    reaction: str | None
    severity: str
    status: str
    onset_date: date | None
    notes: str | None
    source_type: str
    review_status: str
    source_document_id: uuid.UUID | None
    is_archived: bool
    created_at: datetime
    updated_at: datetime


# ---- Symptoms ----


class SymptomCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    severity: SymptomSeverity = "moderate"
    frequency: str | None = Field(None, max_length=100)
    body_location: str | None = Field(None, max_length=150)
    status: SymptomStatus = "ongoing"
    started_at: datetime | None = None
    ended_at: datetime | None = None
    notes: str | None = None


class SymptomUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    severity: SymptomSeverity | None = None
    frequency: str | None = Field(None, max_length=100)
    body_location: str | None = Field(None, max_length=150)
    status: SymptomStatus | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    notes: str | None = None
    review_status: ReviewStatus | None = None
    correction_reason: str | None = Field(None, max_length=500)


class SymptomResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    name: str
    severity: str
    frequency: str | None
    body_location: str | None
    status: str
    started_at: datetime
    ended_at: datetime | None
    notes: str | None
    source_type: str
    review_status: str
    source_document_id: uuid.UUID | None
    is_archived: bool
    created_at: datetime
    updated_at: datetime


# ---- Health Observations ----


class ObservationCreate(BaseModel):
    observation_type: ObservationType = "vital_sign"
    display_name: str = Field(..., min_length=1, max_length=255)
    value_raw: str = Field(..., min_length=1, max_length=255)
    unit_raw: str | None = Field(None, max_length=64)
    value_numeric: float | None = None
    value_normalized: float | None = None
    unit_normalized: str | None = Field(None, max_length=64)
    reference_range_text: str | None = Field(None, max_length=255)
    abnormality_flag: AbnormalityFlag | None = None
    observed_at: datetime | None = None
    notes: str | None = None


class ObservationUpdate(BaseModel):
    observation_type: ObservationType | None = None
    display_name: str | None = Field(None, min_length=1, max_length=255)
    value_raw: str | None = Field(None, min_length=1, max_length=255)
    unit_raw: str | None = Field(None, max_length=64)
    value_numeric: float | None = None
    value_normalized: float | None = None
    unit_normalized: str | None = Field(None, max_length=64)
    reference_range_text: str | None = Field(None, max_length=255)
    abnormality_flag: AbnormalityFlag | None = None
    observed_at: datetime | None = None
    notes: str | None = None
    review_status: ReviewStatus | None = None
    correction_reason: str | None = Field(None, max_length=500)


class ObservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    observation_type: str
    display_name: str
    value_raw: str
    unit_raw: str | None
    value_numeric: float | None
    value_normalized: float | None
    unit_normalized: str | None
    reference_range_text: str | None
    abnormality_flag: str | None
    observed_at: datetime
    notes: str | None
    source_type: str
    review_status: str
    source_document_id: uuid.UUID | None
    source_page: int | None
    extraction_method: str | None
    extraction_confidence: float | None
    provenance_metadata: dict[str, Any] | None
    is_archived: bool
    created_at: datetime
    updated_at: datetime


# ---- Record Revision History ----


class RecordRevisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    revision_number: int
    action: str
    previous_data: dict[str, Any] | None
    new_data: dict[str, Any]
    reason: str | None
    changed_by_user_id: uuid.UUID
    created_at: datetime


# ---- Health Events & Timeline ----


class HealthEventCreate(BaseModel):
    event_category: EventCategory = "general"
    title: str = Field(..., min_length=1, max_length=255)
    summary: str | None = None
    event_occurred_at: datetime | None = None
    metadata_json: dict[str, Any] | None = None


class HealthEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    event_category: str
    title: str
    summary: str | None
    event_occurred_at: datetime
    source_type: str
    review_status: str
    related_entity_type: str | None
    related_entity_id: uuid.UUID | None
    metadata_json: dict[str, Any] | None
    created_at: datetime


class TimelineResponse(BaseModel):
    items: list[HealthEventResponse]
    total: int
    limit: int
    offset: int


class HealthOverviewResponse(BaseModel):
    conditions_count: int
    active_conditions_count: int
    allergies_count: int
    symptoms_count: int
    ongoing_symptoms_count: int
    observations_count: int
    timeline_events_count: int
    recent_events: list[HealthEventResponse]
