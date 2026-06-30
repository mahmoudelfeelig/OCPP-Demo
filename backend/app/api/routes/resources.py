from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.api.schemas import (
    ConnectorsResponse,
    EventsResponse,
    ItemResponse,
    MessagesResponse,
    OutboxResponse,
    PageMeta,
    SessionsResponse,
    SitesResponse,
    StationsResponse,
    TransactionsResponse,
    WebhooksResponse,
)
from app.db.session import get_db
from app.models.entities import (
    AuditEvent,
    ChargingSession,
    Connector,
    OcppMessage,
    OutboxEvent,
    PartnerEvent,
    Site,
    Station,
    Transaction,
)
from app.services.catalog import site_card_data

router = APIRouter()


async def page_params(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> tuple[int, int]:
    return limit, offset


def _meta(items: list[Any], limit: int, offset: int, total: int) -> PageMeta:
    return PageMeta(limit=limit, offset=offset, count=len(items), total=total)


def _paged(db: Session, stmt: Select[tuple[Any]], limit: int, offset: int) -> list[Any]:
    return list(db.scalars(stmt.offset(offset).limit(limit)))


def _total(db: Session, stmt: Select[tuple[Any]]) -> int:
    return db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0


def _station(station: Station) -> dict[str, Any]:
    return {
        "id": station.id,
        "site_id": station.site_id,
        "external_id": station.external_id,
        "label": station.label,
        "connector_count": len(station.connectors),
        "state": station.state,
        "online": station.online,
        "maintenance_mode": station.maintenance_mode,
        "last_seen_at": station.last_seen_at.isoformat() if station.last_seen_at else None,
    }


def _session(session: ChargingSession) -> dict[str, Any]:
    return {
        "id": session.id,
        "site_id": session.site_id,
        "station_id": session.station_id,
        "connector_id": session.connector_id,
        "external_session_id": session.external_session_id,
        "state": session.state,
        "transaction_state": session.transaction_state,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
    }


def _transaction(transaction: Transaction | None) -> dict[str, Any]:
    if transaction is None:
        return {
            "id": None,
            "session_id": None,
            "ocpp_transaction_id": None,
            "state": None,
            "started_at": None,
            "stopped_at": None,
            "stop_reason": None,
        }
    return {
        "id": transaction.id,
        "session_id": transaction.session_id,
        "ocpp_transaction_id": transaction.ocpp_transaction_id,
        "state": transaction.state,
        "started_at": transaction.started_at.isoformat() if transaction.started_at else None,
        "stopped_at": transaction.stopped_at.isoformat() if transaction.stopped_at else None,
        "stop_reason": transaction.stop_reason,
    }


@router.get("/sites", response_model=SitesResponse)
async def list_sites(
    paging: tuple[int, int] = Depends(page_params),
    db: Session = Depends(get_db),
    _user=Depends(require_role("admin", "operator")),
) -> SitesResponse:
    limit, offset = paging
    all_items = site_card_data(db)
    items = all_items[offset : offset + limit]
    return SitesResponse(items=items, meta=_meta(items, limit, offset, len(all_items)))


@router.get("/stations", response_model=StationsResponse)
async def list_stations(
    site_id: str | None = None,
    state: str | None = None,
    online: bool | None = None,
    paging: tuple[int, int] = Depends(page_params),
    db: Session = Depends(get_db),
    _user=Depends(require_role("admin", "operator")),
) -> StationsResponse:
    limit, offset = paging
    stmt = select(Station).order_by(Station.label)
    if site_id:
        stmt = stmt.where(Station.site_id == site_id)
    if state:
        stmt = stmt.where(Station.state == state)
    if online is not None:
        stmt = stmt.where(Station.online.is_(online))
    total = _total(db, stmt)
    stations = _paged(db, stmt, limit, offset)
    items = [_station(station) for station in stations]
    return StationsResponse(items=items, meta=_meta(items, limit, offset, total))


@router.get("/sessions", response_model=SessionsResponse)
async def list_sessions(
    site_id: str | None = None,
    station_id: str | None = None,
    state: str | None = None,
    transaction_state: str | None = None,
    paging: tuple[int, int] = Depends(page_params),
    db: Session = Depends(get_db),
    _user=Depends(require_role("admin", "operator")),
) -> SessionsResponse:
    limit, offset = paging
    stmt = select(ChargingSession).order_by(ChargingSession.started_at.desc().nullslast(), ChargingSession.created_at.desc())
    if site_id:
        stmt = stmt.where(ChargingSession.site_id == site_id)
    if station_id:
        stmt = stmt.where(ChargingSession.station_id == station_id)
    if state:
        stmt = stmt.where(ChargingSession.state == state)
    if transaction_state:
        stmt = stmt.where(ChargingSession.transaction_state == transaction_state)
    total = _total(db, stmt)
    sessions = _paged(db, stmt, limit, offset)
    items = [_session(session) for session in sessions]
    return SessionsResponse(items=items, meta=_meta(items, limit, offset, total))


@router.get("/sessions/{session_id}", response_model=ItemResponse)
async def get_session(session_id: str, db: Session = Depends(get_db), _user=Depends(require_role("admin", "operator"))) -> ItemResponse:
    session = db.get(ChargingSession, session_id)
    if session is None:
        return ItemResponse(item=None)
    meter_values = [
        {
            "id": meter.id,
            "sampled_at": meter.sampled_at.isoformat(),
            "value_kwh": meter.value_kwh,
            "unit": meter.unit,
        }
        for meter in sorted(session.meter_values, key=lambda value: value.sampled_at)
    ]
    return ItemResponse(item={**_session(session), "transaction": _transaction(session.transaction), "meter_values": meter_values})


@router.get("/transactions", response_model=TransactionsResponse)
async def list_transactions(
    state: str | None = None,
    session_id: str | None = None,
    paging: tuple[int, int] = Depends(page_params),
    db: Session = Depends(get_db),
    _user=Depends(require_role("admin", "operator")),
) -> TransactionsResponse:
    limit, offset = paging
    stmt = select(Transaction).order_by(Transaction.started_at.desc().nullslast(), Transaction.created_at.desc())
    if state:
        stmt = stmt.where(Transaction.state == state)
    if session_id:
        stmt = stmt.where(Transaction.session_id == session_id)
    total = _total(db, stmt)
    transactions = _paged(db, stmt, limit, offset)
    items = [_transaction(txn) for txn in transactions]
    return TransactionsResponse(items=items, meta=_meta(items, limit, offset, total))


@router.get("/transactions/{transaction_id}", response_model=ItemResponse)
async def get_transaction(
    transaction_id: str, db: Session = Depends(get_db), _user=Depends(require_role("admin", "operator"))
) -> ItemResponse:
    transaction = db.get(Transaction, transaction_id)
    return ItemResponse(item=None if transaction is None else _transaction(transaction))


@router.get("/events", response_model=EventsResponse)
async def list_events(
    entity_type: str | None = None,
    action: str | None = None,
    paging: tuple[int, int] = Depends(page_params),
    db: Session = Depends(get_db),
    _user=Depends(require_role("admin", "operator")),
) -> EventsResponse:
    limit, offset = paging
    stmt = select(AuditEvent).order_by(AuditEvent.created_at.desc())
    if entity_type:
        stmt = stmt.where(AuditEvent.entity_type == entity_type)
    if action:
        stmt = stmt.where(AuditEvent.action == action)
    total = _total(db, stmt)
    events = _paged(db, stmt, limit, offset)
    items = [
        {
            "id": event.id,
            "action": event.action,
            "entity_type": event.entity_type,
            "entity_id": event.entity_id,
            "created_at": event.created_at.isoformat() if event.created_at else None,
        }
        for event in events
    ]
    return EventsResponse(items=items, meta=_meta(items, limit, offset, total))


@router.get("/messages", response_model=MessagesResponse)
async def list_messages(
    station_id: str | None = None,
    action: str | None = None,
    status: str | None = None,
    paging: tuple[int, int] = Depends(page_params),
    db: Session = Depends(get_db),
    _user=Depends(require_role("admin", "operator")),
) -> MessagesResponse:
    limit, offset = paging
    stmt = select(OcppMessage).order_by(OcppMessage.received_at.desc())
    if station_id:
        stmt = stmt.where(OcppMessage.station_id == station_id)
    if action:
        stmt = stmt.where(OcppMessage.action == action)
    if status:
        stmt = stmt.where(OcppMessage.status == status)
    total = _total(db, stmt)
    messages = _paged(db, stmt, limit, offset)
    items = [
        {
            "id": message.id,
            "station_id": message.station_id,
            "action": message.action,
            "message_id": message.message_id,
            "status": message.status,
            "received_at": message.received_at.isoformat() if message.received_at else None,
            "payload": message.payload,
        }
        for message in messages
    ]
    return MessagesResponse(items=items, meta=_meta(items, limit, offset, total))


@router.get("/outbox", response_model=OutboxResponse)
async def list_outbox(
    status: str | None = None,
    event_type: str | None = None,
    paging: tuple[int, int] = Depends(page_params),
    db: Session = Depends(get_db),
    _user=Depends(require_role("admin", "operator")),
) -> OutboxResponse:
    limit, offset = paging
    stmt = select(OutboxEvent).order_by(OutboxEvent.created_at.desc())
    if status:
        stmt = stmt.where(OutboxEvent.status == status)
    if event_type:
        stmt = stmt.where(OutboxEvent.event_type == event_type)
    total = _total(db, stmt)
    events = _paged(db, stmt, limit, offset)
    items = [
        {
            "id": event.id,
            "event_type": event.event_type,
            "status": event.status,
            "attempts": event.attempts,
            "next_attempt_at": event.next_attempt_at.isoformat() if event.next_attempt_at else None,
            "last_error": event.last_error,
            "acknowledged_at": event.acknowledged_at.isoformat() if event.acknowledged_at else None,
            "acknowledged_by": event.acknowledged_by,
        }
        for event in events
    ]
    return OutboxResponse(items=items, meta=_meta(items, limit, offset, total))


@router.get("/webhooks", response_model=WebhooksResponse)
async def list_webhooks(
    status: str | None = None,
    signature_valid: bool | None = None,
    paging: tuple[int, int] = Depends(page_params),
    db: Session = Depends(get_db),
    _user=Depends(require_role("admin", "operator")),
) -> WebhooksResponse:
    limit, offset = paging
    stmt = select(PartnerEvent).order_by(PartnerEvent.received_at.desc())
    if status:
        stmt = stmt.where(PartnerEvent.status == status)
    if signature_valid is not None:
        stmt = stmt.where(PartnerEvent.signature_valid.is_(signature_valid))
    total = _total(db, stmt)
    events = _paged(db, stmt, limit, offset)
    items = [
        {
            "id": event.id,
            "event_id": event.event_id,
            "status": event.status,
            "signature_valid": event.signature_valid,
            "received_at": event.received_at.isoformat() if event.received_at else None,
            "last_error": event.last_error,
        }
        for event in events
    ]
    return WebhooksResponse(items=items, meta=_meta(items, limit, offset, total))


@router.get("/sites/{site_id}", response_model=ItemResponse)
async def get_site(site_id: str, db: Session = Depends(get_db), _user=Depends(require_role("admin", "operator"))) -> ItemResponse:
    site = db.get(Site, site_id)
    if site is None:
        return ItemResponse(item=None)
    station_count = db.scalar(select(func.count()).select_from(Station).where(Station.site_id == site.id)) or 0
    return ItemResponse(item={"id": site.id, "label": site.label, "slug": site.slug, "is_active": site.is_active, "station_count": station_count})


@router.get("/sites/{site_id}/stations", response_model=StationsResponse)
async def list_site_stations(
    site_id: str,
    state: str | None = None,
    paging: tuple[int, int] = Depends(page_params),
    db: Session = Depends(get_db),
    _user=Depends(require_role("admin", "operator")),
) -> StationsResponse:
    limit, offset = paging
    stmt = select(Station).where(Station.site_id == site_id).order_by(Station.label)
    if state:
        stmt = stmt.where(Station.state == state)
    total = _total(db, stmt)
    stations = _paged(db, stmt, limit, offset)
    items = [_station(station) for station in stations]
    return StationsResponse(items=items, meta=_meta(items, limit, offset, total))


@router.get("/stations/{station_id}", response_model=ItemResponse)
async def get_station(station_id: str, db: Session = Depends(get_db), _user=Depends(require_role("admin", "operator"))) -> ItemResponse:
    station = db.get(Station, station_id)
    return ItemResponse(item=None if station is None else _station(station))


@router.get("/stations/{station_id}/connectors", response_model=ConnectorsResponse)
async def list_station_connectors(
    station_id: str,
    state: str | None = None,
    paging: tuple[int, int] = Depends(page_params),
    db: Session = Depends(get_db),
    _user=Depends(require_role("admin", "operator")),
) -> ConnectorsResponse:
    limit, offset = paging
    stmt = select(Connector).where(Connector.station_id == station_id).order_by(Connector.connector_number)
    if state:
        stmt = stmt.where(Connector.state == state)
    total = _total(db, stmt)
    connectors = _paged(db, stmt, limit, offset)
    items = [
        {
            "id": connector.id,
            "station_id": connector.station_id,
            "connector_number": connector.connector_number,
            "state": connector.state,
            "error_code": connector.error_code,
        }
        for connector in connectors
    ]
    return ConnectorsResponse(items=items, meta=_meta(items, limit, offset, total))
