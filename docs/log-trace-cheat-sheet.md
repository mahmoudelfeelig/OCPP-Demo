# Log And Trace Cheat Sheet

# JSON Log Events

Use these log event names during the demo:

- `request_started`: API request accepted with request ID, method, and path.
- `request_finished`: API response emitted with status code and request ID.
- `worker_started`: worker process booted with worker ID.
- `outbox_processed`: worker processed an outbox event.
- `outbox_stale_locks_recovered`: worker recovered abandoned `processing` rows.

# Useful Commands

```bash
docker compose logs -f backend
docker compose logs -f worker
docker compose logs -f simulator
docker compose logs -f otel-collector
```

Filter for one request or worker path:

```bash
docker compose logs backend | rg request_id
docker compose logs worker | rg outbox
docker compose logs backend | rg ocpp
docker compose logs backend | rg partner
```

# Trace Story

The app creates spans around these areas:

- API request middleware
- OCPP ingestion
- outbox processing
- partner webhook processing

Detailed traces are exported to the local collector/log path. The UI intentionally shows only high-level operational health so it remains an operator console rather than a trace explorer.

# Metrics Story

The System screen summarizes:

- connected stations
- active sessions
- processed messages
- failed messages
- retrying outbox events
- worker lag
- cache health

For the interview, use the UI for high-level status and JSON logs for detailed evidence.
