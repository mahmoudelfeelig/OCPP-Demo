from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.entities import (
    AuditEvent,
    ChargingSession,
    Connector,
    ConnectorState,
    OcppMessage,
    OutboxEvent,
    OutboxStatus,
    PartnerEvent,
    PartnerEventStatus,
    Role,
    SessionState,
    Site,
    Station,
    StationState,
    Transaction,
    TransactionState,
    User,
)


def seed_demo_data(db: Session) -> None:
    if db.scalar(select(Site.id).limit(1)) is not None:
        return

    admin_role = Role(name="admin", description="Full operational access")
    operator_role = Role(name="operator", description="Operational view and safe actions")
    db.add_all([admin_role, operator_role])
    db.flush()

    admin_user = User(
        email="admin@localhost",
        password_hash=hash_password("admin123"),
        role_id=admin_role.id,
        display_name="Local Admin",
    )
    operator_user = User(
        email="operator@localhost",
        password_hash=hash_password("operator123"),
        role_id=operator_role.id,
        display_name="Local Operator",
    )
    db.add_all([admin_user, operator_user])

    sites = [
        Site(slug="berlin-mitte", label="Berlin Mitte"),
        Site(slug="hamburg-harbor", label="Hamburg Harbor"),
        Site(slug="munich-south", label="Munich South"),
    ]
    db.add_all(sites)
    db.flush()

    seeded_at = datetime.now(UTC)
    stations = [
        Station(
            site_id=sites[0].id,
            external_id="BER-001",
            label="Mitte North Bay",
            state=StationState.ONLINE.value,
            online=True,
            last_seen_at=seeded_at,
        ),
        Station(site_id=sites[0].id, external_id="BER-002", label="Mitte South Bay", state=StationState.OFFLINE.value, online=False),
        Station(
            site_id=sites[1].id,
            external_id="HAM-001",
            label="Harbor Fast DC",
            state=StationState.ONLINE.value,
            online=True,
            last_seen_at=seeded_at,
        ),
        Station(site_id=sites[2].id, external_id="MUC-001", label="South Plaza", state=StationState.FAULTED.value, online=False),
    ]
    db.add_all(stations)
    db.flush()

    connectors = [
        Connector(station_id=stations[0].id, connector_number=1, state=ConnectorState.CHARGING.value),
        Connector(station_id=stations[0].id, connector_number=2, state=ConnectorState.AVAILABLE.value),
        Connector(station_id=stations[1].id, connector_number=1, state=ConnectorState.UNAVAILABLE.value),
        Connector(station_id=stations[2].id, connector_number=1, state=ConnectorState.OCCUPIED.value),
        Connector(station_id=stations[3].id, connector_number=1, state=ConnectorState.FAULTED.value, error_code="GroundFailure"),
    ]
    db.add_all(connectors)
    db.flush()

    session = ChargingSession(
        site_id=sites[0].id,
        station_id=stations[0].id,
        connector_id=connectors[0].id,
        external_session_id="sess-ber-001",
        state=SessionState.ACTIVE.value,
        transaction_state=TransactionState.OPEN.value,
        started_at=datetime.now(UTC),
    )
    db.add(session)
    db.flush()

    txn = Transaction(
        session_id=session.id,
        ocpp_transaction_id="txn-1001",
        state=TransactionState.OPEN.value,
        started_at=datetime.now(UTC),
    )
    db.add(txn)

    ocpp_message = OcppMessage(
        station_id=stations[0].id,
        direction="inbound",
        action="BootNotification",
        message_id="boot-001",
        payload={"chargePointVendor": "OCPP-Demo", "chargePointModel": "Demo DC"},
        raw_message_text='[2,"boot-001","BootNotification",{"chargePointVendor":"OCPP-Demo","chargePointModel":"Demo DC"}]',
    )
    db.add(ocpp_message)
    db.flush()

    outbox = OutboxEvent(
        message_id=ocpp_message.id,
        event_type="station.boot_notification.received",
        aggregate_type="station",
        aggregate_id=stations[0].id,
        status=OutboxStatus.PENDING.value,
        payload={"station_id": stations[0].id, "message_id": ocpp_message.message_id},
    )
    db.add(outbox)

    partner_event = PartnerEvent(
        event_id="partner-evt-001",
        signature_valid=True,
        status=PartnerEventStatus.PROCESSED.value,
        raw_payload_text='{"event_id":"partner-evt-001","type":"session.completed"}',
        payload={"event_id": "partner-evt-001", "type": "session.completed"},
        received_at=datetime.now(UTC),
        processed_at=datetime.now(UTC),
    )
    db.add(partner_event)

    db.add(
        AuditEvent(
            actor_user_id=admin_user.id,
            action="seed_demo_data",
            entity_type="system",
            entity_id="demo",
            payload={"sites": len(sites)},
        )
    )

    db.commit()
