#!/usr/bin/env python3
from __future__ import annotations

from cme_weather.server.app import app

settings = app.config["CME_WEATHER_SETTINGS"]


if __name__ == "__main__":
    app.run(host=settings.app.bind_host, port=settings.app.bind_port)
