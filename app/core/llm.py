"""LLM providers — all with full tool use.

Supported (first configured wins):
  1. Anthropic Claude          (ANTHROPIC_API_KEY — best quality, paid)
  2. Google Gemini             (GEMINI_API_KEY — FREE tier, recommended free option)
  3. Groq                      (GROQ_API_KEY — free tier, very fast Llama)
  4. OpenRouter                (OPENROUTER_API_KEY — free models available)
  5. Ollama                    (OLLAMA_MODEL — 100% local & free, needs ~5GB RAM)

Gemini, Groq, OpenRouter and Ollama all speak the OpenAI-compatible
chat-completions API, so one provider class (OpenAICompatProvider) covers all
four, including streaming and tool calling.

Message interchange format is Anthropic-shaped (the agent is provider-agnostic):
user turns are strings or lists of tool_result blocks; assistant turns carry the
provider's own raw payload, which the same provider translates back on the next
round.
"""
from __future__ import annotations

import asyncio
import json
import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.config import Settings
from app.utils.logging import get_logger

log = get_logger(__name__)

OnText = Callable[[str], Awaitable[None]]  # receives the accumulated text so far


class RateLimitError(RuntimeError):
    """HTTP 429 from the LLM API, with the provider's suggested wait."""

    def __init__(self, retry_after: float):
        super().__init__(
            f"rate limited — free-tier quota hit, retry suggested in {retry_after:.0f}s"
        )
        self.retry_after = retry_after


class EmptyResponseError(RuntimeError):
    """Model returned no text and no tool call — a degenerate response to retry."""


def _parse_retry_after(body: str) -> float:
    """Extract 'retry in 15.0s' style hints from a 429 body; default 20s."""
    m = re.search(r"retry in ([0-9.]+)\s*s", body, re.IGNORECASE)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass
    return 20.0


# Some models (notably Llama 3.3 on Groq) emit tool calls as TEXT instead of the
# structured tool_calls field, e.g.  <function/NAME{json}</function>  or
# <function=NAME>{json}</function>. We parse those back into real tool calls so
# tool use works regardless of which provider handled the turn.
_TEXT_TOOL_RE = re.compile(
    r"<function[=/]\s*([a-zA-Z_]\w*)\s*>?\s*(\{.*?\})\s*(?:</function>|<\|eom\|>|$)",
    re.DOTALL,
)


def _extract_text_tool_calls(text: str, valid_names: set[str]) -> list[dict[str, Any]]:
    """Return [{name, input}] parsed from textual tool-call syntax in `text`."""
    out: list[dict[str, Any]] = []
    for m in _TEXT_TOOL_RE.finditer(text):
        name = m.group(1)
        if name not in valid_names:
            continue
        raw = m.group(2)
        for candidate in (raw, raw.replace('\\"', '"').replace("\\'", "'")):
            try:
                args = json.loads(candidate)
                break
            except json.JSONDecodeError:
                args = None
        if args is None:
            continue
        out.append({"name": name, "input": args})
    return out


@dataclass
class LLMTurn:
    """One assistant turn: final text plus any tool calls requested."""
    text: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)  # {id, name, input}
    stop_reason: str = "end_turn"
    raw_content: Any = None  # provider-native assistant payload, round-tripped by the agent
    usage_tokens: int = 0    # tokens used this turn (exact if the API reports it, else estimated)


@dataclass
class _ProviderStat:
    calls: int = 0
    failures: int = 0
    total_latency_ms: float = 0.0
    total_tokens: int = 0
    last_used: float = 0.0
    last_error: str = ""

    def snapshot(self) -> dict[str, Any]:
        return {
            "calls": self.calls,
            "failures": self.failures,
            "avg_latency_ms": round(self.total_latency_ms / self.calls) if self.calls else 0,
            "total_tokens": self.total_tokens,
            "last_used": self.last_used,
            "last_error": self.last_error[:160],
        }


class ProviderMetrics:
    """Shared, in-memory provider observability — one source of truth read by
    both the Telegram bot and the web dashboard (via the /api/status endpoint)."""

    def __init__(self) -> None:
        self._stats: dict[str, _ProviderStat] = {}
        self.active: str = ""

    def _s(self, name: str) -> _ProviderStat:
        return self._stats.setdefault(name, _ProviderStat())

    def record_success(self, name: str, latency_ms: float, tokens: int) -> None:
        s = self._s(name)
        s.calls += 1
        s.total_latency_ms += latency_ms
        s.total_tokens += max(tokens, 0)
        s.last_used = time.time()
        self.active = name

    def record_failure(self, name: str, error: str) -> None:
        s = self._s(name)
        s.failures += 1
        s.last_error = error

    def snapshot(self) -> dict[str, Any]:
        return {
            "active": self.active,
            "providers": {k: v.snapshot() for k, v in self._stats.items()},
        }


# module-level singleton — the shared metrics store
METRICS = ProviderMetrics()


class ClaudeProvider:
    def __init__(self, settings: Settings):
        import anthropic

        self.model = settings.anthropic_model
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def turn(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        on_text: OnText | None = None,
        max_tokens: int = 2048,
    ) -> LLMTurn:
        accumulated = ""
        async with self.client.messages.stream(
            model=self.model,
            system=system,
            messages=messages,
            tools=tools,
            max_tokens=max_tokens,
        ) as stream:
            async for event in stream.text_stream:
                accumulated += event
                if on_text:
                    await on_text(accumulated)
            final = await stream.get_final_message()

        turn = LLMTurn(stop_reason=final.stop_reason or "end_turn", raw_content=final.content)
        for block in final.content:
            if block.type == "text":
                turn.text += block.text
            elif block.type == "tool_use":
                turn.tool_calls.append(
                    {"id": block.id, "name": block.name, "input": block.input or {}}
                )
        return turn


class OpenAICompatProvider:
    """Streaming + tool calling against any OpenAI-compatible /chat/completions.

    Covers Gemini (free tier), Groq (free tier), OpenRouter, and local Ollama.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        transport: httpx.AsyncBaseTransport | None = None,
        max_attempts: int = 3,
        retry_wait_cap: float = 35.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self._transport = transport  # injectable for tests
        self.max_attempts = max_attempts
        self.retry_wait_cap = retry_wait_cap

    # -- format conversion -----------------------------------------------------
    @staticmethod
    def convert_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Anthropic tool schema -> OpenAI function-calling schema."""
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["input_schema"],
                },
            }
            for t in tools
        ]

    @staticmethod
    def convert_messages(system: str, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Agent (Anthropic-shaped) history -> OpenAI chat messages."""
        out: list[dict[str, Any]] = [{"role": "system", "content": system}]
        for m in messages:
            content = m["content"]
            if isinstance(content, str):
                out.append({"role": m["role"], "content": content})
            elif m["role"] == "assistant":
                # our own native assistant payload from a previous round
                out.append(content)
            else:
                # user turn holding tool_result blocks
                for block in content:
                    out.append(
                        {
                            "role": "tool",
                            "tool_call_id": block["tool_use_id"],
                            "content": block["content"],
                        }
                    )
        return out

    # -- request ---------------------------------------------------------------
    async def turn(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        on_text: OnText | None = None,
        max_tokens: int = 2048,
    ) -> LLMTurn:
        """One assistant turn, with automatic retry on rate limits / network errors."""
        for attempt in range(1, self.max_attempts + 1):
            try:
                return await self._turn_once(system, messages, tools, on_text, max_tokens)
            except RateLimitError as e:
                if attempt == self.max_attempts:
                    raise
                delay = min(e.retry_after + 1.0, self.retry_wait_cap)
                log.warning("%s rate limited (attempt %d) — retrying in %.0fs",
                            self.model, attempt, delay)
                await asyncio.sleep(delay)
            except (httpx.TimeoutException, httpx.TransportError) as e:
                if attempt == self.max_attempts:
                    raise
                log.warning("%s network error (attempt %d): %s — retrying",
                            self.model, attempt, e)
                await asyncio.sleep(2.0 * attempt)
            except EmptyResponseError:
                if attempt == self.max_attempts:
                    raise
                log.warning("%s empty response (attempt %d) — retrying", self.model, attempt)
        raise AssertionError("unreachable")

    async def health(self) -> bool:
        """Cheap reachability/auth probe against the provider."""
        try:
            async with httpx.AsyncClient(timeout=6, transport=self._transport) as c:
                r = await c.get(
                    f"{self.base_url}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
            return r.status_code < 500
        except httpx.HTTPError:
            return False

    async def _turn_once(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        on_text: OnText | None = None,
        max_tokens: int = 2048,
    ) -> LLMTurn:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": self.convert_messages(system, messages),
            "stream": True,
            "max_tokens": max_tokens,
            "temperature": 0,  # deterministic tool calling (esp. Llama on Groq)
        }
        if tools:
            payload["tools"] = self.convert_tools(tools)

        headers = {"Authorization": f"Bearer {self.api_key}"}
        text = ""
        finish_reason = ""
        usage_tokens = 0  # captured if the API reports it in the stream
        # tool-call fragments accumulate by stream index
        calls: dict[int, dict[str, Any]] = {}

        async with httpx.AsyncClient(timeout=180, transport=self._transport) as client:
            async with client.stream(
                "POST", f"{self.base_url}/chat/completions", json=payload, headers=headers
            ) as resp:
                if resp.status_code == 429:
                    body = (await resp.aread()).decode(errors="replace")
                    raise RateLimitError(_parse_retry_after(body))
                if resp.status_code >= 400:
                    body = (await resp.aread()).decode(errors="replace")[:500]
                    raise RuntimeError(f"LLM API error {resp.status_code}: {body}")
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    if chunk.get("usage"):  # some providers report token usage
                        usage_tokens = chunk["usage"].get("total_tokens", 0) or usage_tokens
                    choices = chunk.get("choices") or []
                    if not choices:
                        continue
                    choice = choices[0]
                    delta = choice.get("delta") or {}
                    if delta.get("content"):
                        text += delta["content"]
                        if on_text:
                            await on_text(text)
                    for tc in delta.get("tool_calls") or []:
                        slot = calls.setdefault(
                            tc.get("index", 0), {"id": "", "name": "", "arguments": ""}
                        )
                        if tc.get("id"):
                            slot["id"] = tc["id"]
                        fn = tc.get("function") or {}
                        if fn.get("name"):
                            slot["name"] = fn["name"]
                        if fn.get("arguments"):
                            slot["arguments"] += fn["arguments"]
                    if choice.get("finish_reason"):
                        finish_reason = choice["finish_reason"]

        turn = LLMTurn(text=text)
        # exact token count if the API reported it, else a rough estimate (~4 chars/token)
        turn.usage_tokens = usage_tokens or (len(text) // 4)
        if calls:
            turn.stop_reason = "tool_use"
            native_calls = []
            for i in sorted(calls):
                c = calls[i]
                call_id = c["id"] or f"call_{i}"
                try:
                    args = json.loads(c["arguments"]) if c["arguments"] else {}
                except json.JSONDecodeError:
                    args = {}
                turn.tool_calls.append({"id": call_id, "name": c["name"], "input": args})
                native_calls.append(
                    {
                        "id": call_id,
                        "type": "function",
                        "function": {"name": c["name"], "arguments": c["arguments"] or "{}"},
                    }
                )
            # native payload the agent round-trips back to us next turn
            turn.raw_content = {
                "role": "assistant",
                "content": text or None,
                "tool_calls": native_calls,
            }
        elif tools and "<function" in text:
            # provider emitted tool calls as text (Llama/Groq) — recover them
            names = {t["name"] for t in tools}
            parsed = _extract_text_tool_calls(text, names)
            if parsed:
                cleaned = _TEXT_TOOL_RE.sub("", text).strip()
                turn.text = cleaned
                turn.stop_reason = "tool_use"
                native_calls = []
                for i, pc in enumerate(parsed):
                    cid = f"txtcall_{i}"
                    turn.tool_calls.append({"id": cid, "name": pc["name"], "input": pc["input"]})
                    native_calls.append({
                        "id": cid, "type": "function",
                        "function": {"name": pc["name"], "arguments": json.dumps(pc["input"])},
                    })
                turn.raw_content = {
                    "role": "assistant",
                    "content": cleaned or None,
                    "tool_calls": native_calls,
                }
                return turn
            turn.stop_reason = "stop"
            turn.raw_content = {"role": "assistant", "content": text}
        else:
            turn.stop_reason = "stop" if finish_reason != "tool_calls" else "tool_use"
            turn.raw_content = {"role": "assistant", "content": text}

        # a truly empty turn (no text, no tool call) is useless — signal a retry
        if not turn.tool_calls and not turn.text.strip():
            raise EmptyResponseError(f"{self.model} returned an empty response")
        return turn


class FailoverProvider:
    """Ordered chain of providers: try the first healthy one, fall to the next.

    A provider that fails is put in a cooldown so subsequent messages skip it
    instead of re-paying its retries; it is re-tried once the cooldown lapses.
    The Telegram user never sees the switch.
    """

    FAILOVER_ERRORS = (
        RateLimitError, EmptyResponseError,
        httpx.TimeoutException, httpx.TransportError, RuntimeError,
    )
    NETWORK_COOLDOWN = 90.0

    def __init__(self, providers: list[tuple[str, Any]]):
        assert providers, "need at least one provider"
        self.providers = providers
        self._down_until: dict[str, float] = {}

    def _usable(self, name: str, now: float) -> bool:
        return now >= self._down_until.get(name, 0.0)

    def status(self) -> dict[str, Any]:
        now = time.monotonic()
        return {
            name: {"in_cooldown": not self._usable(name, now),
                   "cooldown_left_s": max(0, round(self._down_until.get(name, 0) - now))}
            for name, _ in self.providers
        }

    async def turn(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        on_text: OnText | None = None,
        max_tokens: int = 2048,
    ) -> LLMTurn:
        now = time.monotonic()
        candidates = [(n, p) for n, p in self.providers if self._usable(n, now)]
        if not candidates:  # everything cooling down — try them all anyway
            candidates = self.providers

        last_error: Exception | None = None
        for i, (name, provider) in enumerate(candidates):
            started = time.monotonic()
            try:
                turn = await provider.turn(system, messages, tools, on_text, max_tokens)
                self._down_until.pop(name, None)
                METRICS.record_success(name, (time.monotonic() - started) * 1000, turn.usage_tokens)
                return turn
            except self.FAILOVER_ERRORS as e:
                last_error = e
                METRICS.record_failure(name, f"{type(e).__name__}: {e}")
                cooldown = (
                    max(getattr(e, "retry_after", 0.0), 60.0)
                    if isinstance(e, RateLimitError)
                    else self.NETWORK_COOLDOWN
                )
                self._down_until[name] = time.monotonic() + cooldown
                if i + 1 < len(candidates):
                    log.warning("Provider %s failed (%s) — failing over to %s",
                                name, type(e).__name__, candidates[i + 1][0])
                else:
                    log.error("Provider %s failed (%s) — no fallback left", name, e)
        assert last_error is not None
        raise last_error


async def _ollama_reachable(settings: Settings) -> bool:
    if not settings.ollama_model:
        return False
    try:
        async with httpx.AsyncClient(timeout=3) as c:
            r = await c.get(f"{settings.ollama_url.rstrip('/')}/api/tags")
            return r.status_code == 200
    except httpx.HTTPError:
        return False


async def build_provider(settings: Settings) -> tuple[Any, str]:
    """Assemble the provider chain in priority order.

    One provider configured -> use it directly. Several -> FailoverProvider,
    so quota/network failures on the primary transparently fall to the next.
    """
    # each configured provider keyed by short name, then ordered by llm_priority
    available: dict[str, tuple[str, Any]] = {}

    if settings.anthropic_api_key:
        available["claude"] = (
            f"Claude ({settings.anthropic_model})", ClaudeProvider(settings)
        )
    if settings.gemini_api_key:
        available["gemini"] = (
            f"Gemini ({settings.gemini_model})",
            OpenAICompatProvider(
                "https://generativelanguage.googleapis.com/v1beta/openai",
                settings.gemini_api_key,
                settings.gemini_model,
            ),
        )
    if settings.groq_api_key:
        available["groq"] = (
            f"Groq ({settings.groq_model})",
            OpenAICompatProvider(
                "https://api.groq.com/openai/v1", settings.groq_api_key, settings.groq_model
            ),
        )
    if settings.openrouter_api_key:
        available["openrouter"] = (
            f"OpenRouter ({settings.openrouter_model})",
            OpenAICompatProvider(
                "https://openrouter.ai/api/v1",
                settings.openrouter_api_key,
                settings.openrouter_model,
            ),
        )
    if await _ollama_reachable(settings):
        available["ollama"] = (
            f"Ollama ({settings.ollama_model})",
            OpenAICompatProvider(
                f"{settings.ollama_url.rstrip('/')}/v1", "ollama", settings.ollama_model
            ),
        )

    order = [p.strip() for p in settings.llm_priority.split(",") if p.strip()]
    chain: list[tuple[str, Any]] = [available[k] for k in order if k in available]
    # append any configured providers not named in the priority list
    chain += [v for k, v in available.items() if k not in order]

    if not chain:
        raise RuntimeError(
            "No LLM configured. Free options:\n"
            "  • GEMINI_API_KEY  — free key at https://aistudio.google.com/apikey (recommended)\n"
            "  • GROQ_API_KEY    — free key at https://console.groq.com\n"
            "  • Ollama          — `brew install ollama && ollama pull llama3.1`, set OLLAMA_MODEL=llama3.1\n"
            "Or set ANTHROPIC_API_KEY for Claude. Add one to .env and restart."
        )

    # with a fallback available, don't let the primary burn long waits on 429s
    if len(chain) > 1:
        for _name, p in chain:
            if isinstance(p, OpenAICompatProvider):
                p.max_attempts = 2
                p.retry_wait_cap = 10.0

    # startup health log (non-fatal)
    for name, p in chain:
        if isinstance(p, OpenAICompatProvider):
            ok = await p.health()
            log.info("Provider health: %s -> %s", name, "ok" if ok else "UNREACHABLE")

    # always wrap in FailoverProvider so provider metrics are captured uniformly,
    # even with a single configured provider
    names = " → ".join(n for n, _ in chain)
    return FailoverProvider(chain), names
