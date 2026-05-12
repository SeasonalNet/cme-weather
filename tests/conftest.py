from __future__ import annotations

from cme_weather.config import load_config


def make_settings():
    return load_config(path="/tmp/cme-weather-test-missing.yaml", env={})
