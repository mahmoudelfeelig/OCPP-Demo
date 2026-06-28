from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.api.router import api_router
from app.core.config import get_settings, validate_production_settings
from app.core.logging import configure_logging
from app.core.observability import configure_tracing
from app.core.middleware import RequestIDMiddleware
from app.db.session import SessionLocal
from app.services.bootstrap import bootstrap_admin_user, configure_station_tokens
from app.services.demo import seed_demo_data

configure_logging()
configure_tracing()

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_production_settings(settings)
    db: Session = SessionLocal()
    try:
        if settings.seed_demo_data and settings.app_env != "test":
            seed_demo_data(db)
        if settings.app_env != "test":
            bootstrap_admin_user(db, settings)
            configure_station_tokens(db, settings)
        yield
    finally:
        db.close()


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)
