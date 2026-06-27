SHELL := /bin/bash

.PHONY: up down logs build reset-demo test-backend test-backend-postgres test-frontend test-simulator test-simulator-integration smoke format

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f --tail=200

build:
	docker compose build

reset-demo:
	bash scripts/demo-reset.sh

test-backend:
	docker compose run --rm backend pytest -q

test-backend-postgres:
	docker compose run --rm -e OCPP_POSTGRES_TEST_URL=postgresql+psycopg://ocpp_demo:ocpp_demo@postgres:5432/postgres backend pytest -q tests/test_postgres_repositories.py

test-frontend:
	docker compose run --rm frontend npm test -- --runInBand

test-simulator:
	docker compose run --rm simulator pytest -q

test-simulator-integration:
	docker compose run --rm -e OCPP_BACKEND_WS_URL=ws://backend:8000/ocpp/BER-001 simulator pytest -q tests/test_backend_integration.py

smoke:
	bash scripts/compose-smoke.sh

format:
	docker compose run --rm backend ruff format app tests
