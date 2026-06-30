from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from opentelemetry import trace
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.metrics import failed_messages, processed_messages, retry_events
from app.models.entities import OcppMessage, OutboxEvent, PartnerEvent, PartnerEventStatus
from app.repositories.outbox import OutboxRepository

tracer = trace.get_tracer(__name__)


@dataclass(frozen=True)
class OutboxProcessingResult:
    event_id: str
    status: str
    message: str


def process_outbox_event(db: Session, event: OutboxEvent) -> OutboxProcessingResult:
    with tracer.start_as_current_span("outbox.process") as span:
        repo = OutboxRepository(db)
        try:
            action = event.event_type
            span.set_attribute("outbox.event_type", action)
            if action.startswith("ocpp."):
                # The demo applies the durable state change by observing the event itself.
                # Real integrations would fan out webhooks, dispatch commands, or update projections here.
                if event.message_id is not None:
                    message = db.get(OcppMessage, event.message_id)
                    if message is not None:
                        message.status = "processed"
                        message.processed_at = datetime.now(UTC)
            elif action.startswith("partner."):
                event_id = (event.payload or {}).get("event_id")
                if event_id is not None:
                    partner_event = db.scalar(select(PartnerEvent).where(PartnerEvent.event_id == event_id))
                    if partner_event is not None:
                        partner_event.status = PartnerEventStatus.PROCESSED.value
                        partner_event.processed_at = datetime.now(UTC)
            repo.mark_processed(event)
            db.commit()
            processed_messages.inc()
            return OutboxProcessingResult(event.id, event.status, "processed")
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
            if event.attempts + 1 >= event.max_attempts:
                repo.mark_dead_lettered(event, error)
                db.commit()
                failed_messages.inc()
                return OutboxProcessingResult(event.id, event.status, error)
            repo.mark_retrying(event, error, backoff_seconds=min(300, 2 ** (event.attempts + 1) * 5))
            db.commit()
            retry_events.inc()
            span.record_exception(exc)
            return OutboxProcessingResult(event.id, event.status, error)
