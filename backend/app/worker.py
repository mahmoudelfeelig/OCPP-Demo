from __future__ import annotations

import asyncio
from uuid import uuid4

import structlog
from sqlalchemy.orm import Session

from app.core.logging import configure_logging
from app.db.session import SessionLocal
from app.repositories.outbox import OutboxRepository
from app.services.outbox import process_outbox_event


async def run_worker() -> None:
    logger = structlog.get_logger("worker")
    worker_id = str(uuid4())
    logger.info("worker_started", worker_id=worker_id)
    while True:
        db: Session = SessionLocal()
        try:
            repo = OutboxRepository(db)
            recovered_count = repo.recover_stale_processing()
            if recovered_count:
                db.commit()
                logger.info("outbox_stale_locks_recovered", worker_id=worker_id, count=recovered_count)
            for event in repo.list_due(limit=10):
                repo.lock(event, worker_id=worker_id)
                db.commit()
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
