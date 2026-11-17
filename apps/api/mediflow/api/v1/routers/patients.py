"""
Patient Profile API Endpoints (v1)
Handles profile retrieval, demographic updates, onboarding, portable data export,
cascading account erasure, and ownership enforcement.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from mediflow.api.v1.routers.auth import clear_session_cookie
from mediflow.core.database import get_db
from mediflow.core.dependencies import (
    enforce_patient_ownership,
    get_current_patient,
    get_current_user,
)
from mediflow.modules.auth.models import User
from mediflow.modules.patients.models import PatientProfile
from mediflow.modules.patients.schemas import (
    AccountDeletionRequest,
    AccountDeletionResponse,
    PatientExportResponse,
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
    "/export",
    response_model=PatientExportResponse,
    summary="Export authenticated patient's full longitudinal health vault (JSON)",
)
async def export_patient_vault(
    current_user: User = Depends(get_current_user),
    current_patient: PatientProfile = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Export all health records, observations, timeline events, document metadata,
    conversations, and longitudinal summaries belonging to the authenticated patient.
    """
    return await PatientService.export_patient_data(
        db=db,
        user=current_user,
        patient=current_patient,
    )


@router.delete(
    "/account",
    response_model=AccountDeletionResponse,
    summary="Permanently delete patient account and all associated data & files",
)
async def delete_patient_account(
    payload: AccountDeletionRequest,
    response: Response,
    current_user: User = Depends(get_current_user),
    current_patient: PatientProfile = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Verify current password and explicit confirmation phrase, remove all uploaded
    files from disk, permanently erase all database records across all tables,
    and clear the HttpOnly session cookie.
    """
    result = await PatientService.delete_patient_account(
        db=db,
        user=current_user,
        patient=current_patient,
        payload=payload,
    )
    clear_session_cookie(response)
    return result


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
