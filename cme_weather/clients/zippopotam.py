from __future__ import annotations

import re
from typing import Tuple
from urllib.parse import quote

from cme_weather.clients.http import HttpJsonClient
from cme_weather.config import CacheConfig

ZIP_RE = re.compile(r"^\d{5}(-\d{4})?$", re.ASCII)


class ZippopotamClient:
    """Location lookup client backed by api.zippopotam.us."""

    def __init__(self, *, base_url: str, http: HttpJsonClient, cache_config: CacheConfig) -> None:
        self.base_url = base_url.rstrip("/")
        self.http = http
        self.cache_config = cache_config

    def latlon(self, query: str) -> Tuple[float, float, str]:
        query = (query or "").strip()
        if not query:
            raise ValueError("empty query")

        if ZIP_RE.match(query):
            data = self.http.get_json(
                f"{self.base_url}/us/{query[:5]}",
                cache_ttl_seconds=self.cache_config.locations_ttl_seconds,
                stale_if_error_seconds=self.cache_config.stale_if_error_seconds,
            )
            place = data["places"][0]
            lat = float(place["latitude"])
            lon = float(place["longitude"])
            label = f'{place["place name"]}, {place["state abbreviation"]} {query[:5]}'
            return lat, lon, label

        match = re.match(r"^\s*([^,]+)\s*,\s*([A-Za-z]{2})\s*$", query)
        if not match:
            raise ValueError("format must be ZIP (90210) or City, ST (Belmont, MA)")

        city = match.group(1).strip()
        state = match.group(2).strip().lower()
        data = self.http.get_json(
            f"{self.base_url}/us/{state}/{quote(city)}",
            cache_ttl_seconds=self.cache_config.locations_ttl_seconds,
            stale_if_error_seconds=self.cache_config.stale_if_error_seconds,
        )
        place = data["places"][0]
        lat = float(place["latitude"])
        lon = float(place["longitude"])
        label = f'{place["place name"]}, {place["state abbreviation"]}'
        return lat, lon, label
