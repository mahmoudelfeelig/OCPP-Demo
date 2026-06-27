from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.models.entities import OutboxEvent, OutboxStatus
from app.repositories.outbox import OutboxRepository
from app.services.outbox import process_outbox_event


def test_outbox_event_processes_successfully(db_session) -> None:
    event = OutboxEvent(
        event_type="ocpp.bootnotification",
        aggregate_type="station",
        aggregate_id="station-1",
        status=OutboxStatus.PENDING.value,
        payload={"station_id": "station-1"},
    )
    db_session.add(event)
    db_session.commit()

    result = process_outbox_event(db_session, event)

    assert result.status == OutboxStatus.PROCESSED.value


def test_outbox_retry_sets_backoff(db_session) -> None:
    event = OutboxEvent(
        event_type="ocpp.bootnotification",
        aggregate_type="station",
        aggregate_id="station-1",
        status=OutboxStatus.PENDING.value,
        payload={"station_id": "station-1"},
    )
    db_session.add(event)
    db_session.commit()

    repo = OutboxRepository(db_session)
    repo.mark_retrying(event, "temporary failure", backoff_seconds=15)
    db_session.commit()

    assert event.status == OutboxStatus.RETRYING.value
    assert event.attempts == 1
    assert event.next_attempt_at is not None


def test_outbox_recovers_stale_processing_locks(db_session) -> None:
    event = OutboxEvent(
        event_type="ocpp.heartbeat",
        aggregate_type="station",
        aggregate_id="station-1",
        status=OutboxStatus.PROCESSING.value,
        locked_at=datetime.now(UTC) - timedelta(minutes=10),
        locked_by="worker-old",
        payload={"station_id": "station-1"},
    )
    db_session.add(event)
    db_session.commit()

    recovered = OutboxRepository(db_session).recover_stale_processing(older_than_seconds=300)
    db_session.commit()

    assert recovered == 1
    assert event.status == OutboxStatus.RETRYING.value
    assert event.locked_at is None
    assert event.locked_by is None
    assert event.last_error == "Recovered stale processing lock"


def test_acknowledge_dead_letter_preserves_terminal_status(db_session) -> None:
    event = OutboxEvent(
        event_type="ocpp.bootnotification",
        aggregate_type="station",
        aggregate_id="station-1",
        status=OutboxStatus.DEAD_LETTERED.value,
        last_error="permanent failure",
        payload={"station_id": "station-1"},
    )
    db_session.add(event)
    db_session.commit()

    OutboxRepository(db_session).acknowledge_dead_letter(event, "admin-user")
    db_session.commit()

    assert event.status == OutboxStatus.DEAD_LETTERED.value
    assert event.last_error == "permanent failure"
    assert event.acknowledged_at is not None
    assert event.acknowledged_by == "admin-user"
