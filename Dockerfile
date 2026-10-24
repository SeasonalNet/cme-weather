FROM ghcr.io/astral-sh/uv:0.13.5 AS uv

FROM python:3.15-slim@sha256:044d5bd747976e21f8bc4d746c3479b19a84bb8ae6261b802acdd26b29036c93 AS dependencies

WORKDIR /build
COPY --from=uv /uv /uvx /bin/
COPY requirements.txt .
RUN uv pip install --prefix=/install --no-cache -r requirements.txt

FROM python:3.15-slim@sha256:044d5bd747976e21f8bc4d746c3479b19a84bb8ae6261b802acdd26b29036c93 AS runtime-files

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CME_WEATHER_CONFIG=/run/config/cme-weather.yaml \
    CME_WEATHER_BIND_HOST=0.0.0.0 \
    CME_WEATHER_BIND_PORT=9010 \
    CME_WEATHER_WS_ICON_DIR=/app/icons/ws4kp18

RUN groupadd --system --gid 10001 cmeweather \
    && useradd --system --uid 10001 --gid 10001 --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin cmeweather

WORKDIR /app
COPY --from=dependencies /install /usr/local
COPY --chown=0:0 cme_weather ./cme_weather
COPY --chown=0:0 icons ./icons
COPY --chown=0:0 app.py wsgi.py ./

COPY tools/container/assemble-rootfs.py /tmp/assemble-rootfs.py
RUN chmod -R go-w /app \
    && python /tmp/assemble-rootfs.py python /runtime-root

FROM scratch AS runtime

ARG APP_VERSION=0.0.0+unknown
ARG APP_REVISION=unknown
ENV APP_VERSION=${APP_VERSION} APP_REVISION=${APP_REVISION}
LABEL org.opencontainers.image.version="${APP_VERSION}" org.opencontainers.image.revision="${APP_REVISION}"

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 CME_WEATHER_CONFIG=/run/config/cme-weather.yaml CME_WEATHER_BIND_HOST=0.0.0.0 CME_WEATHER_BIND_PORT=9010 CME_WEATHER_WS_ICON_DIR=/app/icons/ws4kp18
COPY --from=runtime-files /runtime-root /
COPY --from=runtime-files --chown=0:0 /app /app
WORKDIR /app
USER 10001:10001
EXPOSE 9010
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["/usr/local/bin/python3.15", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9010/cme/services/healthz', timeout=3)"]
CMD ["/usr/local/bin/python3.15", "-m", "gunicorn", "--bind", "0.0.0.0:9010", "--workers", "1", "--threads", "4", "--timeout", "15", "wsgi:app"]
RUN ["/usr/local/bin/python3.15", "-c", "import os; assert os.getuid() != 0; assert os.stat('/app/wsgi.py').st_uid == 0; assert not os.access('/app/wsgi.py', os.W_OK); assert not os.access('/app', os.W_OK); import ssl; paths = ssl.get_default_verify_paths(); assert paths.cafile and paths.capath; assert os.path.isfile(paths.cafile)"]
