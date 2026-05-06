# cme-weather

SeasonalCME Cisco IP Phone XML weather service.

This Flask app provides simple weather services for Cisco IP phones under `/cme/services/`.

Intended for use in the SeasonalNet web services stack, but usable anywhere you need a quick Cisco XML service for Cisco IP phones.

## Features

- Root Cisco IP Phone service menu
- Weather lookup by ZIP or `City, ST`
- Current conditions from NWS
- Active alert listing and alert detail pages
- Cisco `IconFileMenu` support
- WS4KP-style weather icon support with generated fallbacks
- Short in-memory HTTP cache for upstream API calls
- YAML configuration with environment variable overrides

## Layout

```text
app.py
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
```

`app.py` remains the compatibility entrypoint. The Flask app and routes live under `cme_weather/server/`; upstream API access lives under `cme_weather/clients/`; route-independent weather orchestration lives under `cme_weather/services/`.

## Install

```bash
python3 -m venv venv
. venv/bin/activate
python -m pip install -r requirements.txt
```

## Configuration

Copy the example config before running the service:

```bash
cp config.yaml.example config.yaml
nano config.yaml
```

`config.yaml` is ignored by git so each host can keep local runtime settings.

Default local config:

```yaml
app:
  bind_host: 127.0.0.1
  bind_port: 9010
  public_base_path: /cme/services

http:
  timeout_seconds: 4.5

cache:
  ttl_seconds: 60

nws:
  base_url: https://api.weather.gov
  user_agent: "(seasonalnet.org, info@seasonalnet.org)"

zippopotam:
  base_url: https://api.zippopotam.us

icons:
  ws_icon_dir: /opt/cme-weather/icons/ws4kp18
  max_icon_index: 9

weather:
  default_query: "90210"
  max_alerts: 6
  fallback_daytime: true

alerts:
  headline_clip_chars: 300
  description_clip_chars: 900
  instruction_clip_chars: 500
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
| `CME_WEATHER_CACHE_TTL_SECONDS` | `cache.ttl_seconds` | In-memory cache TTL |
| `CME_WEATHER_NWS_BASE_URL` | `nws.base_url` | NWS API base URL |
| `CME_WEATHER_NWS_USER_AGENT` | `nws.user_agent` | User-Agent sent to weather.gov |
| `CME_WEATHER_ZIPPOTAM_BASE_URL` | `zippopotam.base_url` | Zippopotam API base URL |
| `CME_WEATHER_WS_ICON_DIR` | `icons.ws_icon_dir` | Runtime icon directory |
| `CME_WEATHER_DEFAULT_QUERY` | `weather.default_query` | Default phone input value |
| `CME_WEATHER_MAX_ALERTS` | `weather.max_alerts` | Alert rows shown in the phone menu |
| `CME_WEATHER_FALLBACK_DAYTIME` | `weather.fallback_daytime` | Day/night fallback if forecast lookup fails |

Legacy variables from the original single-file app are still honored:

| Legacy variable | Replacement |
| --- | --- |
| `NWS_USER_AGENT` | `CME_WEATHER_NWS_USER_AGENT` |
| `HTTP_TIMEOUT` | `CME_WEATHER_HTTP_TIMEOUT_SECONDS` |
| `CACHE_TTL_SECONDS` | `CME_WEATHER_CACHE_TTL_SECONDS` |
| `WS_ICON_DIR` | `CME_WEATHER_WS_ICON_DIR` |

## Runtime

Default local run:

```bash
python3 app.py
```

The default app listens on:

```text
127.0.0.1:9010
```

Expected reverse-proxy/service path:

```text
/cme/services/
```

## Checks

```bash
python3 -m py_compile app.py
python3 -m compileall cme_weather
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
