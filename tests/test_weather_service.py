from __future__ import annotations

from tests.conftest import make_settings

from cme_weather.services.weather import build_alert_detail, build_weather_menu


class FakeLocations:
    def latlon(self, query: str):
        if query == "bad":
            raise ValueError("bad location")
        return 39.0, -76.0, "Jessup, MD 20794"


class FakeNws:
    def points(self, lat: float, lon: float):
        return {"properties": {"forecast": "https://example.test/forecast"}}

    def latest_observation(self, points_obj):
        return {
            "properties": {
                "temperature": {"value": 20.0},
                "textDescription": "Light Rain",
                "relativeHumidity": {"value": 55.0},
                "windSpeed": {"value": 12.0, "unitCode": "wmoUnit:km_h-1"},
                "timestamp": "2026-05-11T15:00:00+00:00",
            }
        }

    def active_alerts(self, lat: float, lon: float):
        return [
            {
                "id": "watch-id",
                "properties": {
                    "event": "Flood Watch",
                    "severity": "Moderate",
                    "urgency": "Future",
                    "certainty": "Possible",
                    "expires": "2026-05-12T01:00:00+00:00",
                    "headline": "Flooding possible",
                },
            },
            {
                "id": "warning-id",
                "properties": {
                    "event": "Severe Thunderstorm Warning",
                    "severity": "Severe",
                    "urgency": "Immediate",
                    "certainty": "Likely",
                    "expires": "2026-05-11T16:00:00+00:00",
                    "headline": "Severe storms now",
                },
            },
        ]

    def forecast(self, points_obj):
        return [
            {
                "name": "This Afternoon",
                "temperature": 72,
                "temperatureUnit": "F",
                "isDaytime": True,
                "shortForecast": "Showers likely",
                "detailedForecast": "Showers are likely this afternoon.",
            },
            {
                "name": "Tonight",
                "temperature": 61,
                "temperatureUnit": "F",
                "isDaytime": False,
                "shortForecast": "Chance Showers",
                "detailedForecast": "A chance of showers tonight.",
            },
        ]

    def alert(self, alert_id: str):
        return {
            "properties": {
                "event": "Severe Thunderstorm Warning",
                "severity": "Severe",
                "urgency": "Immediate",
                "certainty": "Likely",
                "effective": "2026-05-11T15:00:00+00:00",
                "expires": "2026-05-11T16:00:00+00:00",
                "headline": "Severe storms now",
                "description": "A severe thunderstorm is occurring.",
                "instruction": "Move indoors.",
            }
        }


def test_build_weather_menu_sorts_alerts_and_includes_forecast() -> None:
    settings = make_settings()
    data = build_weather_menu(
        "20794",
        locations=FakeLocations(),
        nws=FakeNws(),
        weather_config=settings.weather,
        alerts_config=settings.alerts,
    )

    assert data.current_line == "Now: 68F Light Rain"
    assert data.alerts[0].event == "Severe Thunderstorm Warning"
    assert data.alerts[1].event == "Flood Watch"
    assert data.total_alerts == 2
    assert data.forecast_periods[0].summary_line == "This Afternoon: 72F Showers likely"


def test_alert_detail_includes_metadata_and_body() -> None:
    settings = make_settings()
    detail = build_alert_detail("warning-id", nws=FakeNws(), alerts_config=settings.alerts)

    assert detail.event == "Severe Thunderstorm Warning"
    assert "Severity: Severe" in detail.body
    assert "Severe storms now" in detail.body
    assert "Move indoors." in detail.body
