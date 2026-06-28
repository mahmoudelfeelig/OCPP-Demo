from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.models.entities import AuditEvent, Site, Station, StationState
from app.services.stations import mark_stale_stations_offline


def test_stale_online_station_is_marked_offline(db_session) -> None:
    site = Site(slug="stale-site", label="Stale Site")
    db_session.add(site)
    db_session.flush()
    station = Station(
        site_id=site.id,
        external_id="STALE-1",
        label="Stale Station",
        state=StationState.ONLINE.value,
        online=True,
        last_seen_at=datetime.now(UTC) - timedelta(seconds=700),
    )
    db_session.add(station)
    db_session.commit()

    count = mark_stale_stations_offline(db_session, timeout_seconds=600)
    db_session.commit()
    db_session.refresh(station)

    event = db_session.query(AuditEvent).filter(AuditEvent.action == "station_heartbeat_missed").one()
    assert count == 1
    assert station.online is False
    assert station.state == StationState.OFFLINE.value
    assert event.entity_id == station.id


def test_online_station_without_last_seen_is_not_expired(db_session) -> None:
    site = Site(slug="seed-site", label="Seed Site")
    db_session.add(site)
    db_session.flush()
    station = Station(
        site_id=site.id,
        external_id="SEEDED-ONLINE",
        label="Seeded Online",
        state=StationState.ONLINE.value,
        online=True,
        last_seen_at=None,
    )
    db_session.add(station)
    db_session.commit()

    count = mark_stale_stations_offline(db_session, timeout_seconds=600)
    db_session.commit()
    db_session.refresh(station)

    assert count == 0
    assert station.online is True
    assert station.state == StationState.ONLINE.value
    assert db_session.query(AuditEvent).count() == 0
