from __future__ import annotations

import re
from typing import Tuple
from urllib.parse import quote

from cme_weather.clients.http import HttpJsonClient

ZIP_RE = re.compile(r"^\d{5}(-\d{4})?$", re.ASCII)


class ZippopotamClient:
    """Location lookup client backed by api.zippopotam.us."""

    def __init__(self, *, base_url: str, http: HttpJsonClient) -> None:
        self.base_url = base_url.rstrip("/")
        self.http = http

    def latlon(self, query: str) -> Tuple[float, float, str]:
        query = (query or "").strip()
        if not query:
            raise ValueError("empty query")

        if ZIP_RE.match(query):
            data = self.http.get_json(f"{self.base_url}/us/{query[:5]}")
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
        data = self.http.get_json(f"{self.base_url}/us/{state}/{quote(city)}")
        place = data["places"][0]
        lat = float(place["latitude"])
        lon = float(place["longitude"])
        label = f'{place["place name"]}, {place["state abbreviation"]}'
        return lat, lon, label
