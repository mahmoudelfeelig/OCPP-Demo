from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class PageMeta(BaseModel):
    limit: int
    offset: int
    count: int
    total: int


class SiteSummary(BaseModel):
    id: str
    label: str
    slug: str
    station_count: int = 0
    online_count: int = 0
    active_sessions: int = 0
    is_active: bool = True


class StationSummary(BaseModel):
    id: str
    site_id: str
    external_id: str | None = None
    label: str
    connector_count: int
    state: str
    online: bool
    maintenance_mode: bool
    last_seen_at: str | None = None


class ConnectorSummary(BaseModel):
    id: str
    station_id: str
    connector_number: int
    state: str
    error_code: str | None = None


class TransactionSummary(BaseModel):
    id: str | None = None
    session_id: str | None = None
    ocpp_transaction_id: str | None = None
    state: str | None = None
    started_at: str | None = None
    stopped_at: str | None = None
    stop_reason: str | None = None


class MeterValueSummary(BaseModel):
    id: str
    sampled_at: str
    value_kwh: float
    unit: str


class SessionSummary(BaseModel):
    id: str
    site_id: str
    station_id: str
    connector_id: str | None = None
    external_session_id: str
    state: str
    transaction_state: str
    started_at: str | None = None
    ended_at: str | None = None


class SessionDetail(SessionSummary):
    transaction: TransactionSummary
    meter_values: list[MeterValueSummary]


class EventSummary(BaseModel):
    id: str
    action: str
    entity_type: str
    entity_id: str
    created_at: str | None = None


class MessageSummary(BaseModel):
    id: str
    station_id: str
    action: str
    message_id: str
    status: str
    received_at: str | None = None
    payload: dict[str, Any]


class OutboxSummary(BaseModel):
    id: str
    event_type: str
    status: str
    attempts: int
    next_attempt_at: str | None = None
    last_error: str | None = None
    acknowledged_at: str | None = None
    acknowledged_by: str | None = None


class WebhookSummary(BaseModel):
    id: str
    event_id: str
    status: str
    signature_valid: bool
    received_at: str | None = None
    last_error: str | None = None


class ItemResponse(BaseModel):
    item: dict[str, Any] | None


class SitesResponse(BaseModel):
    items: list[SiteSummary]
    meta: PageMeta


class StationsResponse(BaseModel):
    items: list[StationSummary]
    meta: PageMeta


class ConnectorsResponse(BaseModel):
    items: list[ConnectorSummary]
    meta: PageMeta


class SessionsResponse(BaseModel):
    items: list[SessionSummary]
    meta: PageMeta


class TransactionsResponse(BaseModel):
    items: list[TransactionSummary]
    meta: PageMeta


class EventsResponse(BaseModel):
    items: list[EventSummary]
    meta: PageMeta


class MessagesResponse(BaseModel):
    items: list[MessageSummary]
    meta: PageMeta


class OutboxResponse(BaseModel):
    items: list[OutboxSummary]
    meta: PageMeta


class WebhooksResponse(BaseModel):
    items: list[WebhookSummary]
    meta: PageMeta
