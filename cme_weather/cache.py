from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


@dataclass(frozen=True)
class CacheStats:
    fresh_hits: int
    stale_hits: int
    misses: int
    writes: int
    entries: int


class TtlCache:
    """Small in-memory TTL cache for upstream HTTP responses.

    The cache supports per-call TTLs so slow-changing NWS metadata can live
    longer than observations and alert data. It also supports stale-if-error
    reads for upstream resilience.
    """

    def __init__(self, ttl_seconds: int, *, stale_if_error_seconds: int = 0) -> None:
        self.ttl_seconds = max(0, int(ttl_seconds))
        self.stale_if_error_seconds = max(0, int(stale_if_error_seconds))
        self._items: Dict[str, Tuple[float, Any]] = {}
        self._lock = threading.RLock()
        self._fresh_hits = 0
        self._stale_hits = 0
        self._misses = 0
        self._writes = 0

    def _ttl(self, ttl_seconds: Optional[int]) -> int:
        return self.ttl_seconds if ttl_seconds is None else max(0, int(ttl_seconds))

    def get(self, key: str, *, ttl_seconds: Optional[int] = None) -> Optional[Any]:
        ttl = self._ttl(ttl_seconds)
        with self._lock:
            value = self._items.get(key)
            if value is None:
                self._misses += 1
                return None

            timestamp, data = value
            if ttl <= 0 or (time.time() - timestamp) > ttl:
                self._misses += 1
                return None

            self._fresh_hits += 1
            return data

    def get_stale(
        self,
        key: str,
        *,
        ttl_seconds: Optional[int] = None,
        stale_if_error_seconds: Optional[int] = None,
    ) -> Optional[Any]:
        ttl = self._ttl(ttl_seconds)
        stale_window = (
            self.stale_if_error_seconds
            if stale_if_error_seconds is None
            else max(0, int(stale_if_error_seconds))
        )
        if stale_window <= 0:
            return None

        with self._lock:
            value = self._items.get(key)
            if value is None:
                return None

            timestamp, data = value
            if ttl <= 0:
                return None
            if (time.time() - timestamp) > (ttl + stale_window):
                return None

            self._stale_hits += 1
            return data

    def set(self, key: str, data: Any) -> None:
        with self._lock:
            self._items[key] = (time.time(), data)
            self._writes += 1

    def snapshot(self) -> CacheStats:
        with self._lock:
            return CacheStats(
                fresh_hits=self._fresh_hits,
                stale_hits=self._stale_hits,
                misses=self._misses,
                writes=self._writes,
                entries=len(self._items),
            )
