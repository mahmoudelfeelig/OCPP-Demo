from __future__ import annotations

import hashlib
import hmac
import json

from opentelemetry import trace
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.metrics import failed_messages, webhook_events
from app.models.entities import (
    OutboxEvent,
    OutboxStatus,
    PartnerEvent,
    PartnerEventStatus,
)
from app.repositories.outbox import OutboxRepository

tracer = trace.get_tracer(__name__)


def verify_signature(payload_text: str, signature: str) -> bool:
    secret = get_settings().partner_webhook_secret.encode("utf-8")
    expected = hmac.new(secret, payload_text.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def ingest_partner_webhook(db: Session, event_id: str, payload_text: str, signature: str | None) -> PartnerEvent:
    with tracer.start_as_current_span("partner.webhook") as span:
        try:
            if signature is None:
                raise ValueError("Missing signature")

            if not verify_signature(payload_text, signature):
                raise ValueError("Invalid signature")

            existing = db.scalar(select(PartnerEvent).where(PartnerEvent.event_id == event_id))
            if existing is not None:
                raise LookupError("Duplicate partner event")

            event = PartnerEvent(
                event_id=event_id,
                signature_valid=True,
                status=PartnerEventStatus.RECEIVED.value,
                raw_payload_text=payload_text,
                payload=json.loads(payload_text) if payload_text else {},
            )
            db.add(event)
            db.flush()
            OutboxRepository(db).enqueue(
                OutboxEvent(
                    message_id=None,
                    event_type="partner.webhook.received",
                    aggregate_type="partner_event",
                    aggregate_id=event.id,
                    status=OutboxStatus.PENDING.value,
                    payload={"event_id": event.event_id, "payload": event.payload},
                )
            )
            db.commit()
            db.refresh(event)
            webhook_events.inc()
            span.set_attribute("partner.event_id", event_id)
            return event
        except Exception:
            failed_messages.inc()
            raise
