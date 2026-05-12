from __future__ import annotations

from typing import Any, List

from cme_weather.clients.http import HttpJsonClient
from cme_weather.config import CacheConfig


class NwsClient:
    """Small NWS API client for the Cisco phone weather service."""

    def __init__(self, *, base_url: str, http: HttpJsonClient, cache_config: CacheConfig) -> None:
        self.base_url = base_url.rstrip("/")
        self.http = http
        self.cache_config = cache_config

    def points(self, lat: float, lon: float) -> Any:
        return self.http.get_json(
            f"{self.base_url}/points/{lat:.4f},{lon:.4f}",
            cache_ttl_seconds=self.cache_config.points_ttl_seconds,
            stale_if_error_seconds=self.cache_config.stale_if_error_seconds,
        )

    def latest_observation(self, points_obj: Any) -> Any:
        stations_url = points_obj["properties"]["observationStations"]
        stations = self.http.get_json(
            stations_url,
            cache_ttl_seconds=self.cache_config.stations_ttl_seconds,
            stale_if_error_seconds=self.cache_config.stale_if_error_seconds,
        )
        if not stations.get("features"):
            raise RuntimeError("no observation stations found")
        station_id = stations["features"][0]["properties"]["stationIdentifier"]
        return self.http.get_json(
            f"{self.base_url}/stations/{station_id}/observations/latest",
            cache_ttl_seconds=self.cache_config.observations_ttl_seconds,
            stale_if_error_seconds=self.cache_config.stale_if_error_seconds,
        )

    def active_alerts(self, lat: float, lon: float) -> List[Any]:
        data = self.http.get_json(
            f"{self.base_url}/alerts/active?point={lat:.4f},{lon:.4f}",
            cache_ttl_seconds=self.cache_config.alerts_ttl_seconds,
            stale_if_error_seconds=self.cache_config.stale_if_error_seconds,
        )
        return data.get("features", [])

    def forecast(self, points_obj: Any) -> List[Any]:
        props = points_obj.get("properties") or {}
        forecast_url = props.get("forecast")
        if not forecast_url:
            return []
        data = self.http.get_json(
            forecast_url,
            cache_ttl_seconds=self.cache_config.forecast_ttl_seconds,
            stale_if_error_seconds=self.cache_config.stale_if_error_seconds,
        )
        return ((data.get("properties") or {}).get("periods") or [])

    def is_daytime(self, points_obj: Any) -> bool:
        """Decide day vs night using NWS forecast period 0."""
        periods = self.forecast(points_obj)
        if not periods:
            return True
        return bool(periods[0].get("isDaytime", True))

    def alert(self, alert_id_or_url: str) -> Any:
        url = alert_id_or_url if alert_id_or_url.startswith("http") else f"{self.base_url}/alerts/{alert_id_or_url}"
        return self.http.get_json(
            url,
            cache_ttl_seconds=self.cache_config.alerts_ttl_seconds,
            stale_if_error_seconds=self.cache_config.stale_if_error_seconds,
        )
