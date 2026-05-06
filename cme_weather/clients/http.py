from __future__ import annotations

from typing import Any

import requests

from cme_weather.cache import TtlCache


class HttpJsonClient:
    """Cached JSON HTTP client shared by upstream API clients."""

    def __init__(self, *, cache: TtlCache, timeout_seconds: float, user_agent: str) -> None:
        self.cache = cache
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent

    def get_json(self, url: str) -> Any:
        cache_key = f"GET:{url}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/geo+json, application/json;q=0.9,*/*;q=0.1",
        }
        response = requests.get(url, headers=headers, timeout=self.timeout_seconds)
        response.raise_for_status()
        data = response.json()
        self.cache.set(cache_key, data)
        return data
