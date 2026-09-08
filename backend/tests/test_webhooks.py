from __future__ import annotations

import json

import pytest

from app.core.config import get_settings
from app.models.entities import OutboxEvent, PartnerEvent, PartnerEventStatus
from app.services.webhooks import ingest_partner_webhook, verify_signature


def test_webhook_signature_verification() -> None:
    settings = get_settings()
    payload = json.dumps({"event_id": "evt-1"})
    signature = __import__("hmac").new(
        settings.partner_webhook_secret.encode("utf-8"),
        payload.encode("utf-8"),
        __import__("hashlib").sha256,
    ).hexdigest()
    assert verify_signature(payload, signature)
    assert not verify_signature(payload, "invalid")


def test_partner_webhook_duplicate_event_is_rejected(db_session) -> None:
    settings = get_settings()
    payload = json.dumps({"event_id": "evt-duplicate", "station_id": "ST-1"})
    signature = __import__("hmac").new(
        settings.partner_webhook_secret.encode("utf-8"),
        payload.encode("utf-8"),
        __import__("hashlib").sha256,
    ).hexdigest()

    event = ingest_partner_webhook(db_session, "evt-duplicate", payload, signature)

    with pytest.raises(LookupError, match="Duplicate partner event"):
        ingest_partner_webhook(db_session, "evt-duplicate", payload, signature)

    assert event.status == PartnerEventStatus.RECEIVED.value
    assert db_session.query(PartnerEvent).count() == 1
    assert db_session.query(OutboxEvent).count() == 1


def test_invalid_partner_webhook_signature_does_not_claim_event_id(db_session) -> None:
    settings = get_settings()
    payload = json.dumps({"event_id": "evt-invalid", "station_id": "ST-1"})

    with pytest.raises(ValueError, match="Invalid signature"):
        ingest_partner_webhook(db_session, "evt-invalid", payload, "invalid")

    assert db_session.query(PartnerEvent).count() == 0

    signature = __import__("hmac").new(
        settings.partner_webhook_secret.encode("utf-8"),
        payload.encode("utf-8"),
        __import__("hashlib").sha256,
    ).hexdigest()
    event = ingest_partner_webhook(db_session, "evt-invalid", payload, signature)

    assert event.status == PartnerEventStatus.RECEIVED.value
    assert db_session.query(PartnerEvent).count() == 1
    assert db_session.query(OutboxEvent).count() == 1
