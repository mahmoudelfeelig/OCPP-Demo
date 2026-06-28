from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import verify_station_token
from app.models.entities import Station


def authenticate_station(db: Session, station_ref: str, token: str) -> Station | None:
    station = db.get(Station, station_ref)
    candidates = [station] if station is not None else list(
        db.scalars(select(Station).where(Station.external_id == station_ref))
    )
    authenticated = [
        candidate
        for candidate in candidates
        if candidate is not None and verify_station_token(token, candidate.ocpp_token_hash)
    ]
    return authenticated[0] if len(authenticated) == 1 else None
