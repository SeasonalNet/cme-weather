from __future__ import annotations

from cme_weather.config import load_config


def test_config_loads_extended_cache_defaults() -> None:
    settings = load_config(path="/tmp/cme-weather-test-missing.yaml", env={})

    assert settings.cache.locations_ttl_seconds == 86400
    assert settings.cache.observations_ttl_seconds == 120
    assert settings.cache.stale_if_error_seconds == 1800
    assert settings.alerts.page_size == 6


def test_environment_overrides_extended_cache_values() -> None:
    settings = load_config(
        path="/tmp/cme-weather-test-missing.yaml",
        env={"CME_WEATHER_CACHE_OBSERVATIONS_TTL_SECONDS": "30", "CME_WEATHER_ALERT_PAGE_SIZE": "3"},
    )

    assert settings.cache.observations_ttl_seconds == 30
    assert settings.alerts.page_size == 3
