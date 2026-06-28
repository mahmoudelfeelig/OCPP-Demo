from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Protocol

from redis import Redis
from redis.exceptions import RedisError

from app.core.config import get_settings


class RedisLike(Protocol):
    def get(self, name: str) -> bytes | str | None: ...

    def setex(self, name: str, time: int, value: str) -> bool | None: ...

    def delete(self, *names: str) -> int: ...

    def ping(self) -> bool: ...


def get_redis_client() -> Redis:
    return Redis.from_url(get_settings().redis_url, decode_responses=True)


class StationSnapshotCache:
    def __init__(self, client: RedisLike | None = None, ttl_seconds: int = 30):
        self.client = client or get_redis_client()
        self.ttl_seconds = ttl_seconds

    def key(self, station_id: str) -> str:
        return f"station-snapshot:{station_id}"

    def get(self, station_id: str) -> dict[str, Any] | None:
        raw = self.client.get(self.key(station_id))
        if raw is None:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return json.loads(raw)

    def set(self, station_id: str, snapshot: dict[str, Any]) -> None:
        self.client.setex(self.key(station_id), self.ttl_seconds, json.dumps(snapshot, sort_keys=True))

    def invalidate(self, station_id: str) -> None:
        self.client.delete(self.key(station_id))


def cache_status() -> str:
    try:
        return "ok" if get_redis_client().ping() else "degraded"
    except RedisError:
        return "degraded"


WORKER_HEARTBEAT_KEY = "worker-heartbeat"


def write_worker_heartbeat(worker_id: str, ttl_seconds: int = 15, client: RedisLike | None = None) -> None:
    redis = client or get_redis_client()
    redis.setex(
        WORKER_HEARTBEAT_KEY,
        ttl_seconds,
        json.dumps({"worker_id": worker_id, "seen_at": datetime.now(UTC).isoformat()}, sort_keys=True),
    )


def worker_status(client: RedisLike | None = None) -> str:
    try:
        redis = client or get_redis_client()
        return "ok" if redis.get(WORKER_HEARTBEAT_KEY) is not None else "unknown"
    except RedisError:
        return "unknown"
