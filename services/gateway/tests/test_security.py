"""Auth primitives: password hashing round-trips and JWTs verify."""
from __future__ import annotations

import jwt
import pytest

from app.config import settings
from app.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip() -> None:
    hashed = hash_password("hunter2")
    assert hashed != "hunter2"                  # never stored in plaintext
    assert verify_password("hunter2", hashed)
    assert not verify_password("wrong", hashed)


def test_jwt_roundtrip_returns_subject() -> None:
    token = create_access_token("demo")
    assert decode_access_token(token) == "demo"


def test_tampered_token_is_rejected() -> None:
    token = create_access_token("demo")
    forged = jwt.encode({"sub": "attacker"}, "not-the-secret", algorithm=settings.jwt_algorithm)
    assert decode_access_token(token) == "demo"
    with pytest.raises(jwt.PyJWTError):
        decode_access_token(forged)
