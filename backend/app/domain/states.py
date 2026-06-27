from __future__ import annotations

from enum import StrEnum


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
