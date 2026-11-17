"""
Patient Profile API Endpoints (v1)
Handles profile retrieval, demographic updates, onboarding, and ownership enforcement.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from mediflow.core.database import get_db
from mediflow.core.dependencies import enforce_patient_ownership, get_current_patient
from mediflow.modules.patients.models import PatientProfile
from mediflow.modules.patients.schemas import (
    PatientOnboardingRequest,
    PatientProfileResponse,
    PatientProfileUpdate,
)
from mediflow.modules.patients.service import PatientService

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get(
    "/profile",
    response_model=PatientProfileResponse,
    summary="Get current patient profile",
)
async def get_profile(
    current_patient: PatientProfile = Depends(get_current_patient),
) -> Any:
    """Return the profile belonging to the currently authenticated patient."""
    return current_patient


@router.put(
    "/profile",
    response_model=PatientProfileResponse,
    summary="Update current patient demographics",
)
async def update_profile(
    payload: PatientProfileUpdate,
    current_patient: PatientProfile = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Update demographic and baseline fields on the patient's profile."""
    updated = await PatientService.update_profile(
        db=db,
        patient=current_patient,
        update_data=payload,
    )
    return updated


@router.post(
    "/onboarding",
    response_model=PatientProfileResponse,
    summary="Complete patient initial onboarding",
)
async def complete_onboarding(
    payload: PatientOnboardingRequest,
    current_patient: PatientProfile = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Save baseline medical parameters and mark profile as onboarded."""
    updated = await PatientService.complete_onboarding(
        db=db,
        patient=current_patient,
        onboarding_data=payload,
    )
    return updated


@router.get(
    "/{patient_id}",
    response_model=PatientProfileResponse,
    summary="Access patient profile by ID (Ownership Protected)",
)
async def get_patient_by_id(
    patient_id: uuid.UUID,
    current_patient: PatientProfile = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Direct access to a patient record by ID.
    Strictly enforces ownership: Patient A cannot access Patient B (SEC-001, SEC-002).
    """
    enforce_patient_ownership(target_patient_id=patient_id, authenticated_patient=current_patient)

    profile = await PatientService.get_by_id(db, patient_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found.",
        )
    return profile
