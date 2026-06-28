from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, select, update
from sqlalchemy.orm import Session

from app.models.entities import OutboxEvent, OutboxStatus


class OutboxRepository:
    def __init__(self, db: Session):
        self.db = db

    def enqueue(self, event: OutboxEvent) -> OutboxEvent:
        self.db.add(event)
        self.db.flush()
        return event

    def list_due(self, limit: int = 25) -> list[OutboxEvent]:
        now = datetime.now(UTC)
        stmt = (
            select(OutboxEvent)
            .where(
                and_(
                    OutboxEvent.status.in_([OutboxStatus.PENDING.value, OutboxStatus.RETRYING.value]),
                    (OutboxEvent.next_attempt_at.is_(None) | (OutboxEvent.next_attempt_at <= now)),
                )
            )
            .order_by(OutboxEvent.created_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list(self.db.scalars(stmt))

    def claim_due(self, worker_id: str, limit: int = 25) -> list[OutboxEvent]:
        events = self.list_due(limit=limit)
        for event in events:
            self.lock(event, worker_id)
        return events

    def recover_stale_processing(self, older_than_seconds: int = 300) -> int:
        stale_before = datetime.now(UTC) - timedelta(seconds=older_than_seconds)
        result = self.db.execute(
            update(OutboxEvent)
            .where(
                and_(
                    OutboxEvent.status == OutboxStatus.PROCESSING.value,
                    OutboxEvent.locked_at.is_not(None),
                    OutboxEvent.locked_at <= stale_before,
                )
            )
            .values(
                status=OutboxStatus.RETRYING.value,
                next_attempt_at=datetime.now(UTC),
                locked_at=None,
                locked_by=None,
                last_error="Recovered stale processing lock",
            )
        )
        self.db.flush()
        return result.rowcount or 0

    def lock(self, event: OutboxEvent, worker_id: str) -> None:
        now = datetime.now(UTC)
        event.status = OutboxStatus.PROCESSING.value
        event.locked_at = now
        event.locked_by = worker_id
        self.db.flush()

    def mark_processed(self, event: OutboxEvent) -> None:
        event.status = OutboxStatus.PROCESSED.value
        event.processed_at = datetime.now(UTC)
        event.last_error = None
        event.locked_at = None
        event.locked_by = None
        self.db.flush()

    def mark_retrying(self, event: OutboxEvent, error: str, backoff_seconds: int) -> None:
        event.attempts += 1
        event.last_error = error
        event.status = OutboxStatus.RETRYING.value
        event.next_attempt_at = datetime.now(UTC) + timedelta(seconds=backoff_seconds)
        event.locked_at = None
        event.locked_by = None
        self.db.flush()

    def mark_failed(self, event: OutboxEvent, error: str) -> None:
        event.status = OutboxStatus.FAILED.value
        event.last_error = error
        event.locked_at = None
        event.locked_by = None
        self.db.flush()

    def mark_dead_lettered(self, event: OutboxEvent, error: str) -> None:
        event.status = OutboxStatus.DEAD_LETTERED.value
        event.last_error = error
        event.locked_at = None
        event.locked_by = None
        self.db.flush()

    def acknowledge_dead_letter(self, event: OutboxEvent, user_id: str) -> None:
        event.acknowledged_at = datetime.now(UTC)
        event.acknowledged_by = user_id
        event.locked_at = None
        event.locked_by = None
        self.db.flush()
