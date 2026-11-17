"""
Patient Profile Database Models
Defines the PatientProfile entity for baseline demographics and clinical context.
"""
from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from mediflow.core.database import Base

if TYPE_CHECKING:
    from mediflow.modules.auth.models import User


def utc_now() -> datetime:
    """Return the current UTC datetime."""
    return datetime.now(UTC)


class PatientProfile(Base):
    """
    Patient Profile entity.
    Stores patient demographics, baselines, and emergency contact details.
    """

    __tablename__ = "patient_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    date_of_birth: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    biological_sex: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    blood_group: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )
    height_cm: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    weight_kg: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    emergency_contact: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    medical_baseline: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    is_onboarded: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    # Relationships
    user: Mapped[User] = relationship(
        "User",
        back_populates="patient_profile",
    )

    def __repr__(self) -> str:
        return f"<PatientProfile id={self.id} user_id={self.user_id} name='{self.full_name}'>"
