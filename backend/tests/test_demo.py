from sqlalchemy import select

from app.models.entities import Station
from app.services.demo import seed_demo_data


def test_seeded_online_stations_have_last_seen_timestamp(db_session) -> None:
    seed_demo_data(db_session)

    stations = list(db_session.scalars(select(Station)))
    assert stations
    assert all(station.last_seen_at is not None for station in stations if station.online)
    assert all(station.last_seen_at is None for station in stations if not station.online)
