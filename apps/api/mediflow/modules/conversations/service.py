"""
Conversations Service (Phase 6).
Manages patient-scoped conversations, AI Health Assistant message turns,
strict ownership enforcement (SEC-001/SEC-002), and patient-confirmed symptom proposals.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mediflow.ai.agents.health_assistant import HealthAssistantAgent
from mediflow.core.dependencies import enforce_patient_ownership
from mediflow.modules.conversations.models import Conversation, Message
from mediflow.modules.conversations.schemas import (
    ConversationCreateRequest,
    MessageSendRequest,
    ProposalDecisionRequest,
)
from mediflow.modules.health_records.models import HealthEvent, PatientSymptom
from mediflow.modules.health_records.service import (
    SYMPTOM_FIELDS,
    HealthRecordsService,
    _serialize_snapshot,
)
from mediflow.modules.patients.models import PatientProfile


def _utc_now() -> datetime:
    return datetime.now(UTC)


import re

def _auto_title(first_message: str, symptom_name: str | None = None) -> str:
    if symptom_name:
        return f"{symptom_name.strip().title()} Discussion"
    cleaned = " ".join(first_message.strip().split())
    lower = cleaned.lower()
    for prefix in (
        "can you tell me about",
        "could you tell me about",
        "what do you think about",
        "what does it mean if",
        "i have had a",
        "i have been having a",
        "i've had a",
        "i've been having",
        "i have a",
        "i am having",
        "i feel like",
        "i'm having",
        "tell me about",
        "please explain",
        "what are the",
        "why do i have",
        "how to treat",
        "help with",
    ):
        if lower.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
            cleaned = re.sub(r"^(a|an|the|my|some)\s+", "", cleaned, flags=re.IGNORECASE).strip()
            break

    title = cleaned.strip("?.! ").title()
    if not title:
        title = "Health Consultation"
    if len(title) > 60:
        title = title[:57].rstrip() + "..."
    return title


class ConversationService:
    """Domain service for patient-scoped AI Health Assistant conversations."""

    @staticmethod
    async def _get_owned_conversation(
        db: AsyncSession, conversation_id: uuid.UUID, patient: PatientProfile
    ) -> Conversation:
        conv = (
            await db.execute(select(Conversation).where(Conversation.id == conversation_id))
        ).scalar_one_or_none()
        if conv is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found.",
            )
        enforce_patient_ownership(conv.patient_id, patient)
        return conv

    @staticmethod
    async def create_conversation(
        db: AsyncSession,
        patient: PatientProfile,
        payload: ConversationCreateRequest,
    ) -> Conversation:
        now = _utc_now()
        conv = Conversation(
            id=uuid.uuid4(),
            patient_id=patient.id,
            title=(payload.title or "New Health Conversation").strip()[:255],
            status="active",
            is_archived=False,
            last_message_at=now,
        )
        db.add(conv)
        await db.commit()
        await db.refresh(conv)
        return conv

    @staticmethod
    async def list_conversations(
        db: AsyncSession,
        patient: PatientProfile,
        *,
        include_archived: bool = False,
    ) -> list[Conversation]:
        stmt = select(Conversation).where(Conversation.patient_id == patient.id)
        if not include_archived:
            stmt = stmt.where(Conversation.is_archived.is_(False))
        stmt = stmt.order_by(Conversation.last_message_at.desc())
        rows = (await db.execute(stmt)).scalars().all()
        return list(rows)

    @staticmethod
    async def get_conversation_detail(
        db: AsyncSession,
        conversation_id: uuid.UUID,
        patient: PatientProfile,
    ) -> tuple[Conversation, list[Message]]:
        conv = await ConversationService._get_owned_conversation(db, conversation_id, patient)
        msgs = list(
            (
                await db.execute(
                    select(Message)
                    .where(
                        Message.conversation_id == conv.id,
                        Message.patient_id == patient.id,
                    )
                    .order_by(Message.created_at.asc())
                )
            )
            .scalars()
            .all()
        )
        return conv, msgs

    @staticmethod
    async def archive_conversation(
        db: AsyncSession,
        conversation_id: uuid.UUID,
        patient: PatientProfile,
    ) -> Conversation:
        conv = await ConversationService._get_owned_conversation(db, conversation_id, patient)
        if conv.is_archived:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Conversation is already archived.",
            )
        conv.is_archived = True
        conv.status = "archived"
        await db.commit()
        await db.refresh(conv)
        return conv

    @staticmethod
    async def send_message(
        db: AsyncSession,
        conversation_id: uuid.UUID,
        patient: PatientProfile,
        payload: MessageSendRequest,
    ) -> tuple[Conversation, Message, Message]:
        conv = await ConversationService._get_owned_conversation(db, conversation_id, patient)
        if conv.is_archived:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot post messages to an archived conversation.",
            )

        # Load prior turns for conversational memory
        prior_msgs = list(
            (
                await db.execute(
                    select(Message)
                    .where(
                        Message.conversation_id == conv.id,
                        Message.patient_id == patient.id,
                    )
                    .order_by(Message.created_at.asc())
                )
            )
            .scalars()
            .all()
        )
        history_turns = [(m.role, m.content) for m in prior_msgs]

        user_msg = Message(
            id=uuid.uuid4(),
            conversation_id=conv.id,
            patient_id=patient.id,
            role="user",
            content=payload.content.strip(),
            safety_level="normal",
        )
        db.add(user_msg)
        await db.flush()

        # Run safety triage + patient-scoped tools + AI Health Assistant
        turn = await HealthAssistantAgent.respond(
            db=db,
            patient=patient,
            user_message=user_msg.content,
            history_turns=history_turns,
        )

        assistant_msg = Message(
            id=uuid.uuid4(),
            conversation_id=conv.id,
            patient_id=patient.id,
            role="assistant",
            content=turn.content,
            safety_level=turn.safety_level,
            cited_records_json=turn.cited_records or None,
            clarifying_questions_json=turn.clarifying_questions or None,
            proposed_action_json=turn.proposed_action,
            metadata_json=turn.metadata or None,
        )
        db.add(assistant_msg)
        conv.last_message_at = _utc_now()

        # Auto-title new conversations smartly
        if not prior_msgs and conv.title in ("New Health Conversation", ""):
            sym_name = None
            if turn.proposed_action and isinstance(turn.proposed_action, dict):
                sym_name = turn.proposed_action.get("payload", {}).get("name")
            conv.title = _auto_title(payload.content, sym_name)

        await db.commit()
        await db.refresh(conv)
        await db.refresh(user_msg)
        await db.refresh(assistant_msg)
        return conv, user_msg, assistant_msg

    @staticmethod
    async def resolve_proposal(
        db: AsyncSession,
        conversation_id: uuid.UUID,
        message_id: uuid.UUID,
        patient: PatientProfile,
        payload: ProposalDecisionRequest,
    ) -> Message:
        """
        Patient explicitly accepts or dismisses an AI-proposed symptom draft.
        Zero silent writes: symptom records are only created when the patient approves.
        """
        conv = await ConversationService._get_owned_conversation(db, conversation_id, patient)

        msg = (
            await db.execute(select(Message).where(Message.id == message_id))
        ).scalar_one_or_none()
        if msg is None or msg.conversation_id != conv.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found in this conversation.",
            )
        enforce_patient_ownership(msg.patient_id, patient)

        proposal: dict[str, Any] | None = msg.proposed_action_json
        if not proposal or proposal.get("proposal_type") != "symptom":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This message does not contain an actionable symptom proposal.",
            )
        if proposal.get("status") != "pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Proposal has already been resolved ({proposal.get('status')}).",
            )

        updated_proposal = dict(proposal)
        draft = dict(proposal.get("payload") or {})

        if payload.decision == "dismiss":
            updated_proposal["status"] = "dismissed"
            msg.proposed_action_json = updated_proposal
            await db.commit()
            await db.refresh(msg)
            return msg

        # Accept: create confirmed PatientSymptom with ai_proposed provenance + audit trail
        sym_name = (payload.name or draft.get("name") or "Reported Symptom").strip()[:255]
        sym_sev = payload.severity or draft.get("severity") or "moderate"
        sym_loc = (
            payload.body_location
            if payload.body_location is not None
            else draft.get("body_location")
        )
        sym_notes = payload.notes if payload.notes is not None else draft.get("notes")

        symptom = PatientSymptom(
            id=uuid.uuid4(),
            patient_id=patient.id,
            name=sym_name,
            severity=sym_sev,
            body_location=sym_loc,
            frequency=draft.get("frequency"),
            status="ongoing",
            started_at=_utc_now(),
            notes=sym_notes,
            source_type="ai_proposed",
            review_status="confirmed",
            is_archived=False,
        )
        db.add(symptom)
        await db.flush()

        await HealthRecordsService._record_revision(
            db,
            patient_id=patient.id,
            user_id=patient.user_id,
            entity_type="symptom",
            entity_id=symptom.id,
            action="created",
            previous_data=None,
            new_data=_serialize_snapshot(symptom, SYMPTOM_FIELDS),
            reason="Patient confirmed AI-proposed symptom draft from Health Assistant",
        )

        db.add(
            HealthEvent(
                patient_id=patient.id,
                event_category="symptom",
                title=f"Symptom logged: {symptom.name} ({symptom.severity})",
                summary="Confirmed from AI Health Assistant conversation.",
                event_occurred_at=symptom.started_at,
                source_type="ai_proposed",
                review_status="confirmed",
                related_entity_type="symptom",
                related_entity_id=symptom.id,
                metadata_json={"conversation_id": str(conv.id), "message_id": str(msg.id)},
            )
        )

        updated_proposal["status"] = "saved"
        updated_proposal["saved_entity_id"] = str(symptom.id)
        msg.proposed_action_json = updated_proposal

        await db.commit()
        await db.refresh(msg)
        return msg
