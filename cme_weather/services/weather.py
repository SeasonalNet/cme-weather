from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Optional

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
    severity: str
    urgency: str
    certainty: str
    effective: str
    expires: str
    headline: str


@dataclass(frozen=True)
class ForecastPeriod:
    name: str
    short_forecast: str
    detailed_forecast: str
    temperature: Optional[int]
    temperature_unit: str
    is_daytime: bool

    @property
    def summary_line(self) -> str:
        temp = f" {self.temperature}{self.temperature_unit}" if self.temperature is not None else ""
        forecast = self.short_forecast or "Forecast"
        return f"{self.name}:{temp} {forecast}".strip()


@dataclass(frozen=True)
class WeatherMenuData:
    query: str
    label: str
    current_line: str
    weather_icon: int
    day_night: str
    alerts: List[AlertMenuItem]
    total_alerts: int
    forecast_periods: List[ForecastPeriod]
    description: str
    temperature_f: Optional[float]
    wind: str
    humidity: Optional[float]
    observation_time: str


@dataclass(frozen=True)
class AlertDetailData:
    event: str
    body: str


_SEVERITY_ORDER = {
    "extreme": 0,
    "severe": 1,
    "moderate": 2,
    "minor": 3,
    "unknown": 4,
}
_URGENCY_ORDER = {
    "immediate": 0,
    "expected": 1,
    "future": 2,
    "past": 3,
    "unknown": 4,
}
_CERTAINTY_ORDER = {
    "observed": 0,
    "likely": 1,
    "possible": 2,
    "unlikely": 3,
    "unknown": 4,
}
_EVENT_ORDER = {
    "warning": 0,
    "watch": 1,
    "advisory": 2,
    "statement": 3,
}


def _event_rank(event: str) -> int:
    value = (event or "").lower()
    for key, rank in _EVENT_ORDER.items():
        if key in value:
            return rank
    return 4


def _alert_sort_key(alert: Any) -> tuple[int, int, int, int, str]:
    props = alert.get("properties", {}) if isinstance(alert, dict) else {}
    event = str(props.get("event") or "")
    severity = str(props.get("severity") or "unknown").lower()
    urgency = str(props.get("urgency") or "unknown").lower()
    certainty = str(props.get("certainty") or "unknown").lower()
    expires = str(props.get("expires") or "")
    return (
        _event_rank(event),
        _SEVERITY_ORDER.get(severity, 4),
        _URGENCY_ORDER.get(urgency, 4),
        _CERTAINTY_ORDER.get(certainty, 4),
        expires,
    )


def _alert_icon(event: str, alerts_config: AlertsConfig) -> int:
    event_l = (event or "").lower()
    for needle, icon_index in alerts_config.icon_overrides.items():
        if needle and needle in event_l:
            return icon_index
    icon_index, _level = classify_alert_icon(event)
    return icon_index


def _clip(value: str, length: int) -> str:
    if length <= 0:
        return ""
    return (value[:length] + "…") if len(value) > length else value


def _format_iso(value: str) -> str:
    if not value:
        return ""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    return parsed.strftime("%b %-d %H:%M %Z").strip()


def _humidity_percent(observation_props: dict[str, Any]) -> Optional[float]:
    value = observation_props.get("relativeHumidity", {}).get("value")
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _temperature_f(observation_props: dict[str, Any]) -> Optional[float]:
    value = observation_props.get("temperature", {}).get("value")
    if isinstance(value, (int, float)):
        return (value * 9.0 / 5.0) + 32.0
    return None


def _forecast_periods(raw_periods: List[Any]) -> List[ForecastPeriod]:
    periods: List[ForecastPeriod] = []
    for raw in raw_periods:
        if not isinstance(raw, dict):
            continue
        temperature = raw.get("temperature")
        periods.append(
            ForecastPeriod(
                name=str(raw.get("name") or "Period"),
                short_forecast=str(raw.get("shortForecast") or ""),
                detailed_forecast=str(raw.get("detailedForecast") or ""),
                temperature=int(temperature) if isinstance(temperature, (int, float)) else None,
                temperature_unit=str(raw.get("temperatureUnit") or "F"),
                is_daytime=bool(raw.get("isDaytime", True)),
            )
        )
    return periods


def build_weather_menu(
    query: str,
    *,
    locations: ZippopotamClient,
    nws: NwsClient,
    weather_config: WeatherConfig,
    alerts_config: AlertsConfig,
) -> WeatherMenuData:
    try:
        lat, lon, label = locations.latlon(query)
    except Exception as exc:
        raise WeatherInputError(str(exc)) from exc

    try:
        points = nws.points(lat, lon)
        observation = nws.latest_observation(points)
        raw_alerts = sorted(nws.active_alerts(lat, lon), key=_alert_sort_key)
    except Exception as exc:
        raise WeatherUpstreamError(str(exc)) from exc

    try:
        raw_forecast_periods = nws.forecast(points)
    except Exception:
        raw_forecast_periods = []

    try:
        is_daytime = bool(raw_forecast_periods[0].get("isDaytime", True)) if raw_forecast_periods else weather_config.fallback_daytime
    except Exception:
        is_daytime = weather_config.fallback_daytime
    day_night = "1" if is_daytime else "0"

    props = observation.get("properties", {})
    temp_f = _temperature_f(props)
    description = props.get("textDescription") or "Current conditions"
    wind = props.get("windSpeed", {}).get("value")
    wind_unit = props.get("windSpeed", {}).get("unitCode", "")
    if isinstance(wind, (int, float)):
        wind_text = f"{wind:.0f} {wind_unit.split(':')[-1]}".strip()
    else:
        wind_text = "Unknown"
    humidity = _humidity_percent(props)
    observation_time = _format_iso(str(props.get("timestamp") or ""))

    weather_icon = classify_weather_icon(description)
    current_line = f"Now: {temp_f:.0f}F {description}" if temp_f is not None else f"Now: {description}"

    alerts: List[AlertMenuItem] = []
    for alert in raw_alerts[: weather_config.max_alerts]:
        alert_props = alert.get("properties", {})
        event = str(alert_props.get("event") or "Alert")
        alert_id = str(alert_props.get("id") or alert.get("id") or "")
        alerts.append(
            AlertMenuItem(
                event=event,
                icon_index=_alert_icon(event, alerts_config),
                alert_id=alert_id,
                severity=str(alert_props.get("severity") or "Unknown"),
                urgency=str(alert_props.get("urgency") or "Unknown"),
                certainty=str(alert_props.get("certainty") or "Unknown"),
                effective=_format_iso(str(alert_props.get("effective") or "")),
                expires=_format_iso(str(alert_props.get("expires") or "")),
                headline=str(alert_props.get("headline") or ""),
            )
        )

    return WeatherMenuData(
        query=query,
        label=label,
        current_line=current_line,
        weather_icon=weather_icon,
        day_night=day_night,
        alerts=alerts,
        total_alerts=len(raw_alerts),
        forecast_periods=_forecast_periods(raw_forecast_periods),
        description=str(description),
        temperature_f=temp_f,
        wind=wind_text,
        humidity=humidity,
        observation_time=observation_time,
    )


def build_alert_detail(alert_id: str, *, nws: NwsClient, alerts_config: AlertsConfig) -> AlertDetailData:
    data: Any = nws.alert(alert_id)
    props = data.get("properties", {})
    event = props.get("event", "Alert")
    severity = props.get("severity") or "Unknown"
    urgency = props.get("urgency") or "Unknown"
    certainty = props.get("certainty") or "Unknown"
    effective = _format_iso(str(props.get("effective") or ""))
    expires = _format_iso(str(props.get("expires") or ""))
    headline = (props.get("headline") or "").strip()
    description = (props.get("description") or "").strip()
    instruction = (props.get("instruction") or "").strip()

    meta_lines = [
        f"Severity: {severity}",
        f"Urgency: {urgency}",
        f"Certainty: {certainty}",
    ]
    if effective:
        meta_lines.append(f"Effective: {effective}")
    if expires:
        meta_lines.append(f"Expires: {expires}")

    body = "\n".join(meta_lines)
    sections = [
        _clip(headline, alerts_config.headline_clip_chars),
        _clip(description, alerts_config.description_clip_chars),
        _clip(instruction, alerts_config.instruction_clip_chars),
    ]
    body = "\n\n".join([body, *[section for section in sections if section]]).strip()

    return AlertDetailData(event=event, body=body)
