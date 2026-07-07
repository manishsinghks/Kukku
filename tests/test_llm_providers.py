"""Tests for the OpenAI-compatible provider (Gemini/Groq/OpenRouter/Ollama)."""
from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from app.config import Settings
from app.core.llm import (
    METRICS,
    EmptyResponseError,
    FailoverProvider,
    LLMTurn,
    OpenAICompatProvider,
    ProviderMetrics,
    RateLimitError,
    _extract_text_tool_calls,
    _parse_retry_after,
    build_provider,
)

TOOLS_STUB = [
    {"name": "run_local_command", "description": "run", "input_schema": {"type": "object"}},
    {"name": "search_files", "description": "search", "input_schema": {"type": "object"}},
]


class ScriptedFailover:
    """Fake provider: raises queued exceptions, then answers."""

    def __init__(self, name: str, failures: list[Exception] | None = None):
        self.name = name
        self.failures = list(failures or [])
        self.calls = 0

    async def turn(self, system, messages, tools, on_text=None, max_tokens=2048):
        self.calls += 1
        if self.failures:
            raise self.failures.pop(0)
        return LLMTurn(text=f"answer from {self.name}")


def test_convert_tools_shape():
    tools = [{"name": "t", "description": "d", "input_schema": {"type": "object"}}]
    out = OpenAICompatProvider.convert_tools(tools)
    assert out[0]["type"] == "function"
    assert out[0]["function"]["name"] == "t"
    assert out[0]["function"]["parameters"] == {"type": "object"}


def test_convert_messages_roundtrip():
    native_assistant = {
        "role": "assistant", "content": None,
        "tool_calls": [{"id": "c1", "type": "function",
                        "function": {"name": "search", "arguments": "{}"}}],
    }
    messages = [
        {"role": "user", "content": "find my resume"},
        {"role": "assistant", "content": native_assistant},
        {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "c1", "content": "found it"}
        ]},
    ]
    out = OpenAICompatProvider.convert_messages("SYS", messages)
    assert out[0] == {"role": "system", "content": "SYS"}
    assert out[1] == {"role": "user", "content": "find my resume"}
    assert out[2] is native_assistant  # passed through untouched
    assert out[3] == {"role": "tool", "tool_call_id": "c1", "content": "found it"}


def _sse(chunks: list[dict]) -> bytes:
    lines = [f"data: {json.dumps(c)}\n\n" for c in chunks]
    lines.append("data: [DONE]\n\n")
    return "".join(lines).encode()


def _provider_with_response(body: bytes) -> OpenAICompatProvider:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=body, headers={"content-type": "text/event-stream"})

    return OpenAICompatProvider(
        "https://fake.example/v1", "key", "test-model",
        transport=httpx.MockTransport(handler),
    )


def test_streaming_text_turn():
    body = _sse([
        {"choices": [{"delta": {"content": "Hel"}}]},
        {"choices": [{"delta": {"content": "lo"}}]},
        {"choices": [{"delta": {}, "finish_reason": "stop"}]},
    ])
    provider = _provider_with_response(body)
    seen: list[str] = []

    async def on_text(t: str) -> None:
        seen.append(t)

    turn = asyncio.run(provider.turn("sys", [{"role": "user", "content": "hi"}], [], on_text))
    assert turn.text == "Hello"
    assert turn.stop_reason == "stop"
    assert seen == ["Hel", "Hello"]  # streamed accumulation
    assert not turn.tool_calls


def test_streaming_tool_call_turn():
    body = _sse([
        {"choices": [{"delta": {"tool_calls": [
            {"index": 0, "id": "c9", "function": {"name": "search_files", "arguments": ""}}]}}]},
        {"choices": [{"delta": {"tool_calls": [
            {"index": 0, "function": {"arguments": '{"query": '}}]}}]},
        {"choices": [{"delta": {"tool_calls": [
            {"index": 0, "function": {"arguments": '"resume"}'}}]}}]},
        {"choices": [{"delta": {}, "finish_reason": "tool_calls"}]},
    ])
    provider = _provider_with_response(body)
    turn = asyncio.run(provider.turn("sys", [{"role": "user", "content": "find"}],
                                     [{"name": "search_files", "description": "d",
                                       "input_schema": {"type": "object"}}]))
    assert turn.stop_reason == "tool_use"
    assert turn.tool_calls == [{"id": "c9", "name": "search_files", "input": {"query": "resume"}}]
    # native payload is round-trippable
    assert turn.raw_content["tool_calls"][0]["function"]["name"] == "search_files"


def test_api_error_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, content=b'{"error": "boom"}')

    provider = OpenAICompatProvider(
        "https://fake.example/v1", "key", "m", transport=httpx.MockTransport(handler)
    )
    with pytest.raises(RuntimeError, match="500"):
        asyncio.run(provider.turn("s", [{"role": "user", "content": "x"}], []))


def test_parse_retry_after():
    body = '{"message": "quota exceeded... Please retry in 15.001373265s."}'
    assert _parse_retry_after(body) == pytest.approx(15.001373265)
    assert _parse_retry_after("no hint here") == 20.0


def test_rate_limit_retries_then_succeeds(monkeypatch):
    sleeps: list[float] = []

    async def fake_sleep(s):
        sleeps.append(s)

    monkeypatch.setattr("app.core.llm.asyncio.sleep", fake_sleep)

    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        if attempts["n"] == 1:
            return httpx.Response(429, content=b"Please retry in 3s.")
        return httpx.Response(
            200,
            content=_sse([{"choices": [{"delta": {"content": "recovered"},
                                        "finish_reason": "stop"}]}]),
            headers={"content-type": "text/event-stream"},
        )

    provider = OpenAICompatProvider(
        "https://fake.example/v1", "key", "m", transport=httpx.MockTransport(handler)
    )
    turn = asyncio.run(provider.turn("s", [{"role": "user", "content": "x"}], []))
    assert turn.text == "recovered"
    assert attempts["n"] == 2
    assert sleeps == [4.0]  # suggested 3s + 1s buffer


@pytest.mark.parametrize("text", [
    r'<function/run_local_command{\"action\": \"read_clipboard\"}</function>',
    '<function/run_local_command{"action": "open_folder", "target": "/x"}</function>',
    '<function=search_files>{"query": "resume"}</function>',
    'Sure, doing that. <function/run_local_command{"action": "lock_screen"}</function>',
])
def test_extract_text_tool_calls_formats(text):
    valid = {"run_local_command", "search_files"}
    parsed = _extract_text_tool_calls(text, valid)
    assert len(parsed) == 1
    assert parsed[0]["name"] in valid
    assert isinstance(parsed[0]["input"], dict)


def test_extract_text_tool_calls_ignores_unknown():
    assert _extract_text_tool_calls('<function/evil{"x":1}</function>', {"search_files"}) == []


def test_streaming_text_tool_call_is_recovered():
    """Groq/Llama emits the tool call as text -> parser recovers it."""
    body = _sse([
        {"choices": [{"delta": {"content": '<function/run_local_command'}}]},
        {"choices": [{"delta": {"content": '{"action": "read_clipboard"}</function>'}}]},
        {"choices": [{"delta": {}, "finish_reason": "stop"}]},
    ])
    provider = _provider_with_response(body)
    turn = asyncio.run(provider.turn("s", [{"role": "user", "content": "clip"}], TOOLS_STUB))
    assert turn.stop_reason == "tool_use"
    assert turn.tool_calls == [
        {"id": "txtcall_0", "name": "run_local_command", "input": {"action": "read_clipboard"}}
    ]
    # the raw text must not leak into the visible answer
    assert "<function" not in turn.text


def test_empty_response_raises_and_retries(monkeypatch):
    async def fake_sleep(_):
        pass

    monkeypatch.setattr("app.core.llm.asyncio.sleep", fake_sleep)
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        if attempts["n"] == 1:  # empty first
            body = _sse([{"choices": [{"delta": {}, "finish_reason": "stop"}]}])
        else:
            body = _sse([{"choices": [{"delta": {"content": "hi"}, "finish_reason": "stop"}]}])
        return httpx.Response(200, content=body, headers={"content-type": "text/event-stream"})

    provider = OpenAICompatProvider(
        "https://fake.example/v1", "k", "m", transport=httpx.MockTransport(handler)
    )
    turn = asyncio.run(provider.turn("s", [{"role": "user", "content": "x"}], []))
    assert turn.text == "hi"
    assert attempts["n"] == 2  # retried past the empty one


def test_empty_response_exhausts():
    def handler(request: httpx.Request) -> httpx.Response:
        body = _sse([{"choices": [{"delta": {}, "finish_reason": "stop"}]}])
        return httpx.Response(200, content=body, headers={"content-type": "text/event-stream"})

    provider = OpenAICompatProvider(
        "https://fake.example/v1", "k", "m", max_attempts=1,
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(EmptyResponseError):
        asyncio.run(provider.turn("s", [{"role": "user", "content": "x"}], []))


def test_rate_limit_exhausts_after_three_attempts(monkeypatch):
    async def fake_sleep(_):
        pass

    monkeypatch.setattr("app.core.llm.asyncio.sleep", fake_sleep)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, content=b"Please retry in 2s.")

    provider = OpenAICompatProvider(
        "https://fake.example/v1", "key", "m", transport=httpx.MockTransport(handler)
    )
    with pytest.raises(RateLimitError, match="rate limited"):
        asyncio.run(provider.turn("s", [{"role": "user", "content": "x"}], []))


def test_build_provider_single_gemini(monkeypatch):
    async def fake_health(self):
        return True

    monkeypatch.setattr(OpenAICompatProvider, "health", fake_health)
    s = Settings(anthropic_api_key="", gemini_api_key="g-key", groq_api_key="",
                 openrouter_api_key="", ollama_model="")
    provider, name = asyncio.run(build_provider(s))
    # single provider is still wrapped so metrics are captured uniformly
    assert isinstance(provider, FailoverProvider)
    assert "Gemini" in name
    assert provider.providers[0][1].base_url.startswith("https://generativelanguage")


def test_build_provider_chain_gemini_groq(monkeypatch):
    async def fake_health(self):
        return True

    monkeypatch.setattr(OpenAICompatProvider, "health", fake_health)
    s = Settings(anthropic_api_key="", gemini_api_key="g-key", groq_api_key="q-key",
                 openrouter_api_key="", ollama_model="")
    provider, name = asyncio.run(build_provider(s))
    assert isinstance(provider, FailoverProvider)
    assert "Gemini" in name and "Groq" in name
    # primary retry budget is trimmed when a fallback exists
    assert provider.providers[0][1].max_attempts == 2
    assert provider.providers[0][1].retry_wait_cap == 10.0


def test_provider_metrics_records_success_and_failure():
    m = ProviderMetrics()
    m.record_success("Gemini", 250.0, 120)
    m.record_success("Gemini", 150.0, 80)
    m.record_failure("Groq", "RateLimitError: quota")
    snap = m.snapshot()
    assert snap["active"] == "Gemini"
    g = snap["providers"]["Gemini"]
    assert g["calls"] == 2 and g["avg_latency_ms"] == 200 and g["total_tokens"] == 200
    assert snap["providers"]["Groq"]["failures"] == 1
    assert "quota" in snap["providers"]["Groq"]["last_error"]


def test_failover_records_metrics_on_success():
    METRICS._stats.clear()
    p = ScriptedFailover("groq")
    chain = FailoverProvider([("Groq (llama)", p)])
    asyncio.run(chain.turn("s", [{"role": "user", "content": "hi"}], []))
    snap = METRICS.snapshot()
    assert snap["active"] == "Groq (llama)"
    assert snap["providers"]["Groq (llama)"]["calls"] == 1


def test_provider_priority_groq_first_when_configured(monkeypatch):
    async def fake_health(self):
        return True

    monkeypatch.setattr(OpenAICompatProvider, "health", fake_health)
    s = Settings(anthropic_api_key="", gemini_api_key="g", groq_api_key="q",
                 openrouter_api_key="", ollama_model="", llm_priority="groq,gemini,openrouter")
    _provider, name = asyncio.run(build_provider(s))
    assert name.startswith("Groq")


def test_provider_chain_includes_openrouter(monkeypatch):
    async def fake_health(self):
        return True

    monkeypatch.setattr(OpenAICompatProvider, "health", fake_health)
    s = Settings(anthropic_api_key="", gemini_api_key="g", groq_api_key="q",
                 openrouter_api_key="or", ollama_model="",
                 llm_priority="gemini,groq,openrouter")
    provider, name = asyncio.run(build_provider(s))
    assert "OpenRouter" in name
    assert [n.split()[0] for n, _ in provider.providers][:3] == ["Gemini", "Groq", "OpenRouter"]


def test_provider_priority_configurable(monkeypatch):
    async def fake_health(self):
        return True

    monkeypatch.setattr(OpenAICompatProvider, "health", fake_health)
    s = Settings(anthropic_api_key="", gemini_api_key="g", groq_api_key="q",
                 openrouter_api_key="", ollama_model="", llm_priority="gemini,groq")
    _provider, name = asyncio.run(build_provider(s))
    assert name.startswith("Gemini")


def test_build_provider_no_config_gives_free_options():
    s = Settings(anthropic_api_key="", gemini_api_key="", groq_api_key="",
                 openrouter_api_key="", ollama_model="")
    with pytest.raises(RuntimeError) as e:
        asyncio.run(build_provider(s))
    msg = str(e.value)
    assert "aistudio.google.com" in msg and "Ollama" in msg
