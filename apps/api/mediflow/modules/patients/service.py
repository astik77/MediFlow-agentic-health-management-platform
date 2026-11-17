"""
Patient Profile Domain Services
Handles profile retrieval, demographic updates, and onboarding baselines.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mediflow.modules.patients.models import PatientProfile
from mediflow.modules.patients.schemas import PatientOnboardingRequest, PatientProfileUpdate


class PatientService:
    """Encapsulates patient profile and baseline workflows."""

    @staticmethod
    async def get_by_user_id(db: AsyncSession, user_id: uuid.UUID) -> PatientProfile | None:
        """Fetch patient profile associated with a user account."""
        stmt = select(PatientProfile).where(PatientProfile.user_id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_id(db: AsyncSession, patient_id: uuid.UUID) -> PatientProfile | None:
        """Fetch patient profile by primary key."""
        stmt = select(PatientProfile).where(PatientProfile.id == patient_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def update_profile(
        db: AsyncSession,
        patient: PatientProfile,
        update_data: PatientProfileUpdate,
    ) -> PatientProfile:
        """Apply partial demographic and baseline updates to an existing profile."""
        data_dict = update_data.model_dump(exclude_unset=True)

        for field, value in data_dict.items():
            if hasattr(patient, field) and value is not None:
                setattr(patient, field, value)

        await db.commit()
        await db.refresh(patient)
        return patient

    @staticmethod
    async def complete_onboarding(
        db: AsyncSession,
        patient: PatientProfile,
        onboarding_data: PatientOnboardingRequest,
    ) -> PatientProfile:
        """
        Record initial baseline health parameters and mark profile as onboarded.
        """
        if onboarding_data.date_of_birth is not None:
            patient.date_of_birth = onboarding_data.date_of_birth
        if onboarding_data.biological_sex is not None:
            patient.biological_sex = onboarding_data.biological_sex
        if onboarding_data.blood_group is not None:
            patient.blood_group = onboarding_data.blood_group
        if onboarding_data.height_cm is not None:
            patient.height_cm = onboarding_data.height_cm
        if onboarding_data.weight_kg is not None:
            patient.weight_kg = onboarding_data.weight_kg

        if onboarding_data.emergency_contact:
            patient.emergency_contact = onboarding_data.emergency_contact.model_dump()

        # Consolidate baseline conditions & allergies into medical_baseline JSON
        medical_baseline: dict[str, Any] = patient.medical_baseline or {}
        if onboarding_data.existing_conditions:
            medical_baseline["existing_conditions"] = onboarding_data.existing_conditions
        if onboarding_data.known_allergies:
            medical_baseline["known_allergies"] = onboarding_data.known_allergies

        patient.medical_baseline = medical_baseline
        patient.is_onboarded = True

        await db.commit()
        await db.refresh(patient)
        return patient
