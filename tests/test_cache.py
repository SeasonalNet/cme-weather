from __future__ import annotations

import time

from cme_weather.cache import TtlCache


def test_cache_returns_fresh_entry() -> None:
    cache = TtlCache(60)
    cache.set("k", {"ok": True})

    assert cache.get("k") == {"ok": True}
    stats = cache.snapshot()
    assert stats.fresh_hits == 1
    assert stats.entries == 1


def test_cache_can_return_stale_entry_inside_stale_if_error_window() -> None:
    cache = TtlCache(1, stale_if_error_seconds=60)
    cache.set("k", "old")
    cache._items["k"] = (time.time() - 5, "old")

    assert cache.get("k") is None
    assert cache.get_stale("k") == "old"
    stats = cache.snapshot()
    assert stats.stale_hits == 1
