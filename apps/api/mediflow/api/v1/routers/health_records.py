"""
Health Records API Endpoints (v1)
Manages patient-owned conditions, allergies, symptoms, observations, and revision histories.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from mediflow.core.database import get_db
from mediflow.core.dependencies import get_current_patient, get_current_user
from mediflow.modules.auth.models import User
from mediflow.modules.health_records.models import (
    HealthObservation,
    PatientAllergy,
    PatientCondition,
    PatientSymptom,
)
from mediflow.modules.health_records.schemas import (
    AllergyCreate,
    AllergyResponse,
    AllergyUpdate,
    ConditionCreate,
    ConditionResponse,
    ConditionUpdate,
    HealthOverviewResponse,
    ObservationCreate,
    ObservationResponse,
    ObservationUpdate,
    RecordRevisionResponse,
    SymptomCreate,
    SymptomResponse,
    SymptomUpdate,
)
from mediflow.modules.health_records.service import HealthRecordsService
from mediflow.modules.patients.models import PatientProfile

router = APIRouter(prefix="/health-records", tags=["health-records"])


@router.get("/overview", response_model=HealthOverviewResponse)
async def get_health_overview(
    current_patient: PatientProfile = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Return summary counts and recent timeline activity for the authenticated patient."""
    return await HealthRecordsService.get_overview(db, current_patient)


# ---- CONDITIONS ----


@router.get("/conditions", response_model=list[ConditionResponse])
async def list_conditions(
    include_archived: bool = Query(False),
    current_patient: PatientProfile = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
) -> Any:
    return await HealthRecordsService.list_conditions(
        db, current_patient, include_archived=include_archived
    )


@router.post(
    "/conditions",
    response_model=ConditionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_condition(
    payload: ConditionCreate,
    current_user: User = Depends(get_current_user),
    current_patient: PatientProfile = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
) -> Any:
    return await HealthRecordsService.create_condition(
        db, current_patient, current_user.id, payload
    )


@router.get("/conditions/{condition_id}", response_model=ConditionResponse)
async def get_condition(
    condition_id: uuid.UUID,
    current_patient: PatientProfile = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
) -> Any:
    return await HealthRecordsService.get_condition(db, condition_id, current_patient)


@router.patch("/conditions/{condition_id}", response_model=ConditionResponse)
async def correct_condition(
    condition_id: uuid.UUID,
    payload: ConditionUpdate,
    current_user: User = Depends(get_current_user),
    current_patient: PatientProfile = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
) -> Any:
    return await HealthRecordsService.correct_condition(
        db, condition_id, current_patient, current_user.id, payload
    )


@router.delete("/conditions/{condition_id}", response_model=ConditionResponse)
async def archive_condition(
    condition_id: uuid.UUID,
    reason: str | None = Query(None, max_length=500),
    current_user: User = Depends(get_current_user),
    current_patient: PatientProfile = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
) -> Any:
    return await HealthRecordsService.archive_condition(
        db, condition_id, current_patient, current_user.id, reason=reason
    )


@router.get("/conditions/{condition_id}/history", response_model=list[RecordRevisionResponse])
async def get_condition_history(
    condition_id: uuid.UUID,
    current_patient: PatientProfile = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
) -> Any:
    return await HealthRecordsService.get_entity_history(
        db, PatientCondition, "condition", condition_id, current_patient
    )


# ---- ALLERGIES ----


@router.get("/allergies", response_model=list[AllergyResponse])
async def list_allergies(
    include_archived: bool = Query(False),
    current_patient: PatientProfile = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
) -> Any:
    return await HealthRecordsService.list_allergies(
        db, current_patient, include_archived=include_archived
    )


@router.post(
    "/allergies",
    response_model=AllergyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_allergy(
    payload: AllergyCreate,
    current_user: User = Depends(get_current_user),
    current_patient: PatientProfile = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
) -> Any:
    return await HealthRecordsService.create_allergy(db, current_patient, current_user.id, payload)


@router.get("/allergies/{allergy_id}", response_model=AllergyResponse)
async def get_allergy(
    allergy_id: uuid.UUID,
    current_patient: PatientProfile = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
) -> Any:
    return await HealthRecordsService.get_allergy(db, allergy_id, current_patient)


@router.patch("/allergies/{allergy_id}", response_model=AllergyResponse)
async def correct_allergy(
    allergy_id: uuid.UUID,
    payload: AllergyUpdate,
    current_user: User = Depends(get_current_user),
    current_patient: PatientProfile = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
) -> Any:
    return await HealthRecordsService.correct_allergy(
        db, allergy_id, current_patient, current_user.id, payload
    )


@router.delete("/allergies/{allergy_id}", response_model=AllergyResponse)
async def archive_allergy(
    allergy_id: uuid.UUID,
    reason: str | None = Query(None, max_length=500),
    current_user: User = Depends(get_current_user),
    current_patient: PatientProfile = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
) -> Any:
    return await HealthRecordsService.archive_allergy(
        db, allergy_id, current_patient, current_user.id, reason=reason
    )


@router.get("/allergies/{allergy_id}/history", response_model=list[RecordRevisionResponse])
async def get_allergy_history(
    allergy_id: uuid.UUID,
    current_patient: PatientProfile = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
) -> Any:
    return await HealthRecordsService.get_entity_history(
        db, PatientAllergy, "allergy", allergy_id, current_patient
    )


# ---- SYMPTOMS ----


@router.get("/symptoms", response_model=list[SymptomResponse])
async def list_symptoms(
    include_archived: bool = Query(False),
    current_patient: PatientProfile = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
) -> Any:
    return await HealthRecordsService.list_symptoms(
        db, current_patient, include_archived=include_archived
    )


@router.post(
    "/symptoms",
    response_model=SymptomResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_symptom(
    payload: SymptomCreate,
    current_user: User = Depends(get_current_user),
    current_patient: PatientProfile = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
) -> Any:
    return await HealthRecordsService.create_symptom(db, current_patient, current_user.id, payload)


@router.get("/symptoms/{symptom_id}", response_model=SymptomResponse)
async def get_symptom(
    symptom_id: uuid.UUID,
    current_patient: PatientProfile = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
) -> Any:
    return await HealthRecordsService.get_symptom(db, symptom_id, current_patient)


@router.patch("/symptoms/{symptom_id}", response_model=SymptomResponse)
async def correct_symptom(
    symptom_id: uuid.UUID,
    payload: SymptomUpdate,
    current_user: User = Depends(get_current_user),
    current_patient: PatientProfile = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
) -> Any:
    return await HealthRecordsService.correct_symptom(
        db, symptom_id, current_patient, current_user.id, payload
    )


@router.delete("/symptoms/{symptom_id}", response_model=SymptomResponse)
async def archive_symptom(
    symptom_id: uuid.UUID,
    reason: str | None = Query(None, max_length=500),
    current_user: User = Depends(get_current_user),
    current_patient: PatientProfile = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
) -> Any:
    return await HealthRecordsService.archive_symptom(
        db, symptom_id, current_patient, current_user.id, reason=reason
    )


@router.get("/symptoms/{symptom_id}/history", response_model=list[RecordRevisionResponse])
async def get_symptom_history(
    symptom_id: uuid.UUID,
    current_patient: PatientProfile = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
) -> Any:
    return await HealthRecordsService.get_entity_history(
        db, PatientSymptom, "symptom", symptom_id, current_patient
    )


# ---- OBSERVATIONS ----


@router.get("/observations", response_model=list[ObservationResponse])
async def list_observations(
    observation_type: str | None = Query(None),
    display_name: str | None = Query(None),
    include_archived: bool = Query(False),
    current_patient: PatientProfile = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
) -> Any:
    return await HealthRecordsService.list_observations(
        db,
        current_patient,
        observation_type=observation_type,
        display_name=display_name,
        include_archived=include_archived,
    )


@router.post(
    "/observations",
    response_model=ObservationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_observation(
    payload: ObservationCreate,
    current_user: User = Depends(get_current_user),
    current_patient: PatientProfile = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
) -> Any:
    return await HealthRecordsService.create_observation(
        db, current_patient, current_user.id, payload
    )


@router.get("/observations/{observation_id}", response_model=ObservationResponse)
async def get_observation(
    observation_id: uuid.UUID,
    current_patient: PatientProfile = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
) -> Any:
    return await HealthRecordsService.get_observation(db, observation_id, current_patient)


@router.patch("/observations/{observation_id}", response_model=ObservationResponse)
async def correct_observation(
    observation_id: uuid.UUID,
    payload: ObservationUpdate,
    current_user: User = Depends(get_current_user),
    current_patient: PatientProfile = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
) -> Any:
    return await HealthRecordsService.correct_observation(
        db, observation_id, current_patient, current_user.id, payload
    )


@router.delete("/observations/{observation_id}", response_model=ObservationResponse)
async def archive_observation(
    observation_id: uuid.UUID,
    reason: str | None = Query(None, max_length=500),
    current_user: User = Depends(get_current_user),
    current_patient: PatientProfile = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
) -> Any:
    return await HealthRecordsService.archive_observation(
        db, observation_id, current_patient, current_user.id, reason=reason
    )


@router.get("/observations/{observation_id}/history", response_model=list[RecordRevisionResponse])
async def get_observation_history(
    observation_id: uuid.UUID,
    current_patient: PatientProfile = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
) -> Any:
    return await HealthRecordsService.get_entity_history(
        db, HealthObservation, "observation", observation_id, current_patient
    )
