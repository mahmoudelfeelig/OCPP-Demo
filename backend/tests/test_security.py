from __future__ import annotations

from app.core.security import hash_password, verify_password


def test_password_hash_roundtrip() -> None:
    hashed = hash_password("secret123")
    assert verify_password("secret123", hashed)
    assert not verify_password("wrong", hashed)

