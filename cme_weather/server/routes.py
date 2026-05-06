from __future__ import annotations

from typing import List
from urllib.parse import quote

from flask import Flask, Response, request

from cme_weather.clients.nws import NwsClient
from cme_weather.clients.zippopotam import ZippopotamClient
from cme_weather.config import Settings
from cme_weather.icons import icon_png
from cme_weather.renderers.cisco_xml import escape_xml, input_page, text_page, xml_response
from cme_weather.services.weather import (
    WeatherInputError,
    WeatherUpstreamError,
    build_alert_detail,
    build_weather_menu,
)


def register_routes(
    app: Flask,
    *,
    settings: Settings,
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

    @app.get(route_path("/ping"))
    def ping() -> Response:
        return xml_response(text_page(title="SeasonalCME", prompt="Ping", text="OK"))

    @app.get(route_path("/"))
    def root_menu() -> Response:
        xml = f"""
<CiscoIPPhoneMenu>
  <Title>SeasonalCME</Title>
  <Prompt>Select a service</Prompt>
  <MenuItem>
    <Name>Weather</Name>
    <URL>{escape_xml(abs_url(route_path('/weather')))}</URL>
  </MenuItem>
  <MenuItem>
    <Name>Ping</Name>
    <URL>{escape_xml(abs_url(route_path('/ping')))}</URL>
  </MenuItem>
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

        try:
            data = build_weather_menu(
                query,
                locations=locations,
                nws=nws,
                weather_config=settings.weather,
            )
        except WeatherInputError as exc:
            return xml_response(text_page(title="Weather", prompt="Bad input", text=str(exc)))
        except WeatherUpstreamError as exc:
            return xml_response(text_page(title="Weather", prompt="NWS error", text=str(exc)))

        icon_base = abs_url(route_path("/weather/icon.png"))
        icon_lines: List[str] = []
        for index in range(settings.icons.max_icon_index + 1):
            url = f"{icon_base}?i={index}"
            if index == 0:
                url += f"&dn={data.day_night}"
            icon_lines.append(f"  <IconItem><Index>{index}</Index><URL>{escape_xml(url)}</URL></IconItem>")
        icon_items = "\n".join(icon_lines)

        menu_items: List[str] = []
        refresh_url = f"{escape_xml(abs_url(route_path('/weather/show')))}?q={quote(data.query)}"
        menu_items.append(
            f"""
  <MenuItem>
    <IconIndex>{data.weather_icon}</IconIndex>
    <Name>{escape_xml(data.current_line)}</Name>
    <URL>{refresh_url}</URL>
  </MenuItem>
""".rstrip()
        )

        if data.alerts:
            for alert in data.alerts:
                alert_url = f"{escape_xml(abs_url(route_path('/weather/alert')))}?id={quote(alert.alert_id, safe='')}"
                menu_items.append(
                    f"""
  <MenuItem>
    <IconIndex>{alert.icon_index}</IconIndex>
    <Name>{escape_xml(alert.event)}</Name>
    <URL>{alert_url}</URL>
  </MenuItem>
""".rstrip()
                )
        else:
            menu_items.append(
                f"""
  <MenuItem>
    <IconIndex>9</IconIndex>
    <Name>No active alerts</Name>
    <URL>{refresh_url}</URL>
  </MenuItem>
""".rstrip()
            )

        menu_items.append(
            f"""
  <MenuItem>
    <IconIndex>{data.weather_icon}</IconIndex>
    <Name>Refresh</Name>
    <URL>{refresh_url}</URL>
  </MenuItem>
""".rstrip()
        )

        xml = f"""
<CiscoIPPhoneIconFileMenu>
  <Title>Weather</Title>
  <Prompt>{escape_xml(data.label)}</Prompt>
{''.join(menu_items)}
{icon_items}
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
        except Exception as exc:
            return xml_response(text_page(title="Alert", prompt="Error", text=str(exc)))

        return xml_response(text_page(title=detail.event, prompt="Active alert", text=detail.body))
