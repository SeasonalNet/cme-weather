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

## Runtime

Default local bind:

```bash
 python3 app.py
```

The app listens on:

```text
127.0.0.1:9010
```

Expected reverse-proxy/service path:

```text
/cme/services/
```

## Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `NWS_USER_AGENT` | `(seasonalnet.org, info@seasonalnet.org)` | User-Agent sent to weather.gov |
| `HTTP_TIMEOUT` | `4.5` | Upstream HTTP timeout in seconds |
| `CACHE_TTL_SECONDS` | `60` | In-memory cache TTL |
| `WS_ICON_DIR` | `/opt/cme-weather/icons/ws4kp18` | Runtime icon directory |

## Install

```bash
python3 -m venv venv
. venv/bin/activate
python -m pip install -r requirements.txt
```

## Checks

```bash
python3 -m py_compile app.py
curl -s http://127.0.0.1:9010/cme/services/ping
```

## External `ws4kp` source checkout

This repository does ***not*** vendor the full upstream `ws4kp` project.

For local asset reference work, clone it beside the app as an ignored working copy:

```bash
git clone https://github.com/netbymatt/ws4kp ws4kp
```

The `ws4kp/` directory is ignored by this repository. Runtime icon assets used by this app live under:

```text
icons/ws4kp18/
```
