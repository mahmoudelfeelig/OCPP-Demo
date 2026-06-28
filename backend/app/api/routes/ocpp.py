from __future__ import annotations

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from opentelemetry import trace

from app.db.session import SessionLocal
from app.services.ingestion import extract_ocpp_message_id, ingest_ocpp_message
from app.services.station_auth import authenticate_station

router = APIRouter()
tracer = trace.get_tracer(__name__)


@router.websocket("/ocpp/{station_id}")
async def ocpp_socket(websocket: WebSocket, station_id: str) -> None:
    db = SessionLocal()
    try:
        authorization = websocket.headers.get("authorization", "")
        scheme, _, token = authorization.partition(" ")
        station = authenticate_station(db, station_id, token) if scheme.lower() == "bearer" and token else None
        if station is None:
            await websocket.accept()
            await websocket.close(code=1008, reason="Invalid station credentials")
            return
        await websocket.accept()
        while True:
            message = await websocket.receive_text()
            with tracer.start_as_current_span("ocpp.websocket_message") as span:
                span.set_attribute("ocpp.station_id", station_id)
                try:
                    result = ingest_ocpp_message(db, station.id, message)
                    message_id = result["message_id"]
                    await websocket.send_text(json.dumps([3, message_id, result["response_payload"]]))
                except Exception as exc:  # noqa: BLE001
                    db.rollback()
                    span.record_exception(exc)
                    message_id = extract_ocpp_message_id(message) or "unknown"
                    await websocket.send_text(json.dumps([4, message_id, "FormationViolation", str(exc), {}]))
    except WebSocketDisconnect:
        return
    finally:
        db.close()
