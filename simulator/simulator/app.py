from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import httpx
import websockets
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="ocpp-backend-demo simulator", version="0.1.0")


class ScenarioRequest(BaseModel):
    site_id: str | None = None
    station_id: str | None = None
    connector_id: str | None = None
    speed: str = "normal"


@dataclass
class SimulatorState:
    connected: bool = False
    running: bool = False
    scenario: str | None = None
    station_id: str | None = None
    last_message: str | None = None
    messages: list[dict[str, Any]] = field(default_factory=list)
    websocket_url: str = "ws://backend:8000/ocpp/BER-001"


STATE = SimulatorState()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def state_payload() -> dict[str, Any]:
    return {
        "connected": STATE.connected,
        "running": STATE.running,
        "scenario": STATE.scenario,
        "station_id": STATE.station_id,
        "last_message": STATE.last_message,
        "messages": STATE.messages[-25:],
    }


@app.get("/state")
async def state() -> dict[str, Any]:
    return state_payload()


@app.get("/scenarios")
async def scenarios() -> dict[str, list[str]]:
    return {
        "scenarios": [
            "happy-path-charging-session",
            "duplicate-meter-value",
            "station-offline-online",
            "connector-fault",
            "interrupted-session",
            "partner-webhook",
            "invalid-partner-signature",
            "duplicate-partner-event",
        ]
    }


async def send_frame(ws, frame: list[Any]) -> None:
    payload = json.dumps(frame)
    await ws.send(payload)
    STATE.last_message = payload
    STATE.messages.append({"direction": "outbound", "payload": frame, "timestamp": datetime.now(UTC).isoformat()})
    response = await ws.recv()
    STATE.messages.append({"direction": "inbound", "payload": response, "timestamp": datetime.now(UTC).isoformat()})
    STATE.last_message = response


def scenario_delay(speed: str) -> float:
    return {"slow": 0.7, "normal": 0.15, "fast": 0.0}.get(speed, 0.15)


async def pause(speed: str) -> None:
    delay = scenario_delay(speed)
    if delay:
        await asyncio.sleep(delay)


async def run_happy_path(ws, station_id: str, connector_id: int, speed: str) -> None:
    message_id = str(uuid4())
    await send_frame(ws, [2, message_id, "BootNotification", {"chargePointVendor": "OCPP-Demo", "chargePointModel": "Demo"}])
    await pause(speed)
    await send_frame(ws, [2, str(uuid4()), "Heartbeat", {}])
    await pause(speed)
    await send_frame(
        ws,
        [
            2,
            str(uuid4()),
            "StatusNotification",
            {"connectorId": connector_id, "status": "Available", "errorCode": "NoError"},
        ],
    )
    await pause(speed)
    await send_frame(
        ws,
        [
            2,
            str(uuid4()),
            "StartTransaction",
            {"connectorId": connector_id, "idTag": "DEMO-TAG", "meterStart": 12345, "transactionId": 9001},
        ],
    )
    await pause(speed)
    await send_frame(
        ws,
        [
            2,
            str(uuid4()),
            "MeterValues",
            {
                "transactionId": 9001,
                "connectorId": connector_id,
                "meterValue": [
                    {
                        "timestamp": datetime.now(UTC).isoformat(),
                        "sampledValue": [{"value": "12410.5", "unit": "kWh", "measurand": "Energy.Active.Import.Register"}],
                    }
                ],
            },
        ],
    )
    await pause(speed)
    await send_frame(
        ws,
        [
            2,
            str(uuid4()),
            "StopTransaction",
            {"transactionId": 9001, "meterStop": 12410, "reason": "Local"},
        ],
    )


async def run_duplicate_meter(ws, connector_id: int, speed: str) -> None:
    transaction_id = 9901
    await send_frame(
        ws,
        [
            2,
            str(uuid4()),
            "StartTransaction",
            {"connectorId": connector_id, "idTag": "DEMO-TAG", "meterStart": 12345, "transactionId": transaction_id},
        ],
    )
    await pause(speed)
    meter_message_id = str(uuid4())
    meter_frame = [
        2,
        meter_message_id,
        "MeterValues",
        {
            "transactionId": transaction_id,
            "connectorId": connector_id,
            "meterValue": [
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "sampledValue": [{"value": "12411.0", "unit": "kWh", "measurand": "Energy.Active.Import.Register"}],
                }
            ],
        },
    ]
    await send_frame(ws, meter_frame)
    await pause(speed)
    await send_frame(ws, meter_frame)


async def run_station_offline_online(ws, connector_id: int, speed: str) -> None:
    await send_frame(ws, [2, str(uuid4()), "StatusNotification", {"connectorId": connector_id, "status": "Unavailable"}])
    await pause(speed)
    await send_frame(ws, [2, str(uuid4()), "StatusNotification", {"connectorId": connector_id, "status": "Available"}])


async def run_connector_fault(ws, connector_id: int) -> None:
    await send_frame(ws, [2, str(uuid4()), "StatusNotification", {"connectorId": connector_id, "status": "Faulted", "errorCode": "GroundFailure"}])


async def run_interrupted_session(ws, connector_id: int, speed: str) -> None:
    await send_frame(
        ws,
        [
            2,
            str(uuid4()),
            "StartTransaction",
            {"connectorId": connector_id, "idTag": "DEMO-TAG", "meterStart": 20000, "transactionId": 9902},
        ],
    )
    await pause(speed)
    await send_frame(ws, [2, str(uuid4()), "StatusNotification", {"connectorId": connector_id, "status": "SuspendedEVSE"}])


async def post_partner_webhook(station_id: str, event_id: str, signature_override: str | None = None) -> httpx.Response:
    async with httpx.AsyncClient(base_url="http://backend:8000") as client:
        payload = {"event_id": event_id, "type": "session.completed", "station_id": station_id}
        payload_text = json.dumps(payload)
        import hashlib, hmac

        from os import getenv

        secret = getenv("PARTNER_WEBHOOK_SECRET", "change-me").encode("utf-8")
        signature = hmac.new(secret, payload_text.encode("utf-8"), hashlib.sha256).hexdigest()
        return await client.post(
            "/partner/webhook",
            content=payload_text,
            headers={"X-Event-Id": payload["event_id"], "X-Signature": signature_override or signature},
        )


async def run_partner_webhook(station_id: str) -> None:
    response = await post_partner_webhook(station_id, f"partner-{uuid4()}")
    response.raise_for_status()


async def run_invalid_partner_signature(station_id: str) -> None:
    response = await post_partner_webhook(station_id, f"partner-invalid-{uuid4()}", signature_override="invalid")
    STATE.messages.append(
        {
            "direction": "inbound",
            "payload": {"status_code": response.status_code, "body": response.text},
            "timestamp": datetime.now(UTC).isoformat(),
        }
    )


async def run_duplicate_partner_event(station_id: str) -> None:
    event_id = f"partner-duplicate-{uuid4()}"
    first = await post_partner_webhook(station_id, event_id)
    second = await post_partner_webhook(station_id, event_id)
    STATE.messages.append(
        {
            "direction": "inbound",
            "payload": {"first_status": first.status_code, "second_status": second.status_code, "second_body": second.text},
            "timestamp": datetime.now(UTC).isoformat(),
        }
    )


async def connect_and_run(scenario: str, request: ScenarioRequest) -> dict[str, Any]:
    station_id = request.station_id or "BER-001"
    connector_id = int(request.connector_id or 1)
    websocket_url = f"ws://backend:8000/ocpp/{station_id}"
    STATE.connected = False
    STATE.running = True
    STATE.scenario = scenario
    STATE.station_id = station_id
    STATE.websocket_url = websocket_url
    try:
        async with websockets.connect(websocket_url) as ws:
            STATE.connected = True
            if scenario == "happy-path-charging-session":
                await run_happy_path(ws, station_id, connector_id, request.speed)
            elif scenario == "duplicate-meter-value":
                await run_duplicate_meter(ws, connector_id, request.speed)
            elif scenario == "station-offline-online":
                await run_station_offline_online(ws, connector_id, request.speed)
            elif scenario == "connector-fault":
                await run_connector_fault(ws, connector_id)
            elif scenario == "interrupted-session":
                await run_interrupted_session(ws, connector_id, request.speed)
            elif scenario == "partner-webhook":
                await run_partner_webhook(station_id)
            elif scenario == "invalid-partner-signature":
                await run_invalid_partner_signature(station_id)
            elif scenario == "duplicate-partner-event":
                await run_duplicate_partner_event(station_id)
            else:
                raise HTTPException(status_code=400, detail=f"Unknown scenario: {scenario}")
    finally:
        STATE.connected = False
        STATE.running = False
    return state_payload()


@app.post("/run/{scenario_name}")
async def run_scenario(scenario_name: str, request: ScenarioRequest) -> dict[str, Any]:
    return await connect_and_run(scenario_name, request)
