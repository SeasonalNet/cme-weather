from __future__ import annotations

import logging
import os
from math import ceil
from typing import List
from urllib.parse import quote

from flask import Flask, Response, jsonify, request

from cme_weather.cache import TtlCache
from cme_weather.clients.nws import NwsClient
from cme_weather.clients.zippopotam import ZippopotamClient
from cme_weather.config import Settings
from cme_weather.icons import icon_png
from cme_weather.renderers.cisco_xml import escape_xml, input_page, text_page, xml_response
from cme_weather.services.weather import (
    AlertMenuItem,
    ForecastPeriod,
    WeatherInputError,
    WeatherMenuData,
    WeatherUpstreamError,
    build_alert_detail,
    build_weather_menu,
)

logger = logging.getLogger(__name__)


def register_routes(
    app: Flask,
    *,
    settings: Settings,
    cache: TtlCache,
    locations: ZippopotamClient,
    nws: NwsClient,
) -> None:
    base_path = settings.app.public_base_path

    def route_path(suffix: str = "") -> str:
        if base_path == "/":
            return f"/{suffix.lstrip('/')}" if suffix else "/"
        return f"{base_path}{suffix}"

    def abs_url(path: str) -> str:
        return request.host_url.rstrip("/") + path

    def show_url(endpoint: str, query: str, **params: str | int) -> str:
        url = f"{abs_url(route_path(endpoint))}?q={quote(query, safe='')}"
        for key, value in params.items():
            url += f"&{quote(str(key), safe='')}={quote(str(value), safe='')}"
        return escape_xml(url)

    def icon_url(index: int, *, day_night: str = "1") -> str:
        url = f"{abs_url(route_path('/weather/icon.png'))}?i={index}"
        if index == 0:
            url += f"&dn={day_night}"
        return escape_xml(url)

    def icon_items(day_night: str) -> str:
        lines: List[str] = []
        for index in range(settings.icons.max_icon_index + 1):
            lines.append(f"  <IconItem><Index>{index}</Index><URL>{icon_url(index, day_night=day_night)}</URL></IconItem>")
        return "\n".join(lines)

    def menu_item(name: str, url: str, *, icon_index: int | None = None) -> str:
        icon_line = f"    <IconIndex>{icon_index}</IconIndex>\n" if icon_index is not None else ""
        return f"""
  <MenuItem>
{icon_line}    <Name>{escape_xml(name)}</Name>
    <URL>{url}</URL>
  </MenuItem>
""".rstrip()

    def weather_data_or_page(query: str) -> WeatherMenuData | Response:
        try:
            data = build_weather_menu(
                query,
                locations=locations,
                nws=nws,
                weather_config=settings.weather,
                alerts_config=settings.alerts,
            )
        except WeatherInputError as exc:
            logger.info("event=weather_bad_input query=%r error=%r", query, str(exc))
            return xml_response(text_page(title="Weather", prompt="Bad input", text=str(exc)))
        except WeatherUpstreamError:
            logger.warning("event=weather_upstream_unavailable query=%r", query, exc_info=True)
            return xml_response(
                text_page(
                    title="Weather",
                    prompt="Weather unavailable",
                    text="Upstream weather data is unavailable and no usable cached data is available. Try Refresh soon.",
                )
            )

        logger.info(
            "event=weather_show query=%r label=%r alerts=%s forecast_periods=%s",
            query,
            data.label,
            data.total_alerts,
            len(data.forecast_periods),
        )
        return data

    @app.get(route_path("/ping"))
    def ping() -> Response:
        return xml_response(text_page(title="SeasonalCME", prompt="Ping", text="OK"))

    @app.get(route_path("/healthz"))
    def healthz() -> Response:
        return jsonify({"ok": True, "service": settings.app.name})

    @app.get(route_path("/status.json"))
    def status_json() -> Response:
        stats = cache.snapshot()
        config_path = str(settings.config_path) if settings.config_path else None
        return jsonify(
            {
                "ok": True,
                "service": settings.app.name,
                "public_base_path": settings.app.public_base_path,
                "config_path": config_path,
                "icons": {
                    "ws_icon_dir": settings.icons.ws_icon_dir,
                    "exists": os.path.isdir(settings.icons.ws_icon_dir),
                    "max_icon_index": settings.icons.max_icon_index,
                },
                "cache": {
                    "entries": stats.entries,
                    "fresh_hits": stats.fresh_hits,
                    "stale_hits": stats.stale_hits,
                    "misses": stats.misses,
                    "writes": stats.writes,
                    "default_ttl_seconds": settings.cache.ttl_seconds,
                    "stale_if_error_seconds": settings.cache.stale_if_error_seconds,
                },
            }
        )

    @app.get(route_path("/"))
    def root_menu() -> Response:
        xml = f"""
<CiscoIPPhoneMenu>
  <Title>SeasonalCME</Title>
  <Prompt>Select a service</Prompt>
{menu_item("Weather", escape_xml(abs_url(route_path('/weather'))))}
{menu_item("Ping", escape_xml(abs_url(route_path('/ping'))))}
</CiscoIPPhoneMenu>
""".strip()
        return xml_response(xml)

    @app.get(route_path("/weather"))
    def weather_input() -> Response:
        return xml_response(
            input_page(
                title="Weather",
                prompt="Enter ZIP or City, ST",
                url=abs_url(route_path("/weather/show")),
                default_value=settings.weather.default_query,
            )
        )

    @app.get(route_path("/weather/icon.png"))
    def icon_endpoint() -> Response:
        try:
            index = int(request.args.get("i", "0"))
        except ValueError:
            index = 0

        day_night = request.args.get("dn", "1")
        png = icon_png(
            index,
            day_night=day_night,
            icon_dir=settings.icons.ws_icon_dir,
            max_icon_index=settings.icons.max_icon_index,
        )
        return Response(png, mimetype="image/png")

    @app.get(route_path("/weather/show"))
    def weather_show() -> Response:
        query = (request.args.get("q", "") or "").strip()
        data = weather_data_or_page(query)
        if isinstance(data, Response):
            return data

        items = [
            menu_item(data.current_line, show_url("/weather/current", data.query), icon_index=data.weather_icon),
            menu_item(
                f"Active Alerts ({data.total_alerts})",
                show_url("/weather/alerts", data.query),
                icon_index=data.alerts[0].icon_index if data.alerts else 9,
            ),
            menu_item("Today / Tonight", show_url("/weather/forecast", data.query, mode="today"), icon_index=data.weather_icon),
            menu_item("3-Day Forecast", show_url("/weather/forecast", data.query, mode="three-day"), icon_index=data.weather_icon),
            menu_item("Refresh", show_url("/weather/show", data.query), icon_index=data.weather_icon),
        ]

        xml = f"""
<CiscoIPPhoneIconFileMenu>
  <Title>Weather</Title>
  <Prompt>{escape_xml(data.label)}</Prompt>
{''.join(items)}
{icon_items(data.day_night)}
</CiscoIPPhoneIconFileMenu>
""".strip()
        return xml_response(xml)

    @app.get(route_path("/weather/current"))
    def weather_current() -> Response:
        query = (request.args.get("q", "") or "").strip()
        data = weather_data_or_page(query)
        if isinstance(data, Response):
            return data

        lines = [data.current_line]
        if data.wind:
            lines.append(f"Wind: {data.wind}")
        if data.humidity is not None:
            lines.append(f"Humidity: {data.humidity:.0f}%")
        if data.observation_time:
            lines.append(f"Observed: {data.observation_time}")
        lines.append("")
        lines.append(f"Alerts: {data.total_alerts}")
        lines.append(f"Location: {data.label}")
        return xml_response(text_page(title="Current", prompt=data.label, text="\n".join(lines)))

    @app.get(route_path("/weather/alerts"))
    def weather_alerts() -> Response:
        query = (request.args.get("q", "") or "").strip()
        data = weather_data_or_page(query)
        if isinstance(data, Response):
            return data

        if not data.alerts:
            return xml_response(text_page(title="Alerts", prompt=data.label, text="No active alerts."))

        try:
            page = max(0, int(request.args.get("page", "0")))
        except ValueError:
            page = 0
        page_size = max(1, settings.alerts.page_size)
        page_count = max(1, ceil(len(data.alerts) / page_size))
        page = min(page, page_count - 1)
        start = page * page_size
        page_alerts = data.alerts[start : start + page_size]

        items: List[str] = []
        for alert in page_alerts:
            items.append(_alert_menu_item(alert, data.query, show_url, menu_item))
        if page + 1 < page_count:
            items.append(menu_item("More alerts", show_url("/weather/alerts", data.query, page=page + 1), icon_index=9))
        if page > 0:
            items.append(menu_item("Previous alerts", show_url("/weather/alerts", data.query, page=page - 1), icon_index=9))

        xml = f"""
<CiscoIPPhoneIconFileMenu>
  <Title>Alerts</Title>
  <Prompt>{escape_xml(data.label)} p{page + 1}/{page_count}</Prompt>
{''.join(items)}
{icon_items(data.day_night)}
</CiscoIPPhoneIconFileMenu>
""".strip()
        return xml_response(xml)

    @app.get(route_path("/weather/alert"))
    def alert_detail() -> Response:
        alert_id = request.args.get("id", "") or ""
        if not alert_id:
            return xml_response(text_page(title="Alert", prompt="Error", text="Missing alert id"))

        try:
            detail = build_alert_detail(alert_id, nws=nws, alerts_config=settings.alerts)
        except Exception:
            logger.warning("event=alert_detail_error alert_id=%r", alert_id, exc_info=True)
            return xml_response(
                text_page(
                    title="Alert",
                    prompt="Unavailable",
                    text="Alert detail is unavailable. Return to the active alert list and try again.",
                )
            )

        return xml_response(text_page(title=detail.event, prompt="Active alert", text=detail.body))

    @app.get(route_path("/weather/forecast"))
    def weather_forecast() -> Response:
        query = (request.args.get("q", "") or "").strip()
        mode = (request.args.get("mode", "today") or "today").strip().lower()
        data = weather_data_or_page(query)
        if isinstance(data, Response):
            return data

        if not data.forecast_periods:
            return xml_response(text_page(title="Forecast", prompt=data.label, text="Forecast data is unavailable."))

        periods = data.forecast_periods[:2] if mode == "today" else data.forecast_periods[:6]
        title = "Today" if mode == "today" else "3-Day Forecast"
        body = _forecast_text(periods)
        return xml_response(text_page(title=title, prompt=data.label, text=body))


def _alert_menu_item(
    alert: AlertMenuItem,
    query: str,
    show_url,
    menu_item,
) -> str:
    label = alert.event
    if alert.expires:
        label = f"{label} until {alert.expires}"
    return menu_item(label, show_url("/weather/alert", query, id=alert.alert_id), icon_index=alert.icon_index)


def _forecast_text(periods: List[ForecastPeriod]) -> str:
    lines: List[str] = []
    for period in periods:
        lines.append(period.summary_line)
        if period.detailed_forecast:
            lines.append(period.detailed_forecast)
        lines.append("")
    return "\n".join(lines).strip()
