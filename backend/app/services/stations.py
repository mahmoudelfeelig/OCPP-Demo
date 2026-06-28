from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import AuditEvent, Station, StationState


def mark_stale_stations_offline(db: Session, timeout_seconds: int) -> int:
    stale_before = datetime.now(UTC) - timedelta(seconds=timeout_seconds)
    stations = list(
        db.scalars(
            select(Station).where(
                Station.online.is_(True),
                Station.last_seen_at.is_not(None),
                Station.last_seen_at <= stale_before,
            )
        )
    )
    for station in stations:
        previous_state = station.state
        station.online = False
        station.state = StationState.OFFLINE.value
        db.add(
            AuditEvent(
                action="station_heartbeat_missed",
                entity_type="station",
                entity_id=station.id,
                payload={
                    "from": previous_state,
                    "to": StationState.OFFLINE.value,
                    "last_seen_at": station.last_seen_at.isoformat() if station.last_seen_at else None,
                    "timeout_seconds": timeout_seconds,
                },
            )
        )
    return len(stations)
