from __future__ import annotations

from cme_weather.server.app import app

# Gunicorn and other WSGI servers can import either name.
application = app
