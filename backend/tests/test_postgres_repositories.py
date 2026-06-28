from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base
from app.models.entities import OutboxEvent, OutboxStatus, Site
from app.repositories.catalog import CatalogRepository
from app.repositories.outbox import OutboxRepository


pytestmark = pytest.mark.skipif(
    not os.getenv("OCPP_POSTGRES_TEST_URL"),
    reason="Set OCPP_POSTGRES_TEST_URL to a disposable PostgreSQL database to run repository integration tests.",
)


@pytest.fixture()
def postgres_session_factory():
    engine = create_engine(os.environ["OCPP_POSTGRES_TEST_URL"], future=True)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        yield SessionLocal
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_catalog_repository_reads_sites_from_postgres(postgres_session_factory) -> None:
    session = postgres_session_factory()
    try:
        session.add(Site(slug="postgres-site", label="Postgres Site"))
        session.commit()

        sites = CatalogRepository(session).list_sites()

        assert [site.slug for site in sites] == ["postgres-site"]
    finally:
        session.close()


def test_two_workers_do_not_claim_same_outbox_row(postgres_session_factory) -> None:
    setup = postgres_session_factory()
    try:
        setup.add(
            OutboxEvent(
                event_type="postgres.lock",
                aggregate_type="station",
                aggregate_id="station-1",
                status=OutboxStatus.PENDING.value,
                payload={},
            )
        )
        setup.commit()
    finally:
        setup.close()

    worker_one = postgres_session_factory()
    worker_two = postgres_session_factory()
    try:
        first_claim = OutboxRepository(worker_one).claim_due("worker-one", limit=1)
        worker_one.commit()
        second_claim = OutboxRepository(worker_two).claim_due("worker-two", limit=1)

        assert len(first_claim) == 1
        assert second_claim == []
    finally:
        worker_one.rollback()
        worker_two.rollback()
        worker_one.close()
        worker_two.close()
