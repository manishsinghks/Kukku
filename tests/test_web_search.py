"""Tests for the web_search tool (DuckDuckGo backend fallback + generator fix)."""
from __future__ import annotations

import app.tools.web_search as ws


class FakeDDGS:
    """Mimics ddgs.DDGS as a context manager whose text() is a generator that
    only yields while the session is open — catches the 'iterate after close' bug.
    """

    # class-level script: which backends return results
    results_by_backend: dict = {}

    def __enter__(self):
        self._open = True
        return self

    def __exit__(self, *a):
        self._open = False
        return False

    def text(self, query, max_results=6, backend="auto"):
        for item in self.results_by_backend.get(backend, []):
            assert self._open, "generator consumed after DDGS session closed"
            yield item


def _install(monkeypatch, by_backend):
    FakeDDGS.results_by_backend = by_backend
    monkeypatch.setattr(ws, "DDGS", FakeDDGS, raising=False)
    # ensure the import inside _duckduckgo_search resolves to our fake
    import sys
    import types

    fake_mod = types.ModuleType("ddgs")
    fake_mod.DDGS = FakeDDGS
    monkeypatch.setitem(sys.modules, "ddgs", fake_mod)


HIT = {"title": "T", "href": "https://x", "body": "snippet"}


def test_returns_results_when_html_backend_works(monkeypatch):
    # auto empty, html has results — must fall through to html
    _install(monkeypatch, {"auto": [], "html": [HIT], "lite": []})
    out = ws.web_search("q")
    assert len(out) == 1
    assert out[0] == {"title": "T", "url": "https://x", "snippet": "snippet"}


def test_first_nonempty_backend_wins(monkeypatch):
    _install(monkeypatch, {"html": [HIT, HIT], "lite": [], "auto": []})
    assert len(ws.web_search("q")) == 2


def test_all_backends_empty_returns_empty(monkeypatch):
    _install(monkeypatch, {"auto": [], "html": [], "lite": []})
    assert ws.web_search("q") == []


def test_backend_exception_falls_through(monkeypatch):
    class Boom(FakeDDGS):
        def text(self, query, max_results=6, backend="auto"):
            if backend == "html":
                raise RuntimeError("blocked")
            yield from super().text(query, max_results, backend)

    Boom.results_by_backend = {"html": [HIT], "lite": [HIT], "auto": []}
    import sys
    import types

    monkeypatch.setattr(ws, "DDGS", Boom, raising=False)
    m = types.ModuleType("ddgs")
    m.DDGS = Boom
    monkeypatch.setitem(sys.modules, "ddgs", m)
    # html raises -> lite succeeds
    assert len(ws.web_search("q")) == 1


def test_gemini_grounding_preferred_over_ddg(monkeypatch):
    """When a Gemini key is present, grounded search is used and DDG is skipped."""
    called = {"ddg": False}

    def fake_grounded(query, api_key, model):
        return [{"title": "Google answer", "url": "https://src", "snippet": "Australia won."}]

    def fake_ddg(query, max_results):
        called["ddg"] = True
        return []

    monkeypatch.setattr(ws, "_gemini_grounded_search", fake_grounded)
    monkeypatch.setattr(ws, "_duckduckgo_search", fake_ddg)
    out = ws.web_search("who won", gemini_api_key="k")
    assert out[0]["snippet"] == "Australia won."
    assert called["ddg"] is False


def test_gemini_failure_falls_back_to_ddg(monkeypatch):
    def boom(query, api_key, model):
        raise RuntimeError("gemini down")

    monkeypatch.setattr(ws, "_gemini_grounded_search", boom)
    monkeypatch.setattr(ws, "_duckduckgo_search",
                        lambda q, n: [{"title": "d", "url": "u", "snippet": "s"}])
    out = ws.web_search("q", gemini_api_key="k")
    assert out[0]["title"] == "d"  # fell back to DDG


def test_parse_gemini_grounding_response(monkeypatch):
    """_gemini_grounded_search extracts the answer + source URLs from the API shape."""
    payload = {
        "candidates": [{
            "content": {"parts": [{"text": "Australia won the 2023 World Cup."}]},
            "groundingMetadata": {
                "groundingChunks": [
                    {"web": {"uri": "https://en.wikipedia.org/x", "title": "Wikipedia"}},
                ]
            },
        }]
    }

    def fake_post(url, json=None, timeout=None):
        assert "google_search" in str(json)

        class R:
            def raise_for_status(self):
                pass

            def json(self):
                return payload

        return R()

    monkeypatch.setattr(ws.httpx, "post", fake_post)
    out = ws._gemini_grounded_search("q", "key", "gemini-2.5-flash")
    assert out[0]["snippet"] == "Australia won the 2023 World Cup."
    assert out[0]["url"] == "https://en.wikipedia.org/x"
