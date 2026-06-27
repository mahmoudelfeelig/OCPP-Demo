from __future__ import annotations

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(tags=["metadata"])


@router.get("/")
def root() -> dict[str, str]:
    settings = get_settings()
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
    }
