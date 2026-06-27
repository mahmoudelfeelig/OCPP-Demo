# Interview Demo Script

# Opening
- Show the dashboard and frame the scope: this is a lifecycle backend demo, not a billing or roaming platform.
- Call out the architecture choices: FastAPI, PostgreSQL, SQLAlchemy, Alembic, outbox worker, Redis cache, Next.js UI, Caddy, Docker Compose.
- Explain that OCPP is real WebSocket traffic and the UI is an operator console, not Swagger-only.

# Fleet Overview
- Start on Overview.
- Point to station counts, active sessions, retry/dead-letter counts, webhook status, and health summary.
- Explain the domain separation: station online state, connector state, session state, and transaction state are modeled independently.

# OCPP Happy Path
- Open Simulator and run `happy-path-charging-session`.
- Move to Raw Messages and show BootNotification, Heartbeat, StatusNotification, StartTransaction, MeterValues, StopTransaction.
- Move to Session Detail and show the completed session, closed transaction, and meter timeline.
- Explain idempotency: raw message IDs are unique, and duplicate messages return the previous response.

# Failure And Recovery
- Run `duplicate-meter-value`.
- Show that duplicate meter samples are audited rather than double-counted.
- Run `connector-fault` or `station-offline-online`.
- Show connector state and station state changing separately.
- Open System and Admin to show outbox retry/dead-letter surfaces.

# Worker Reliability
- Explain the outbox path: API transaction writes raw message plus outbox event, then worker processes asynchronously.
- Highlight retry/backoff, max attempts, stale processing lock recovery, and dead-letter acknowledgement.
- Explain that acknowledging a dead letter does not mark it processed; it records acknowledgement metadata while preserving the terminal status.

# Partner Webhook
- Run `partner-webhook`.
- Show signature verification, idempotent partner event IDs, outbox processing, and UI visibility.
- Explain that invalid signatures and duplicate event IDs are handled deterministically.

# Observability
- Open System Health and Observability.
- Show high-level health, readiness, worker, cache, and retry/failure counts.
- Explain that detailed traces and JSON logs remain in logs/local OTel collector output.

# Admin And Roles
- Log in as `operator@localhost` and show operational access.
- Log in as `admin@localhost` and show user/role management, dead-letter acknowledgement, maintenance, and operational override controls.
- Explain that every admin action is audited.

# Close
- State the non-goals clearly: billing, tariffs, payments, roaming, mobile app, Kubernetes, serverless, and OCPP 2.0.1.
- Close on the engineering claim: durable ingestion, idempotency, async processing, observable operations, and a product-quality dashboard.
