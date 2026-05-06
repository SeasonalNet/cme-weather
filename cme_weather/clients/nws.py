from __future__ import annotations

from typing import Any, List

from cme_weather.clients.http import HttpJsonClient


class NwsClient:
    """Small NWS API client for the Cisco phone weather service."""

    def __init__(self, *, base_url: str, http: HttpJsonClient) -> None:
        self.base_url = base_url.rstrip("/")
        self.http = http

    def points(self, lat: float, lon: float) -> Any:
        return self.http.get_json(f"{self.base_url}/points/{lat:.4f},{lon:.4f}")

    def latest_observation(self, points_obj: Any) -> Any:
        stations_url = points_obj["properties"]["observationStations"]
        stations = self.http.get_json(stations_url)
        if not stations.get("features"):
            raise RuntimeError("no observation stations found")
        station_id = stations["features"][0]["properties"]["stationIdentifier"]
        return self.http.get_json(f"{self.base_url}/stations/{station_id}/observations/latest")

    def active_alerts(self, lat: float, lon: float) -> List[Any]:
        data = self.http.get_json(f"{self.base_url}/alerts/active?point={lat:.4f},{lon:.4f}")
        return data.get("features", [])

    def is_daytime(self, points_obj: Any) -> bool:
        """Decide day vs night using NWS forecast period 0."""
        props = points_obj.get("properties") or {}
        forecast_url = props.get("forecast")
        if not forecast_url:
            return True
        data = self.http.get_json(forecast_url)
        periods = ((data.get("properties") or {}).get("periods") or [])
        if not periods:
            return True
        return bool(periods[0].get("isDaytime", True))

    def alert(self, alert_id_or_url: str) -> Any:
        url = alert_id_or_url if alert_id_or_url.startswith("http") else f"{self.base_url}/alerts/{alert_id_or_url}"
        return self.http.get_json(url)
