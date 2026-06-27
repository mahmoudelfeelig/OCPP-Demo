from __future__ import annotations

from prometheus_client import Counter, Gauge

connected_stations = Gauge("ocpp_connected_stations", "Stations currently marked online")
active_sessions = Gauge("ocpp_active_sessions", "Sessions currently active")
processed_messages = Counter("ocpp_processed_messages_total", "Processed OCPP and partner messages")
failed_messages = Counter("ocpp_failed_messages_total", "Failed OCPP and partner messages")
retry_events = Counter("ocpp_retry_events_total", "Outbox events scheduled for retry")
webhook_events = Counter("ocpp_webhook_events_total", "Inbound partner webhook events handled")
worker_lag_seconds = Gauge("ocpp_worker_lag_seconds", "Age of the oldest pending outbox event")
