"""
Authentication Domain Services
Handles user registration, credential verification, session creation, and lifecycle management.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from mediflow.core.config import get_settings
from mediflow.core.security import (
    generate_password_reset_token,
    generate_session_token,
    hash_password,
    hash_session_token,
    needs_rehash,
    verify_password,
)
from mediflow.modules.auth.models import PasswordResetToken, Session, User
from mediflow.modules.patients.models import PatientProfile

settings = get_settings()


class AuthService:
    """Encapsulates authentication, session, and recovery business logic."""

    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
        """Query an active user by normalized email address."""
        stmt = (
            select(User)
            .options(selectinload(User.patient_profile))
            .where(User.email == email.lower().strip())
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
        """Query a user by primary key."""
        stmt = (
            select(User)
            .options(selectinload(User.patient_profile))
            .where(User.id == user_id)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def register_patient_user(
        db: AsyncSession,
        email: str,
        password: str,
        full_name: str,
    ) -> tuple[User, PatientProfile]:
        """
        Register a new patient account with an associated initial patient profile.
        Raises ValueError if the email is already registered.
        """
        normalized_email = email.lower().strip()
        existing = await AuthService.get_user_by_email(db, normalized_email)
        if existing:
            raise ValueError("An account with this email address already exists.")

        hashed_pw = hash_password(password)

        new_user = User(
            email=normalized_email,
            password_hash=hashed_pw,
            is_active=True,
            is_verified=False,
        )
        db.add(new_user)
        await db.flush()  # Generates new_user.id

        new_profile = PatientProfile(
            user_id=new_user.id,
            full_name=full_name.strip(),
            is_onboarded=False,
        )
        db.add(new_profile)
        await db.commit()
        await db.refresh(new_user)
        await db.refresh(new_profile)

        return new_user, new_profile

    @staticmethod
    async def authenticate_user(
        db: AsyncSession,
        email: str,
        password: str,
    ) -> User | None:
        """
        Verify credentials. If valid, check for rehash need and return the user.
        Returns None if user is not found, inactive, or password does not match.
        """
        user = await AuthService.get_user_by_email(db, email)
        if not user or not user.is_active:
            return None

        if not verify_password(password, user.password_hash):
            return None

        # Opportunistic upgrade if Argon2id parameters changed
        if needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)
            await db.commit()

        return user

    @staticmethod
    async def create_session(
        db: AsyncSession,
        user_id: uuid.UUID,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[str, Session]:
        """
        Create a new server-managed session.
        Returns (raw_session_token, session_record).
        """
        generated = generate_session_token()
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=settings.session_max_age_seconds)

        session = Session(
            user_id=user_id,
            session_token_hash=generated.token_hash,
            expires_at=expires_at,
            is_revoked=False,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

        return generated.raw_token, session

    @staticmethod
    async def validate_session(
        db: AsyncSession,
        raw_token: str,
    ) -> tuple[User, Session] | None:
        """
        Validate a raw session token against stored hashes.
        Returns (User, Session) if active and non-expired, else None.
        """
        if not raw_token:
            return None

        token_hash = hash_session_token(raw_token)
        stmt = (
            select(Session)
            .options(
                selectinload(Session.user).selectinload(User.patient_profile)
            )
            .where(
                Session.session_token_hash == token_hash,
                Session.is_revoked.is_(False),
            )
        )
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()

        if not session or not session.is_valid:
            return None

        user = session.user
        if not user or not user.is_active:
            return None

        return user, session

    @staticmethod
    async def revoke_session(db: AsyncSession, raw_token: str) -> bool:
        """Mark a single session as revoked (SEC-006)."""
        if not raw_token:
            return False

        token_hash = hash_session_token(raw_token)
        stmt = (
            update(Session)
            .where(Session.session_token_hash == token_hash)
            .values(is_revoked=True)
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount > 0

    @staticmethod
    async def revoke_all_user_sessions(db: AsyncSession, user_id: uuid.UUID) -> int:
        """Revoke all active sessions belonging to a user."""
        stmt = (
            update(Session)
            .where(Session.user_id == user_id, Session.is_revoked.is_(False))
            .values(is_revoked=True)
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount

    @staticmethod
    async def create_password_reset_token(
        db: AsyncSession,
        email: str,
    ) -> str | None:
        """
        Create a one-time password reset token for the given user email.
        Returns the raw token string (for delivery) if user exists, else None.
        """
        user = await AuthService.get_user_by_email(db, email)
        if not user or not user.is_active:
            return None

        generated = generate_password_reset_token()
        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=1)  # 1-hour expiration

        token_record = PasswordResetToken(
            user_id=user.id,
            token_hash=generated.token_hash,
            expires_at=expires_at,
            is_used=False,
        )
        db.add(token_record)
        await db.commit()

        return generated.raw_token

    @staticmethod
    async def reset_password(
        db: AsyncSession,
        raw_token: str,
        new_password: str,
    ) -> bool:
        """
        Reset user password using a valid one-time recovery token.
        Revokes all existing user sessions upon password reset for security.
        """
        token_hash = hash_session_token(raw_token)
        stmt = (
            select(PasswordResetToken)
            .options(selectinload(PasswordResetToken.user))
            .where(
                PasswordResetToken.token_hash == token_hash,
                PasswordResetToken.is_used.is_(False),
            )
        )
        result = await db.execute(stmt)
        token_record = result.scalar_one_or_none()

        if not token_record or not token_record.is_valid:
            return False

        user = token_record.user
        if not user or not user.is_active:
            return False

        # Update password
        user.password_hash = hash_password(new_password)
        token_record.is_used = True

        # Invalidate all active sessions for security
        await AuthService.revoke_all_user_sessions(db, user.id)

        await db.commit()
        return True
