from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def _uuid() -> str:
    return str(uuid4())


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class StationState(StrEnum):
    UNKNOWN = "unknown"
    ONLINE = "online"
    OFFLINE = "offline"
    FAULTED = "faulted"


class ConnectorState(StrEnum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    CHARGING = "charging"
    SUSPENDED_EV = "suspended_ev"
    SUSPENDED_EVSE = "suspended_evse"
    FINISHING = "finishing"
    RESERVED = "reserved"
    UNAVAILABLE = "unavailable"
    FAULTED = "faulted"


class SessionState(StrEnum):
    REQUESTED = "requested"
    STARTING = "starting"
    ACTIVE = "active"
    STOPPING = "stopping"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class TransactionState(StrEnum):
    OPEN = "open"
    CLOSING = "closing"
    CLOSED = "closed"
    RECONCILED = "reconciled"
    FAILED = "failed"


class MessageDirection(StrEnum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class OcppMessageStatus(StrEnum):
    RECEIVED = "received"
    PROCESSED = "processed"
    FAILED = "failed"


class OutboxStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    RETRYING = "retrying"
    FAILED = "failed"
    DEAD_LETTERED = "dead_lettered"


class PartnerEventStatus(StrEnum):
    RECEIVED = "received"
    PROCESSED = "processed"
    RETRYING = "retrying"
    FAILED = "failed"
    DEAD_LETTERED = "dead_lettered"


class UserRole(StrEnum):
    ADMIN = "admin"
    OPERATOR = "operator"


class Site(Base, TimestampMixin):
    __tablename__ = "sites"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    stations: Mapped[list["Station"]] = relationship(back_populates="site", cascade="all, delete-orphan")
    sessions: Mapped[list["ChargingSession"]] = relationship(back_populates="site", cascade="all, delete-orphan")


class Station(Base, TimestampMixin):
    __tablename__ = "stations"
    __table_args__ = (UniqueConstraint("site_id", "external_id", name="uq_station_site_external_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    site_id: Mapped[str] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False)
    external_id: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default=StationState.UNKNOWN.value)
    online: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    maintenance_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ocpp_token_hash: Mapped[str | None] = mapped_column(String(64))

    site: Mapped[Site] = relationship(back_populates="stations")
    connectors: Mapped[list["Connector"]] = relationship(back_populates="station", cascade="all, delete-orphan")
    ocpp_messages: Mapped[list["OcppMessage"]] = relationship(back_populates="station")


class Connector(Base, TimestampMixin):
    __tablename__ = "connectors"
    __table_args__ = (UniqueConstraint("station_id", "connector_number", name="uq_connector_station_number"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    station_id: Mapped[str] = mapped_column(ForeignKey("stations.id", ondelete="CASCADE"), nullable=False)
    connector_number: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default=ConnectorState.AVAILABLE.value)
    error_code: Mapped[str | None] = mapped_column(String(64))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    station: Mapped[Station] = relationship(back_populates="connectors")


class ChargingSession(Base, TimestampMixin):
    __tablename__ = "charging_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    site_id: Mapped[str] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False)
    station_id: Mapped[str] = mapped_column(ForeignKey("stations.id", ondelete="CASCADE"), nullable=False)
    connector_id: Mapped[str | None] = mapped_column(ForeignKey("connectors.id", ondelete="SET NULL"))
    external_session_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default=SessionState.REQUESTED.value)
    transaction_state: Mapped[str] = mapped_column(String(32), nullable=False, default=TransactionState.OPEN.value)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    site: Mapped[Site] = relationship(back_populates="sessions")
    station: Mapped[Station] = relationship()
    connector: Mapped[Connector | None] = relationship()
    transaction: Mapped["Transaction"] = relationship(back_populates="session", uselist=False)
    meter_values: Mapped[list["MeterValue"]] = relationship(back_populates="session")


class Transaction(Base, TimestampMixin):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("charging_sessions.id", ondelete="CASCADE"), unique=True, nullable=False)
    ocpp_transaction_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default=TransactionState.OPEN.value)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stop_reason: Mapped[str | None] = mapped_column(String(128))

    session: Mapped[ChargingSession] = relationship(back_populates="transaction")
    meter_values: Mapped[list["MeterValue"]] = relationship(back_populates="transaction", cascade="all, delete-orphan")


class MeterValue(Base, TimestampMixin):
    __tablename__ = "meter_values"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("charging_sessions.id", ondelete="CASCADE"), nullable=False)
    transaction_id: Mapped[str] = mapped_column(ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False)
    message_id: Mapped[str] = mapped_column(String(64), nullable=False)
    sampled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    value_kwh: Mapped[float] = mapped_column(nullable=False)
    unit: Mapped[str] = mapped_column(String(16), nullable=False, default="kWh")
    measurand: Mapped[str | None] = mapped_column(String(64))
    duplicate_of_id: Mapped[str | None] = mapped_column(ForeignKey("meter_values.id", ondelete="SET NULL"))
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    session: Mapped[ChargingSession] = relationship(back_populates="meter_values")
    transaction: Mapped[Transaction] = relationship(back_populates="meter_values")


class OcppMessage(Base, TimestampMixin):
    __tablename__ = "ocpp_messages"
    __table_args__ = (UniqueConstraint("station_id", "message_id", name="uq_ocpp_message_station_message_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    station_id: Mapped[str] = mapped_column(ForeignKey("stations.id", ondelete="CASCADE"), nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    message_id: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    raw_message_text: Mapped[str] = mapped_column(Text, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=func.now())
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=OcppMessageStatus.RECEIVED.value)
    error_message: Mapped[str | None] = mapped_column(Text)

    station: Mapped[Station] = relationship(back_populates="ocpp_messages")
    outbox_event: Mapped["OutboxEvent"] = relationship(back_populates="message", uselist=False)


class OutboxEvent(Base, TimestampMixin):
    __tablename__ = "outbox_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    message_id: Mapped[str | None] = mapped_column(ForeignKey("ocpp_messages.id", ondelete="SET NULL"))
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=OutboxStatus.PENDING.value)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=6)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locked_by: Mapped[str | None] = mapped_column(String(64))
    last_error: Mapped[str | None] = mapped_column(Text)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acknowledged_by: Mapped[str | None] = mapped_column(String(36))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    message: Mapped[OcppMessage | None] = relationship(back_populates="outbox_event")


class PartnerEvent(Base, TimestampMixin):
    __tablename__ = "partner_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    event_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    signature_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=PartnerEventStatus.RECEIVED.value)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=func.now())
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    raw_payload_text: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class WebhookDelivery(Base, TimestampMixin):
    __tablename__ = "webhook_deliveries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    partner_event_id: Mapped[str | None] = mapped_column(ForeignKey("partner_events.id", ondelete="SET NULL"))
    delivery_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=PartnerEventStatus.RECEIVED.value)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class Role(Base, TimestampMixin):
    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(200))

    users: Mapped[list["User"]] = relationship(back_populates="role")


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    display_name: Mapped[str | None] = mapped_column(String(200))

    role: Mapped[Role] = relationship(back_populates="users")


class AuditEvent(Base, TimestampMixin):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(64))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
