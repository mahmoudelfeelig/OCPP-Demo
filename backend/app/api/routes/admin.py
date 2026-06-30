from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, require_role
from app.db.session import get_db
from app.core.security import hash_password, hash_station_token
from app.models.entities import AuditEvent, Connector, ConnectorState, OutboxEvent, OutboxStatus, Role, Station, StationState, User
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
    created_at: str
    last_login_at: str | None = None


class StationTokenRequest(BaseModel):
    token: str = Field(min_length=32, max_length=256)


def lock_active_admins(db: Session) -> list[User]:
    return list(
        db.scalars(
            select(User)
            .join(Role)
            .where(User.is_active.is_(True), Role.name == "admin")
            .with_for_update(of=User)
        )
    )


@router.post(
    "/simulator/remote-start",
    response_model=AdminActionResponse,
    summary="Record a simulated start action",
    description="Writes an admin audit event only. It does not send an outbound OCPP command.",
)
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
    return AdminActionResponse(status="recorded", action="remote_start_simulation")


@router.post(
    "/simulator/remote-stop",
    response_model=AdminActionResponse,
    summary="Record a simulated stop action",
    description="Writes an admin audit event only. It does not send an outbound OCPP command.",
)
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
    return AdminActionResponse(status="recorded", action="remote_stop_simulation")


@router.post("/outbox/{event_id}/retry", response_model=AdminActionResponse)
async def retry_outbox_event(
    event_id: str,
    current_user: CurrentUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> AdminActionResponse:
    event = db.get(OutboxEvent, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Outbox event not found")
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
    if event is None:
        raise HTTPException(status_code=404, detail="Outbox event not found")
    if event.status != OutboxStatus.DEAD_LETTERED.value:
        raise HTTPException(status_code=409, detail="Only dead-lettered events can be acknowledged")
    OutboxRepository(db).acknowledge_dead_letter(event, current_user.id)
    db.add(
        AuditEvent(
            actor_user_id=current_user.id,
            action="ack_dead_letter",
            entity_type="outbox",
            entity_id=event_id,
            payload={"status_preserved": event.status},
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
            created_at=user.created_at.isoformat(),
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
    return UserResponse(
        id=user.id,
        email=user.email,
        role=user_role.name if user_role else payload.role,
        display_name=user.display_name,
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
    )


@router.post("/users/{user_id}/role", response_model=AdminActionResponse)
async def update_user_role(
    user_id: str,
    payload: dict[str, str],
    current_user: CurrentUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> AdminActionResponse:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    role = db.scalar(select(Role).where(Role.name == payload.get("role", "operator")))
    if role is None:
        raise HTTPException(status_code=400, detail="Unknown role")
    if user.role.name == "admin" and role.name != "admin" and user.is_active:
        if len(lock_active_admins(db)) <= 1:
            raise HTTPException(status_code=409, detail="Cannot demote the last active admin")
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


@router.post("/users/{user_id}/deactivate", response_model=AdminActionResponse)
async def deactivate_user(
    user_id: str,
    current_user: CurrentUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> AdminActionResponse:
    if user_id == current_user.id:
        raise HTTPException(status_code=409, detail="You cannot remove your own account")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role.name == "admin" and user.is_active:
        if len(lock_active_admins(db)) <= 1:
            raise HTTPException(status_code=409, detail="Cannot remove the last active admin")
    user.is_active = False
    db.add(
        AuditEvent(
            actor_user_id=current_user.id,
            action="deactivate_user",
            entity_type="user",
            entity_id=user.id,
            payload={"email": user.email},
        )
    )
    db.commit()
    return AdminActionResponse(status="accepted", action=f"deactivate_user:{user_id}")


@router.post("/users/{user_id}/activate", response_model=AdminActionResponse)
async def activate_user(
    user_id: str,
    current_user: CurrentUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> AdminActionResponse:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = True
    db.add(
        AuditEvent(
            actor_user_id=current_user.id,
            action="activate_user",
            entity_type="user",
            entity_id=user.id,
            payload={"email": user.email},
        )
    )
    db.commit()
    return AdminActionResponse(status="accepted", action=f"activate_user:{user_id}")


@router.post("/stations/{station_id}/maintenance", response_model=AdminActionResponse)
async def toggle_station_maintenance(
    station_id: str,
    payload: dict[str, bool],
    current_user: CurrentUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> AdminActionResponse:
    station = db.get(Station, station_id)
    if station is None:
        raise HTTPException(status_code=404, detail="Station not found")
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


@router.post("/stations/{station_id}/online", response_model=AdminActionResponse)
async def station_online(
    station_id: str,
    current_user: CurrentUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> AdminActionResponse:
    station = db.get(Station, station_id)
    if station is None:
        raise HTTPException(status_code=404, detail="Station not found")
    previous_state = station.state
    station.online = True
    station.state = StationState.ONLINE.value
    station.last_seen_at = datetime.now(UTC)
    db.add(
        AuditEvent(
            actor_user_id=current_user.id,
            action="station_online",
            entity_type="station",
            entity_id=station.id,
            payload={"previous_state": previous_state, "online": True},
        )
    )
    db.commit()
    return AdminActionResponse(status="accepted", action=f"station_online:{station_id}")


@router.post("/stations/{station_id}/offline", response_model=AdminActionResponse)
async def station_offline(
    station_id: str,
    current_user: CurrentUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> AdminActionResponse:
    station = db.get(Station, station_id)
    if station is None:
        raise HTTPException(status_code=404, detail="Station not found")
    previous_state = station.state
    station.online = False
    station.state = StationState.OFFLINE.value
    station.last_seen_at = None
    db.add(
        AuditEvent(
            actor_user_id=current_user.id,
            action="station_offline",
            entity_type="station",
            entity_id=station.id,
            payload={"previous_state": previous_state, "online": False},
        )
    )
    db.commit()
    return AdminActionResponse(status="accepted", action=f"station_offline:{station_id}")


@router.post("/stations/{station_id}/token", response_model=AdminActionResponse)
async def rotate_station_token(
    station_id: str,
    payload: StationTokenRequest,
    current_user: CurrentUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> AdminActionResponse:
    station = db.get(Station, station_id)
    if station is None:
        raise HTTPException(status_code=404, detail="Station not found")
    station.ocpp_token_hash = hash_station_token(payload.token)
    db.add(
        AuditEvent(
            actor_user_id=current_user.id,
            action="rotate_station_token",
            entity_type="station",
            entity_id=station.id,
            payload={},
        )
    )
    db.commit()
    return AdminActionResponse(status="accepted", action=f"rotate_station_token:{station_id}")


@router.post("/connectors/{connector_id}/available", response_model=AdminActionResponse)
async def connector_available(
    connector_id: str,
    current_user: CurrentUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> AdminActionResponse:
    connector = db.get(Connector, connector_id)
    if connector is None:
        raise HTTPException(status_code=404, detail="Connector not found")
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
    if connector is None:
        raise HTTPException(status_code=404, detail="Connector not found")
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
