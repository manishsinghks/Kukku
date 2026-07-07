"""Weather via Open-Meteo (free, no API key needed)."""
from __future__ import annotations

from typing import Any

import httpx

from app.utils.logging import get_logger

log = get_logger(__name__)

_WMO = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "rime fog", 51: "light drizzle", 53: "drizzle", 55: "dense drizzle",
    61: "light rain", 63: "rain", 65: "heavy rain", 66: "freezing rain", 67: "freezing rain",
    71: "light snow", 73: "snow", 75: "heavy snow", 77: "snow grains",
    80: "light showers", 81: "showers", 82: "violent showers",
    85: "snow showers", 86: "snow showers",
    95: "thunderstorm", 96: "thunderstorm w/ hail", 99: "thunderstorm w/ hail",
}


def get_weather(city: str) -> dict[str, Any]:
    """Return current weather for a city, or {'error': ...}."""
    try:
        with httpx.Client(timeout=10) as c:
            geo = c.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": city, "count": 1},
            ).json()
            results = geo.get("results") or []
            if not results:
                return {"error": f"couldn't find location '{city}'"}
            loc = results[0]
            w = c.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": loc["latitude"], "longitude": loc["longitude"],
                    "current": "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m",
                    "daily": "temperature_2m_max,temperature_2m_min",
                    "timezone": "auto", "forecast_days": 1,
                },
            ).json()
        cur = w.get("current", {})
        daily = w.get("daily", {})
        return {
            "location": f"{loc['name']}, {loc.get('country', '')}".strip(", "),
            "temp_c": cur.get("temperature_2m"),
            "feels_like_c": cur.get("apparent_temperature"),
            "humidity_pct": cur.get("relative_humidity_2m"),
            "wind_kmh": cur.get("wind_speed_10m"),
            "condition": _WMO.get(cur.get("weather_code"), "unknown"),
            "high_c": (daily.get("temperature_2m_max") or [None])[0],
            "low_c": (daily.get("temperature_2m_min") or [None])[0],
        }
    except Exception as e:  # noqa: BLE001
        log.warning("weather lookup failed: %s", e)
        return {"error": f"weather service unavailable ({type(e).__name__})"}
