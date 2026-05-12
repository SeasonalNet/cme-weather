# cme-weather

SeasonalCME Cisco IP Phone XML weather service.

This Flask app provides weather services for Cisco IP phones under `/cme/services/`. It is intended for the SeasonalNet web services stack, but it is usable anywhere a small Cisco XML weather app is useful.

## Features

- Root Cisco IP Phone service menu
- Weather lookup by ZIP or `City, ST`
- Current conditions from NWS
- Active alert menu with severity/event-priority ordering
- Alert detail pages with severity, urgency, certainty, effective time, expiration time, headline, description, and instructions
- Today/Tonight and 3-day forecast text pages
- Cisco `IconFileMenu` support
- WS4KP-style weather icon support with generated fallbacks
- Data-specific in-memory cache TTLs
- Stale-if-error upstream cache fallback
- `/healthz` and `/status.json` monitoring endpoints
- YAML configuration with environment variable overrides
- WSGI entrypoint for Gunicorn/systemd/nginx deployment
- pytest coverage for cache, config, service orchestration, and Flask routes

## Layout

```text
app.py                  # local/development compatibility entrypoint
wsgi.py                 # WSGI entrypoint for Gunicorn/production-style service use
DEPLOYMENT.md           # systemd/nginx/Gunicorn deployment notes
cme_weather/
  config.py
  cache.py
  icons.py
  clients/
    http.py
    nws.py
    zippopotam.py
  renderers/
    cisco_xml.py
  server/
    app.py
    routes.py
  services/
    weather.py
tests/
```

The Flask app and routes live under `cme_weather/server/`; upstream API access lives under `cme_weather/clients/`; route-independent weather orchestration lives under `cme_weather/services/`.

## Install

```bash
python3 -m venv venv
. venv/bin/activate
python -m pip install -r requirements.txt
```

For development/test work:

```bash
python -m pip install -r requirements-dev.txt
```

## Configuration

Copy the example config before running the service:

```bash
cp config.yaml.example config.yaml
nano config.yaml
```

`config.yaml` is ignored by git so each host can keep local runtime settings.

Default local config highlights:

```yaml
app:
  bind_host: 127.0.0.1
  bind_port: 9010
  public_base_path: /cme/services

http:
  timeout_seconds: 4.5

cache:
  ttl_seconds: 60
  locations_ttl_seconds: 86400
  points_ttl_seconds: 21600
  stations_ttl_seconds: 21600
  observations_ttl_seconds: 120
  alerts_ttl_seconds: 60
  forecast_ttl_seconds: 900
  stale_if_error_seconds: 1800

nws:
  base_url: https://api.weather.gov
  user_agent: "(seasonalnet.org, info@seasonalnet.org)"

zippopotam:
  base_url: https://api.zippopotam.us

weather:
  default_query: "90210"
  max_alerts: 6
  fallback_daytime: true

alerts:
  headline_clip_chars: 300
  description_clip_chars: 900
  instruction_clip_chars: 500
  page_size: 6
  icon_overrides: {}
```

The default config path is `config.yaml` at the repository root. To use another file:

```bash
export CME_WEATHER_CONFIG=/opt/cme-weather/config.yaml
```

Configuration precedence is:

```text
built-in defaults -> config.yaml -> environment variables
```

## Environment variable overrides

Service-scoped variables are preferred:

| Variable | Config key | Purpose |
| --- | --- | --- |
| `CME_WEATHER_CONFIG` | n/a | Path to the YAML config file |
| `CME_WEATHER_BIND_HOST` | `app.bind_host` | Local bind host |
| `CME_WEATHER_BIND_PORT` | `app.bind_port` | Local bind port |
| `CME_WEATHER_PUBLIC_BASE_PATH` | `app.public_base_path` | Public Cisco service path |
| `CME_WEATHER_HTTP_TIMEOUT_SECONDS` | `http.timeout_seconds` | Upstream HTTP timeout in seconds |
| `CME_WEATHER_CACHE_TTL_SECONDS` | `cache.ttl_seconds` | Default in-memory cache TTL |
| `CME_WEATHER_CACHE_LOCATIONS_TTL_SECONDS` | `cache.locations_ttl_seconds` | Location lookup cache TTL |
| `CME_WEATHER_CACHE_POINTS_TTL_SECONDS` | `cache.points_ttl_seconds` | NWS point metadata cache TTL |
| `CME_WEATHER_CACHE_STATIONS_TTL_SECONDS` | `cache.stations_ttl_seconds` | NWS station metadata cache TTL |
| `CME_WEATHER_CACHE_OBSERVATIONS_TTL_SECONDS` | `cache.observations_ttl_seconds` | NWS latest-observation cache TTL |
| `CME_WEATHER_CACHE_ALERTS_TTL_SECONDS` | `cache.alerts_ttl_seconds` | NWS active-alert cache TTL |
| `CME_WEATHER_CACHE_FORECAST_TTL_SECONDS` | `cache.forecast_ttl_seconds` | NWS forecast cache TTL |
| `CME_WEATHER_CACHE_STALE_IF_ERROR_SECONDS` | `cache.stale_if_error_seconds` | Extra stale cache window used after upstream failures |
| `CME_WEATHER_NWS_BASE_URL` | `nws.base_url` | NWS API base URL |
| `CME_WEATHER_NWS_USER_AGENT` | `nws.user_agent` | User-Agent sent to weather.gov |
| `CME_WEATHER_ZIPPOTAM_BASE_URL` | `zippopotam.base_url` | Zippopotam API base URL |
| `CME_WEATHER_WS_ICON_DIR` | `icons.ws_icon_dir` | Runtime icon directory |
| `CME_WEATHER_DEFAULT_QUERY` | `weather.default_query` | Default phone input value |
| `CME_WEATHER_MAX_ALERTS` | `weather.max_alerts` | Alert rows shown in phone menus |
| `CME_WEATHER_FALLBACK_DAYTIME` | `weather.fallback_daytime` | Day/night fallback if forecast lookup fails |
| `CME_WEATHER_ALERT_HEADLINE_CLIP_CHARS` | `alerts.headline_clip_chars` | Alert headline clipping length |
| `CME_WEATHER_ALERT_DESCRIPTION_CLIP_CHARS` | `alerts.description_clip_chars` | Alert description clipping length |
| `CME_WEATHER_ALERT_INSTRUCTION_CLIP_CHARS` | `alerts.instruction_clip_chars` | Alert instruction clipping length |
| `CME_WEATHER_ALERT_PAGE_SIZE` | `alerts.page_size` | Alerts shown per phone menu page |

Legacy variables from the original single-file app are still honored:

| Legacy variable | Replacement |
| --- | --- |
| `NWS_USER_AGENT` | `CME_WEATHER_NWS_USER_AGENT` |
| `HTTP_TIMEOUT` | `CME_WEATHER_HTTP_TIMEOUT_SECONDS` |
| `CACHE_TTL_SECONDS` | `CME_WEATHER_CACHE_TTL_SECONDS` |
| `WS_ICON_DIR` | `CME_WEATHER_WS_ICON_DIR` |

## Runtime

Development/local run:

```bash
python3 app.py
```

Production-style WSGI run:

```bash
gunicorn --bind 127.0.0.1:9010 --workers 1 --threads 4 --timeout 15 wsgi:app
```

Expected reverse-proxy/service path:

```text
/cme/services/
```

See `DEPLOYMENT.md` for the full systemd and nginx deployment example.

## Cisco phone flow

```text
/cme/services/
  Weather
    ZIP / City input
      Current conditions
      Active alerts
      Today / Tonight
      3-Day Forecast
      Refresh
  Ping
```

The older `/cme/services/weather/show?q=...` endpoint remains the main post-input page, but now acts as a weather dashboard instead of a single crowded menu.

## Checks

```bash
python3 -m py_compile app.py wsgi.py
python3 -m compileall cme_weather tests
python3 -m pytest
curl -s http://127.0.0.1:9010/cme/services/healthz
curl -s http://127.0.0.1:9010/cme/services/status.json
curl -s http://127.0.0.1:9010/cme/services/ping
curl -s http://127.0.0.1:9010/cme/services/
```

## External `ws4kp` source checkout

This repository does **not** vendor the full upstream `ws4kp` project.

For local asset reference work, clone it beside the app as an ignored working copy:

```bash
git clone https://github.com/netbymatt/ws4kp ws4kp
```

The `ws4kp/` directory is ignored by this repository. Runtime icon assets used by this app live under:

```text
icons/ws4kp18/
```
