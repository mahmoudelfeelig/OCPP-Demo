from __future__ import annotations

import json
import inspect
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
    station_id = url.rstrip("/").rsplit("/", 1)[-1]
    station_tokens = json.loads(os.environ["OCPP_STATION_TOKENS"])
    token = station_tokens[station_id]
    header_parameter = (
        "additional_headers"
        if "additional_headers" in inspect.signature(websockets.connect).parameters
        else "extra_headers"
    )
    message_id = str(uuid4())
    async with websockets.connect(
        url,
        **{header_parameter: {"Authorization": f"Bearer {token}"}},
    ) as ws:
        await ws.send(json.dumps([2, message_id, "BootNotification", {"chargePointVendor": "OCPP-Demo", "chargePointModel": "Integration"}]))
        response = json.loads(await ws.recv())

    assert response[0] == 3
    assert response[1] == message_id
    assert response[2]["status"] == "Accepted"
