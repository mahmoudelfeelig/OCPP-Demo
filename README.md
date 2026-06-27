# ocpp-backend-demo

`ocpp-backend-demo` is a backend lifecycle demo for EV charging operations.
It focuses on the engineering judgment behind reliable OCPP ingestion, async processing, operational observability, and a product-quality dashboard rather than on billing, roaming, or a full charging platform.

## Scope

- Backend lifecycle demo, not a complete charging platform
- Multi-site fleet management
- OCPP 1.6 over WebSocket
- Python backend with FastAPI
- PostgreSQL as the source of truth
- SQLAlchemy and Alembic for persistence
- Redis for cache-only use
- Outbox-driven async processing
- Separate frontend and simulator containers
- Caddy reverse proxy
- JWT auth with `admin` and `operator` roles
- JSON logs and OpenTelemetry export to logs/local collector

## Repository Layout

- `backend/` - FastAPI app, domain logic, migrations, and tests
- `frontend/` - Next.js operations UI
- `simulator/` - Python simulator process
- `caddy/` - reverse proxy config
- `otel/` - local OpenTelemetry collector config
- `deploy/` - server-only environment templates

## Local Setup

1. Copy the example env files:
   - `cp .env.example .env`
   - `cp deploy/.env.example deploy/.env`
2. Start the stack:
   - `make up`
3. Open the demo through Caddy:
   - `http://localhost:8080`

## Useful Commands

- `make up` - start the full Compose stack
- `make down` - stop the stack
- `make reset-demo` - reset Compose volumes, rebuild, start, and smoke-check a clean rehearsal state
- `make logs` - follow service logs
- `make test-backend` - run backend tests
- `make test-backend-postgres` - run repository locking tests against PostgreSQL
- `make test-frontend` - run frontend tests
- `make test-simulator` - run simulator tests
- `make test-simulator-integration` - run the simulator WebSocket integration test against the backend container
- `make smoke` - run the Compose smoke check

## Demo Flow

1. Log in as an operator or admin.
2. Review the overview dashboard for fleet health and backlog signals.
3. Inspect a site, then drill into a station and connector.
4. Run a simulator scenario such as a happy-path session, duplicate meter value, invalid partner signature, or duplicate partner event.
5. Observe raw OCPP messages, outbox processing, and webhook status.
6. As an admin, retry or acknowledge failed work and audit the action trail.

## Operations Notes

- Production secrets live in `deploy/.env` and are not committed.
- Rotate the partner webhook secret by updating `PARTNER_WEBHOOK_SECRET` in `deploy/.env` and restarting the stack; the UI shows this as a manual operator flow rather than an automated secret manager integration.
- The database is the durable source of truth.
- Redis is a cache only.
- Worker processing is idempotent and outbox-backed.
- Detailed traces stay in logs or the local collector output, not in the UI.
- Demo JWTs are intentionally short-lived operational tokens, not refresh-token sessions. Expired tokens are cleared by the UI and require logging in again.
- Repository tests that need PostgreSQL use a disposable database URL through `OCPP_POSTGRES_TEST_URL`; do not point that variable at a database you want to keep.

## Troubleshooting

- If the stack fails to boot, check `docker compose logs -f`.
- If the UI cannot reach the API, confirm Caddy is listening on port `8080`.
- If OCPP traffic is not flowing, confirm the backend WebSocket endpoint and simulator connection settings.
- If the database schema is missing, run the Alembic migration command in the backend container.

## Deployment

- See [`docs/hetzner-deployment.md`](/mnt/d/Stuff/Projects/Tools/OCPP-Demo/docs/hetzner-deployment.md) for the Hetzner/Caddy production layout.
- The production stack uses [`docker-compose.prod.yml`](/mnt/d/Stuff/Projects/Tools/OCPP-Demo/docker-compose.prod.yml).
- The host-Caddy sample lives in [`deploy/Caddyfile.host.example`](/mnt/d/Stuff/Projects/Tools/OCPP-Demo/deploy/Caddyfile.host.example).

## Demo References

- [`docs/architecture.md`](/mnt/d/Stuff/Projects/Tools/OCPP-Demo/docs/architecture.md) - system diagram and reliability notes
- [`docs/interview-demo-script.md`](/mnt/d/Stuff/Projects/Tools/OCPP-Demo/docs/interview-demo-script.md) - screen-by-screen interview walkthrough
- [`docs/ocpp-happy-path-transcript.md`](/mnt/d/Stuff/Projects/Tools/OCPP-Demo/docs/ocpp-happy-path-transcript.md) - representative OCPP frames and expected state
- [`docs/log-trace-cheat-sheet.md`](/mnt/d/Stuff/Projects/Tools/OCPP-Demo/docs/log-trace-cheat-sheet.md) - logs, traces, and metrics talking points
- [`docs/compose-smoke-transcript.md`](/mnt/d/Stuff/Projects/Tools/OCPP-Demo/docs/compose-smoke-transcript.md) - Compose verification checklist
- [`docs/final-demo-checklist.md`](/mnt/d/Stuff/Projects/Tools/OCPP-Demo/docs/final-demo-checklist.md) - clean checkout, rehearsal, and `ocpp.elfeel.me` checklist
