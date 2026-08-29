FROM python:3.12-slim@sha256:09f7da3bc104798d0afb40bc08d23ab2da20a76130cec1f2ef170848f5d85217 AS dependencies

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim@sha256:09f7da3bc104798d0afb40bc08d23ab2da20a76130cec1f2ef170848f5d85217

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CME_WEATHER_CONFIG=/run/config/cme-weather.yaml \
    CME_WEATHER_BIND_HOST=0.0.0.0 \
    CME_WEATHER_BIND_PORT=9010 \
    CME_WEATHER_WS_ICON_DIR=/app/icons/ws4kp18

RUN groupadd --system --gid 10001 cmeweather \
    && useradd --system --uid 10001 --gid 10001 --create-home --home-dir /home/cmeweather cmeweather

WORKDIR /app
COPY --from=dependencies /install /usr/local
COPY --chown=10001:10001 cme_weather ./cme_weather
COPY --chown=10001:10001 icons ./icons
COPY --chown=10001:10001 app.py wsgi.py ./

USER 10001:10001
EXPOSE 9010

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9010/cme/services/healthz', timeout=3)"

CMD ["gunicorn", "--bind", "0.0.0.0:9010", "--workers", "1", "--threads", "4", "--timeout", "15", "wsgi:app"]
