# AGENTS.md

## Project

`cme-weather` is the SeasonalCME Cisco IP Phone XML weather service.

It serves Cisco phone XML menus and text pages under `/cme/services/`, including weather lookup, current conditions, alert listings, and icon PNGs.

## Layout

- `app.py` is a compatibility entrypoint for local/systemd execution.
- `cme_weather/server/` contains Flask app construction and route glue.
- `cme_weather/services/` contains route-independent weather and alert orchestration.
- `cme_weather/clients/` contains upstream API clients.
- `cme_weather/renderers/` contains Cisco XML rendering helpers.
- `cme_weather/icons.py` contains icon classification, loading, and fallback PNG generation.
- `cme_weather/config.py` contains config loading and validation.

## Rules

- Keep endpoints compatible with Cisco IP Phone XML service payloads.
- Keep the default public service path rooted under `/cme/services/`.
- Preserve the root `app.py` entrypoint unless the deployment documentation and systemd wrapper are intentionally changed.
- Keep Flask route handlers thin. Push upstream API access and menu-generation decisions into `clients/` and `services/`.
- Use `config.yaml` for normal service configuration. Commit only `config.yaml.example`; do not commit local `config.yaml` files.
- Environment variables may override config values for deployment-specific or emergency changes.
- Keep NWS API access polite: preserve the User-Agent behavior and caching.
- Do not commit virtualenvs, bytecode, caches, logs, secrets, local `.env` files, or local `config.yaml` files.
- Do not add large generated assets unless they are required runtime assets.
- Treat icon/source artwork licensing carefully before committing it to a public repository.

## Configuration

For local runtime configuration:

    cp config.yaml.example config.yaml
    nano config.yaml

The default config path is `./config.yaml` at the repository root. Set `CME_WEATHER_CONFIG=/path/to/config.yaml` to use another file.

Service-scoped environment variable overrides are preferred over legacy names. Legacy names are kept for compatibility with the original script.

## Validation

Before committing app changes, run:

    python3 -m py_compile app.py
    python3 -m compileall cme_weather

When the service is running locally, also check:

    curl -s http://127.0.0.1:9010/cme/services/ping
    curl -s http://127.0.0.1:9010/cme/services/
