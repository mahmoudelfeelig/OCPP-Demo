# Product Direction
- [x] Build `ocpp-backend-demo` as a backend lifecycle demo.
- [x] Focus on backend engineering judgment, not a complete charging platform.
- [x] Model a multi-site EV charging fleet.
- [x] Use OCPP 1.6 as the demo protocol scope.
- [x] Use real OCPP over WebSocket.
- [x] Include a product-quality operations dashboard instead of relying on Swagger.
- [x] Keep billing, tariffs, payments, roaming, mobile apps, Kubernetes, serverless, and OCPP 2.0.1 out of scope.
- [x] Add a short interview demo script that maps each screen to the engineering concept it proves.

# Runtime Architecture
- [x] Use Python and FastAPI for the backend.
- [x] Use PostgreSQL as the durable source of truth.
- [x] Use SQLAlchemy for persistence.
- [x] Use Alembic for migrations.
- [x] Use Redis only as a cache.
- [x] Use a containerized backend and worker.
- [x] Use Docker Compose as the only runtime target.
- [x] Include backend, worker, PostgreSQL, Redis, frontend, simulator, Caddy, and local OTel collector services.
- [x] Add Caddy reverse proxy for local demo routing.
- [x] Keep the future public host target as `ocpp.elfeel.me`.
- [ ] Verify the full Compose stack from a clean checkout.
- [x] Add a one-command seed/reset flow for demo rehearsals.

# Backend API
- [x] Expose REST APIs through FastAPI.
- [x] Add `/health`, `/ready`, and metrics/status endpoints.
- [x] Add JWT login and current-user endpoints.
- [x] Add site, station, connector, session, transaction, event, message, outbox, webhook, system, and admin API surfaces.
- [x] Add role checks for admin and operator paths.
- [x] Return explicit API errors for common admin validation failures.
- [x] Add Pydantic response models for all resource endpoints.
- [x] Add pagination and filtering for operational tables.
- [x] Add API contract tests for every dashboard-facing endpoint.

# OCPP WebSocket Ingestion
- [x] Add WebSocket endpoint `/ocpp/{station_id}`.
- [x] Accept internal station IDs or seeded external station IDs such as `BER-001`.
- [x] Support `BootNotification`.
- [x] Support `Heartbeat`.
- [x] Support `StatusNotification`.
- [x] Support `Authorize`.
- [x] Support `StartTransaction`.
- [x] Support `MeterValues`.
- [x] Support `StopTransaction`.
- [x] Persist raw inbound OCPP messages.
- [x] Create an outbox row in the same database transaction.
- [x] Enforce unique OCPP message IDs.
- [x] Return OCPP CALLRESULT or CALLERROR frames.
- [x] Preserve a parseable CALL message ID in CALLERROR responses.
- [x] Assign the OCPP transaction ID in the StartTransaction CALLRESULT and reuse it in later charger messages.
- [x] Validate required fields and non-empty MeterValues arrays for supported actions.
- [x] Add protocol-level tests for malformed arrays and unsupported message types.
- [x] Add a documented OCPP message transcript for the demo happy path.

# Domain Model
- [x] Add sites with human-readable labels.
- [x] Add stations belonging to sites.
- [x] Add connectors belonging to stations.
- [x] Add sessions scoped to sites in the UI.
- [x] Keep station online/offline state separate from connector state.
- [x] Keep session lifecycle state separate from transaction state.
- [x] Add OCPP messages, outbox events, partner events, webhook deliveries, users, roles, and audit events.
- [x] Add explicit enums for station, connector, session, transaction, outbox, partner event, and role states.
- [x] Record state transition history as audit events.
- [x] Add stronger idempotency handling for duplicate meter samples.
- [x] Add repository tests against PostgreSQL, not only in-memory SQLite.

# Async Processing And Reliability
- [x] Use a Postgres outbox pattern.
- [x] Add a separate worker process.
- [x] Add outbox statuses: `pending`, `processing`, `processed`, `retrying`, `failed`, `dead_lettered`.
- [x] Add retry attempts and next-attempt scheduling.
- [x] Add exponential backoff.
- [x] Add dead-letter state and visible failure reasons.
- [x] Use `FOR UPDATE SKIP LOCKED` for worker locking on PostgreSQL.
- [x] Roll back failed OCPP WebSocket message transactions before continuing.
- [x] Add integration tests with two workers racing for the same outbox row.
- [x] Add dead-letter acknowledgement semantics that preserve the original terminal failure state.
- [x] Add stale `processing` lock recovery.
- [x] Document the outbox as durable worker scaffolding without downstream fanout or command dispatch.

# Authentication And Roles
- [x] Use JWT authentication.
- [x] Seed local `admin@localhost` and `operator@localhost` users.
- [x] Hash passwords.
- [x] Protect dashboard APIs with admin/operator roles.
- [x] Let operators view operational data and run safe simulator actions.
- [x] Restrict user management, dead-letter handling, and maintenance controls to admins.
- [x] Audit admin actions.
- [x] Add refresh-token behavior or document short-lived demo-token limits.
- [x] Add frontend route guards that redirect expired sessions cleanly.
- [x] Add tests for every role-sensitive API action.

# Partner Webhooks
- [x] Add partner webhook receiver.
- [x] Verify HMAC signatures.
- [x] Enforce idempotent event IDs.
- [x] Persist raw partner webhook events.
- [x] Process partner webhook work through the outbox.
- [x] Show partner webhook state in the UI.
- [x] Add simulator support for partner webhook scenario.
- [x] Decide outbound webhook delivery retry simulation is out of scope for this receiver-focused demo.
- [x] Add failure injection for invalid signatures and duplicate partner events in the UI.

# Simulator
- [x] Add a separate Python simulator service.
- [x] Expose simulator health, state, scenario list, and run endpoint.
- [x] Add happy-path charging session scenario.
- [x] Add duplicate meter value scenario.
- [x] Add station offline/online scenario.
- [x] Add connector fault scenario.
- [x] Add interrupted session scenario.
- [x] Add partner webhook scenario.
- [x] Default simulator traffic to seeded station `BER-001`.
- [x] Expose scenario controls in the UI.
- [x] Add scenario speed handling.
- [x] Add simulator integration tests against the real backend container.
- [x] Add clear UI feedback when simulator WebSocket connection fails.
- [x] Label simulated start/stop admin controls as audit-only rather than outbound OCPP commands.

# Frontend Operations UI
- [x] Use Next.js and React.
- [x] Use a separate frontend container.
- [x] Build a dense operations dashboard.
- [x] Use a custom visual direction with liquid-glass styling.
- [x] Add login screen.
- [x] Add app shell with sidebar navigation.
- [x] Add overview, sites, site detail, stations, station detail, sessions, session detail, events, raw messages, webhooks, simulator, system, and admin views.
- [x] Add connector detail panel.
- [x] Add role-aware admin visibility.
- [x] Show high-level health and metrics summaries.
- [x] Compare the visual treatment against `/mnt/d/Stuff/Projects/Sites/RPS` and tune spacing, glass, and typography.
- [x] Add frontend smoke tests.
- [ ] Add mobile layout QA screenshots.
- [x] Add loading, empty, and error states for every major panel.

# Observability
- [x] Add JSON structured logging setup.
- [x] Add request correlation middleware.
- [x] Add OpenTelemetry tracing setup.
- [x] Add OpenTelemetry collector config for local logs/collector output.
- [x] Add metrics counters/gauges for key operational signals.
- [x] Show health, readiness, worker, cache, retry, and failure summaries in the UI.
- [x] Document Redis as limited station-snapshot and worker-heartbeat infrastructure; PostgreSQL remains the dashboard read source.
- [x] Confirm traces are emitted for API requests in the running stack.
- [ ] Confirm traces are emitted for OCPP ingestion, outbox processing, and partner webhooks in the running stack.
- [x] Add a documented log query cheat sheet for the interview demo.

# Testing
- [x] Add pytest backend test scaffold.
- [x] Add ingestion idempotency test.
- [x] Add state transition history test.
- [x] Add illegal connector transition test.
- [x] Add outbox retry and dead-letter tests.
- [x] Add partner webhook signature and duplicate tests.
- [x] Add API auth/security tests.
- [x] Add simulator smoke test.
- [x] Add Compose smoke script documentation.
- [x] Install or containerize test execution so tests run consistently from this workspace.
- [x] Add OCPP happy-path integration test.
- [x] Add interrupted session integration test.
- [x] Add Redis cache behavior tests.
- [x] Add Docker Compose smoke run in CI or a documented manual transcript.

# Deployment And Documentation
- [x] Add `README.md` with scope, setup, commands, demo flow, operations notes, troubleshooting, and deployment links.
- [x] Add `.env.example`.
- [x] Add deployment docs for Hetzner/Caddy.
- [x] Add production Compose file.
- [x] Document that production secrets are not committed.
- [x] Add smoke-check script documentation.
- [x] Add architecture diagram.
- [x] Add final demo checklist for `ocpp.elfeel.me` once the host is provisioned.
