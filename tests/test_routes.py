from __future__ import annotations

from tests.conftest import make_settings
from tests.test_weather_service import FakeLocations, FakeNws

from cme_weather.cache import TtlCache
from cme_weather.server.app import create_app


def make_client():
    settings = make_settings()
    app = create_app(settings=settings, cache=TtlCache(settings.cache.ttl_seconds), locations=FakeLocations(), nws=FakeNws())
    app.config.update(TESTING=True)
    return app.test_client()


def test_healthz_and_status_json() -> None:
    client = make_client()

    health = client.get("/cme/services/healthz")
    assert health.status_code == 200
    assert health.get_json()["ok"] is True

    status = client.get("/cme/services/status.json")
    assert status.status_code == 200
    assert status.get_json()["service"] == "SeasonalCMEWeather"


def test_weather_dashboard_links_to_richer_pages() -> None:
    client = make_client()

    response = client.get("/cme/services/weather/show?q=20794")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "CiscoIPPhoneIconFileMenu" in body
    assert "Current Conditions" not in body  # label is current weather line, not static copy
    assert "Active Alerts (2)" in body
    assert "Today / Tonight" in body
    assert "3-Day Forecast" in body


def test_current_and_forecast_pages() -> None:
    client = make_client()

    current = client.get("/cme/services/weather/current?q=20794").get_data(as_text=True)
    forecast = client.get("/cme/services/weather/forecast?q=20794&mode=today").get_data(as_text=True)

    assert "Wind:" in current
    assert "Humidity: 55%" in current
    assert "This Afternoon: 72F Showers likely" in forecast
    assert "Tonight: 61F Chance Showers" in forecast


def test_alert_list_and_detail_pages() -> None:
    client = make_client()

    alerts = client.get("/cme/services/weather/alerts?q=20794").get_data(as_text=True)
    assert "Severe Thunderstorm Warning" in alerts
    assert "Flood Watch" in alerts

    detail = client.get("/cme/services/weather/alert?id=warning-id").get_data(as_text=True)
    assert "Severity: Severe" in detail
    assert "Move indoors." in detail
