"""
Authentication API Endpoints (v1)
Handles registration, login, logout, session revocation, and password recovery.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from mediflow.core.config import get_settings
from mediflow.core.database import get_db
from mediflow.core.dependencies import SESSION_COOKIE_NAME, get_current_user
from mediflow.modules.auth.models import User
from mediflow.modules.auth.schemas import (
    AuthStatusResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from mediflow.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


def set_session_cookie(response: Response, raw_token: str) -> None:
    """Helper to attach the secure HttpOnly session cookie to the response."""
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=raw_token,
        max_age=settings.session_max_age_seconds,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    """Helper to clear the session cookie upon logout."""
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new patient account",
)
async def register(
    payload: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Create a new patient user and initial profile."""
    try:
        user, _ = await AuthService.register_patient_user(
            db=db,
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
        )
        return user
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/login",
    response_model=UserResponse,
    summary="Authenticate and establish server-managed session",
)
async def login(
    payload: UserLoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Verify credentials and establish a secure server-managed session.
    Sets HttpOnly session cookie on the response.
    """
    user = await AuthService.authenticate_user(
        db=db,
        email=payload.email,
        password=payload.password,
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None

    raw_token, _ = await AuthService.create_session(
        db=db,
        user_id=user.id,
        user_agent=user_agent,
        ip_address=ip_address,
    )

    set_session_cookie(response, raw_token)
    return user


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Log out and revoke current session",
)
async def logout(
    response: Response,
    mediflow_session: str | None = Cookie(None, alias=SESSION_COOKIE_NAME),
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Revoke active session and delete cookie (SEC-006)."""
    token = mediflow_session
    if not token and authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]

    if token:
        await AuthService.revoke_session(db, token)

    clear_session_cookie(response)
    return {"message": "Logged out successfully."}


@router.get(
    "/me",
    response_model=AuthStatusResponse,
    summary="Get current authentication status and user details",
)
async def get_me(
    mediflow_session: str | None = Cookie(None, alias=SESSION_COOKIE_NAME),
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Return identity and onboarding status for current session."""
    token = mediflow_session
    if not token and authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]

    if not token:
        return AuthStatusResponse(authenticated=False)

    resolved = await AuthService.validate_session(db, token)
    if not resolved:
        return AuthStatusResponse(authenticated=False)

    user, _ = resolved
    patient = user.patient_profile

    return AuthStatusResponse(
        authenticated=True,
        user=UserResponse.model_validate(user),
        patient_id=patient.id if patient else None,
        is_onboarded=patient.is_onboarded if patient else False,
    )


@router.post(
    "/sessions/revoke-all",
    summary="Revoke all active sessions for current user",
)
async def revoke_all_sessions(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Revoke all sessions across all devices for the authenticated user."""
    count = await AuthService.revoke_all_user_sessions(db, current_user.id)
    clear_session_cookie(response)
    return {
        "message": "All active sessions have been revoked.",
        "revoked_count": count,
    }


@router.post(
    "/password-reset/request",
    summary="Request a password recovery token",
)
async def request_password_reset(
    payload: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    Initiate password reset.
    Returns token in development/test response; in production this dispatches email.
    """
    token = await AuthService.create_password_reset_token(db, payload.email)
    # Always return a generic success message to prevent user enumeration
    response_data = {
        "message": (
            "If an account matches that email, password reset instructions have been generated."
        ),
    }
    if (settings.is_development or settings.app_env == "test") and token:
        response_data["dev_reset_token"] = token
    return response_data


@router.post(
    "/password-reset/confirm",
    summary="Confirm password reset with token",
)
async def confirm_password_reset(
    payload: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Reset account password using one-time token."""
    success = await AuthService.reset_password(
        db=db,
        raw_token=payload.token,
        new_password=payload.new_password,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset token is invalid, expired, or has already been used.",
        )
    return {
        "message": (
            "Password has been successfully updated. Please log in with your new password."
        )
    }
