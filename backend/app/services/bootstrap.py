from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import hash_password, hash_station_token
from app.models.entities import Role, Station, User

logger = logging.getLogger(__name__)


def ensure_role(db: Session, name: str, description: str) -> Role:
    role = db.scalar(select(Role).where(Role.name == name))
    if role is not None:
        return role

    role = Role(name=name, description=description)
    db.add(role)
    db.flush()
    return role


def bootstrap_admin_user(db: Session, settings: Settings) -> None:
    email = settings.admin_bootstrap_email
    password = settings.admin_bootstrap_password
    if not email or not password:
        return

    if settings.app_env == "production" and password == "change-me":
        raise RuntimeError("ADMIN_BOOTSTRAP_PASSWORD must be changed before production startup")

    admin_role = ensure_role(db, "admin", "Full operational access")
    ensure_role(db, "operator", "Operational view and safe actions")

    existing = db.scalar(select(User).where(User.email == email))
    if existing is not None:
        return

    db.add(
        User(
            email=email,
            password_hash=hash_password(password),
            role_id=admin_role.id,
            display_name="Bootstrap Admin",
        )
    )
    db.commit()
    logger.info("bootstrapped admin user", extra={"email": email})


def configure_station_tokens(db: Session, settings: Settings) -> None:
    configured = settings.station_tokens()
    if not configured:
        return

    for station_ref, token in configured.items():
        if len(token) < 32:
            raise RuntimeError(f"OCPP token for station {station_ref} must contain at least 32 characters")
        station = db.get(Station, station_ref)
        if station is None:
            matches = list(db.scalars(select(Station).where(Station.external_id == station_ref)))
            if len(matches) > 1:
                raise RuntimeError(f"OCPP station identifier is ambiguous: {station_ref}")
            station = matches[0] if matches else None
        if station is None:
            logger.warning("station token references an unknown station", extra={"station_ref": station_ref})
            continue
        configured_hash = hash_station_token(token)
        if station.ocpp_token_hash is None:
            station.ocpp_token_hash = configured_hash
        elif station.ocpp_token_hash != configured_hash:
            logger.warning(
                "station token differs from environment; keeping the database value",
                extra={"station_ref": station_ref},
            )
    db.commit()
