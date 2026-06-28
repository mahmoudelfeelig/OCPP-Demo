from __future__ import annotations

import json
from datetime import UTC, datetime
import zlib
from typing import Any

from opentelemetry import trace
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.metrics import failed_messages, processed_messages
from app.models.entities import (
    AuditEvent,
    ChargingSession,
    Connector,
    ConnectorState,
    MeterValue,
    OcppMessage,
    OutboxEvent,
    OutboxStatus,
    SessionState,
    Station,
    StationState,
    Transaction,
    TransactionState,
)
from app.repositories.messages import MessageRepository
from app.repositories.outbox import OutboxRepository

tracer = trace.get_tracer(__name__)


SUPPORTED_ACTIONS = {
    "BootNotification",
    "Heartbeat",
    "StatusNotification",
    "Authorize",
    "StartTransaction",
    "MeterValues",
    "StopTransaction",
}

STATION_TRANSITIONS = {
    "unknown": {"online", "offline", "faulted"},
    "online": {"offline", "faulted"},
    "offline": {"online", "faulted"},
    "faulted": {"online", "offline"},
}

CONNECTOR_TRANSITIONS = {
    "available": {"occupied", "charging", "suspended_ev", "suspended_evse", "finishing", "reserved", "unavailable", "faulted"},
    "occupied": {"available", "charging", "suspended_ev", "suspended_evse", "finishing", "unavailable", "faulted"},
    "charging": {"available", "suspended_ev", "suspended_evse", "finishing", "unavailable", "faulted"},
    "suspended_ev": {"available", "charging", "finishing", "unavailable", "faulted"},
    "suspended_evse": {"available", "charging", "finishing", "unavailable", "faulted"},
    "finishing": {"available", "unavailable", "faulted"},
    "reserved": {"available", "occupied", "unavailable", "faulted"},
    "unavailable": {"available", "faulted"},
    "faulted": {"available", "unavailable"},
}

SESSION_TRANSITIONS = {
    "requested": {"starting", "active", "failed", "interrupted"},
    "starting": {"active", "failed", "interrupted"},
    "active": {"stopping", "completed", "failed", "interrupted"},
    "stopping": {"completed", "failed", "interrupted"},
    "completed": set(),
    "failed": set(),
    "interrupted": {"failed", "completed"},
}

TRANSACTION_TRANSITIONS = {
    "open": {"closing", "closed", "failed"},
    "closing": {"closed", "failed"},
    "closed": {"reconciled", "failed"},
    "reconciled": set(),
    "failed": set(),
}


def _ocpp_response(action: str, message_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    if action == "BootNotification":
        return {"currentTime": now, "interval": 300, "status": "Accepted"}
    if action == "Heartbeat":
        return {"currentTime": now}
    if action == "Authorize":
        return {"idTagInfo": {"status": "Accepted"}}
    if action == "StartTransaction":
        return {
            "transactionId": _transaction_id_for_message(message_id),
            "idTagInfo": {"status": "Accepted"},
        }
    return {}


def _transaction_id_for_message(message_id: str) -> int:
    return int(zlib.crc32(message_id.encode("utf-8")))


def extract_ocpp_message_id(message_text: str) -> str | None:
    try:
        frame = json.loads(message_text)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(frame, list) or len(frame) < 2:
        return None
    message_id = frame[1]
    return message_id if isinstance(message_id, str) and message_id else None


def _require_fields(action: str, payload: dict[str, Any], fields: tuple[str, ...]) -> None:
    missing = [field for field in fields if field not in payload or payload[field] is None]
    if missing:
        raise ValueError(f"{action} payload missing required field(s): {', '.join(missing)}")


def _validate_timestamp(action: str, field: str, value: Any) -> None:
    if not isinstance(value, str):
        raise ValueError(f"{action}.{field} must be an ISO-8601 timestamp")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{action}.{field} must be an ISO-8601 timestamp") from exc


def _validate_payload(action: str, payload: dict[str, Any]) -> None:
    required_fields = {
        "BootNotification": ("chargePointVendor", "chargePointModel"),
        "Heartbeat": (),
        "StatusNotification": ("connectorId", "errorCode", "status"),
        "Authorize": ("idTag",),
        "StartTransaction": ("connectorId", "idTag", "meterStart", "timestamp"),
        "MeterValues": ("connectorId", "meterValue"),
        "StopTransaction": ("meterStop", "timestamp", "transactionId"),
    }
    _require_fields(action, payload, required_fields[action])

    if action in {"StatusNotification", "StartTransaction", "MeterValues"}:
        try:
            connector_id = int(payload["connectorId"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{action}.connectorId must be an integer") from exc
        if connector_id < 0:
            raise ValueError(f"{action}.connectorId must be non-negative")

    if action in {"StartTransaction", "StopTransaction"}:
        _validate_timestamp(action, "timestamp", payload["timestamp"])

    if action == "StartTransaction" and "transactionId" in payload:
        raise ValueError("StartTransaction.transactionId is assigned by the central system and must not be sent")

    if action == "MeterValues":
        meter_values = payload["meterValue"]
        if not isinstance(meter_values, list) or not meter_values:
            raise ValueError("MeterValues.meterValue must be a non-empty array")
        for index, meter_value in enumerate(meter_values):
            if not isinstance(meter_value, dict):
                raise ValueError(f"MeterValues.meterValue[{index}] must be an object")
            _require_fields("MeterValues", meter_value, ("timestamp", "sampledValue"))
            _validate_timestamp("MeterValues", f"meterValue[{index}].timestamp", meter_value["timestamp"])
            sampled_values = meter_value["sampledValue"]
            if not isinstance(sampled_values, list) or not sampled_values:
                raise ValueError(f"MeterValues.meterValue[{index}].sampledValue must be a non-empty array")
            for sample_index, sample in enumerate(sampled_values):
                if not isinstance(sample, dict) or "value" not in sample:
                    raise ValueError(
                        f"MeterValues.meterValue[{index}].sampledValue[{sample_index}] must contain value"
                    )
                try:
                    float(sample["value"])
                except (TypeError, ValueError) as exc:
                    raise ValueError(
                        f"MeterValues.meterValue[{index}].sampledValue[{sample_index}].value must be numeric"
                    ) from exc


def _parse_message(message_text: str) -> tuple[str, str, str, dict[str, Any]]:
    payload = json.loads(message_text)
    if not isinstance(payload, list) or len(payload) != 4:
        raise ValueError("OCPP payload must be a 4-element array")
    message_type_id, message_id, action, action_payload = payload
    if message_type_id != 2:
        raise ValueError("Only CALL messages are supported by the demo")
    if action not in SUPPORTED_ACTIONS:
        raise ValueError(f"Unsupported action: {action}")
    if not isinstance(action_payload, dict):
        raise ValueError("OCPP CALL payload must be an object")
    _validate_payload(str(action), action_payload)
    return str(message_type_id), str(message_id), str(action), action_payload


def _validate_transition(entity: str, previous: str, current: str, allowed: dict[str, set[str]]) -> None:
    if previous == current:
        return
    if current not in allowed.get(previous, set()):
        raise ValueError(f"Illegal {entity} state transition: {previous} -> {current}")


def _record_transition(
    db: Session,
    *,
    entity_type: str,
    entity_id: str,
    field: str,
    previous: str,
    current: str,
    source: str,
    payload: dict[str, Any],
) -> None:
    if previous == current:
        return
    db.add(
        AuditEvent(
            action=f"{entity_type}_{field}_changed",
            entity_type=entity_type,
            entity_id=entity_id,
            payload={
                "field": field,
                "from": previous,
                "to": current,
                "source": source,
                "payload": payload,
            },
        )
    )


def ingest_ocpp_message(db: Session, station_id: str, message_text: str) -> dict[str, Any]:
    with tracer.start_as_current_span("ocpp.ingest") as span:
        try:
            message_type_id, message_id, action, payload = _parse_message(message_text)
            span.set_attribute("ocpp.station_id", station_id)
            span.set_attribute("ocpp.action", action)
            existing = MessageRepository(db).get_by_message_id(message_id)
            if existing is not None:
                processed_messages.inc()
                return {
                    "message_id": existing.message_id,
                    "status": existing.status,
                    "action": existing.action,
                    "duplicate": True,
                    "response_payload": _ocpp_response(existing.action, existing.message_id, existing.payload),
                }

            station = db.get(Station, station_id)
            if station is None:
                station = db.scalar(select(Station).where(Station.external_id == station_id))
            if station is None:
                raise LookupError("Station not found")

            message = OcppMessage(
                station_id=station.id,
                direction="inbound",
                action=action,
                message_id=message_id,
                payload=payload,
                raw_message_text=message_text,
                status="received",
                received_at=datetime.now(UTC),
            )
            db.add(message)
            db.flush()

            outbox = OutboxEvent(
                message_id=message.id,
                event_type=f"ocpp.{action.lower()}",
                aggregate_type="station",
                aggregate_id=station.id,
                status=OutboxStatus.PENDING.value,
                payload={
                    "station_id": station.id,
                    "station_external_id": station.external_id,
                    "message_id": message_id,
                    "message_type_id": message_type_id,
                    "action": action,
                    "payload": payload,
                },
            )
            OutboxRepository(db).enqueue(outbox)

            if action in {"BootNotification", "Heartbeat"}:
                previous_state = station.state
                _validate_transition("station", previous_state, StationState.ONLINE.value, STATION_TRANSITIONS)
                _record_transition(
                    db,
                    entity_type="station",
                    entity_id=station.id,
                    field="state",
                    previous=previous_state,
                    current=StationState.ONLINE.value,
                    source=action,
                    payload=payload,
                )
                station.state = StationState.ONLINE.value
                station.online = True
                station.last_seen_at = datetime.now(UTC)

            if action == "StatusNotification":
                next_station_state = StationState.ONLINE.value
                if payload.get("status") in {"Unavailable", "Faulted"}:
                    next_station_state = StationState.OFFLINE.value if payload.get("status") == "Unavailable" else StationState.FAULTED.value
                _validate_transition("station", station.state, next_station_state, STATION_TRANSITIONS)
                _record_transition(
                    db,
                    entity_type="station",
                    entity_id=station.id,
                    field="state",
                    previous=station.state,
                    current=next_station_state,
                    source=action,
                    payload=payload,
                )
                station.state = next_station_state
                station.online = payload.get("status") != "Unavailable"
                station.last_seen_at = datetime.now(UTC)
                connector_number = int(payload.get("connectorId", 1))
                connector = next((item for item in station.connectors if item.connector_number == connector_number), None)
                if connector is None:
                    connector = Connector(station_id=station.id, connector_number=connector_number)
                    db.add(connector)
                status_map = {
                    "Available": ConnectorState.AVAILABLE.value,
                    "Occupied": ConnectorState.OCCUPIED.value,
                    "Charging": ConnectorState.CHARGING.value,
                    "SuspendedEV": ConnectorState.SUSPENDED_EV.value,
                    "SuspendedEVSE": ConnectorState.SUSPENDED_EVSE.value,
                    "Finishing": ConnectorState.FINISHING.value,
                    "Reserved": ConnectorState.RESERVED.value,
                    "Unavailable": ConnectorState.UNAVAILABLE.value,
                    "Faulted": ConnectorState.FAULTED.value,
                }
                next_connector_state = status_map.get(payload.get("status"), connector.state)
                _validate_transition("connector", connector.state, next_connector_state, CONNECTOR_TRANSITIONS)
                _record_transition(
                    db,
                    entity_type="connector",
                    entity_id=connector.id,
                    field="state",
                    previous=connector.state,
                    current=next_connector_state,
                    source=action,
                    payload=payload,
                )
                connector.state = next_connector_state
                connector.error_code = payload.get("errorCode")
                connector.last_seen_at = datetime.now(UTC)
                if next_connector_state in {ConnectorState.SUSPENDED_EV.value, ConnectorState.SUSPENDED_EVSE.value, ConnectorState.FAULTED.value}:
                    active_session = db.scalar(
                        select(ChargingSession).where(
                            ChargingSession.connector_id == connector.id,
                            ChargingSession.state.in_([SessionState.ACTIVE.value, SessionState.STARTING.value]),
                        )
                    )
                    if active_session is not None:
                        _validate_transition("session", active_session.state, SessionState.INTERRUPTED.value, SESSION_TRANSITIONS)
                        _record_transition(
                            db,
                            entity_type="session",
                            entity_id=active_session.id,
                            field="state",
                            previous=active_session.state,
                            current=SessionState.INTERRUPTED.value,
                            source=action,
                            payload=payload,
                        )
                        active_session.state = SessionState.INTERRUPTED.value

            if action == "StartTransaction":
                connector_number = int(payload.get("connectorId", 1))
                ocpp_transaction_id = str(_transaction_id_for_message(message_id))
                connector = next((item for item in station.connectors if item.connector_number == connector_number), None)
                if connector is None:
                    connector = Connector(station_id=station.id, connector_number=connector_number, state=ConnectorState.OCCUPIED.value)
                    db.add(connector)
                    db.flush()
                external_session_id = f"session-{message_id}"
                session = db.scalar(select(ChargingSession).where(ChargingSession.external_session_id == external_session_id))
                if session is None:
                    session = ChargingSession(
                        site_id=station.site_id,
                        station_id=station.id,
                        connector_id=connector.id,
                        external_session_id=external_session_id,
                        state=SessionState.ACTIVE.value,
                        transaction_state=TransactionState.OPEN.value,
                        started_at=datetime.now(UTC),
                    )
                    db.add(session)
                    db.flush()
                if session.transaction is None:
                    db.add(
                        Transaction(
                            session_id=session.id,
                            ocpp_transaction_id=ocpp_transaction_id,
                            state=TransactionState.OPEN.value,
                            started_at=datetime.now(UTC),
                        )
                    )
                _validate_transition("session", session.state, SessionState.ACTIVE.value, SESSION_TRANSITIONS)
                _record_transition(
                    db,
                    entity_type="session",
                    entity_id=session.id,
                    field="state",
                    previous=session.state,
                    current=SessionState.ACTIVE.value,
                    source=action,
                    payload=payload,
                )
                _validate_transition("transaction", session.transaction.state if session.transaction else TransactionState.OPEN.value, TransactionState.OPEN.value, TRANSACTION_TRANSITIONS)
                if session.transaction is not None:
                    _record_transition(
                        db,
                        entity_type="transaction",
                        entity_id=session.transaction.id,
                        field="state",
                        previous=session.transaction.state,
                        current=TransactionState.OPEN.value,
                        source=action,
                        payload=payload,
                    )
                    session.transaction.state = TransactionState.OPEN.value
                station.state = StationState.ONLINE.value
                station.online = True
                _validate_transition("connector", connector.state, ConnectorState.CHARGING.value, CONNECTOR_TRANSITIONS)
                _record_transition(
                    db,
                    entity_type="connector",
                    entity_id=connector.id,
                    field="state",
                    previous=connector.state,
                    current=ConnectorState.CHARGING.value,
                    source=action,
                    payload=payload,
                )
                connector.state = ConnectorState.CHARGING.value

            if action == "MeterValues":
                transaction_id = payload.get("transactionId")
                txn = (
                    db.scalar(select(Transaction).where(Transaction.ocpp_transaction_id == str(transaction_id)))
                    if transaction_id is not None
                    else None
                )
                if txn is not None:
                    meter_value = payload["meterValue"][0]
                    sample = meter_value["sampledValue"][0]
                    timestamp_text = meter_value["timestamp"].replace("Z", "+00:00")
                    sampled_at = datetime.fromisoformat(timestamp_text)
                    value_kwh = float(sample.get("value", 0.0))
                    existing_meter_value = db.scalar(
                        select(MeterValue).where(
                            MeterValue.transaction_id == txn.id,
                            MeterValue.sampled_at == sampled_at,
                            MeterValue.value_kwh == value_kwh,
                        )
                    )
                    if existing_meter_value is None:
                        db.add(
                            MeterValue(
                                session_id=txn.session_id,
                                transaction_id=txn.id,
                                message_id=message_id,
                                sampled_at=sampled_at,
                                value_kwh=value_kwh,
                                unit=sample.get("unit", "kWh"),
                                raw_payload=payload,
                            )
                        )
                    else:
                        db.add(
                            AuditEvent(
                                action="duplicate_meter_value_ignored",
                                entity_type="meter_value",
                                entity_id=existing_meter_value.id,
                                payload={"message_id": message_id, "transaction_id": transaction_id},
                            )
                        )

            if action == "StopTransaction":
                transaction_id = str(payload.get("transactionId", message_id))
                txn = db.scalar(select(Transaction).where(Transaction.ocpp_transaction_id == transaction_id))
                if txn is not None:
                    _validate_transition("transaction", txn.state, TransactionState.CLOSED.value, TRANSACTION_TRANSITIONS)
                    _record_transition(
                        db,
                        entity_type="transaction",
                        entity_id=txn.id,
                        field="state",
                        previous=txn.state,
                        current=TransactionState.CLOSED.value,
                        source=action,
                        payload=payload,
                    )
                    txn.state = TransactionState.CLOSED.value
                    txn.stopped_at = datetime.now(UTC)
                    txn.stop_reason = payload.get("reason")
                    session = txn.session
                    _validate_transition("session", session.state, SessionState.COMPLETED.value, SESSION_TRANSITIONS)
                    _record_transition(
                        db,
                        entity_type="session",
                        entity_id=session.id,
                        field="state",
                        previous=session.state,
                        current=SessionState.COMPLETED.value,
                        source=action,
                        payload=payload,
                    )
                    session.state = SessionState.COMPLETED.value
                    session.transaction_state = TransactionState.CLOSED.value
                    session.ended_at = datetime.now(UTC)
                    if session.connector is not None:
                        _validate_transition("connector", session.connector.state, ConnectorState.AVAILABLE.value, CONNECTOR_TRANSITIONS)
                        _record_transition(
                            db,
                            entity_type="connector",
                            entity_id=session.connector.id,
                            field="state",
                            previous=session.connector.state,
                            current=ConnectorState.AVAILABLE.value,
                            source=action,
                            payload=payload,
                        )
                        session.connector.state = ConnectorState.AVAILABLE.value

            if action == "Authorize":
                station.last_seen_at = datetime.now(UTC)

            db.commit()
            processed_messages.inc()
            return {
                "message_id": message_id,
                "status": "accepted",
                "action": action,
                "duplicate": False,
                "response_payload": _ocpp_response(action, message_id, payload),
            }
        except Exception:
            failed_messages.inc()
            raise
