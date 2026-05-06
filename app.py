#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import time
import html
from typing import Any, Dict, Tuple, Optional, List
import requests
from flask import Flask, request, Response

from PIL import Image, ImageDraw

APP_NAME = "SeasonalCMEWeather"

# NWS asks for a real UA string w/ contact info; you're setting it here.
DEFAULT_UA = "(seasonalnet.org, info@seasonalnet.org)"
NWS_USER_AGENT = os.getenv("NWS_USER_AGENT", DEFAULT_UA)

HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "4.5"))
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "60"))

ZIPPOTOPAM_BASE = "https://api.zippopotam.us"
NWS_BASE = "https://api.weather.gov"

app = Flask(__name__)
_cache: Dict[str, Tuple[float, Any]] = {}

WS_ICON_DIR = os.getenv("WS_ICON_DIR", "/opt/cme-weather/icons/ws4kp18")
# cache icon bytes by (index, dn) so day/night can differ
_icon_file_cache: Dict[str, bytes] = {}


def cache_get(key: str) -> Optional[Any]:
    v = _cache.get(key)
    if not v:
        return None
    ts, data = v
    if (time.time() - ts) > CACHE_TTL_SECONDS:
        _cache.pop(key, None)
        return None
    return data


def cache_set(key: str, data: Any) -> None:
    _cache[key] = (time.time(), data)


def http_get_json(url: str) -> Any:
    ck = f"GET:{url}"
    cached = cache_get(ck)
    if cached is not None:
        return cached

    headers = {
        "User-Agent": NWS_USER_AGENT,
        "Accept": "application/geo+json, application/json;q=0.9,*/*;q=0.1",
    }
    r = requests.get(url, headers=headers, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    data = r.json()
    cache_set(ck, data)
    return data


def xml_response(xml: str) -> Response:
    body = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml
    return Response(body, status=200, mimetype="text/xml")


def abs_url(path: str) -> str:
    return request.host_url.rstrip("/") + path


def x(s: str) -> str:
    return html.escape(s or "", quote=False)


ZIP_RE = re.compile(r"^\d{5}(-\d{4})?$", re.ASCII)


def zippopotam_latlon(q: str) -> Tuple[float, float, str]:
    q = (q or "").strip()
    if not q:
        raise ValueError("empty query")

    if ZIP_RE.match(q):
        url = f"{ZIPPOTOPAM_BASE}/us/{q[:5]}"
        data = http_get_json(url)
        place = data["places"][0]
        lat = float(place["latitude"])
        lon = float(place["longitude"])
        label = f'{place["place name"]}, {place["state abbreviation"]} {q[:5]}'
        return lat, lon, label

    m = re.match(r"^\s*([^,]+)\s*,\s*([A-Za-z]{2})\s*$", q)
    if not m:
        raise ValueError("format must be ZIP (90210) or City, ST (Belmont, MA)")

    city = m.group(1).strip()
    st = m.group(2).strip().lower()
    url = f"{ZIPPOTOPAM_BASE}/us/{st}/{requests.utils.quote(city)}"
    data = http_get_json(url)
    place = data["places"][0]
    lat = float(place["latitude"])
    lon = float(place["longitude"])
    label = f'{place["place name"]}, {place["state abbreviation"]}'
    return lat, lon, label


def nws_points(lat: float, lon: float) -> Any:
    return http_get_json(f"{NWS_BASE}/points/{lat:.4f},{lon:.4f}")


def nws_latest_observation(points_obj: Any) -> Any:
    stations_url = points_obj["properties"]["observationStations"]
    stations = http_get_json(stations_url)
    if not stations.get("features"):
        raise RuntimeError("no observation stations found")
    station_id = stations["features"][0]["properties"]["stationIdentifier"]
    return http_get_json(f"{NWS_BASE}/stations/{station_id}/observations/latest")


def nws_active_alerts(lat: float, lon: float) -> List[Any]:
    data = http_get_json(f"{NWS_BASE}/alerts/active?point={lat:.4f},{lon:.4f}")
    return data.get("features", [])


def nws_is_daytime(points_obj: Any) -> bool:
    """
    Decide day vs night using NWS forecast period 0.
    This is cached by http_get_json() so it won't hammer NWS.
    """
    props = points_obj.get("properties") or {}
    forecast_url = props.get("forecast")
    if not forecast_url:
        return True
    data = http_get_json(forecast_url)
    periods = ((data.get("properties") or {}).get("periods") or [])
    if not periods:
        return True
    return bool(periods[0].get("isDaytime", True))


def classify_weather_icon(desc: str) -> int:
    d = (desc or "").lower()
    if "thunder" in d or "tstm" in d:
        return 5
    if "snow" in d or "blizzard" in d or "sleet" in d:
        return 3
    if "rain" in d or "shower" in d or "drizzle" in d:
        return 2
    if "fog" in d or "mist" in d or "haze" in d:
        return 4
    if "cloud" in d or "overcast" in d:
        return 1
    return 0


def classify_alert_icon(event: str) -> Tuple[int, str]:
    el = (event or "").lower()
    if "warning" in el:
        return 6, "warning"
    if "watch" in el:
        return 7, "watch"
    if "advisory" in el:
        return 8, "advisory"
    if "statement" in el:
        return 9, "statement"
    return 8, "advisory"


def _read_icon_file(index: int, dn: str) -> Optional[bytes]:
    """
    Load WS4KP-derived PNGs for weather slots 0..5.
    Supports optional night variants as '{index}n.png' when dn == '0'.
    """
    if not (0 <= index <= 5):
        return None

    # Prefer night variant if requested and present
    if dn == "0":
        pn = os.path.join(WS_ICON_DIR, f"{index}n.png")
        if os.path.isfile(pn):
            with open(pn, "rb") as f:
                return f.read()

    # Fall back to day/primary
    p = os.path.join(WS_ICON_DIR, f"{index}.png")
    if os.path.isfile(p):
        with open(p, "rb") as f:
            return f.read()

    return None


def icon_png(index: int, dn: str = "1") -> bytes:
    """
    Returns PNG bytes for icon index.
    dn: "1" (day) or "0" (night). Only matters for WS4KP file-backed icons.
    """
    dn = "0" if dn == "0" else "1"
    ck = f"{index}:{dn}"

    cached = _icon_file_cache.get(ck)
    if cached is not None:
        return cached

    file_bytes = _read_icon_file(index, dn)
    if file_bytes is not None:
        _icon_file_cache[ck] = file_bytes
        return file_bytes

    # --- fallback: generated icons below ---

    img = Image.new("RGBA", (18, 18), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    if index == 0:  # clear
        d.ellipse((3, 3, 15, 15), fill=(255, 215, 0, 255))
    elif index == 1:  # cloudy
        d.ellipse((3, 7, 11, 15), fill=(180, 180, 180, 255))
        d.ellipse((7, 5, 16, 14), fill=(160, 160, 160, 255))
        d.rectangle((4, 10, 16, 15), fill=(170, 170, 170, 255))
    elif index == 2:  # rain
        d.ellipse((3, 5, 16, 13), fill=(170, 170, 170, 255))
        for x0 in (6, 10, 14):
            d.line((x0, 13, x0 - 1, 17), fill=(70, 130, 180, 255), width=2)
    elif index == 3:  # snow
        d.ellipse((3, 5, 16, 13), fill=(170, 170, 170, 255))
        for x0 in (7, 11, 15):
            d.ellipse((x0 - 1, 14), (x0 + 1, 16), fill=(230, 230, 255, 255))
    elif index == 4:  # fog
        for y in (6, 9, 12, 15):
            d.line((2, y, 16, y), fill=(180, 180, 180, 255), width=2)
    elif index == 5:  # thunder
        d.ellipse((3, 5, 16, 13), fill=(140, 140, 140, 255))
        d.polygon([(9, 10), (7, 17), (11, 17)], fill=(255, 215, 0, 255))
    else:
        color = {
            6: (220, 20, 60, 255),    # warning
            7: (255, 140, 0, 255),    # watch
            8: (255, 215, 0, 255),    # advisory
            9: (34, 139, 34, 255),    # statement
        }.get(index, (128, 128, 128, 255))
        d.rectangle((2, 2, 16, 16), fill=color)

    import io
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    out = buf.getvalue()
    _icon_file_cache[ck] = out
    return out


@app.get("/cme/services/ping")
def ping() -> Response:
    return xml_response(
        """
<CiscoIPPhoneText>
  <Title>SeasonalCME</Title>
  <Prompt>Ping</Prompt>
  <Text>OK</Text>
</CiscoIPPhoneText>
""".strip()
    )


@app.get("/cme/services/")
def root_menu() -> Response:
    xml = f"""
<CiscoIPPhoneMenu>
  <Title>SeasonalCME</Title>
  <Prompt>Select a service</Prompt>
  <MenuItem>
    <Name>Weather</Name>
    <URL>{x(abs_url("/cme/services/weather"))}</URL>
  </MenuItem>
  <MenuItem>
    <Name>Ping</Name>
    <URL>{x(abs_url("/cme/services/ping"))}</URL>
  </MenuItem>
</CiscoIPPhoneMenu>
""".strip()
    return xml_response(xml)


@app.get("/cme/services/weather")
def weather_input() -> Response:
    xml = f"""
<CiscoIPPhoneInput>
  <Title>Weather</Title>
  <Prompt>Enter ZIP or City, ST</Prompt>
  <URL>{x(abs_url("/cme/services/weather/show"))}</URL>
  <InputItem>
    <DisplayName>Location</DisplayName>
    <QueryStringParam>q</QueryStringParam>
    <DefaultValue>90210</DefaultValue>
    <InputFlags>A</InputFlags>
  </InputItem>
</CiscoIPPhoneInput>
""".strip()
    return xml_response(xml)


@app.get("/cme/services/weather/icon.png")
def icon_endpoint() -> Response:
    try:
        i = int(request.args.get("i", "0"))
    except ValueError:
        i = 0
    if i < 0 or i > 9:
        i = 0

    dn = request.args.get("dn", "1")
    dn = "0" if dn == "0" else "1"

    return Response(icon_png(i, dn), mimetype="image/png")


@app.get("/cme/services/weather/show")
def weather_show() -> Response:
    q = (request.args.get("q", "") or "").strip()
    try:
        lat, lon, label = zippopotam_latlon(q)
    except Exception as e:
        return xml_response(
            f"""
<CiscoIPPhoneText>
  <Title>Weather</Title>
  <Prompt>Bad input</Prompt>
  <Text>{x(str(e))}</Text>
</CiscoIPPhoneText>
""".strip()
        )

    try:
        pts = nws_points(lat, lon)
        obs = nws_latest_observation(pts)
        alerts = nws_active_alerts(lat, lon)
    except Exception as e:
        return xml_response(
            f"""
<CiscoIPPhoneText>
  <Title>Weather</Title>
  <Prompt>NWS error</Prompt>
  <Text>{x(str(e))}</Text>
</CiscoIPPhoneText>
""".strip()
        )

    # Day/night decision (cached via http_get_json)
    is_day = True
    try:
        is_day = nws_is_daytime(pts)
    except Exception:
        is_day = True
    dn = "1" if is_day else "0"

    props = obs.get("properties", {})
    temp_c = props.get("temperature", {}).get("value")
    desc = props.get("textDescription") or "Current conditions"
    temp_f = (temp_c * 9.0 / 5.0) + 32.0 if isinstance(temp_c, (int, float)) else None

    wx_icon = classify_weather_icon(desc)
    now_line = f"Now: {temp_f:.0f}F {desc}" if temp_f is not None else f"Now: {desc}"

    icon_base = abs_url("/cme/services/weather/icon.png")
    icon_lines: List[str] = []
    for i in range(10):
        url = f"{icon_base}?i={i}"
        # only index 0 (clear/sunny) gets day/night switching today,
        # but icon_png supports i*n.png for any 0..5 if you add them later.
        if i == 0:
            url += f"&dn={dn}"
        icon_lines.append(f"  <IconItem><Index>{i}</Index><URL>{x(url)}</URL></IconItem>")
    icon_items = "\n".join(icon_lines)

    menu_items: List[str] = []

    menu_items.append(
        f"""
  <MenuItem>
    <IconIndex>{wx_icon}</IconIndex>
    <Name>{x(now_line)}</Name>
    <URL>{x(abs_url("/cme/services/weather/show"))}?q={requests.utils.quote(q)}</URL>
  </MenuItem>
""".rstrip()
    )

    if alerts:
        for a in alerts[:6]:
            ap = a.get("properties", {})
            event = ap.get("event", "Alert")
            icon_idx, _level = classify_alert_icon(event)
            aid = ap.get("id") or a.get("id") or ""
            menu_items.append(
                f"""
  <MenuItem>
    <IconIndex>{icon_idx}</IconIndex>
    <Name>{x(event)}</Name>
    <URL>{x(abs_url("/cme/services/weather/alert"))}?id={requests.utils.quote(aid)}</URL>
  </MenuItem>
""".rstrip()
            )
    else:
        menu_items.append(
            f"""
  <MenuItem>
    <IconIndex>9</IconIndex>
    <Name>No active alerts</Name>
    <URL>{x(abs_url("/cme/services/weather/show"))}?q={requests.utils.quote(q)}</URL>
  </MenuItem>
""".rstrip()
        )

    menu_items.append(
        f"""
  <MenuItem>
    <IconIndex>{wx_icon}</IconIndex>
    <Name>Refresh</Name>
    <URL>{x(abs_url("/cme/services/weather/show"))}?q={requests.utils.quote(q)}</URL>
  </MenuItem>
""".rstrip()
    )

    xml = f"""
<CiscoIPPhoneIconFileMenu>
  <Title>Weather</Title>
  <Prompt>{x(label)}</Prompt>
{''.join(menu_items)}
{icon_items}
</CiscoIPPhoneIconFileMenu>
""".strip()
    return xml_response(xml)


@app.get("/cme/services/weather/alert")
def alert_detail() -> Response:
    aid = request.args.get("id", "") or ""
    if not aid:
        return xml_response(
            """
<CiscoIPPhoneText><Title>Alert</Title><Prompt>Error</Prompt><Text>Missing alert id</Text></CiscoIPPhoneText>
""".strip()
        )

    url = aid if aid.startswith("http") else f"{NWS_BASE}/alerts/{aid}"
    try:
        data = http_get_json(url)
    except Exception as e:
        return xml_response(
            f"""
<CiscoIPPhoneText><Title>Alert</Title><Prompt>Error</Prompt><Text>{x(str(e))}</Text></CiscoIPPhoneText>
""".strip()
        )

    p = data.get("properties", {})
    event = p.get("event", "Alert")
    headline = (p.get("headline") or "").strip()
    desc = (p.get("description") or "").strip()
    instr = (p.get("instruction") or "").strip()

    def clip(s: str, n: int) -> str:
        return (s[:n] + "…") if len(s) > n else s

    body = "\n\n".join(
        [
            clip(headline, 300),
            clip(desc, 900),
            clip(instr, 500),
        ]
    ).strip()

    return xml_response(
        f"""
<CiscoIPPhoneText>
  <Title>{x(event)}</Title>
  <Prompt>Active alert</Prompt>
  <Text>{x(body)}</Text>
</CiscoIPPhoneText>
""".strip()
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=9010)
