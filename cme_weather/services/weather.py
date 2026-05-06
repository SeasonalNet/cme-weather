from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List

from cme_weather.clients.nws import NwsClient
from cme_weather.clients.zippopotam import ZippopotamClient
from cme_weather.config import AlertsConfig, WeatherConfig
from cme_weather.icons import classify_alert_icon, classify_weather_icon


class WeatherInputError(ValueError):
    """Raised when a phone-supplied weather query is invalid."""


class WeatherUpstreamError(RuntimeError):
    """Raised when an upstream weather API cannot satisfy a request."""


@dataclass(frozen=True)
class AlertMenuItem:
    event: str
    icon_index: int
    alert_id: str


@dataclass(frozen=True)
class WeatherMenuData:
    query: str
    label: str
    current_line: str
    weather_icon: int
    day_night: str
    alerts: List[AlertMenuItem]


@dataclass(frozen=True)
class AlertDetailData:
    event: str
    body: str


def build_weather_menu(
    query: str,
    *,
    locations: ZippopotamClient,
    nws: NwsClient,
    weather_config: WeatherConfig,
) -> WeatherMenuData:
    try:
        lat, lon, label = locations.latlon(query)
    except Exception as exc:
        raise WeatherInputError(str(exc)) from exc

    try:
        points = nws.points(lat, lon)
        observation = nws.latest_observation(points)
        raw_alerts = nws.active_alerts(lat, lon)
    except Exception as exc:
        raise WeatherUpstreamError(str(exc)) from exc

    try:
        is_daytime = nws.is_daytime(points)
    except Exception:
        is_daytime = weather_config.fallback_daytime
    day_night = "1" if is_daytime else "0"

    props = observation.get("properties", {})
    temp_c = props.get("temperature", {}).get("value")
    description = props.get("textDescription") or "Current conditions"
    temp_f = (temp_c * 9.0 / 5.0) + 32.0 if isinstance(temp_c, (int, float)) else None

    weather_icon = classify_weather_icon(description)
    current_line = f"Now: {temp_f:.0f}F {description}" if temp_f is not None else f"Now: {description}"

    alerts: List[AlertMenuItem] = []
    for alert in raw_alerts[: weather_config.max_alerts]:
        alert_props = alert.get("properties", {})
        event = alert_props.get("event", "Alert")
        icon_index, _level = classify_alert_icon(event)
        alert_id = alert_props.get("id") or alert.get("id") or ""
        alerts.append(AlertMenuItem(event=event, icon_index=icon_index, alert_id=alert_id))

    return WeatherMenuData(
        query=query,
        label=label,
        current_line=current_line,
        weather_icon=weather_icon,
        day_night=day_night,
        alerts=alerts,
    )


def _clip(value: str, length: int) -> str:
    if length <= 0:
        return ""
    return (value[:length] + "…") if len(value) > length else value


def build_alert_detail(alert_id: str, *, nws: NwsClient, alerts_config: AlertsConfig) -> AlertDetailData:
    data: Any = nws.alert(alert_id)
    props = data.get("properties", {})
    event = props.get("event", "Alert")
    headline = (props.get("headline") or "").strip()
    description = (props.get("description") or "").strip()
    instruction = (props.get("instruction") or "").strip()

    body = "\n\n".join(
        [
            _clip(headline, alerts_config.headline_clip_chars),
            _clip(description, alerts_config.description_clip_chars),
            _clip(instruction, alerts_config.instruction_clip_chars),
        ]
    ).strip()

    return AlertDetailData(event=event, body=body)
