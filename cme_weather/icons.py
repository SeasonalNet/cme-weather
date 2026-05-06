from __future__ import annotations

import io
import os
from typing import Dict, Optional, Tuple

from PIL import Image, ImageDraw

_icon_file_cache: Dict[str, bytes] = {}


def classify_weather_icon(description: str) -> int:
    desc = (description or "").lower()
    if "thunder" in desc or "tstm" in desc:
        return 5
    if "snow" in desc or "blizzard" in desc or "sleet" in desc:
        return 3
    if "rain" in desc or "shower" in desc or "drizzle" in desc:
        return 2
    if "fog" in desc or "mist" in desc or "haze" in desc:
        return 4
    if "cloud" in desc or "overcast" in desc:
        return 1
    return 0


def classify_alert_icon(event: str) -> Tuple[int, str]:
    event_l = (event or "").lower()
    if "warning" in event_l:
        return 6, "warning"
    if "watch" in event_l:
        return 7, "watch"
    if "advisory" in event_l:
        return 8, "advisory"
    if "statement" in event_l:
        return 9, "statement"
    return 8, "advisory"


def _read_icon_file(icon_dir: str, index: int, day_night: str) -> Optional[bytes]:
    """
    Load WS4KP-derived PNGs for weather slots 0..5.

    Supports optional night variants as '{index}n.png' when day_night == '0'.
    """
    if not (0 <= index <= 5):
        return None

    if day_night == "0":
        night_path = os.path.join(icon_dir, f"{index}n.png")
        if os.path.isfile(night_path):
            with open(night_path, "rb") as handle:
                return handle.read()

    path = os.path.join(icon_dir, f"{index}.png")
    if os.path.isfile(path):
        with open(path, "rb") as handle:
            return handle.read()

    return None


def icon_png(index: int, *, day_night: str = "1", icon_dir: str, max_icon_index: int) -> bytes:
    """
    Return PNG bytes for a Cisco icon index.

    day_night: "1" for day, "0" for night. Only file-backed weather icons use this today.
    """
    if index < 0 or index > max_icon_index:
        index = 0

    day_night = "0" if day_night == "0" else "1"
    cache_key = f"{icon_dir}:{index}:{day_night}"

    cached = _icon_file_cache.get(cache_key)
    if cached is not None:
        return cached

    file_bytes = _read_icon_file(icon_dir, index, day_night)
    if file_bytes is not None:
        _icon_file_cache[cache_key] = file_bytes
        return file_bytes

    img = Image.new("RGBA", (18, 18), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if index == 0:  # clear
        draw.ellipse((3, 3, 15, 15), fill=(255, 215, 0, 255))
    elif index == 1:  # cloudy
        draw.ellipse((3, 7, 11, 15), fill=(180, 180, 180, 255))
        draw.ellipse((7, 5, 16, 14), fill=(160, 160, 160, 255))
        draw.rectangle((4, 10, 16, 15), fill=(170, 170, 170, 255))
    elif index == 2:  # rain
        draw.ellipse((3, 5, 16, 13), fill=(170, 170, 170, 255))
        for x0 in (6, 10, 14):
            draw.line((x0, 13, x0 - 1, 17), fill=(70, 130, 180, 255), width=2)
    elif index == 3:  # snow
        draw.ellipse((3, 5, 16, 13), fill=(170, 170, 170, 255))
        for x0 in (7, 11, 15):
            draw.ellipse((x0 - 1, 14, x0 + 1, 16), fill=(230, 230, 255, 255))
    elif index == 4:  # fog
        for y in (6, 9, 12, 15):
            draw.line((2, y, 16, y), fill=(180, 180, 180, 255), width=2)
    elif index == 5:  # thunder
        draw.ellipse((3, 5, 16, 13), fill=(140, 140, 140, 255))
        draw.polygon([(9, 10), (7, 17), (11, 17)], fill=(255, 215, 0, 255))
    else:
        color = {
            6: (220, 20, 60, 255),
            7: (255, 140, 0, 255),
            8: (255, 215, 0, 255),
            9: (34, 139, 34, 255),
        }.get(index, (128, 128, 128, 255))
        draw.rectangle((2, 2, 16, 16), fill=color)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    output = buf.getvalue()
    _icon_file_cache[cache_key] = output
    return output
