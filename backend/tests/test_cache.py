from __future__ import annotations

from app.services.cache import StationSnapshotCache


class FakeRedis:
    def __init__(self):
        self.values: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    def get(self, name: str) -> str | None:
        return self.values.get(name)

    def setex(self, name: str, time: int, value: str) -> bool:
        self.values[name] = value
        self.ttls[name] = time
        return True

    def delete(self, *names: str) -> int:
        deleted = 0
        for name in names:
            if name in self.values:
                deleted += 1
                self.values.pop(name)
        return deleted

    def ping(self) -> bool:
        return True


def test_station_snapshot_cache_roundtrip_and_invalidate() -> None:
    redis = FakeRedis()
    cache = StationSnapshotCache(redis, ttl_seconds=12)

    assert cache.get("station-1") is None

    cache.set("station-1", {"online": True, "state": "online"})

    assert redis.ttls["station-snapshot:station-1"] == 12
    assert cache.get("station-1") == {"online": True, "state": "online"}

    cache.invalidate("station-1")

    assert cache.get("station-1") is None
