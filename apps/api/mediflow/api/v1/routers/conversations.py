"""
Conversations & AI Health Assistant API Router (v1).
All routes require authentication (401) and enforce patient ownership (403).
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from mediflow.core.database import get_db
from mediflow.core.dependencies import get_current_patient
from mediflow.modules.conversations.schemas import (
    ConversationCreateRequest,
    ConversationDetailResponse,
    ConversationResponse,
    MessageResponse,
    MessageSendRequest,
    MessageTurnResponse,
    ProposalDecisionRequest,
)
from mediflow.modules.conversations.service import ConversationService
from mediflow.modules.patients.models import PatientProfile

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post(
    "",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new AI Health Assistant conversation",
)
async def create_conversation(
    payload: ConversationCreateRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_patient: PatientProfile = Depends(get_current_patient),
) -> ConversationResponse:
    conv = await ConversationService.create_conversation(
        db, current_patient, payload or ConversationCreateRequest(title=None)
    )
    return ConversationResponse.model_validate(conv)


@router.get(
    "",
    response_model=list[ConversationResponse],
    summary="List authenticated patient's conversations",
)
async def list_conversations(
    include_archived: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    current_patient: PatientProfile = Depends(get_current_patient),
) -> list[ConversationResponse]:
    rows = await ConversationService.list_conversations(
        db, current_patient, include_archived=include_archived
    )
    return [ConversationResponse.model_validate(c) for c in rows]


@router.get(
    "/{conversation_id}",
    response_model=ConversationDetailResponse,
    summary="Get conversation with full message history",
)
async def get_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_patient: PatientProfile = Depends(get_current_patient),
) -> ConversationDetailResponse:
    conv, msgs = await ConversationService.get_conversation_detail(
        db, conversation_id, current_patient
    )
    return ConversationDetailResponse(
        conversation=ConversationResponse.model_validate(conv),
        messages=[MessageResponse.model_validate(m) for m in msgs],
    )


@router.delete(
    "/{conversation_id}",
    response_model=ConversationResponse,
    summary="Soft-archive a conversation",
)
async def archive_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_patient: PatientProfile = Depends(get_current_patient),
) -> ConversationResponse:
    conv = await ConversationService.archive_conversation(
        db, conversation_id, current_patient
    )
    return ConversationResponse.model_validate(conv)


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageTurnResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send a patient message and receive a safety-checked AI Health Assistant reply",
)
async def send_message(
    conversation_id: uuid.UUID,
    payload: MessageSendRequest,
    db: AsyncSession = Depends(get_db),
    current_patient: PatientProfile = Depends(get_current_patient),
) -> MessageTurnResponse:
    conv, user_msg, asst_msg = await ConversationService.send_message(
        db, conversation_id, current_patient, payload
    )
    return MessageTurnResponse(
        conversation=ConversationResponse.model_validate(conv),
        user_message=MessageResponse.model_validate(user_msg),
        assistant_message=MessageResponse.model_validate(asst_msg),
    )


@router.post(
    "/{conversation_id}/messages/{message_id}/proposal",
    response_model=MessageResponse,
    summary="Accept or dismiss an AI-proposed symptom draft",
)
async def resolve_message_proposal(
    conversation_id: uuid.UUID,
    message_id: uuid.UUID,
    payload: ProposalDecisionRequest,
    db: AsyncSession = Depends(get_db),
    current_patient: PatientProfile = Depends(get_current_patient),
) -> MessageResponse:
    msg = await ConversationService.resolve_proposal(
        db, conversation_id, message_id, current_patient, payload
    )
    return MessageResponse.model_validate(msg)
