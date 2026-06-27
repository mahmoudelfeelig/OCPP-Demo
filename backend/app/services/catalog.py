from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.catalog import CatalogRepository


def site_card_data(db: Session) -> list[dict[str, object]]:
    repo = CatalogRepository(db)
    stations = repo.list_stations()
    sessions = repo.list_sessions()
    return [
        {
            "id": site.id,
            "label": site.label,
            "slug": site.slug,
            "station_count": sum(1 for station in stations if station.site_id == site.id),
            "active_sessions": sum(1 for session in sessions if session.site_id == site.id and session.state == "active"),
        }
        for site in repo.list_sites()
    ]

