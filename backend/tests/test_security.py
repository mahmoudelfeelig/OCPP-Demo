from __future__ import annotations

import pytest

from app.core.config import Settings, validate_production_settings
from app.core.security import hash_password, hash_station_token, verify_password, verify_station_token


def test_password_hash_roundtrip() -> None:
    hashed = hash_password("secret123")
    assert verify_password("secret123", hashed)
    assert not verify_password("wrong", hashed)


def test_station_token_hash_roundtrip() -> None:
    token = "station-token-with-at-least-32-characters"
    hashed = hash_station_token(token)

    assert hashed != token
    assert verify_station_token(token, hashed)
    assert not verify_station_token("wrong-token", hashed)
    assert not verify_station_token(token, None)


def test_production_rejects_default_or_short_secrets() -> None:
    with pytest.raises(RuntimeError, match="JWT_SECRET.*PARTNER_WEBHOOK_SECRET"):
        validate_production_settings(
            Settings(
                app_env="production",
                jwt_secret="change-me",
                partner_webhook_secret="short",
            )
        )


def test_production_accepts_strong_secrets() -> None:
    validate_production_settings(
        Settings(
            app_env="production",
            jwt_secret="j" * 32,
            partner_webhook_secret="w" * 32,
        )
    )
