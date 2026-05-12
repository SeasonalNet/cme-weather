from __future__ import annotations

import os
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, MutableMapping, Optional

import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.yaml"


class ConfigError(RuntimeError):
    """Raised when the service configuration is malformed."""


@dataclass(frozen=True)
class AppConfig:
    name: str
    bind_host: str
    bind_port: int
    public_base_path: str


@dataclass(frozen=True)
class HttpConfig:
    timeout_seconds: float


@dataclass(frozen=True)
class CacheConfig:
    ttl_seconds: int
    locations_ttl_seconds: int
    points_ttl_seconds: int
    stations_ttl_seconds: int
    observations_ttl_seconds: int
    alerts_ttl_seconds: int
    forecast_ttl_seconds: int
    stale_if_error_seconds: int


@dataclass(frozen=True)
class NwsConfig:
    base_url: str
    user_agent: str


@dataclass(frozen=True)
class ZippopotamConfig:
    base_url: str


@dataclass(frozen=True)
class IconsConfig:
    ws_icon_dir: str
    max_icon_index: int


@dataclass(frozen=True)
class WeatherConfig:
    default_query: str
    max_alerts: int
    fallback_daytime: bool


@dataclass(frozen=True)
class AlertsConfig:
    headline_clip_chars: int
    description_clip_chars: int
    instruction_clip_chars: int
    page_size: int
    icon_overrides: Dict[str, int]


@dataclass(frozen=True)
class Settings:
    app: AppConfig
    http: HttpConfig
    cache: CacheConfig
    nws: NwsConfig
    zippopotam: ZippopotamConfig
    icons: IconsConfig
    weather: WeatherConfig
    alerts: AlertsConfig
    config_path: Optional[Path]


DEFAULTS: Dict[str, Any] = {
    "app": {
        "name": "SeasonalCMEWeather",
        "bind_host": "127.0.0.1",
        "bind_port": 9010,
        "public_base_path": "/cme/services",
    },
    "http": {
        "timeout_seconds": 4.5,
    },
    "cache": {
        "ttl_seconds": 60,
        "locations_ttl_seconds": 86400,
        "points_ttl_seconds": 21600,
        "stations_ttl_seconds": 21600,
        "observations_ttl_seconds": 120,
        "alerts_ttl_seconds": 60,
        "forecast_ttl_seconds": 900,
        "stale_if_error_seconds": 1800,
    },
    "nws": {
        "base_url": "https://api.weather.gov",
        "user_agent": "(seasonalnet.org, info@seasonalnet.org)",
    },
    "zippopotam": {
        "base_url": "https://api.zippopotam.us",
    },
    "icons": {
        "ws_icon_dir": "/opt/cme-weather/icons/ws4kp18",
        "max_icon_index": 9,
    },
    "weather": {
        "default_query": "90210",
        "max_alerts": 6,
        "fallback_daytime": True,
    },
    "alerts": {
        "headline_clip_chars": 300,
        "description_clip_chars": 900,
        "instruction_clip_chars": 500,
        "page_size": 6,
        "icon_overrides": {},
    },
}


def _deep_merge(base: MutableMapping[str, Any], override: Mapping[str, Any]) -> MutableMapping[str, Any]:
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(base.get(key), MutableMapping):
            _deep_merge(base[key], value)  # type: ignore[index]
        else:
            base[key] = value
    return base


def _copy_defaults() -> Dict[str, Any]:
    return deepcopy(DEFAULTS)


def _read_yaml_config(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"failed to parse {path}: {exc}") from exc
    except OSError as exc:
        raise ConfigError(f"failed to read {path}: {exc}") from exc

    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ConfigError(f"{path} must contain a YAML mapping at the top level")
    return raw


def _env_path(env: Mapping[str, str]) -> Path:
    configured = env.get("CME_WEATHER_CONFIG")
    return Path(configured).expanduser() if configured else DEFAULT_CONFIG_PATH


def _set_from_env(config: Dict[str, Any], env: Mapping[str, str], env_name: str, path: tuple[str, ...]) -> None:
    if env_name not in env:
        return
    cursor: Dict[str, Any] = config
    for key in path[:-1]:
        cursor = cursor.setdefault(key, {})
    cursor[path[-1]] = env[env_name]


def _apply_env_overrides(config: Dict[str, Any], env: Mapping[str, str]) -> None:
    # Legacy names are retained for compatibility, but service-scoped names win.
    legacy_mappings = {
        "NWS_USER_AGENT": ("nws", "user_agent"),
        "HTTP_TIMEOUT": ("http", "timeout_seconds"),
        "CACHE_TTL_SECONDS": ("cache", "ttl_seconds"),
        "WS_ICON_DIR": ("icons", "ws_icon_dir"),
    }
    service_mappings = {
        "CME_WEATHER_BIND_HOST": ("app", "bind_host"),
        "CME_WEATHER_BIND_PORT": ("app", "bind_port"),
        "CME_WEATHER_PUBLIC_BASE_PATH": ("app", "public_base_path"),
        "CME_WEATHER_HTTP_TIMEOUT_SECONDS": ("http", "timeout_seconds"),
        "CME_WEATHER_CACHE_TTL_SECONDS": ("cache", "ttl_seconds"),
        "CME_WEATHER_CACHE_LOCATIONS_TTL_SECONDS": ("cache", "locations_ttl_seconds"),
        "CME_WEATHER_CACHE_POINTS_TTL_SECONDS": ("cache", "points_ttl_seconds"),
        "CME_WEATHER_CACHE_STATIONS_TTL_SECONDS": ("cache", "stations_ttl_seconds"),
        "CME_WEATHER_CACHE_OBSERVATIONS_TTL_SECONDS": ("cache", "observations_ttl_seconds"),
        "CME_WEATHER_CACHE_ALERTS_TTL_SECONDS": ("cache", "alerts_ttl_seconds"),
        "CME_WEATHER_CACHE_FORECAST_TTL_SECONDS": ("cache", "forecast_ttl_seconds"),
        "CME_WEATHER_CACHE_STALE_IF_ERROR_SECONDS": ("cache", "stale_if_error_seconds"),
        "CME_WEATHER_NWS_BASE_URL": ("nws", "base_url"),
        "CME_WEATHER_NWS_USER_AGENT": ("nws", "user_agent"),
        "CME_WEATHER_ZIPPOTAM_BASE_URL": ("zippopotam", "base_url"),
        "CME_WEATHER_WS_ICON_DIR": ("icons", "ws_icon_dir"),
        "CME_WEATHER_MAX_ICON_INDEX": ("icons", "max_icon_index"),
        "CME_WEATHER_DEFAULT_QUERY": ("weather", "default_query"),
        "CME_WEATHER_MAX_ALERTS": ("weather", "max_alerts"),
        "CME_WEATHER_FALLBACK_DAYTIME": ("weather", "fallback_daytime"),
        "CME_WEATHER_ALERT_HEADLINE_CLIP_CHARS": ("alerts", "headline_clip_chars"),
        "CME_WEATHER_ALERT_DESCRIPTION_CLIP_CHARS": ("alerts", "description_clip_chars"),
        "CME_WEATHER_ALERT_INSTRUCTION_CLIP_CHARS": ("alerts", "instruction_clip_chars"),
        "CME_WEATHER_ALERT_PAGE_SIZE": ("alerts", "page_size"),
    }
    for env_name, path in legacy_mappings.items():
        _set_from_env(config, env, env_name, path)
    for env_name, path in service_mappings.items():
        _set_from_env(config, env, env_name, path)


def _section(config: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    value = config.get(name)
    if not isinstance(value, Mapping):
        raise ConfigError(f"config section {name!r} must be a mapping")
    return value


def _str(section: Mapping[str, Any], key: str) -> str:
    value = section.get(key)
    if value is None:
        return ""
    return str(value)


def _int(section: Mapping[str, Any], key: str) -> int:
    value = section.get(key)
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"config value {key!r} must be an integer") from exc


def _float(section: Mapping[str, Any], key: str) -> float:
    value = section.get(key)
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"config value {key!r} must be a number") from exc


def _bool(section: Mapping[str, Any], key: str) -> bool:
    value = section.get(key)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    raise ConfigError(f"config value {key!r} must be a boolean")


def _strip_trailing_slash(value: str, key: str) -> str:
    value = value.strip()
    if not value:
        raise ConfigError(f"config value {key!r} cannot be empty")
    return value.rstrip("/")


def _base_path(value: str) -> str:
    value = value.strip()
    if not value.startswith("/"):
        raise ConfigError("app.public_base_path must start with '/'")
    return value.rstrip("/") or "/"


def _build_settings(config: Mapping[str, Any], config_path: Optional[Path]) -> Settings:
    app = _section(config, "app")
    http = _section(config, "http")
    cache = _section(config, "cache")
    nws = _section(config, "nws")
    zippopotam = _section(config, "zippopotam")
    icons = _section(config, "icons")
    weather = _section(config, "weather")
    alerts = _section(config, "alerts")

    bind_port = _int(app, "bind_port")
    if not 1 <= bind_port <= 65535:
        raise ConfigError("app.bind_port must be between 1 and 65535")

    timeout_seconds = _float(http, "timeout_seconds")
    if timeout_seconds <= 0:
        raise ConfigError("http.timeout_seconds must be greater than zero")

    cache_values = {
        "ttl_seconds": _int(cache, "ttl_seconds"),
        "locations_ttl_seconds": _int(cache, "locations_ttl_seconds"),
        "points_ttl_seconds": _int(cache, "points_ttl_seconds"),
        "stations_ttl_seconds": _int(cache, "stations_ttl_seconds"),
        "observations_ttl_seconds": _int(cache, "observations_ttl_seconds"),
        "alerts_ttl_seconds": _int(cache, "alerts_ttl_seconds"),
        "forecast_ttl_seconds": _int(cache, "forecast_ttl_seconds"),
        "stale_if_error_seconds": _int(cache, "stale_if_error_seconds"),
    }
    for key, value in cache_values.items():
        if value < 0:
            raise ConfigError(f"cache.{key} must be zero or greater")

    max_icon_index = _int(icons, "max_icon_index")
    if max_icon_index < 0:
        raise ConfigError("icons.max_icon_index must be zero or greater")

    max_alerts = _int(weather, "max_alerts")
    if max_alerts < 0:
        raise ConfigError("weather.max_alerts must be zero or greater")

    alert_icon_overrides_raw = alerts.get("icon_overrides", {})
    if not isinstance(alert_icon_overrides_raw, Mapping):
        raise ConfigError("alerts.icon_overrides must be a mapping")
    alert_icon_overrides: Dict[str, int] = {}
    for key, value in alert_icon_overrides_raw.items():
        try:
            icon_index = int(value)
        except (TypeError, ValueError) as exc:
            raise ConfigError("alerts.icon_overrides values must be integers") from exc
        if icon_index < 0:
            raise ConfigError("alerts.icon_overrides values must be zero or greater")
        alert_icon_overrides[str(key).lower()] = icon_index

    alert_values = {
        "headline_clip_chars": _int(alerts, "headline_clip_chars"),
        "description_clip_chars": _int(alerts, "description_clip_chars"),
        "instruction_clip_chars": _int(alerts, "instruction_clip_chars"),
        "page_size": _int(alerts, "page_size"),
    }
    for key, value in alert_values.items():
        if value < 0:
            raise ConfigError(f"alerts.{key} must be zero or greater")

    return Settings(
        app=AppConfig(
            name=_str(app, "name") or "SeasonalCMEWeather",
            bind_host=_str(app, "bind_host") or "127.0.0.1",
            bind_port=bind_port,
            public_base_path=_base_path(_str(app, "public_base_path")),
        ),
        http=HttpConfig(timeout_seconds=timeout_seconds),
        cache=CacheConfig(**cache_values),
        nws=NwsConfig(
            base_url=_strip_trailing_slash(_str(nws, "base_url"), "nws.base_url"),
            user_agent=_str(nws, "user_agent"),
        ),
        zippopotam=ZippopotamConfig(
            base_url=_strip_trailing_slash(_str(zippopotam, "base_url"), "zippopotam.base_url"),
        ),
        icons=IconsConfig(
            ws_icon_dir=_str(icons, "ws_icon_dir"),
            max_icon_index=max_icon_index,
        ),
        weather=WeatherConfig(
            default_query=_str(weather, "default_query"),
            max_alerts=max_alerts,
            fallback_daytime=_bool(weather, "fallback_daytime"),
        ),
        alerts=AlertsConfig(**alert_values, icon_overrides=alert_icon_overrides),
        config_path=config_path,
    )


def load_config(path: str | os.PathLike[str] | None = None, env: Mapping[str, str] | None = None) -> Settings:
    if env is None:
        env = os.environ
    config_path = Path(path).expanduser() if path is not None else _env_path(env)

    config = _copy_defaults()
    _deep_merge(config, _read_yaml_config(config_path))
    _apply_env_overrides(config, env)
    return _build_settings(config, config_path if config_path.exists() else None)
