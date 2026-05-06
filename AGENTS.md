# AGENTS.md

## Project

`cme-weather` is the SeasonalCME Cisco IP Phone XML weather service.

It serves Cisco phone XML menus and text pages under `/cme/services/`, including weather lookup, current conditions, alert listings, and icon PNGs.

## Rules

- Keep endpoints compatible with Cisco IP Phone XML service payloads.
- Keep the public service path rooted under `/cme/services/`.
- Do not commit virtualenvs, bytecode, caches, logs, secrets, or local `.env` files.
- Prefer environment variables for deployment-specific settings.
- Keep NWS API access polite: preserve the User-Agent behavior and caching.
- Do not add large generated assets unless they are required runtime assets.
- Treat icon/source artwork licensing carefully before committing it to a public repository.

## Validation

Before committing app changes, run:

    python3 -m py_compile app.py

When the service is running locally, also check:

    curl -s http://127.0.0.1:9010/cme/services/ping
    curl -s http://127.0.0.1:9010/cme/services/
