from __future__ import annotations

import logging
from typing import Any, Optional

import requests

from cme_weather.cache import TtlCache

logger = logging.getLogger(__name__)


class HttpJsonClient:
    """Cached JSON HTTP client shared by upstream API clients."""

    def __init__(self, *, cache: TtlCache, timeout_seconds: float, user_agent: str) -> None:
        self.cache = cache
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent

    def get_json(
        self,
        url: str,
        *,
        cache_ttl_seconds: Optional[int] = None,
        stale_if_error_seconds: Optional[int] = None,
    ) -> Any:
        cache_key = f"GET:{url}"
        cached = self.cache.get(cache_key, ttl_seconds=cache_ttl_seconds)
        if cached is not None:
            return cached

        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/geo+json, application/json;q=0.9,*/*;q=0.1",
        }
        try:
            response = requests.get(url, headers=headers, timeout=self.timeout_seconds)
            response.raise_for_status()
            data = response.json()
        except Exception:
            stale = self.cache.get_stale(
                cache_key,
                ttl_seconds=cache_ttl_seconds,
                stale_if_error_seconds=stale_if_error_seconds,
            )
            if stale is not None:
                logger.warning("event=upstream_stale_served url=%s", url)
                return stale
            logger.warning("event=upstream_error url=%s", url, exc_info=True)
            raise

        self.cache.set(cache_key, data)
        return data
