from __future__ import annotations

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, joinedload

from app.models.entities import ChargingSession, Connector, Site, Station, Transaction


class CatalogRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_sites(self) -> list[Site]:
        return list(self.db.scalars(select(Site).order_by(Site.label)))

    def list_stations(self) -> list[Station]:
        stmt: Select[tuple[Station]] = select(Station).options(joinedload(Station.site)).order_by(Station.label)
        return list(self.db.scalars(stmt))

    def list_sessions(self) -> list[ChargingSession]:
        stmt = select(ChargingSession).options(joinedload(ChargingSession.site)).order_by(ChargingSession.created_at.desc())
        return list(self.db.scalars(stmt))

    def list_transactions(self) -> list[Transaction]:
        return list(self.db.scalars(select(Transaction).order_by(Transaction.created_at.desc())))

    def list_connectors(self) -> list[Connector]:
        return list(self.db.scalars(select(Connector).order_by(Connector.station_id, Connector.connector_number)))

