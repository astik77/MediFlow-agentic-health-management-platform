"""
Medical History & Timeline Domain Services
Implements atomic CRUD, immutable correction revision tracking (SEC-018),
unified timeline event generation, and strict patient-scoped ownership checks.
"""
from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time
from typing import Any, TypeVar

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from mediflow.core.dependencies import enforce_patient_ownership
from mediflow.modules.health_records.models import (
    HealthEvent,
    HealthObservation,
    PatientAllergy,
    PatientCondition,
    PatientSymptom,
    RecordRevision,
)
from mediflow.modules.health_records.schemas import (
    AllergyCreate,
    AllergyUpdate,
    ConditionCreate,
    ConditionUpdate,
    HealthEventCreate,
    ObservationCreate,
    ObservationUpdate,
    SymptomCreate,
    SymptomUpdate,
)
from mediflow.modules.patients.models import PatientProfile

ModelT = TypeVar(
    "ModelT",
    PatientCondition,
    PatientAllergy,
    PatientSymptom,
    HealthObservation,
)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _date_to_utc_datetime(value: date | None) -> datetime:
    """Convert an optional date into an aware UTC datetime for timeline placement."""
    if value is None:
        return _utc_now()
    return datetime.combine(value, time.min, tzinfo=UTC)


def _try_parse_float(raw: str) -> float | None:
    """Deterministically parse a plain numeric string without altering value_raw."""
    cleaned = raw.strip().replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _serialize_snapshot(record: Any, fields: list[str]) -> dict[str, Any]:
    """Serialize entity fields into JSON-safe dictionary for immutable revision logs."""
    snapshot: dict[str, Any] = {}
    for field in fields:
        val = getattr(record, field)
        if isinstance(val, (datetime, date)):
            snapshot[field] = val.isoformat()
        elif isinstance(val, uuid.UUID):
            snapshot[field] = str(val)
        else:
            snapshot[field] = val
    return snapshot


CONDITION_FIELDS = [
    "name",
    "status",
    "severity",
    "onset_date",
    "resolved_date",
    "notes",
    "source_type",
    "review_status",
    "is_archived",
]
ALLERGY_FIELDS = [
    "allergen",
    "category",
    "reaction",
    "severity",
    "status",
    "onset_date",
    "notes",
    "source_type",
    "review_status",
    "is_archived",
]
SYMPTOM_FIELDS = [
    "name",
    "severity",
    "frequency",
    "body_location",
    "status",
    "started_at",
    "ended_at",
    "notes",
    "source_type",
    "review_status",
    "is_archived",
]
OBSERVATION_FIELDS = [
    "observation_type",
    "display_name",
    "value_raw",
    "unit_raw",
    "value_numeric",
    "value_normalized",
    "unit_normalized",
    "reference_range_text",
    "abnormality_flag",
    "observed_at",
    "notes",
    "source_type",
    "review_status",
    "is_archived",
]


class HealthRecordsService:
    """Domain service for longitudinal medical history, provenance, and timeline."""

    @staticmethod
    async def _next_revision_number(
        db: AsyncSession,
        patient_id: uuid.UUID,
        entity_type: str,
        entity_id: uuid.UUID,
    ) -> int:
        stmt = select(func.coalesce(func.max(RecordRevision.revision_number), 0)).where(
            RecordRevision.patient_id == patient_id,
            RecordRevision.entity_type == entity_type,
            RecordRevision.entity_id == entity_id,
        )
        result = await db.execute(stmt)
        current_max = result.scalar_one()
        return int(current_max) + 1

    @staticmethod
    async def _record_revision(
        db: AsyncSession,
        *,
        patient_id: uuid.UUID,
        user_id: uuid.UUID,
        entity_type: str,
        entity_id: uuid.UUID,
        action: str,
        previous_data: dict[str, Any] | None,
        new_data: dict[str, Any],
        reason: str | None = None,
    ) -> RecordRevision:
        rev_num = await HealthRecordsService._next_revision_number(
            db, patient_id, entity_type, entity_id
        )
        revision = RecordRevision(
            patient_id=patient_id,
            entity_type=entity_type,
            entity_id=entity_id,
            revision_number=rev_num,
            action=action,
            previous_data=previous_data,
            new_data=new_data,
            reason=reason,
            changed_by_user_id=user_id,
        )
        db.add(revision)
        return revision

    @staticmethod
    async def _get_owned_entity(
        db: AsyncSession,
        model_cls: type[ModelT],
        entity_id: uuid.UUID,
        patient: PatientProfile,
    ) -> ModelT:
        """
        Fetch record by primary key and enforce strict ownership.
        Raises 403 Forbidden if record belongs to another patient (SEC-001/SEC-018),
        or 404 Not Found if nonexistent.
        """
        stmt = select(model_cls).where(model_cls.id == entity_id)
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Medical record not found.",
            )
        enforce_patient_ownership(record.patient_id, patient)
        return record

    @staticmethod
    async def get_entity_history(
        db: AsyncSession,
        model_cls: type[ModelT],
        entity_type: str,
        entity_id: uuid.UUID,
        patient: PatientProfile,
    ) -> list[RecordRevision]:
        """Return chronological revision log for a patient-owned medical record."""
        await HealthRecordsService._get_owned_entity(db, model_cls, entity_id, patient)
        stmt = (
            select(RecordRevision)
            .where(
                RecordRevision.patient_id == patient.id,
                RecordRevision.entity_type == entity_type,
                RecordRevision.entity_id == entity_id,
            )
            .order_by(RecordRevision.revision_number.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # CONDITIONS
    # ------------------------------------------------------------------

    @staticmethod
    async def list_conditions(
        db: AsyncSession,
        patient: PatientProfile,
        include_archived: bool = False,
    ) -> list[PatientCondition]:
        stmt = select(PatientCondition).where(PatientCondition.patient_id == patient.id)
        if not include_archived:
            stmt = stmt.where(PatientCondition.is_archived.is_(False))
        stmt = stmt.order_by(PatientCondition.created_at.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_condition(
        db: AsyncSession,
        condition_id: uuid.UUID,
        patient: PatientProfile,
    ) -> PatientCondition:
        return await HealthRecordsService._get_owned_entity(
            db, PatientCondition, condition_id, patient
        )

    @staticmethod
    async def create_condition(
        db: AsyncSession,
        patient: PatientProfile,
        user_id: uuid.UUID,
        payload: ConditionCreate,
    ) -> PatientCondition:
        record = PatientCondition(
            patient_id=patient.id,
            name=payload.name.strip(),
            status=payload.status,
            severity=payload.severity,
            onset_date=payload.onset_date,
            resolved_date=payload.resolved_date,
            notes=payload.notes,
            source_type="patient_reported",
            review_status="confirmed",
        )
        db.add(record)
        await db.flush()

        await HealthRecordsService._record_revision(
            db,
            patient_id=patient.id,
            user_id=user_id,
            entity_type="condition",
            entity_id=record.id,
            action="created",
            previous_data=None,
            new_data=_serialize_snapshot(record, CONDITION_FIELDS),
            reason="Initial patient entry",
        )

        db.add(
            HealthEvent(
                patient_id=patient.id,
                event_category="condition",
                title=f"Condition recorded: {record.name}",
                summary=record.notes or f"Status: {record.status}",
                event_occurred_at=_date_to_utc_datetime(record.onset_date),
                source_type=record.source_type,
                review_status=record.review_status,
                related_entity_type="condition",
                related_entity_id=record.id,
                metadata_json={"status": record.status, "severity": record.severity},
            )
        )
        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def correct_condition(
        db: AsyncSession,
        condition_id: uuid.UUID,
        patient: PatientProfile,
        user_id: uuid.UUID,
        payload: ConditionUpdate,
    ) -> PatientCondition:
        record = await HealthRecordsService._get_owned_entity(
            db, PatientCondition, condition_id, patient
        )
        previous_snapshot = _serialize_snapshot(record, CONDITION_FIELDS)

        updates = payload.model_dump(exclude_unset=True, exclude={"correction_reason"})
        for field, val in updates.items():
            setattr(record, field, val.strip() if isinstance(val, str) and field == "name" else val)

        new_snapshot = _serialize_snapshot(record, CONDITION_FIELDS)
        await HealthRecordsService._record_revision(
            db,
            patient_id=patient.id,
            user_id=user_id,
            entity_type="condition",
            entity_id=record.id,
            action="corrected",
            previous_data=previous_snapshot,
            new_data=new_snapshot,
            reason=payload.correction_reason or "Patient record correction",
        )

        db.add(
            HealthEvent(
                patient_id=patient.id,
                event_category="correction",
                title=f"Condition updated: {record.name}",
                summary=payload.correction_reason or f"Updated fields: {', '.join(updates.keys())}",
                event_occurred_at=_utc_now(),
                source_type="patient_confirmed",
                review_status=record.review_status,
                related_entity_type="condition",
                related_entity_id=record.id,
                metadata_json={"changed_fields": list(updates.keys())},
            )
        )
        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def archive_condition(
        db: AsyncSession,
        condition_id: uuid.UUID,
        patient: PatientProfile,
        user_id: uuid.UUID,
        reason: str | None = None,
    ) -> PatientCondition:
        record = await HealthRecordsService._get_owned_entity(
            db, PatientCondition, condition_id, patient
        )
        previous_snapshot = _serialize_snapshot(record, CONDITION_FIELDS)
        record.is_archived = True
        new_snapshot = _serialize_snapshot(record, CONDITION_FIELDS)

        await HealthRecordsService._record_revision(
            db,
            patient_id=patient.id,
            user_id=user_id,
            entity_type="condition",
            entity_id=record.id,
            action="archived",
            previous_data=previous_snapshot,
            new_data=new_snapshot,
            reason=reason or "Archived by patient",
        )
        await db.commit()
        await db.refresh(record)
        return record

    # ------------------------------------------------------------------
    # ALLERGIES
    # ------------------------------------------------------------------

    @staticmethod
    async def list_allergies(
        db: AsyncSession,
        patient: PatientProfile,
        include_archived: bool = False,
    ) -> list[PatientAllergy]:
        stmt = select(PatientAllergy).where(PatientAllergy.patient_id == patient.id)
        if not include_archived:
            stmt = stmt.where(PatientAllergy.is_archived.is_(False))
        stmt = stmt.order_by(PatientAllergy.created_at.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_allergy(
        db: AsyncSession,
        allergy_id: uuid.UUID,
        patient: PatientProfile,
    ) -> PatientAllergy:
        return await HealthRecordsService._get_owned_entity(
            db, PatientAllergy, allergy_id, patient
        )

    @staticmethod
    async def create_allergy(
        db: AsyncSession,
        patient: PatientProfile,
        user_id: uuid.UUID,
        payload: AllergyCreate,
    ) -> PatientAllergy:
        record = PatientAllergy(
            patient_id=patient.id,
            allergen=payload.allergen.strip(),
            category=payload.category,
            reaction=payload.reaction,
            severity=payload.severity,
            status=payload.status,
            onset_date=payload.onset_date,
            notes=payload.notes,
            source_type="patient_reported",
            review_status="confirmed",
        )
        db.add(record)
        await db.flush()

        await HealthRecordsService._record_revision(
            db,
            patient_id=patient.id,
            user_id=user_id,
            entity_type="allergy",
            entity_id=record.id,
            action="created",
            previous_data=None,
            new_data=_serialize_snapshot(record, ALLERGY_FIELDS),
            reason="Initial patient entry",
        )

        db.add(
            HealthEvent(
                patient_id=patient.id,
                event_category="allergy",
                title=f"Allergy recorded: {record.allergen}",
                summary=record.reaction or f"Category: {record.category} ({record.severity})",
                event_occurred_at=_date_to_utc_datetime(record.onset_date),
                source_type=record.source_type,
                review_status=record.review_status,
                related_entity_type="allergy",
                related_entity_id=record.id,
                metadata_json={"category": record.category, "severity": record.severity},
            )
        )
        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def correct_allergy(
        db: AsyncSession,
        allergy_id: uuid.UUID,
        patient: PatientProfile,
        user_id: uuid.UUID,
        payload: AllergyUpdate,
    ) -> PatientAllergy:
        record = await HealthRecordsService._get_owned_entity(
            db, PatientAllergy, allergy_id, patient
        )
        previous_snapshot = _serialize_snapshot(record, ALLERGY_FIELDS)

        updates = payload.model_dump(exclude_unset=True, exclude={"correction_reason"})
        for field, val in updates.items():
            setattr(
                record,
                field,
                val.strip() if isinstance(val, str) and field == "allergen" else val,
            )

        new_snapshot = _serialize_snapshot(record, ALLERGY_FIELDS)
        await HealthRecordsService._record_revision(
            db,
            patient_id=patient.id,
            user_id=user_id,
            entity_type="allergy",
            entity_id=record.id,
            action="corrected",
            previous_data=previous_snapshot,
            new_data=new_snapshot,
            reason=payload.correction_reason or "Patient record correction",
        )

        db.add(
            HealthEvent(
                patient_id=patient.id,
                event_category="correction",
                title=f"Allergy updated: {record.allergen}",
                summary=payload.correction_reason or f"Updated fields: {', '.join(updates.keys())}",
                event_occurred_at=_utc_now(),
                source_type="patient_confirmed",
                review_status=record.review_status,
                related_entity_type="allergy",
                related_entity_id=record.id,
                metadata_json={"changed_fields": list(updates.keys())},
            )
        )
        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def archive_allergy(
        db: AsyncSession,
        allergy_id: uuid.UUID,
        patient: PatientProfile,
        user_id: uuid.UUID,
        reason: str | None = None,
    ) -> PatientAllergy:
        record = await HealthRecordsService._get_owned_entity(
            db, PatientAllergy, allergy_id, patient
        )
        previous_snapshot = _serialize_snapshot(record, ALLERGY_FIELDS)
        record.is_archived = True
        new_snapshot = _serialize_snapshot(record, ALLERGY_FIELDS)

        await HealthRecordsService._record_revision(
            db,
            patient_id=patient.id,
            user_id=user_id,
            entity_type="allergy",
            entity_id=record.id,
            action="archived",
            previous_data=previous_snapshot,
            new_data=new_snapshot,
            reason=reason or "Archived by patient",
        )
        await db.commit()
        await db.refresh(record)
        return record

    # ------------------------------------------------------------------
    # SYMPTOMS
    # ------------------------------------------------------------------

    @staticmethod
    async def list_symptoms(
        db: AsyncSession,
        patient: PatientProfile,
        include_archived: bool = False,
    ) -> list[PatientSymptom]:
        stmt = select(PatientSymptom).where(PatientSymptom.patient_id == patient.id)
        if not include_archived:
            stmt = stmt.where(PatientSymptom.is_archived.is_(False))
        stmt = stmt.order_by(PatientSymptom.started_at.desc(), PatientSymptom.created_at.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_symptom(
        db: AsyncSession,
        symptom_id: uuid.UUID,
        patient: PatientProfile,
    ) -> PatientSymptom:
        return await HealthRecordsService._get_owned_entity(
            db, PatientSymptom, symptom_id, patient
        )

    @staticmethod
    async def create_symptom(
        db: AsyncSession,
        patient: PatientProfile,
        user_id: uuid.UUID,
        payload: SymptomCreate,
    ) -> PatientSymptom:
        started_at = payload.started_at or _utc_now()
        record = PatientSymptom(
            patient_id=patient.id,
            name=payload.name.strip(),
            severity=payload.severity,
            frequency=payload.frequency,
            body_location=payload.body_location,
            status=payload.status,
            started_at=started_at,
            ended_at=payload.ended_at,
            notes=payload.notes,
            source_type="patient_reported",
            review_status="confirmed",
        )
        db.add(record)
        await db.flush()

        await HealthRecordsService._record_revision(
            db,
            patient_id=patient.id,
            user_id=user_id,
            entity_type="symptom",
            entity_id=record.id,
            action="created",
            previous_data=None,
            new_data=_serialize_snapshot(record, SYMPTOM_FIELDS),
            reason="Initial patient entry",
        )

        db.add(
            HealthEvent(
                patient_id=patient.id,
                event_category="symptom",
                title=f"Symptom reported: {record.name}",
                summary=record.notes or f"Severity: {record.severity} • Status: {record.status}",
                event_occurred_at=record.started_at,
                source_type=record.source_type,
                review_status=record.review_status,
                related_entity_type="symptom",
                related_entity_id=record.id,
                metadata_json={"severity": record.severity, "status": record.status},
            )
        )
        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def correct_symptom(
        db: AsyncSession,
        symptom_id: uuid.UUID,
        patient: PatientProfile,
        user_id: uuid.UUID,
        payload: SymptomUpdate,
    ) -> PatientSymptom:
        record = await HealthRecordsService._get_owned_entity(
            db, PatientSymptom, symptom_id, patient
        )
        previous_snapshot = _serialize_snapshot(record, SYMPTOM_FIELDS)

        updates = payload.model_dump(exclude_unset=True, exclude={"correction_reason"})
        for field, val in updates.items():
            setattr(record, field, val.strip() if isinstance(val, str) and field == "name" else val)

        new_snapshot = _serialize_snapshot(record, SYMPTOM_FIELDS)
        await HealthRecordsService._record_revision(
            db,
            patient_id=patient.id,
            user_id=user_id,
            entity_type="symptom",
            entity_id=record.id,
            action="corrected",
            previous_data=previous_snapshot,
            new_data=new_snapshot,
            reason=payload.correction_reason or "Patient record correction",
        )

        db.add(
            HealthEvent(
                patient_id=patient.id,
                event_category="correction",
                title=f"Symptom updated: {record.name}",
                summary=payload.correction_reason or f"Updated fields: {', '.join(updates.keys())}",
                event_occurred_at=_utc_now(),
                source_type="patient_confirmed",
                review_status=record.review_status,
                related_entity_type="symptom",
                related_entity_id=record.id,
                metadata_json={"changed_fields": list(updates.keys())},
            )
        )
        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def archive_symptom(
        db: AsyncSession,
        symptom_id: uuid.UUID,
        patient: PatientProfile,
        user_id: uuid.UUID,
        reason: str | None = None,
    ) -> PatientSymptom:
        record = await HealthRecordsService._get_owned_entity(
            db, PatientSymptom, symptom_id, patient
        )
        previous_snapshot = _serialize_snapshot(record, SYMPTOM_FIELDS)
        record.is_archived = True
        new_snapshot = _serialize_snapshot(record, SYMPTOM_FIELDS)

        await HealthRecordsService._record_revision(
            db,
            patient_id=patient.id,
            user_id=user_id,
            entity_type="symptom",
            entity_id=record.id,
            action="archived",
            previous_data=previous_snapshot,
            new_data=new_snapshot,
            reason=reason or "Archived by patient",
        )
        await db.commit()
        await db.refresh(record)
        return record

    # ------------------------------------------------------------------
    # HEALTH OBSERVATIONS
    # ------------------------------------------------------------------

    @staticmethod
    async def list_observations(
        db: AsyncSession,
        patient: PatientProfile,
        observation_type: str | None = None,
        display_name: str | None = None,
        include_archived: bool = False,
    ) -> list[HealthObservation]:
        stmt = select(HealthObservation).where(HealthObservation.patient_id == patient.id)
        if not include_archived:
            stmt = stmt.where(HealthObservation.is_archived.is_(False))
        if observation_type:
            stmt = stmt.where(HealthObservation.observation_type == observation_type)
        if display_name:
            stmt = stmt.where(HealthObservation.display_name.ilike(f"%{display_name}%"))
        stmt = stmt.order_by(
            HealthObservation.observed_at.desc(), HealthObservation.created_at.desc()
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_observation(
        db: AsyncSession,
        observation_id: uuid.UUID,
        patient: PatientProfile,
    ) -> HealthObservation:
        return await HealthRecordsService._get_owned_entity(
            db, HealthObservation, observation_id, patient
        )

    @staticmethod
    async def create_observation(
        db: AsyncSession,
        patient: PatientProfile,
        user_id: uuid.UUID,
        payload: ObservationCreate,
    ) -> HealthObservation:
        observed_at = payload.observed_at or _utc_now()
        value_numeric = (
            payload.value_numeric
            if payload.value_numeric is not None
            else _try_parse_float(payload.value_raw)
        )
        record = HealthObservation(
            patient_id=patient.id,
            observation_type=payload.observation_type,
            display_name=payload.display_name.strip(),
            value_raw=payload.value_raw.strip(),
            unit_raw=payload.unit_raw.strip() if payload.unit_raw else None,
            value_numeric=value_numeric,
            value_normalized=payload.value_normalized,
            unit_normalized=payload.unit_normalized,
            reference_range_text=payload.reference_range_text,
            abnormality_flag=payload.abnormality_flag,
            observed_at=observed_at,
            notes=payload.notes,
            source_type="patient_reported",
            review_status="confirmed",
            extraction_method="manual_entry",
        )
        db.add(record)
        await db.flush()

        await HealthRecordsService._record_revision(
            db,
            patient_id=patient.id,
            user_id=user_id,
            entity_type="observation",
            entity_id=record.id,
            action="created",
            previous_data=None,
            new_data=_serialize_snapshot(record, OBSERVATION_FIELDS),
            reason="Initial patient entry",
        )

        unit_part = f" {record.unit_raw}" if record.unit_raw else ""
        ref_part = (
            f" (Ref: {record.reference_range_text})" if record.reference_range_text else ""
        )
        db.add(
            HealthEvent(
                patient_id=patient.id,
                event_category="observation",
                title=f"{record.display_name}: {record.value_raw}{unit_part}",
                summary=record.notes or f"Recorded measurement{ref_part}",
                event_occurred_at=record.observed_at,
                source_type=record.source_type,
                review_status=record.review_status,
                related_entity_type="observation",
                related_entity_id=record.id,
                metadata_json={
                    "observation_type": record.observation_type,
                    "value_raw": record.value_raw,
                    "unit_raw": record.unit_raw,
                    "reference_range_text": record.reference_range_text,
                    "abnormality_flag": record.abnormality_flag,
                },
            )
        )
        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def correct_observation(
        db: AsyncSession,
        observation_id: uuid.UUID,
        patient: PatientProfile,
        user_id: uuid.UUID,
        payload: ObservationUpdate,
    ) -> HealthObservation:
        record = await HealthRecordsService._get_owned_entity(
            db, HealthObservation, observation_id, patient
        )
        previous_snapshot = _serialize_snapshot(record, OBSERVATION_FIELDS)

        updates = payload.model_dump(exclude_unset=True, exclude={"correction_reason"})
        for field, val in updates.items():
            setattr(record, field, val)

        if "value_raw" in updates and "value_numeric" not in updates:
            record.value_numeric = _try_parse_float(record.value_raw)

        new_snapshot = _serialize_snapshot(record, OBSERVATION_FIELDS)
        await HealthRecordsService._record_revision(
            db,
            patient_id=patient.id,
            user_id=user_id,
            entity_type="observation",
            entity_id=record.id,
            action="corrected",
            previous_data=previous_snapshot,
            new_data=new_snapshot,
            reason=payload.correction_reason or "Patient observation correction",
        )

        db.add(
            HealthEvent(
                patient_id=patient.id,
                event_category="correction",
                title=f"Observation corrected: {record.display_name}",
                summary=payload.correction_reason or f"Updated fields: {', '.join(updates.keys())}",
                event_occurred_at=_utc_now(),
                source_type="patient_confirmed",
                review_status=record.review_status,
                related_entity_type="observation",
                related_entity_id=record.id,
                metadata_json={"changed_fields": list(updates.keys())},
            )
        )
        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def archive_observation(
        db: AsyncSession,
        observation_id: uuid.UUID,
        patient: PatientProfile,
        user_id: uuid.UUID,
        reason: str | None = None,
    ) -> HealthObservation:
        record = await HealthRecordsService._get_owned_entity(
            db, HealthObservation, observation_id, patient
        )
        previous_snapshot = _serialize_snapshot(record, OBSERVATION_FIELDS)
        record.is_archived = True
        new_snapshot = _serialize_snapshot(record, OBSERVATION_FIELDS)

        await HealthRecordsService._record_revision(
            db,
            patient_id=patient.id,
            user_id=user_id,
            entity_type="observation",
            entity_id=record.id,
            action="archived",
            previous_data=previous_snapshot,
            new_data=new_snapshot,
            reason=reason or "Archived by patient",
        )
        await db.commit()
        await db.refresh(record)
        return record

    # ------------------------------------------------------------------
    # TIMELINE & OVERVIEW
    # ------------------------------------------------------------------

    @staticmethod
    async def create_timeline_event(
        db: AsyncSession,
        patient: PatientProfile,
        payload: HealthEventCreate,
    ) -> HealthEvent:
        event = HealthEvent(
            patient_id=patient.id,
            event_category=payload.event_category,
            title=payload.title.strip(),
            summary=payload.summary,
            event_occurred_at=payload.event_occurred_at or _utc_now(),
            source_type="patient_reported",
            review_status="confirmed",
            metadata_json=payload.metadata_json,
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)
        return event

    @staticmethod
    async def delete_timeline_event(
        db: AsyncSession,
        patient: PatientProfile,
        event_id: uuid.UUID,
    ) -> bool:
        stmt = select(HealthEvent).where(
            HealthEvent.id == event_id,
            HealthEvent.patient_id == patient.id,
        )
        event = (await db.execute(stmt)).scalar_one_or_none()
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Timeline event not found.",
            )
        # Cascade soft-archive to related clinical entity if linked
        if event.related_entity_type and event.related_entity_id:
            try:
                if event.related_entity_type == "symptom":
                    sym = await db.get(PatientSymptom, event.related_entity_id)
                    if sym and sym.patient_id == patient.id:
                        sym.is_archived = True
                elif event.related_entity_type == "condition":
                    cond = await db.get(PatientCondition, event.related_entity_id)
                    if cond and cond.patient_id == patient.id:
                        cond.is_archived = True
                elif event.related_entity_type == "allergy":
                    allg = await db.get(PatientAllergy, event.related_entity_id)
                    if allg and allg.patient_id == patient.id:
                        allg.is_archived = True
                elif event.related_entity_type == "observation":
                    obs = await db.get(HealthObservation, event.related_entity_id)
                    if obs and obs.patient_id == patient.id:
                        obs.is_archived = True
            except Exception as err:
                logger.warning("timeline_cascade_archive_failed", error=str(err))

        await db.delete(event)
        await db.commit()
        return True

    @staticmethod
    async def list_timeline(
        db: AsyncSession,
        patient: PatientProfile,
        *,
        category: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        search: str | None = None,
        review_status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[HealthEvent], int]:
        filters = [HealthEvent.patient_id == patient.id]

        if category:
            filters.append(HealthEvent.event_category == category)
        if start_date:
            filters.append(HealthEvent.event_occurred_at >= start_date)
        if end_date:
            filters.append(HealthEvent.event_occurred_at <= end_date)
        if review_status:
            filters.append(HealthEvent.review_status == review_status)
        if search:
            pattern = f"%{search.strip()}%"
            filters.append(
                or_(
                    HealthEvent.title.ilike(pattern),
                    HealthEvent.summary.ilike(pattern),
                )
            )

        count_stmt = select(func.count(HealthEvent.id)).where(*filters)
        total = int((await db.execute(count_stmt)).scalar_one())

        items_stmt = (
            select(HealthEvent)
            .where(*filters)
            .order_by(HealthEvent.event_occurred_at.desc(), HealthEvent.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        items = list((await db.execute(items_stmt)).scalars().all())
        return items, total

    @staticmethod
    async def get_overview(
        db: AsyncSession,
        patient: PatientProfile,
    ) -> dict[str, Any]:
        cond_total = int(
            (
                await db.execute(
                    select(func.count(PatientCondition.id)).where(
                        PatientCondition.patient_id == patient.id,
                        PatientCondition.is_archived.is_(False),
                    )
                )
            ).scalar_one()
        )
        cond_active = int(
            (
                await db.execute(
                    select(func.count(PatientCondition.id)).where(
                        PatientCondition.patient_id == patient.id,
                        PatientCondition.is_archived.is_(False),
                        PatientCondition.status == "active",
                    )
                )
            ).scalar_one()
        )
        allergies_total = int(
            (
                await db.execute(
                    select(func.count(PatientAllergy.id)).where(
                        PatientAllergy.patient_id == patient.id,
                        PatientAllergy.is_archived.is_(False),
                    )
                )
            ).scalar_one()
        )
        symptoms_total = int(
            (
                await db.execute(
                    select(func.count(PatientSymptom.id)).where(
                        PatientSymptom.patient_id == patient.id,
                        PatientSymptom.is_archived.is_(False),
                    )
                )
            ).scalar_one()
        )
        symptoms_ongoing = int(
            (
                await db.execute(
                    select(func.count(PatientSymptom.id)).where(
                        PatientSymptom.patient_id == patient.id,
                        PatientSymptom.is_archived.is_(False),
                        PatientSymptom.status == "ongoing",
                    )
                )
            ).scalar_one()
        )
        observations_total = int(
            (
                await db.execute(
                    select(func.count(HealthObservation.id)).where(
                        HealthObservation.patient_id == patient.id,
                        HealthObservation.is_archived.is_(False),
                    )
                )
            ).scalar_one()
        )
        recent_events, timeline_total = await HealthRecordsService.list_timeline(
            db, patient, limit=5, offset=0
        )

        return {
            "conditions_count": cond_total,
            "active_conditions_count": cond_active,
            "allergies_count": allergies_total,
            "symptoms_count": symptoms_total,
            "ongoing_symptoms_count": symptoms_ongoing,
            "observations_count": observations_total,
            "timeline_events_count": timeline_total,
            "recent_events": recent_events,
        }
