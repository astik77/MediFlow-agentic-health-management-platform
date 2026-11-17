"""
MediFlow Core Security Utilities
Provides Argon2id password hashing, verification, and cryptographic token management.
"""
from __future__ import annotations

import hashlib
import secrets
from typing import NamedTuple

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from mediflow.core.config import get_settings

settings = get_settings()

# Initialize Argon2id password hasher with configured parameters
_ph = PasswordHasher(
    time_cost=settings.argon2_time_cost,
    memory_cost=settings.argon2_memory_cost,
    parallelism=settings.argon2_parallelism,
    hash_len=32,
    salt_len=16,
)


class GeneratedSessionToken(NamedTuple):
    raw_token: str
    token_hash: str


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    return _ph.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against an Argon2id hash."""
    try:
        return _ph.verify(hashed_password, password)
    except (VerifyMismatchError, Exception):
        return False


def needs_rehash(hashed_password: str) -> bool:
    """Check if the password hash needs to be upgraded to newer parameters."""
    return _ph.check_needs_rehash(hashed_password)


def generate_session_token() -> GeneratedSessionToken:
    """
    Generate an opaque 256-bit cryptographic session token and its SHA-256 hash.
    The raw token is returned to the client in an HttpOnly cookie.
    Only the SHA-256 hash is persisted in the database.
    """
    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_session_token(raw_token)
    return GeneratedSessionToken(raw_token=raw_token, token_hash=token_hash)


def hash_session_token(raw_token: str) -> str:
    """Compute the SHA-256 hash of a session token."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def generate_password_reset_token() -> GeneratedSessionToken:
    """Generate an opaque token and hash for password recovery."""
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    return GeneratedSessionToken(raw_token=raw_token, token_hash=token_hash)
