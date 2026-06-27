from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, require_role
from app.db.session import get_db
from app.core.security import hash_password
from app.models.entities import AuditEvent, Connector, ConnectorState, OutboxEvent, OutboxStatus, Role, Station, User
from app.repositories.outbox import OutboxRepository

router = APIRouter(prefix="/admin", tags=["admin"])


class AdminActionResponse(BaseModel):
    status: str
    action: str


class UserCreateRequest(BaseModel):
    email: str
    password: str
    role: str = "operator"
    display_name: str | None = None


class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    display_name: str | None = None
    is_active: bool


@router.post("/simulator/remote-start", response_model=AdminActionResponse)
async def remote_start_simulation(
    current_user: CurrentUser = Depends(require_role("admin", "operator")),
    db: Session = Depends(get_db),
) -> AdminActionResponse:
    db.add(
        AuditEvent(
            actor_user_id=current_user.id,
            action="remote_start_simulation",
            entity_type="simulator",
            entity_id="remote-start",
            payload={},
        )
    )
    db.commit()
    return AdminActionResponse(status="accepted", action="remote_start_simulation")


@router.post("/simulator/remote-stop", response_model=AdminActionResponse)
async def remote_stop_simulation(
    current_user: CurrentUser = Depends(require_role("admin", "operator")),
    db: Session = Depends(get_db),
) -> AdminActionResponse:
    db.add(
        AuditEvent(
            actor_user_id=current_user.id,
            action="remote_stop_simulation",
            entity_type="simulator",
            entity_id="remote-stop",
            payload={},
        )
    )
    db.commit()
    return AdminActionResponse(status="accepted", action="remote_stop_simulation")


@router.post("/outbox/{event_id}/retry", response_model=AdminActionResponse)
async def retry_outbox_event(
    event_id: str,
    current_user: CurrentUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> AdminActionResponse:
    event = db.get(OutboxEvent, event_id)
    if event is not None:
        event.status = OutboxStatus.PENDING.value
        event.next_attempt_at = None
        event.last_error = None
        event.locked_at = None
        event.locked_by = None
        event.attempts = 0
    db.add(
        AuditEvent(
            actor_user_id=current_user.id,
            action="retry_outbox_event",
            entity_type="outbox",
            entity_id=event_id,
            payload={},
        )
    )
    db.commit()
    return AdminActionResponse(status="accepted", action=f"retry_outbox_event:{event_id}")


@router.post("/outbox/{event_id}/ack", response_model=AdminActionResponse)
async def acknowledge_dead_letter(
    event_id: str,
    current_user: CurrentUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> AdminActionResponse:
    event = db.get(OutboxEvent, event_id)
    if event is not None:
        if event.status != OutboxStatus.DEAD_LETTERED.value:
            raise HTTPException(status_code=409, detail="Only dead-lettered events can be acknowledged")
        OutboxRepository(db).acknowledge_dead_letter(event, current_user.id)
    db.add(
        AuditEvent(
            actor_user_id=current_user.id,
            action="ack_dead_letter",
            entity_type="outbox",
            entity_id=event_id,
            payload={"status_preserved": event.status if event is not None else None},
        )
    )
    db.commit()
    return AdminActionResponse(status="accepted", action=f"ack_dead_letter:{event_id}")


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    current_user: CurrentUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> list[UserResponse]:
    users = list(db.scalars(select(User)))
    return [
        UserResponse(
            id=user.id,
            email=user.email,
            role=user.role.name,
            display_name=user.display_name,
            is_active=user.is_active,
        )
        for user in users
    ]


@router.post("/users", response_model=UserResponse)
async def create_user(
    payload: UserCreateRequest,
    current_user: CurrentUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> UserResponse:
    role = db.scalar(select(Role).where(Role.name == payload.role))
    if role is None:
        raise HTTPException(status_code=400, detail="Unknown role")
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role_id=role.id,
        display_name=payload.display_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    user_role = db.scalar(select(Role).where(Role.id == user.role_id))
    db.add(
        AuditEvent(
            actor_user_id=current_user.id,
            action="create_user",
            entity_type="user",
            entity_id=user.id,
            payload={"email": user.email, "role": user_role.name if user_role else payload.role},
        )
    )
    db.commit()
    return UserResponse(id=user.id, email=user.email, role=user_role.name if user_role else payload.role, display_name=user.display_name, is_active=user.is_active)


@router.post("/users/{user_id}/role", response_model=AdminActionResponse)
async def update_user_role(
    user_id: str,
    payload: dict[str, str],
    current_user: CurrentUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> AdminActionResponse:
    user = db.get(User, user_id)
    if user is None:
        return AdminActionResponse(status="missing", action=f"update_user_role:{user_id}")
    role = db.scalar(select(Role).where(Role.name == payload.get("role", "operator")))
    if role is None:
        raise HTTPException(status_code=400, detail="Unknown role")
    user.role_id = role.id
    db.add(
        AuditEvent(
            actor_user_id=current_user.id,
            action="update_user_role",
            entity_type="user",
            entity_id=user.id,
            payload={"role": role.name},
        )
    )
    db.commit()
    return AdminActionResponse(status="accepted", action=f"update_user_role:{user_id}")


@router.post("/stations/{station_id}/maintenance", response_model=AdminActionResponse)
async def toggle_station_maintenance(
    station_id: str,
    payload: dict[str, bool],
    current_user: CurrentUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> AdminActionResponse:
    station = db.get(Station, station_id)
    if station is not None:
        station.maintenance_mode = bool(payload.get("enabled", True))
        db.add(
            AuditEvent(
                actor_user_id=current_user.id,
                action="toggle_station_maintenance",
                entity_type="station",
                entity_id=station.id,
                payload={"enabled": station.maintenance_mode},
            )
        )
        db.commit()
    return AdminActionResponse(status="accepted", action=f"station_maintenance:{station_id}")


@router.post("/connectors/{connector_id}/available", response_model=AdminActionResponse)
async def connector_available(
    connector_id: str,
    current_user: CurrentUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> AdminActionResponse:
    connector = db.get(Connector, connector_id)
    if connector is not None:
        connector.state = ConnectorState.AVAILABLE.value
        db.add(
            AuditEvent(
                actor_user_id=current_user.id,
                action="connector_available",
                entity_type="connector",
                entity_id=connector.id,
                payload={},
            )
        )
        db.commit()
    return AdminActionResponse(status="accepted", action=f"connector_available:{connector_id}")


@router.post("/connectors/{connector_id}/unavailable", response_model=AdminActionResponse)
async def connector_unavailable(
    connector_id: str,
    current_user: CurrentUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> AdminActionResponse:
    connector = db.get(Connector, connector_id)
    if connector is not None:
        connector.state = ConnectorState.UNAVAILABLE.value
        db.add(
            AuditEvent(
                actor_user_id=current_user.id,
                action="connector_unavailable",
                entity_type="connector",
                entity_id=connector.id,
                payload={},
            )
        )
        db.commit()
    return AdminActionResponse(status="accepted", action=f"connector_unavailable:{connector_id}")
