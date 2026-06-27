from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.security import create_access_token
from app.api import deps
from app.api.routes import admin, auth, resources
from app.main import app
from app.models.entities import Connector, OutboxEvent, OutboxStatus, Role, Site, Station, User


@pytest.fixture()
def api_db(db_session):
    async def override_db():
        yield db_session

    app.dependency_overrides[resources.get_db] = override_db
    app.dependency_overrides[admin.get_db] = override_db
    app.dependency_overrides[auth.get_db] = override_db
    app.dependency_overrides[deps.get_db] = override_db
    admin_role = Role(name="admin", description="Admin")
    operator_role = Role(name="operator", description="Operator")
    db_session.add_all([admin_role, operator_role])
    db_session.flush()
    db_session.add_all(
        [
            User(email="admin@test.local", password_hash="not-used", role_id=admin_role.id),
            User(email="operator@test.local", password_hash="not-used", role_id=operator_role.id),
        ]
    )
    site = Site(slug="contract", label="Contract Site")
    db_session.add(site)
    db_session.flush()
    station = Station(site_id=site.id, external_id="CON-001", label="Contract Station", state="online", online=True)
    db_session.add(station)
    db_session.flush()
    db_session.add(Connector(station_id=station.id, connector_number=1, state="available"))
    db_session.add_all(
        [
        OutboxEvent(
            event_type="contract.test",
            aggregate_type="station",
            aggregate_id=station.id,
            status=OutboxStatus.DEAD_LETTERED.value,
            last_error="contract failure",
            payload={"station_id": station.id},
        ),
        OutboxEvent(
            event_type="contract.retry",
            aggregate_type="station",
            aggregate_id=station.id,
            status=OutboxStatus.FAILED.value,
            last_error="retry failure",
            payload={"station_id": station.id},
        ),
        ]
    )
    db_session.commit()
    try:
        yield db_session
    finally:
        app.dependency_overrides.clear()


def token_for(db_session, email: str) -> str:
    user = db_session.scalar(select(User).where(User.email == email))
    assert user is not None
    return create_access_token(user.id, user.role.name)


@pytest.mark.asyncio
async def test_dashboard_endpoints_return_typed_item_envelopes(api_db) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = token_for(api_db, "admin@test.local")
        headers = {"Authorization": f"Bearer {token}"}
        for path in [
            "/sites",
            "/stations?limit=10&online=true",
            "/sessions?limit=10",
            "/transactions?limit=10",
            "/events?limit=10",
            "/messages?limit=10",
            "/outbox?status=dead_lettered",
            "/webhooks?limit=10",
        ]:
            response = await client.get(path, headers=headers)
            assert response.status_code == 200, path
            payload = response.json()
            assert "items" in payload
            assert payload["meta"]["limit"] <= 200
            assert payload["meta"]["offset"] == 0
            assert payload["meta"]["count"] == len(payload["items"])

        station_id = (await client.get("/stations", headers=headers)).json()["items"][0]["id"]
        response = await client.get(f"/stations/{station_id}/connectors?state=available", headers=headers)
        assert response.status_code == 200
        assert response.json()["items"][0]["state"] == "available"


@pytest.mark.asyncio
async def test_operator_cannot_use_admin_only_actions(api_db) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = token_for(api_db, "operator@test.local")
        headers = {"Authorization": f"Bearer {token}"}
        station = (await client.get("/stations", headers=headers)).json()["items"][0]
        connector = (await client.get(f"/stations/{station['id']}/connectors", headers=headers)).json()["items"][0]
        outbox = (await client.get("/outbox", headers=headers)).json()["items"]
        dead_letter = next(row for row in outbox if row["status"] == "dead_lettered")
        failed = next(row for row in outbox if row["status"] == "failed")

        remote_response = await client.post("/admin/simulator/remote-start", headers=headers)
        users_response = await client.get("/admin/users", headers=headers)
        create_response = await client.post("/admin/users", json={"email": "new@test.local", "password": "secret123"}, headers=headers)
        maintenance_response = await client.post(f"/admin/stations/{station['id']}/maintenance", json={"enabled": True}, headers=headers)
        connector_response = await client.post(f"/admin/connectors/{connector['id']}/unavailable", headers=headers)
        retry_response = await client.post(f"/admin/outbox/{failed['id']}/retry", headers=headers)
        ack_response = await client.post(f"/admin/outbox/{dead_letter['id']}/ack", headers=headers)

        assert remote_response.status_code == 200
        assert users_response.status_code == 403
        assert create_response.status_code == 403
        assert maintenance_response.status_code == 403
        assert connector_response.status_code == 403
        assert retry_response.status_code == 403
        assert ack_response.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_use_recovery_and_maintenance_actions(api_db) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = token_for(api_db, "admin@test.local")
        headers = {"Authorization": f"Bearer {token}"}
        station = (await client.get("/stations", headers=headers)).json()["items"][0]
        connector = (await client.get(f"/stations/{station['id']}/connectors", headers=headers)).json()["items"][0]
        outbox = (await client.get("/outbox", headers=headers)).json()["items"]
        dead_letter = next(row for row in outbox if row["status"] == "dead_lettered")
        failed = next(row for row in outbox if row["status"] == "failed")

        assert (await client.post(f"/admin/stations/{station['id']}/maintenance", json={"enabled": True}, headers=headers)).status_code == 200
        assert (await client.post(f"/admin/connectors/{connector['id']}/unavailable", headers=headers)).status_code == 200
        assert (await client.post(f"/admin/connectors/{connector['id']}/available", headers=headers)).status_code == 200
        assert (await client.post(f"/admin/outbox/{failed['id']}/retry", headers=headers)).status_code == 200
        assert (await client.post(f"/admin/outbox/{dead_letter['id']}/ack", headers=headers)).status_code == 200
