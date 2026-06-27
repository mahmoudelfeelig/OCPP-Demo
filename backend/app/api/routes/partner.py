from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from opentelemetry import trace
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.webhooks import ingest_partner_webhook

router = APIRouter(prefix="/partner")
tracer = trace.get_tracer(__name__)


@router.post("/webhook")
async def webhook(
    request: Request,
    x_event_id: str | None = Header(default=None, alias="X-Event-Id"),
    x_signature: str | None = Header(default=None, alias="X-Signature"),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    with tracer.start_as_current_span("partner.webhook.request") as span:
        if x_event_id is None:
            raise HTTPException(status_code=400, detail="Missing event id")
        payload_text = (await request.body()).decode("utf-8")
        span.set_attribute("partner.event_id", x_event_id)
        try:
            event = ingest_partner_webhook(db, x_event_id, payload_text, x_signature)
        except ValueError as exc:
            span.record_exception(exc)
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except LookupError as exc:
            span.record_exception(exc)
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {"status": event.status, "event_id": event.event_id}
