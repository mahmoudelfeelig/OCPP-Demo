from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter
from sqlalchemy import func, select, text
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from app.db.session import get_session
from app.core.metrics import active_sessions, connected_stations, worker_lag_seconds
from app.models.entities import ChargingSession, OcppMessage, OutboxEvent, Station
from app.services.cache import cache_status

router = APIRouter(prefix="/metrics")


@router.get("", include_in_schema=False)
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.get("/status")
async def status() -> dict[str, str]:
    db = get_session()
    try:
        connected_count = db.scalar(select(func.count()).select_from(Station).where(Station.online.is_(True))) or 0
        session_count = db.scalar(select(func.count()).select_from(ChargingSession).where(ChargingSession.state == "active")) or 0
        processed_count = db.scalar(select(func.count()).select_from(OcppMessage).where(OcppMessage.status == "processed")) or 0
        failed_count = db.scalar(select(func.count()).select_from(OcppMessage).where(OcppMessage.status == "failed")) or 0
        retry_count = db.scalar(select(func.count()).select_from(OutboxEvent).where(OutboxEvent.status == "retrying")) or 0
        oldest_pending = db.scalar(
            select(func.min(OutboxEvent.created_at)).where(OutboxEvent.status == "pending")
        )
        lag_seconds = 0.0
        if oldest_pending is not None:
            lag_seconds = max(0.0, (datetime.now(UTC) - oldest_pending).total_seconds())
        connected_stations.set(float(connected_count))
        active_sessions.set(float(session_count))
        worker_lag_seconds.set(lag_seconds)
        db.execute(text("select 1"))
        cache = cache_status()
    finally:
        db.close()
    return {
        "worker": "unknown",
        "cache": cache,
        "status": "ok",
        "connected_stations": str(connected_count),
        "active_sessions": str(session_count),
        "processed_messages": str(processed_count),
        "failed_messages": str(failed_count),
        "retrying_outbox": str(retry_count),
        "worker_lag_seconds": f"{lag_seconds:.1f}",
    }
