from __future__ import annotations

import asyncio
from uuid import uuid4

import structlog
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import SessionLocal
from app.repositories.outbox import OutboxRepository
from app.services.cache import write_worker_heartbeat
from app.services.outbox import process_outbox_event
from app.services.stations import mark_stale_stations_offline


async def run_worker() -> None:
    logger = structlog.get_logger("worker")
    worker_id = str(uuid4())
    settings = get_settings()
    logger.info("worker_started", worker_id=worker_id)
    while True:
        write_worker_heartbeat(worker_id)
        db: Session = SessionLocal()
        try:
            stale_count = mark_stale_stations_offline(db, settings.station_heartbeat_timeout_seconds)
            if stale_count:
                db.commit()
                logger.info("stale_stations_marked_offline", worker_id=worker_id, count=stale_count)
            repo = OutboxRepository(db)
            recovered_count = repo.recover_stale_processing()
            if recovered_count:
                db.commit()
                logger.info("outbox_stale_locks_recovered", worker_id=worker_id, count=recovered_count)
            claimed_events = repo.claim_due(worker_id=worker_id, limit=10)
            if claimed_events:
                db.commit()
            for event in claimed_events:
                result = process_outbox_event(db, event)
                logger.info("outbox_processed", worker_id=worker_id, event_id=result.event_id, status=result.status)
        finally:
            db.close()
        await asyncio.sleep(3)


def main() -> None:
    configure_logging()
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
