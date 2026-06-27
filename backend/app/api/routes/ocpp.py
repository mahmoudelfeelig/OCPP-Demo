from __future__ import annotations

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from opentelemetry import trace

from app.db.session import SessionLocal
from app.services.ingestion import ingest_ocpp_message

router = APIRouter()
tracer = trace.get_tracer(__name__)


@router.websocket("/ocpp/{station_id}")
async def ocpp_socket(websocket: WebSocket, station_id: str) -> None:
    await websocket.accept()
    db = SessionLocal()
    try:
        while True:
            message = await websocket.receive_text()
            with tracer.start_as_current_span("ocpp.websocket_message") as span:
                span.set_attribute("ocpp.station_id", station_id)
                try:
                    result = ingest_ocpp_message(db, station_id, message)
                    message_id = result["message_id"]
                    await websocket.send_text(json.dumps([3, message_id, result["response_payload"]]))
                except Exception as exc:  # noqa: BLE001
                    db.rollback()
                    span.record_exception(exc)
                    await websocket.send_text(json.dumps([4, "unknown", "FormationViolation", str(exc), {}]))
    except WebSocketDisconnect:
        return
    finally:
        db.close()
