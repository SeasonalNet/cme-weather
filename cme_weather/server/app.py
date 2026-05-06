from __future__ import annotations

from flask import Flask

from cme_weather.cache import TtlCache
from cme_weather.clients.http import HttpJsonClient
from cme_weather.clients.nws import NwsClient
from cme_weather.clients.zippopotam import ZippopotamClient
from cme_weather.config import Settings, load_config
from cme_weather.server.routes import register_routes


def create_app(settings: Settings | None = None) -> Flask:
    settings = settings or load_config()

    app = Flask(__name__)
    app.config["CME_WEATHER_SETTINGS"] = settings
    cache = TtlCache(settings.cache.ttl_seconds)
    http = HttpJsonClient(
        cache=cache,
        timeout_seconds=settings.http.timeout_seconds,
        user_agent=settings.nws.user_agent,
    )
    locations = ZippopotamClient(base_url=settings.zippopotam.base_url, http=http)
    nws = NwsClient(base_url=settings.nws.base_url, http=http)

    register_routes(app, settings=settings, locations=locations, nws=nws)
    return app


app = create_app()
