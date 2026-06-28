import json

import pytest
from httpx import ASGITransport, AsyncClient

from simulator.app import app, require_authenticated_user, run_happy_path


class FakeWebSocket:
    def __init__(self) -> None:
        self.frames: list[list[object]] = []

    async def send(self, payload: str) -> None:
        self.frames.append(json.loads(payload))

    async def recv(self) -> str:
        frame = self.frames[-1]
        response_payload = (
            {"transactionId": 4242, "idTagInfo": {"status": "Accepted"}}
            if frame[2] == "StartTransaction"
            else {}
        )
        return json.dumps([3, frame[1], response_payload])


@pytest.mark.asyncio
async def test_health_endpoint() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_scenarios_require_authentication() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/scenarios")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_scenarios_include_webhook_failure_injection() -> None:
    async def authenticated_user() -> dict[str, str]:
        return {"email": "operator@test.local", "role": "operator"}

    app.dependency_overrides[require_authenticated_user] = authenticated_user
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/scenarios")
        assert response.status_code == 200
        scenarios = response.json()["scenarios"]
        assert "partner-webhook" in scenarios
        assert "invalid-partner-signature" in scenarios
        assert "duplicate-partner-event" in scenarios
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_happy_path_uses_transaction_id_returned_by_central_system() -> None:
    websocket = FakeWebSocket()

    await run_happy_path(websocket, "BER-001", 1, "fast")

    start_frame = next(frame for frame in websocket.frames if frame[2] == "StartTransaction")
    meter_frame = next(frame for frame in websocket.frames if frame[2] == "MeterValues")
    stop_frame = next(frame for frame in websocket.frames if frame[2] == "StopTransaction")
    assert "transactionId" not in start_frame[3]
    assert meter_frame[3]["transactionId"] == 4242
    assert stop_frame[3]["transactionId"] == 4242
