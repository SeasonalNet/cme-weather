# cme-weather deployment

`cme-weather` should run as a WSGI service behind nginx for maintained SeasonalNet deployments. The root `app.py` entrypoint remains available for local development, but production-style use should import `wsgi:app` or `wsgi:application`.

## Install

```bash
cd /opt/cme-weather
python3 -m venv venv
. venv/bin/activate
python -m pip install -r requirements.txt
cp config.yaml.example config.yaml
nano config.yaml
```

## Gunicorn smoke test

```bash
cd /opt/cme-weather
. venv/bin/activate
gunicorn --bind 127.0.0.1:9010 --workers 1 --threads 4 --timeout 15 wsgi:app
```

In another shell:

```bash
curl -fsS http://127.0.0.1:9010/cme/services/healthz
curl -fsS http://127.0.0.1:9010/cme/services/status.json
curl -fsS http://127.0.0.1:9010/cme/services/ping
curl -fsS http://127.0.0.1:9010/cme/services/
```

## systemd unit

Install as `/etc/systemd/system/cme-weather.service`:

```ini
[Unit]
Description=SeasonalCME Cisco XML Weather Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=cmeweather
Group=cmeweather
WorkingDirectory=/opt/cme-weather
Environment=CME_WEATHER_CONFIG=/opt/cme-weather/config.yaml
ExecStart=/opt/cme-weather/venv/bin/gunicorn --bind 127.0.0.1:9010 --workers 1 --threads 4 --timeout 15 --access-logfile - --error-logfile - wsgi:app
Restart=on-failure
RestartSec=5

NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true
ReadWritePaths=/opt/cme-weather
CapabilityBoundingSet=
LockPersonality=true
MemoryDenyWriteExecute=true

[Install]
WantedBy=multi-user.target
```

One worker with several threads is intentional. The service uses in-memory caches; multiple workers would create independent cache copies. That is safe, but not useful for this small phone service.

Enable it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now cme-weather.service
sudo systemctl status cme-weather.service --no-pager
```

## nginx location

Example reverse-proxy block:

```nginx
location /cme/services/ {
    proxy_pass http://127.0.0.1:9010/cme/services/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

Reload nginx after validation:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## Operational checks

```bash
journalctl -u cme-weather.service -f
curl -fsS http://127.0.0.1:9010/cme/services/status.json | jq
curl -fsS http://127.0.0.1:9010/cme/services/weather/show?q=20794
```

## Rollback

If WSGI deployment fails, the development entrypoint can still be used temporarily:

```bash
cd /opt/cme-weather
. venv/bin/activate
python3 app.py
```

Use this only as a temporary diagnostic path. Long-running service use should go back through Gunicorn/systemd/nginx.
