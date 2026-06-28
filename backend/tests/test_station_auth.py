from __future__ import annotations

import json

from app.core.config import Settings
from app.core.security import hash_station_token
from app.models.entities import Site, Station
from app.services.bootstrap import configure_station_tokens
from app.services.station_auth import authenticate_station


def test_station_authentication_accepts_id_or_unique_external_id(db_session) -> None:
    site = Site(slug="station-auth", label="Station Auth")
    db_session.add(site)
    db_session.flush()
    token = "station-auth-token-with-at-least-32-characters"
    station = Station(
        site_id=site.id,
        external_id="AUTH-001",
        label="Authenticated Station",
        ocpp_token_hash=hash_station_token(token),
    )
    db_session.add(station)
    db_session.commit()

    assert authenticate_station(db_session, station.id, token).id == station.id
    assert authenticate_station(db_session, station.external_id, token).id == station.id
    assert authenticate_station(db_session, station.external_id, "wrong-token") is None


def test_station_authentication_rejects_ambiguous_external_id(db_session) -> None:
    sites = [
        Site(slug="station-auth-a", label="Station Auth A"),
        Site(slug="station-auth-b", label="Station Auth B"),
    ]
    db_session.add_all(sites)
    db_session.flush()
    token = "shared-station-token-with-at-least-32-characters"
    db_session.add_all(
        [
            Station(
                site_id=site.id,
                external_id="SHARED-ID",
                label=f"Station {index}",
                ocpp_token_hash=hash_station_token(token),
            )
            for index, site in enumerate(sites)
        ]
    )
    db_session.commit()

    assert authenticate_station(db_session, "SHARED-ID", token) is None


def test_environment_token_only_bootstraps_missing_station_hash(db_session) -> None:
    site = Site(slug="token-bootstrap", label="Token Bootstrap")
    db_session.add(site)
    db_session.flush()
    station = Station(site_id=site.id, external_id="BOOTSTRAP-001", label="Bootstrap Station")
    db_session.add(station)
    db_session.commit()
    initial_token = "initial-station-token-with-at-least-32-characters"
    settings = Settings(ocpp_station_tokens=json.dumps({station.external_id: initial_token}))

    configure_station_tokens(db_session, settings)
    db_session.refresh(station)
    assert authenticate_station(db_session, station.external_id, initial_token) is not None

    rotated_token = "rotated-station-token-with-at-least-32-characters"
    station.ocpp_token_hash = hash_station_token(rotated_token)
    db_session.commit()
    configure_station_tokens(db_session, settings)
    db_session.refresh(station)

    assert authenticate_station(db_session, station.external_id, rotated_token) is not None
    assert authenticate_station(db_session, station.external_id, initial_token) is None
