"""
Conversations & Messages Database Models (Phase 6).
Strictly scoped to patient_id on both conversations and messages for
defense-in-depth cross-patient isolation (SEC-001/SEC-002).
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from mediflow.core.database import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class Conversation(Base):
    """Patient-scoped conversational thread with the MEDIFLOW AI Health Assistant."""

    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("patient_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(255), default="New Health Conversation", nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(32), default="active", nullable=False
    )  # active | archived
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    last_message_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class Message(Base):
    """
    Individual message inside a patient conversation.
    Stores safety triage classification, record citations, clarifying questions,
    and optional proposal-only symptom drafts (never silently committed).
    """

    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("patient_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user | assistant | system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    safety_level: Mapped[str] = mapped_column(
        String(32), default="normal", nullable=False
    )  # normal | boundary_refusal | emergency_escalation
    cited_records_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    clarifying_questions_json: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    proposed_action_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )


Index(
    "ix_conversations_patient_last_msg",
    Conversation.patient_id,
    Conversation.last_message_at.desc(),
)
Index(
    "ix_messages_conv_created",
    Message.conversation_id,
    Message.created_at.asc(),
)
