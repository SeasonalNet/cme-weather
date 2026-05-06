from __future__ import annotations

import time
from typing import Any, Dict, Optional, Tuple


class TtlCache:
    """Small in-memory TTL cache for upstream HTTP responses."""

    def __init__(self, ttl_seconds: int) -> None:
        self.ttl_seconds = max(0, int(ttl_seconds))
        self._items: Dict[str, Tuple[float, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        value = self._items.get(key)
        if value is None:
            return None

        timestamp, data = value
        if self.ttl_seconds <= 0 or (time.time() - timestamp) > self.ttl_seconds:
            self._items.pop(key, None)
            return None

        return data

    def set(self, key: str, data: Any) -> None:
        if self.ttl_seconds <= 0:
            return
        self._items[key] = (time.time(), data)
