import pytest
from httpx import ASGITransport, AsyncClient

from simulator.app import app


@pytest.mark.asyncio
async def test_health_endpoint() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_scenarios_include_webhook_failure_injection() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/scenarios")
    assert response.status_code == 200
    scenarios = response.json()["scenarios"]
    assert "partner-webhook" in scenarios
    assert "invalid-partner-signature" in scenarios
    assert "duplicate-partner-event" in scenarios
