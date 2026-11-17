"""
Conversations & AI Health Assistant Pydantic Schemas (Phase 6).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

SafetyLevel = Literal["normal", "boundary_refusal", "emergency_escalation"]
ProposalDecision = Literal["accept", "dismiss"]


class ConversationCreateRequest(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)


class MessageSendRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)


class ProposalDecisionRequest(BaseModel):
    decision: ProposalDecision
    name: str | None = Field(None, min_length=1, max_length=255)
    severity: Literal["mild", "moderate", "severe"] | None = None
    body_location: str | None = Field(None, max_length=150)
    notes: str | None = Field(None, max_length=500)


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    patient_id: uuid.UUID
    role: str
    content: str
    safety_level: str
    cited_records_json: list[dict[str, Any]] | None
    clarifying_questions_json: list[str] | None
    proposed_action_json: dict[str, Any] | None
    metadata_json: dict[str, Any] | None
    created_at: datetime


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    title: str
    status: str
    is_archived: bool
    last_message_at: datetime
    created_at: datetime
    updated_at: datetime


class ConversationDetailResponse(BaseModel):
    conversation: ConversationResponse
    messages: list[MessageResponse]


class MessageTurnResponse(BaseModel):
    conversation: ConversationResponse
    user_message: MessageResponse
    assistant_message: MessageResponse
