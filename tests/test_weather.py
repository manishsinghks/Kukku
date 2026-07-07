"""Tests for the weather tool (mocked Open-Meteo)."""
from __future__ import annotations

import httpx

import app.tools.weather as weather

_REAL_CLIENT = httpx.Client  # capture before any monkeypatch


def _client_with(handler):
    return _REAL_CLIENT(transport=httpx.MockTransport(handler))


def test_weather_parsed(monkeypatch):
    def handler(req: httpx.Request) -> httpx.Response:
        if "geocoding" in req.url.host:
            return httpx.Response(200, json={"results": [
                {"name": "Delhi", "country": "India", "latitude": 28.6, "longitude": 77.2}
            ]})
        return httpx.Response(200, json={
            "current": {"temperature_2m": 34.5, "apparent_temperature": 40.4,
                        "relative_humidity_2m": 56, "weather_code": 95, "wind_speed_10m": 2.8},
            "daily": {"temperature_2m_max": [37.6], "temperature_2m_min": [28.7]},
        })

    monkeypatch.setattr(weather.httpx, "Client", lambda **k: _client_with(handler))
    out = weather.get_weather("Delhi")
    assert out["location"] == "Delhi, India"
    assert out["temp_c"] == 34.5
    assert out["condition"] == "thunderstorm"
    assert out["high_c"] == 37.6


def test_weather_unknown_city(monkeypatch):
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"results": []})

    monkeypatch.setattr(weather.httpx, "Client", lambda **k: _client_with(handler))
    out = weather.get_weather("Xyzzy")
    assert "error" in out


def test_weather_network_error(monkeypatch):
    def handler(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    monkeypatch.setattr(weather.httpx, "Client", lambda **k: _client_with(handler))
    out = weather.get_weather("Delhi")
    assert "error" in out
