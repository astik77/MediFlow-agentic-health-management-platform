"""
Patient Profile Domain Services
Handles profile retrieval, demographic updates, onboarding baselines,
portable health vault export (Phase 9), and cascading account erasure (SEC-016).
"""
from __future__ import annotations

import contextlib
import uuid
from collections import defaultdict
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from mediflow.ai.models import AIInvocationLog
from mediflow.core.config import get_settings
from mediflow.core.logging import get_logger
from mediflow.core.security import verify_password
from mediflow.modules.analytics.models import HealthSummary
from mediflow.modules.auth.models import PasswordResetToken, Session, User
from mediflow.modules.conversations.models import Conversation, Message
from mediflow.modules.documents.models import (
    Document,
    DocumentChunk,
    DocumentEmbedding,
    DocumentPage,
    DocumentProcessingJob,
)
from mediflow.modules.health_records.models import (
    HealthEvent,
    HealthObservation,
    PatientAllergy,
    PatientCondition,
    PatientSymptom,
    RecordRevision,
)
from mediflow.modules.patients.models import PatientProfile
from mediflow.modules.patients.schemas import (
    AccountDeletionRequest,
    AccountDeletionResponse,
    PatientExportResponse,
    PatientOnboardingRequest,
    PatientProfileResponse,
    PatientProfileUpdate,
)

logger = get_logger(__name__)

ACCOUNT_DELETION_CONFIRM_PHRASE = "DELETE MY ACCOUNT"


def _iso(val: datetime | date | None) -> str | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        dt = val if val.tzinfo is not None else val.replace(tzinfo=UTC)
        return dt.astimezone(UTC).isoformat()
    return val.isoformat()


class PatientService:
    """Encapsulates patient profile, baseline, export, and erasure workflows."""

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

    @staticmethod
    async def export_patient_data(
        db: AsyncSession,
        user: User,
        patient: PatientProfile,
    ) -> PatientExportResponse:
        """
        Compile a strictly patient-scoped portable JSON export of the entire
        longitudinal health vault. Never includes secrets or server file paths.
        """
        conditions = list(
            (
                await db.execute(
                    select(PatientCondition)
                    .where(PatientCondition.patient_id == patient.id)
                    .order_by(PatientCondition.created_at.asc())
                )
            )
            .scalars()
            .all()
        )
        allergies = list(
            (
                await db.execute(
                    select(PatientAllergy)
                    .where(PatientAllergy.patient_id == patient.id)
                    .order_by(PatientAllergy.created_at.asc())
                )
            )
            .scalars()
            .all()
        )
        symptoms = list(
            (
                await db.execute(
                    select(PatientSymptom)
                    .where(PatientSymptom.patient_id == patient.id)
                    .order_by(PatientSymptom.started_at.asc())
                )
            )
            .scalars()
            .all()
        )
        observations = list(
            (
                await db.execute(
                    select(HealthObservation)
                    .where(HealthObservation.patient_id == patient.id)
                    .order_by(HealthObservation.observed_at.asc())
                )
            )
            .scalars()
            .all()
        )
        events = list(
            (
                await db.execute(
                    select(HealthEvent)
                    .where(HealthEvent.patient_id == patient.id)
                    .order_by(HealthEvent.event_occurred_at.asc())
                )
            )
            .scalars()
            .all()
        )
        revisions = list(
            (
                await db.execute(
                    select(RecordRevision)
                    .where(RecordRevision.patient_id == patient.id)
                    .order_by(RecordRevision.created_at.asc())
                )
            )
            .scalars()
            .all()
        )
        documents = list(
            (
                await db.execute(
                    select(Document)
                    .where(Document.patient_id == patient.id)
                    .order_by(Document.uploaded_at.asc())
                )
            )
            .scalars()
            .all()
        )
        conversations = list(
            (
                await db.execute(
                    select(Conversation)
                    .where(Conversation.patient_id == patient.id)
                    .order_by(Conversation.created_at.asc())
                )
            )
            .scalars()
            .all()
        )
        messages = list(
            (
                await db.execute(
                    select(Message)
                    .where(Message.patient_id == patient.id)
                    .order_by(Message.created_at.asc())
                )
            )
            .scalars()
            .all()
        )
        summaries = list(
            (
                await db.execute(
                    select(HealthSummary)
                    .where(HealthSummary.patient_id == patient.id)
                    .order_by(HealthSummary.created_at.desc())
                )
            )
            .scalars()
            .all()
        )

        msgs_by_conv: dict[uuid.UUID, list[dict[str, Any]]] = defaultdict(list)
        for m in messages:
            msgs_by_conv[m.conversation_id].append(
                {
                    "id": str(m.id),
                    "role": m.role,
                    "content": m.content,
                    "safety_level": m.safety_level,
                    "cited_records": m.cited_records_json,
                    "clarifying_questions": m.clarifying_questions_json,
                    "proposed_action": m.proposed_action_json,
                    "created_at": _iso(m.created_at),
                }
            )

        conditions_out = [
            {
                "id": str(c.id),
                "name": c.name,
                "status": c.status,
                "severity": c.severity,
                "onset_date": _iso(c.onset_date),
                "resolved_date": _iso(c.resolved_date),
                "notes": c.notes,
                "source_type": c.source_type,
                "review_status": c.review_status,
                "source_document_id": str(c.source_document_id) if c.source_document_id else None,
                "is_archived": c.is_archived,
                "created_at": _iso(c.created_at),
            }
            for c in conditions
        ]
        allergies_out = [
            {
                "id": str(a.id),
                "allergen": a.allergen,
                "category": a.category,
                "reaction": a.reaction,
                "severity": a.severity,
                "status": a.status,
                "onset_date": _iso(a.onset_date),
                "notes": a.notes,
                "source_type": a.source_type,
                "review_status": a.review_status,
                "is_archived": a.is_archived,
                "created_at": _iso(a.created_at),
            }
            for a in allergies
        ]
        symptoms_out = [
            {
                "id": str(s.id),
                "name": s.name,
                "severity": s.severity,
                "frequency": s.frequency,
                "body_location": s.body_location,
                "status": s.status,
                "started_at": _iso(s.started_at),
                "ended_at": _iso(s.ended_at),
                "notes": s.notes,
                "source_type": s.source_type,
                "review_status": s.review_status,
                "is_archived": s.is_archived,
            }
            for s in symptoms
        ]
        observations_out = [
            {
                "id": str(o.id),
                "observation_type": o.observation_type,
                "display_name": o.display_name,
                "value_raw": o.value_raw,
                "unit_raw": o.unit_raw,
                "value_numeric": o.value_numeric,
                "value_normalized": o.value_normalized,
                "unit_normalized": o.unit_normalized,
                "reference_range_text": o.reference_range_text,
                "abnormality_flag": o.abnormality_flag,
                "observed_at": _iso(o.observed_at),
                "source_type": o.source_type,
                "review_status": o.review_status,
                "source_document_id": str(o.source_document_id) if o.source_document_id else None,
                "source_page": o.source_page,
                "is_archived": o.is_archived,
            }
            for o in observations
        ]
        events_out = [
            {
                "id": str(e.id),
                "event_category": e.event_category,
                "title": e.title,
                "summary": e.summary,
                "event_occurred_at": _iso(e.event_occurred_at),
                "source_type": e.source_type,
                "review_status": e.review_status,
                "related_entity_type": e.related_entity_type,
                "related_entity_id": str(e.related_entity_id) if e.related_entity_id else None,
            }
            for e in events
        ]
        revisions_out = [
            {
                "id": str(r.id),
                "entity_type": r.entity_type,
                "entity_id": str(r.entity_id),
                "revision_number": r.revision_number,
                "action": r.action,
                "previous_data": r.previous_data,
                "new_data": r.new_data,
                "reason": r.reason,
                "created_at": _iso(r.created_at),
            }
            for r in revisions
        ]
        # Strictly exclude internal file_path & stored_filename (SEC-009/SEC-015)
        documents_out = [
            {
                "id": str(d.id),
                "title": d.title,
                "original_filename": d.original_filename,
                "document_type": d.document_type,
                "mime_type": d.mime_type,
                "file_size_bytes": d.file_size_bytes,
                "sha256_hash": d.sha256_hash,
                "document_date": _iso(d.document_date),
                "page_count": d.page_count,
                "upload_status": d.upload_status,
                "review_status": d.review_status,
                "is_archived": d.is_archived,
                "uploaded_at": _iso(d.uploaded_at),
            }
            for d in documents
        ]
        conversations_out = [
            {
                "id": str(c.id),
                "title": c.title,
                "status": c.status,
                "is_archived": c.is_archived,
                "created_at": _iso(c.created_at),
                "last_message_at": _iso(c.last_message_at),
                "messages": msgs_by_conv.get(c.id, []),
            }
            for c in conversations
        ]
        summaries_out = [
            {
                "id": str(s.id),
                "window_days": s.window_days,
                "period_start": _iso(s.period_start),
                "period_end": _iso(s.period_end),
                "headline": s.headline,
                "summary_text": s.summary_text,
                "highlights": s.highlights_json,
                "notable_trends": s.notable_trends_json,
                "questions_for_doctor": s.questions_for_doctor_json,
                "metrics_snapshot": s.metrics_snapshot_json,
                "generation_mode": s.generation_mode,
                "created_at": _iso(s.created_at),
            }
            for s in summaries
        ]

        return PatientExportResponse(
            exported_at=datetime.now(UTC),
            account_email=user.email,
            profile=PatientProfileResponse.model_validate(patient),
            counts={
                "conditions": len(conditions_out),
                "allergies": len(allergies_out),
                "symptoms": len(symptoms_out),
                "observations": len(observations_out),
                "timeline_events": len(events_out),
                "record_revisions": len(revisions_out),
                "documents": len(documents_out),
                "conversations": len(conversations_out),
                "messages": len(messages),
                "health_summaries": len(summaries_out),
            },
            conditions=conditions_out,
            allergies=allergies_out,
            symptoms=symptoms_out,
            observations=observations_out,
            timeline_events=events_out,
            record_revisions=revisions_out,
            documents=documents_out,
            conversations=conversations_out,
            health_summaries=summaries_out,
        )

    @staticmethod
    async def delete_patient_account(
        db: AsyncSession,
        user: User,
        patient: PatientProfile,
        payload: AccountDeletionRequest,
        *,
        storage_root: Path | None = None,
    ) -> AccountDeletionResponse:
        """
        Verified cascading patient account erasure (SEC-016).
        Requires matching Argon2id password and explicit confirmation phrase.
        Wipes physical uploaded files on disk and removes all rows belonging to
        this patient across every database table without affecting any other user.
        """
        if payload.confirm_text.strip() != ACCOUNT_DELETION_CONFIRM_PHRASE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Confirmation text must exactly match "
                    f"'{ACCOUNT_DELETION_CONFIRM_PHRASE}'."
                ),
            )

        if not verify_password(payload.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid password. Account deletion aborted.",
            )

        # 1. Remove physical uploaded files inside storage_root safely (SEC-009/SEC-016)
        cfg = get_settings()
        root = (storage_root or Path(cfg.upload_dir)).resolve()
        docs = list(
            (
                await db.execute(
                    select(Document).where(Document.patient_id == patient.id)
                )
            )
            .scalars()
            .all()
        )
        files_removed = 0
        for doc in docs:
            if not doc.file_path:
                continue
            target = Path(doc.file_path)
            try:
                resolved = target.resolve()
                if resolved.is_relative_to(root) and resolved.is_file():
                    resolved.unlink(missing_ok=True)
                    files_removed += 1
            except OSError:
                logger.warning("account_deletion_file_cleanup_error", document_id=str(doc.id))

        # Remove patient upload subdirectory if empty
        patient_dir = (root / str(patient.id)).resolve()
        if patient_dir.is_relative_to(root) and patient_dir.is_dir():
            with contextlib.suppress(OSError):
                patient_dir.rmdir()

        # 2. Explicit child-to-parent DB erasure (guaranteed orphan-free on Postgres & SQLite)
        pid = patient.id
        uid = user.id

        await db.execute(delete(DocumentEmbedding).where(DocumentEmbedding.patient_id == pid))
        await db.execute(delete(DocumentChunk).where(DocumentChunk.patient_id == pid))
        await db.execute(delete(DocumentPage).where(DocumentPage.patient_id == pid))
        await db.execute(
            delete(DocumentProcessingJob).where(DocumentProcessingJob.patient_id == pid)
        )
        await db.execute(delete(RecordRevision).where(RecordRevision.patient_id == pid))
        await db.execute(delete(HealthEvent).where(HealthEvent.patient_id == pid))
        await db.execute(delete(HealthObservation).where(HealthObservation.patient_id == pid))
        await db.execute(delete(PatientSymptom).where(PatientSymptom.patient_id == pid))
        await db.execute(delete(PatientAllergy).where(PatientAllergy.patient_id == pid))
        await db.execute(delete(PatientCondition).where(PatientCondition.patient_id == pid))
        await db.execute(delete(Document).where(Document.patient_id == pid))
        await db.execute(delete(Message).where(Message.patient_id == pid))
        await db.execute(delete(Conversation).where(Conversation.patient_id == pid))
        await db.execute(delete(HealthSummary).where(HealthSummary.patient_id == pid))
        await db.execute(delete(AIInvocationLog).where(AIInvocationLog.patient_id == pid))
        await db.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == uid))
        await db.execute(delete(Session).where(Session.user_id == uid))
        await db.execute(delete(PatientProfile).where(PatientProfile.id == pid))
        await db.execute(delete(User).where(User.id == uid))
        await db.commit()

        logger.info("patient_account_deleted", files_removed=files_removed)
        return AccountDeletionResponse(
            deleted=True,
            deleted_at=datetime.now(UTC),
            files_removed=files_removed,
            message=(
                "Your account and all associated health records and files "
                "have been permanently deleted."
            ),
        )
