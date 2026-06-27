# Final Demo Checklist

# Clean Checkout
- [ ] Clone the repository into a fresh directory.
- [ ] Copy `.env.example` to `.env`.
- [ ] Run `docker compose build`.
- [ ] Run `docker compose up -d`.
- [ ] Run `./scripts/compose-smoke.sh`.
- [ ] Open `http://localhost:8080`.
- [ ] Log in with `admin@localhost / admin123`.
- [ ] Run `happy-path-charging-session` from the Simulator panel.
- [ ] Confirm Sessions shows a completed session.
- [ ] Confirm Raw Messages shows `BootNotification`, `StartTransaction`, `MeterValues`, and `StopTransaction`.
- [ ] Confirm worker logs contain `outbox_processed`.

# Rehearsal Reset
- [ ] Run `make reset-demo` before a recorded or live interview rehearsal.
- [ ] Confirm the command ends with `demo reset complete`.
- [ ] Avoid pointing `OCPP_POSTGRES_TEST_URL` at a database that contains data you want to keep.

# Local Test Suite
- [ ] Run `make test-backend`.
- [ ] Run `make test-simulator`.
- [ ] Run `make test-frontend`.
- [ ] Run `make test-backend-postgres` when the Compose Postgres service is available.

# Observability
- [ ] Run a simulator scenario.
- [ ] Confirm backend logs are JSON structured.
- [ ] Confirm worker logs show `worker_started` and `outbox_processed`.
- [ ] Confirm OTel collector logs show `TracesExporter` records for API requests.
- [ ] Confirm `/api/metrics/status` reports health, cache, retry, and worker lag values.

# Public Host `ocpp.elfeel.me`
- [ ] Provision the host and Docker runtime.
- [ ] Copy `deploy/.env.example` to `deploy/.env` on the host.
- [ ] Replace all demo secrets in `deploy/.env`.
- [ ] Configure host Caddy from `deploy/Caddyfile.host.example`.
- [ ] Point DNS for `ocpp.elfeel.me` at the host.
- [ ] Pull the GHCR images.
- [ ] Run `docker compose --env-file deploy/.env -f docker-compose.prod.yml up -d`.
- [ ] Check `https://ocpp.elfeel.me/healthz`.
- [ ] Check `https://ocpp.elfeel.me/api/ready`.
- [ ] Run one simulator scenario and verify dashboard state.
