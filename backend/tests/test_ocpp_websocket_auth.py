from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import WebSocketDisconnect

from app.api.routes import ocpp


class FakeSession:
    def __init__(self) -> None:
        self.closed = False

    def rollback(self) -> None:
        pass

    def close(self) -> None:
        self.closed = True


class FakeWebSocket:
    def __init__(self, authorization: str | None = None, messages: list[str] | None = None) -> None:
        self.headers = {"authorization": authorization} if authorization else {}
        self.messages = iter(messages or [])
        self.accepted = False
        self.closed: tuple[int, str] | None = None
        self.sent: list[str] = []

    async def accept(self) -> None:
        self.accepted = True

    async def close(self, code: int, reason: str) -> None:
        self.closed = (code, reason)

    async def receive_text(self) -> str:
        try:
            return next(self.messages)
        except StopIteration as exc:
            raise WebSocketDisconnect() from exc

    async def send_text(self, message: str) -> None:
        self.sent.append(message)


@pytest.mark.asyncio
async def test_ocpp_websocket_rejects_missing_station_token(monkeypatch) -> None:
    session = FakeSession()
    websocket = FakeWebSocket()
    monkeypatch.setattr(ocpp, "SessionLocal", lambda: session)

    await ocpp.ocpp_socket(websocket, "STATION-1")

    assert websocket.accepted is True
    assert websocket.closed == (1008, "Invalid station credentials")
    assert session.closed is True


@pytest.mark.asyncio
async def test_ocpp_websocket_uses_authenticated_station_id(monkeypatch) -> None:
    session = FakeSession()
    websocket = FakeWebSocket(
        authorization="Bearer valid-token",
        messages=['[2,"heartbeat-1","Heartbeat",{}]'],
    )
    ingested_station_ids: list[str] = []
    monkeypatch.setattr(ocpp, "SessionLocal", lambda: session)
    monkeypatch.setattr(
        ocpp,
        "authenticate_station",
        lambda _db, _station_ref, _token: SimpleNamespace(id="internal-station-id"),
    )

    def ingest(_db, station_id: str, _message: str):
        ingested_station_ids.append(station_id)
        return {
            "message_id": "heartbeat-1",
            "response_payload": {"currentTime": "2026-06-28T00:00:00+00:00"},
        }

    monkeypatch.setattr(ocpp, "ingest_ocpp_message", ingest)

    await ocpp.ocpp_socket(websocket, "EXTERNAL-STATION-ID")

    assert ingested_station_ids == ["internal-station-id"]
    assert websocket.accepted is True
    assert websocket.sent
    assert session.closed is True
