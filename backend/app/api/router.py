from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import admin, auth, health, metadata, ocpp, partner, resources, system

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(metadata.router)
api_router.include_router(resources.router, tags=["resources"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(system.router, tags=["system"])
api_router.include_router(ocpp.router, tags=["ocpp"])
api_router.include_router(partner.router, tags=["partner"])
api_router.include_router(admin.router)
