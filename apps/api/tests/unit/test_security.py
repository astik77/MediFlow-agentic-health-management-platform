"""
Unit tests for cryptographic security utilities (Argon2id and Session tokens).
"""
from __future__ import annotations

import hashlib

from mediflow.core.security import (
    generate_password_reset_token,
    generate_session_token,
    hash_password,
    hash_session_token,
    needs_rehash,
    verify_password,
)


class TestArgon2PasswordHashing:
    def test_hash_password_produces_argon2id_hash(self) -> None:
        pw = "MySecurePassword123!"
        hashed = hash_password(pw)
        assert hashed.startswith("$argon2id$")
        assert len(hashed) > 50

    def test_verify_password_returns_true_for_matching_password(self) -> None:
        pw = "CorrectHorseBatteryStaple!"
        hashed = hash_password(pw)
        assert verify_password(pw, hashed) is True

    def test_verify_password_returns_false_for_wrong_password(self) -> None:
        pw = "CorrectHorseBatteryStaple!"
        hashed = hash_password(pw)
        assert verify_password("WrongPassword123!", hashed) is False

    def test_verify_password_handles_empty_and_garbage_hash(self) -> None:
        assert verify_password("password", "") is False
        assert verify_password("password", "invalid_hash_format") is False

    def test_needs_rehash_returns_false_for_fresh_hash(self) -> None:
        hashed = hash_password("CurrentParametersPassword")
        assert needs_rehash(hashed) is False


class TestSessionTokenUtilities:
    def test_generate_session_token_produces_opaque_raw_and_sha256_hash(self) -> None:
        token = generate_session_token()
        assert len(token.raw_token) >= 32
        assert len(token.token_hash) == 64  # SHA-256 hex digest length

        # Verify hash correspondence
        expected_hash = hashlib.sha256(token.raw_token.encode("utf-8")).hexdigest()
        assert token.token_hash == expected_hash

    def test_hash_session_token_is_deterministic(self) -> None:
        raw = "test_raw_opaque_session_token_12345"
        h1 = hash_session_token(raw)
        h2 = hash_session_token(raw)
        assert h1 == h2
        assert len(h1) == 64

    def test_generate_password_reset_token_produces_valid_pair(self) -> None:
        reset_token = generate_password_reset_token()
        assert len(reset_token.raw_token) >= 32
        assert len(reset_token.token_hash) == 64
        expected = hashlib.sha256(reset_token.raw_token.encode("utf-8")).hexdigest()
        assert reset_token.token_hash == expected
