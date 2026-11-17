"""
Patient Profile Pydantic Schemas
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EmergencyContactSchema(BaseModel):
    """Emergency contact information structure."""

    name: str = Field(..., min_length=1)
    relationship: str = Field(..., min_length=1)
    phone_number: str = Field(..., min_length=4)


class PatientProfileResponse(BaseModel):
    """Public representation of a patient profile."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    full_name: str
    date_of_birth: date | None = None
    biological_sex: str | None = None
    blood_group: str | None = None
    height_cm: float | None = None
    weight_kg: float | None = None
    emergency_contact: dict[str, Any] | None = None
    medical_baseline: dict[str, Any] | None = None
    is_onboarded: bool = False
    created_at: datetime
    updated_at: datetime


class PatientProfileUpdate(BaseModel):
    """Payload to update editable patient profile demographics."""

    full_name: str | None = Field(None, min_length=1, max_length=255)
    date_of_birth: date | None = None
    biological_sex: str | None = Field(None, max_length=20)
    blood_group: str | None = Field(None, max_length=10)
    height_cm: float | None = Field(None, ge=30.0, le=300.0)
    weight_kg: float | None = Field(None, ge=1.0, le=500.0)
    emergency_contact: dict[str, Any] | None = None
    medical_baseline: dict[str, Any] | None = None


class PatientOnboardingRequest(BaseModel):
    """Payload submitted when completing patient onboarding."""

    date_of_birth: date | None = None
    biological_sex: str | None = Field(None, max_length=20)
    blood_group: str | None = Field(None, max_length=10)
    height_cm: float | None = Field(None, ge=30.0, le=300.0)
    weight_kg: float | None = Field(None, ge=1.0, le=500.0)
    emergency_contact: EmergencyContactSchema | None = None
    existing_conditions: list[str] | None = Field(default_factory=list)
    known_allergies: list[str] | None = Field(default_factory=list)
