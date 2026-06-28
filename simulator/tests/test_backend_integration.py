from __future__ import annotations

import json
import os
from uuid import uuid4

import pytest
import websockets


pytestmark = pytest.mark.skipif(
    not os.getenv("OCPP_BACKEND_WS_URL"),
    reason="Set OCPP_BACKEND_WS_URL to a real backend container WebSocket URL to run simulator integration tests.",
)


@pytest.mark.asyncio
async def test_happy_path_boot_notification_against_backend_container() -> None:
    url = os.environ["OCPP_BACKEND_WS_URL"]
    message_id = str(uuid4())
    async with websockets.connect(url) as ws:
        await ws.send(json.dumps([2, message_id, "BootNotification", {"chargePointVendor": "OCPP-Demo", "chargePointModel": "Integration"}]))
        response = json.loads(await ws.recv())

    assert response[0] == 3
    assert response[1] == message_id
    assert response[2]["status"] == "Accepted"
