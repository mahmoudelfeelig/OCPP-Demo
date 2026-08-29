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
- Per-station bearer-token authentication for OCPP WebSocket connections

## Repository Layout

- `backend/` - FastAPI app, domain logic, migrations, and tests
- `frontend/` - Next.js operations UI
- `simulator/` - Python simulator process
- `caddy/` - reverse proxy config
- `otel/` - local OpenTelemetry collector config
- `deploy/` - server-only environment templates

## Local Setup

1. Copy the local example environment: `cp .env.example .env`.
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

- Production runtime values are held by the private deployment controller. They are never committed or copied into repository-level GitHub secrets.
- Local demo data is controlled by `SEED_DEMO_DATA=true` in `.env`. It creates sample sites, stations, messages, and demo accounts for development only.
- The controller-managed production environment must keep `SEED_DEMO_DATA=false`.
- Creating the first production admin is an attended runtime operation: provide the bootstrap values through the controller, verify the account, and clear them immediately afterward.
- Do not use demo seeded accounts as a production bootstrap path.
- Rotate `PARTNER_WEBHOOK_SECRET` through a reviewed controller-managed runtime update; the UI shows this as a manual operator flow rather than an automated secret-manager integration.
- Configure `OCPP_STATION_TOKENS` as a JSON object mapping station external IDs to unique random tokens of at least 32 characters. The backend stores only SHA-256 token hashes.
- Chargers connect to `/ocpp/{station-id}` with `Authorization: Bearer <station-token>`. Admins can rotate a station token from the Admin view; update the charger and simulator environment with the same new token before reconnecting.
- Simulator state, scenario, and run endpoints require a currently active admin or operator bearer token.
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
- If OCPP traffic is not flowing, confirm the backend WebSocket endpoint, station ID, and matching entry in `OCPP_STATION_TOKENS`.
- If the database schema is missing, run the Alembic migration command in the backend container.

## Deployment

After a successful `ci-deploy` push workflow on `main`, [the production caller](.github/workflows/deploy-production.yml) delegates the release to the shared gateway at an immutable commit. The caller has only `actions: read`, `contents: read`, and `id-token: write`; its short-lived OIDC identity binds the request to the repository, branch, CI run, and exact source commit.

[The release manifest](.github/hetzner-release.json) defines the reviewed backend, frontend, and simulator image build inputs. The shared gateway publishes the immutable release request, and the private controller independently owns runtime configuration, routing, deployment policy, receipts, and rollback state. No host login, private key, address, or filesystem path belongs in this repository or its GitHub configuration.

[`docker-compose.prod.yml`](docker-compose.prod.yml), [`deploy/.env.example`](deploy/.env.example), and [`deploy/Caddyfile.prod`](deploy/Caddyfile.prod) remain application-level runtime specifications. They are not direct production deployment instructions. Changes to the release caller, manifest, or runtime specifications require production review.
