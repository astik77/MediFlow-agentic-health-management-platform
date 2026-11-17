"""
Authentication Pydantic Request & Response Schemas
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegisterRequest(BaseModel):
    """Payload required to register a new patient user."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128, description="Minimum 8 characters")
    full_name: str = Field(..., min_length=1, max_length=255)


class UserLoginRequest(BaseModel):
    """Payload to authenticate an existing user."""

    email: EmailStr
    password: str = Field(..., min_length=1)


class PasswordResetRequest(BaseModel):
    """Payload to request a password reset token."""

    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Payload to finalize password reset using a valid token."""

    token: str = Field(..., min_length=16, description="Opaque password reset token")
    new_password: str = Field(..., min_length=8, max_length=128)


class SessionInfo(BaseModel):
    """Public representation of an active session."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    expires_at: datetime
    created_at: datetime
    is_revoked: bool
    user_agent: str | None = None
    ip_address: str | None = None


class UserResponse(BaseModel):
    """Public representation of a user identity."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    is_active: bool
    is_verified: bool
    created_at: datetime


class AuthStatusResponse(BaseModel):
    """Status payload returned on authentication check."""

    authenticated: bool
    user: UserResponse | None = None
    patient_id: uuid.UUID | None = None
    is_onboarded: bool = False
