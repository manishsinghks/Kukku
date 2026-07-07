"""Tests for the FailoverProvider chain (Gemini primary -> Groq secondary)."""
from __future__ import annotations

import asyncio

import httpx
import pytest

from app.core.llm import FailoverProvider, RateLimitError
from tests.test_llm_providers import ScriptedFailover

MSGS = [{"role": "user", "content": "hi"}]


def _chain(primary: ScriptedFailover, secondary: ScriptedFailover) -> FailoverProvider:
    return FailoverProvider([("gemini", primary), ("groq", secondary)])


def test_primary_healthy_secondary_untouched():
    p, s = ScriptedFailover("gemini"), ScriptedFailover("groq")
    turn = asyncio.run(_chain(p, s).turn("sys", MSGS, []))
    assert turn.text == "answer from gemini"
    assert s.calls == 0


def test_failover_on_rate_limit():
    p = ScriptedFailover("gemini", [RateLimitError(15.0)])
    s = ScriptedFailover("groq")
    turn = asyncio.run(_chain(p, s).turn("sys", MSGS, []))
    assert turn.text == "answer from groq"


def test_failover_on_timeout_and_network():
    for exc in (httpx.ConnectTimeout("t"), httpx.ConnectError("down")):
        p = ScriptedFailover("gemini", [exc])
        s = ScriptedFailover("groq")
        turn = asyncio.run(_chain(p, s).turn("sys", MSGS, []))
        assert turn.text == "answer from groq"


def test_cooldown_skips_failed_primary():
    p = ScriptedFailover("gemini", [RateLimitError(120.0)])
    s = ScriptedFailover("groq")
    chain = _chain(p, s)
    asyncio.run(chain.turn("sys", MSGS, []))          # fails over, gemini cools down
    asyncio.run(chain.turn("sys", MSGS, []))          # second message
    assert p.calls == 1                                # gemini skipped while cooling
    assert s.calls == 2
    assert chain.status()["gemini"]["in_cooldown"] is True


def test_primary_recovers_after_cooldown():
    p = ScriptedFailover("gemini", [RateLimitError(30.0)])
    s = ScriptedFailover("groq")
    chain = _chain(p, s)
    asyncio.run(chain.turn("sys", MSGS, []))
    chain._down_until["gemini"] = 0.0                  # simulate cooldown expiry
    turn = asyncio.run(chain.turn("sys", MSGS, []))
    assert turn.text == "answer from gemini"
    assert chain.status()["gemini"]["in_cooldown"] is False


def test_all_providers_fail_raises_last_error():
    p = ScriptedFailover("gemini", [RateLimitError(5.0)])
    s = ScriptedFailover("groq", [httpx.ConnectError("down")])
    with pytest.raises(httpx.ConnectError):
        asyncio.run(_chain(p, s).turn("sys", MSGS, []))


def test_all_in_cooldown_still_tries():
    p = ScriptedFailover("gemini", [RateLimitError(300.0)])
    s = ScriptedFailover("groq", [RateLimitError(300.0)])
    chain = _chain(p, s)
    with pytest.raises(RateLimitError):
        asyncio.run(chain.turn("sys", MSGS, []))
    # both cooling down — a new message must still attempt rather than dead-end
    turn = asyncio.run(chain.turn("sys", MSGS, []))
    assert turn.text == "answer from gemini"
