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
- Redis for limited cache and worker-heartbeat use
- Durable outbox processing scaffolding
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
- Local demo data is controlled by `SEED_DEMO_DATA=true` in `.env`. It creates sample sites, stations, messages, and demo accounts for development only.
- Production should keep `SEED_DEMO_DATA=false` in `deploy/.env`.
- For a first production admin, set `ADMIN_BOOTSTRAP_EMAIL` and `ADMIN_BOOTSTRAP_PASSWORD` in `deploy/.env`, start the stack once, sign in, then remove or clear those bootstrap values after the admin exists.
- Do not use demo seeded accounts as a production bootstrap path.
- Rotate the partner webhook secret by updating `PARTNER_WEBHOOK_SECRET` in `deploy/.env` and restarting the stack; the UI shows this as a manual operator flow rather than an automated secret manager integration.
- The database is the durable source of truth.
- Redis is used for short-lived station snapshots and worker heartbeat state. Most dashboard reads still query PostgreSQL directly.
- Worker processing is idempotent and outbox-backed. The current handlers mark OCPP messages and partner events processed; downstream webhook fanout, command dispatch, and projection consumers are not implemented.
- The controls named as simulated start/stop actions write audit events only. They do not call the simulator or send OCPP `RemoteStartTransaction` or `RemoteStopTransaction` commands.
- `StartTransaction` follows OCPP 1.6 ownership: the charger sends the request without a transaction ID, the central system returns one, and later `MeterValues` and `StopTransaction` requests reuse it.
- Detailed traces stay in logs or the local collector output, not in the UI.
- Demo JWTs are intentionally short-lived operational tokens, not refresh-token sessions. Expired tokens are cleared by the UI and require logging in again.
- Repository tests that need PostgreSQL use a disposable database URL through `OCPP_POSTGRES_TEST_URL`; do not point that variable at a database you want to keep.

## Troubleshooting

- If the stack fails to boot, check `docker compose logs -f`.
- If the UI cannot reach the API, confirm Caddy is listening on port `8080`.
- If OCPP traffic is not flowing, confirm the backend WebSocket endpoint and simulator connection settings.
- If the database schema is missing, run the Alembic migration command in the backend container.

## Deployment

- The production stack uses [`docker-compose.prod.yml`](/mnt/d/Stuff/Projects/Tools/OCPP-Demo/docker-compose.prod.yml).
- Production builds images directly on the Hetzner server from the checked-out source; no GHCR registry is required.
- The app edge container is named `ocpp-demo-web` and joins the shared external Docker network `web`.
- The host-Caddy sample lives in [`deploy/Caddyfile.host.example`](/mnt/d/Stuff/Projects/Tools/OCPP-Demo/deploy/Caddyfile.host.example).

Host Caddy route:

```caddy
ocpp.elfeel.me {
    reverse_proxy ocpp-demo-web:80
}
```

Server deploy command:

```bash
cd /opt/ocpp-backend-demo
git pull --ff-only
docker compose --env-file deploy/.env -f docker-compose.prod.yml up -d --build --remove-orphans
```

GitHub Actions deploys by SSHing into the server and running that same source-build flow after tests pass.
