from __future__ import annotations

from functools import lru_cache
import json

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ocpp-backend-demo"
    app_version: str = "0.1.0"
    app_env: str = "development"
    seed_demo_data: bool = Field(default=False)
    database_url: str = Field(default="postgresql+psycopg://ocpp_demo:ocpp_demo@postgres:5432/ocpp_demo")
    redis_url: str = Field(default="redis://redis:6379/0")
    otel_exporter_otlp_endpoint: str = Field(default="http://otel-collector:4318")
    station_heartbeat_timeout_seconds: int = Field(default=600)
    jwt_secret: str = Field(default="change-me")
    jwt_issuer: str = Field(default="ocpp-backend-demo")
    jwt_audience: str = Field(default="ocpp-backend-demo-web")
    partner_webhook_secret: str = Field(default="change-me")
    admin_bootstrap_email: str | None = Field(default=None)
    admin_bootstrap_password: str | None = Field(default=None)
    ocpp_station_tokens: str | None = Field(default=None)

    def station_tokens(self) -> dict[str, str]:
        if not self.ocpp_station_tokens:
            return {}
        parsed = json.loads(self.ocpp_station_tokens)
        if not isinstance(parsed, dict) or not all(
            isinstance(key, str) and isinstance(value, str) for key, value in parsed.items()
        ):
            raise ValueError("OCPP_STATION_TOKENS must be a JSON object of station identifiers to tokens")
        return parsed


def validate_production_settings(settings: Settings) -> None:
    if settings.app_env != "production":
        return
    insecure = []
    if settings.jwt_secret == "change-me" or len(settings.jwt_secret) < 32:
        insecure.append("JWT_SECRET")
    if settings.partner_webhook_secret == "change-me" or len(settings.partner_webhook_secret) < 32:
        insecure.append("PARTNER_WEBHOOK_SECRET")
    if insecure:
        raise RuntimeError(f"Production secrets must be changed and contain at least 32 characters: {', '.join(insecure)}")


@lru_cache
def get_settings() -> Settings:
    return Settings()
