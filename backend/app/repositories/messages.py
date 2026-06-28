from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import OcppMessage


class MessageRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_message_id(self, station_id: str, message_id: str) -> OcppMessage | None:
        return self.db.scalar(
            select(OcppMessage).where(
                OcppMessage.station_id == station_id,
                OcppMessage.message_id == message_id,
            )
        )
