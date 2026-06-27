from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ocpp-backend-demo"
    app_version: str = "0.1.0"
    app_env: str = "development"
    database_url: str = Field(default="postgresql+psycopg://ocpp_demo:ocpp_demo@postgres:5432/ocpp_demo")
    redis_url: str = Field(default="redis://redis:6379/0")
    otel_exporter_otlp_endpoint: str = Field(default="http://otel-collector:4318")
    jwt_secret: str = Field(default="change-me")
    jwt_issuer: str = Field(default="ocpp-backend-demo")
    jwt_audience: str = Field(default="ocpp-backend-demo-web")
    partner_webhook_secret: str = Field(default="change-me")


@lru_cache
def get_settings() -> Settings:
    return Settings()
