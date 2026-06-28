from __future__ import annotations

from sqlalchemy import select

import pytest

from app.models.entities import (
    AuditEvent,
    ChargingSession,
    Connector,
    ConnectorState,
    MeterValue,
    OutboxEvent,
    OutboxStatus,
    SessionState,
    Site,
    Station,
    StationState,
    Transaction,
    TransactionState,
)
from app.services.outbox import process_outbox_event
from app.services.ingestion import ingest_ocpp_message


def test_ocpp_message_ingestion_is_idempotent(db_session) -> None:
    site = Site(slug="test-site", label="Test Site")
    db_session.add(site)
    db_session.flush()
    station = Station(site_id=site.id, external_id="ST-1", label="Station 1", state=StationState.ONLINE.value, online=True)
    db_session.add(station)
    db_session.flush()
    db_session.add(Connector(station_id=station.id, connector_number=1))
    db_session.commit()

    message = '[2,"msg-001","BootNotification",{"chargePointVendor":"OCPP-Demo","chargePointModel":"Demo"}]'
    first = ingest_ocpp_message(db_session, station.id, message)
    second = ingest_ocpp_message(db_session, station.id, message)

    assert first["duplicate"] is False
    assert second["duplicate"] is True


def test_ocpp_ingestion_records_state_history(db_session) -> None:
    site = Site(slug="history-site", label="History Site")
    db_session.add(site)
    db_session.flush()
    station = Station(site_id=site.id, external_id="ST-2", label="Station 2", state=StationState.UNKNOWN.value, online=False)
    db_session.add(station)
    db_session.flush()
    db_session.add(Connector(station_id=station.id, connector_number=1))
    db_session.commit()

    ingest_ocpp_message(db_session, station.id, '[2,"msg-002","BootNotification",{"chargePointVendor":"OCPP-Demo","chargePointModel":"Demo"}]')

    history = list(db_session.scalars(select(AuditEvent).order_by(AuditEvent.created_at.asc())))
    assert any(event.entity_type == "station" and event.action == "station_state_changed" for event in history)


def test_ocpp_ingestion_rejects_illegal_connector_transition(db_session) -> None:
    site = Site(slug="transition-site", label="Transition Site")
    db_session.add(site)
    db_session.flush()
    station = Station(site_id=site.id, external_id="ST-3", label="Station 3", state=StationState.ONLINE.value, online=True)
    db_session.add(station)
    db_session.flush()
    db_session.add(
        Connector(
            station_id=station.id,
            connector_number=1,
            state=ConnectorState.FAULTED.value,
        )
    )
    db_session.commit()

    with pytest.raises(ValueError, match="Illegal connector state transition"):
        ingest_ocpp_message(
            db_session,
            station.id,
            '[2,"msg-003","StartTransaction",{"connectorId":1,"idTag":"ABC","meterStart":0,"timestamp":"2026-06-26T12:00:00Z"}]',
        )


def test_ocpp_ingestion_rejects_malformed_call(db_session) -> None:
    site = Site(slug="malformed-site", label="Malformed Site")
    db_session.add(site)
    db_session.flush()
    station = Station(site_id=site.id, external_id="ST-BAD", label="Station Bad", state=StationState.ONLINE.value, online=True)
    db_session.add(station)
    db_session.commit()

    with pytest.raises(ValueError, match="4-element array"):
        ingest_ocpp_message(db_session, station.id, '[2,"bad","Heartbeat"]')


def test_ocpp_ingestion_rejects_unsupported_action(db_session) -> None:
    site = Site(slug="unsupported-site", label="Unsupported Site")
    db_session.add(site)
    db_session.flush()
    station = Station(site_id=site.id, external_id="ST-UNSUPPORTED", label="Station Unsupported", state=StationState.ONLINE.value, online=True)
    db_session.add(station)
    db_session.commit()

    with pytest.raises(ValueError, match="Unsupported action"):
        ingest_ocpp_message(db_session, station.id, '[2,"bad-action","DataTransfer",{}]')


def test_outbox_event_dead_letters_after_handler_failure(db_session, monkeypatch) -> None:
    event = OutboxEvent(
        event_type="ocpp.bootnotification",
        aggregate_type="station",
        aggregate_id="station-1",
        status=OutboxStatus.PENDING.value,
        max_attempts=1,
        payload={"station_id": "station-1"},
    )
    db_session.add(event)
    db_session.commit()

    from app.repositories.outbox import OutboxRepository

    def boom(self, *_args, **_kwargs):  # noqa: ANN001
        raise RuntimeError("boom")

    monkeypatch.setattr(OutboxRepository, "mark_processed", boom)

    result = process_outbox_event(db_session, event)

    assert result.status == OutboxStatus.DEAD_LETTERED.value
    assert "boom" in result.message


def test_duplicate_meter_value_payload_is_idempotent(db_session) -> None:
    site = Site(slug="meter-site", label="Meter Site")
    db_session.add(site)
    db_session.flush()
    station = Station(site_id=site.id, external_id="ST-METER", label="Station Meter", state=StationState.ONLINE.value, online=True)
    db_session.add(station)
    db_session.flush()
    db_session.add(Connector(station_id=station.id, connector_number=1, state=ConnectorState.AVAILABLE.value))
    db_session.commit()

    ingest_ocpp_message(
        db_session,
        station.id,
        '[2,"start-meter","StartTransaction",{"connectorId":1,"idTag":"ABC","meterStart":0,"transactionId":7001}]',
    )
    meter_payload = '{"transactionId":7001,"connectorId":1,"meterValue":[{"timestamp":"2026-06-26T12:00:00Z","sampledValue":[{"value":"42.5","unit":"kWh"}]}]}'
    ingest_ocpp_message(db_session, station.id, f'[2,"meter-a","MeterValues",{meter_payload}]')
    ingest_ocpp_message(db_session, station.id, f'[2,"meter-b","MeterValues",{meter_payload}]')

    meter_values = list(db_session.query(MeterValue).all())
    duplicate_events = list(db_session.query(AuditEvent).filter(AuditEvent.action == "duplicate_meter_value_ignored").all())

    assert len(meter_values) == 1
    assert len(duplicate_events) == 1


def test_ocpp_happy_path_lifecycle(db_session) -> None:
    site = Site(slug="happy-site", label="Happy Site")
    db_session.add(site)
    db_session.flush()
    station = Station(site_id=site.id, external_id="ST-HAPPY", label="Station Happy", state=StationState.UNKNOWN.value, online=False)
    db_session.add(station)
    db_session.flush()
    connector = Connector(station_id=station.id, connector_number=1, state=ConnectorState.AVAILABLE.value)
    db_session.add(connector)
    db_session.commit()

    ingest_ocpp_message(db_session, "ST-HAPPY", '[2,"boot-happy","BootNotification",{"chargePointVendor":"OCPP-Demo","chargePointModel":"Demo"}]')
    ingest_ocpp_message(db_session, "ST-HAPPY", '[2,"auth-happy","Authorize",{"idTag":"ABC"}]')
    ingest_ocpp_message(
        db_session,
        "ST-HAPPY",
        '[2,"start-happy","StartTransaction",{"connectorId":1,"idTag":"ABC","meterStart":0,"transactionId":8801}]',
    )
    ingest_ocpp_message(
        db_session,
        "ST-HAPPY",
        '[2,"meter-happy","MeterValues",{"transactionId":8801,"connectorId":1,"meterValue":[{"timestamp":"2026-06-26T12:05:00Z","sampledValue":[{"value":"12.5","unit":"kWh"}]}]}]',
    )
    ingest_ocpp_message(db_session, "ST-HAPPY", '[2,"stop-happy","StopTransaction",{"transactionId":8801,"meterStop":13,"reason":"Local"}]')

    session = db_session.query(ChargingSession).one()
    transaction = db_session.query(Transaction).one()
    db_session.refresh(station)
    db_session.refresh(connector)

    assert station.online is True
    assert session.state == SessionState.COMPLETED.value
    assert session.transaction_state == TransactionState.CLOSED.value
    assert transaction.state == TransactionState.CLOSED.value
    assert connector.state == ConnectorState.AVAILABLE.value
    assert db_session.query(MeterValue).count() == 1


def test_ocpp_interrupted_session_lifecycle(db_session) -> None:
    site = Site(slug="interrupt-site", label="Interrupt Site")
    db_session.add(site)
    db_session.flush()
    station = Station(site_id=site.id, external_id="ST-INTERRUPT", label="Station Interrupt", state=StationState.ONLINE.value, online=True)
    db_session.add(station)
    db_session.flush()
    connector = Connector(station_id=station.id, connector_number=1, state=ConnectorState.AVAILABLE.value)
    db_session.add(connector)
    db_session.commit()

    ingest_ocpp_message(
        db_session,
        "ST-INTERRUPT",
        '[2,"start-interrupt","StartTransaction",{"connectorId":1,"idTag":"ABC","meterStart":0,"transactionId":9902}]',
    )
    ingest_ocpp_message(
        db_session,
        "ST-INTERRUPT",
        '[2,"status-interrupt","StatusNotification",{"connectorId":1,"status":"SuspendedEVSE","errorCode":"NoError"}]',
    )

    session = db_session.query(ChargingSession).one()
    db_session.refresh(connector)

    assert session.state == SessionState.INTERRUPTED.value
    assert connector.state == ConnectorState.SUSPENDED_EVSE.value
