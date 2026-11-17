"""
MediFlow Core API Dependencies
Provides authentication, session resolution, and patient ownership authorization checks.
"""
from __future__ import annotations

import uuid

from fastapi import Cookie, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from mediflow.core.database import get_db
from mediflow.modules.auth.models import User
from mediflow.modules.auth.service import AuthService
from mediflow.modules.patients.models import PatientProfile

SESSION_COOKIE_NAME = "mediflow_session"


async def get_current_user(
    mediflow_session: str | None = Cookie(None, alias=SESSION_COOKIE_NAME),
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    FastAPI dependency: Resolves and validates the authenticated user.
    Prefers the secure HttpOnly cookie `mediflow_session`.
    Falls back to `Authorization: Bearer <token>` for API test clients.
    Raises HTTP 401 Unauthorized if the session is invalid, expired, or revoked (SEC-004, SEC-005).
    """
    token: str | None = mediflow_session

    if not token and authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    resolved = await AuthService.validate_session(db, token)
    if not resolved:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired or is invalid. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user, _ = resolved
    return user


async def get_current_patient(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PatientProfile:
    """
    FastAPI dependency: Resolves the PatientProfile attached to the authenticated user.
    Raises HTTP 404 if no profile is found.
    """
    if current_user.patient_profile:
        return current_user.patient_profile

    # Defensive fallback query if relationship was not loaded
    from mediflow.modules.patients.service import PatientService

    profile = await PatientService.get_by_user_id(db, current_user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient profile not found for authenticated user.",
        )
    return profile


def enforce_patient_ownership(
    target_patient_id: uuid.UUID,
    authenticated_patient: PatientProfile,
) -> None:
    """
    Security check: Strictly enforces that the requested resource belongs to the
    currently authenticated patient identity (SEC-001, SEC-002).
    Never trusts client-provided patient identifiers.
    Raises HTTP 403 Forbidden on mismatch.
    """
    if target_patient_id != authenticated_patient.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You are not authorized to view or modify this patient record.",
        )
