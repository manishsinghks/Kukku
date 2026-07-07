"""Agent loop tests with a scripted fake LLM provider — no network, no API key."""
from __future__ import annotations

import asyncio

import pytest

from app.config import Settings
from app.core.agent import Agent, AgentReply
from app.core.llm import LLMTurn
from app.search.file_search import FileSearch


class ScriptedProvider:
    """Returns pre-scripted turns; records what it was called with."""

    def __init__(self, turns: list[LLMTurn]):
        self.turns = list(turns)
        self.calls: list[dict] = []

    async def turn(self, system, messages, tools, on_text=None, max_tokens=2048):
        self.calls.append({"system": system, "messages": messages})
        turn = self.turns.pop(0)
        if on_text and turn.text:
            await on_text(turn.text)
        return turn


@pytest.fixture()
def agent_env(db, fake_store, tmp_path):
    settings = Settings(data_dir=tmp_path / "data", index_dirs=str(tmp_path))
    search = FileSearch(db, fake_store)

    def make(turns):
        return Agent(settings, db, search, ScriptedProvider(turns))

    return make, db, fake_store


def test_plain_answer(agent_env):
    make, db, _ = agent_env
    agent = make([LLMTurn(text="Paris is the capital of France.")])
    reply = asyncio.run(agent.run(1, "capital of france?"))
    assert "Paris" in reply.text
    # history + request log persisted
    assert len(db.recent_messages(1)) == 2
    assert db.recent_requests()[0]["kind"] == "text"


def test_agent_publishes_events_for_sync(agent_env):
    """The real agent must broadcast user + assistant messages so the dashboard
    stays in sync with Telegram (and carry the source + provider)."""
    from app.core.events import EVENTS

    make, _, _ = agent_env
    agent = make([LLMTurn(text="Hi there")])

    async def run():
        q = EVENTS.subscribe()
        try:
            await agent.run(7, "hello", source="dashboard")
            events = [q.get_nowait() for _ in range(q.qsize())]
        finally:
            EVENTS.unsubscribe(q)
        return events

    events = asyncio.run(run())
    roles = [(e["role"], e["source"]) for e in events if e.get("type") == "message"]
    assert ("user", "dashboard") in roles
    assert ("assistant", "dashboard") in roles


def test_tool_loop_search_then_answer(agent_env):
    make, db, store = agent_env
    store.index_file("/d/resume.pdf", "resume.pdf", "document", ["my resume content"])
    db.upsert_file({
        "path": "/d/resume.pdf", "name": "resume.pdf", "ext": ".pdf", "size": 10,
        "mtime": 0, "file_type": "document", "status": "indexed", "chunks": 1,
        "error": None, "indexed_at": 0,
    })
    tool_turn = LLMTurn(
        stop_reason="tool_use",
        tool_calls=[{"id": "t1", "name": "search_files", "input": {"query": "resume"}}],
        raw_content=[{"type": "tool_use", "id": "t1", "name": "search_files", "input": {}}],
    )
    final_turn = LLMTurn(text="Found your resume at /d/resume.pdf")
    provider_agent = make([tool_turn, final_turn])
    reply = asyncio.run(provider_agent.run(1, "find my resume"))
    assert "resume" in reply.text
    # the second LLM call must include a tool_result message
    second_call = provider_agent.provider.calls[1]
    roles = [m["role"] for m in second_call["messages"]]
    assert roles[-1] == "user"
    assert second_call["messages"][-1]["content"][0]["type"] == "tool_result"


def test_send_file_collects_files(agent_env, tmp_path):
    make, _, _ = agent_env
    f = tmp_path / "doc.txt"
    f.write_text("hi")
    turns = [
        LLMTurn(
            stop_reason="tool_use",
            tool_calls=[{"id": "t1", "name": "send_file", "input": {"path": str(f)}}],
            raw_content=[],
        ),
        LLMTurn(text="Sent!"),
    ]
    reply: AgentReply = asyncio.run(make(turns).run(1, "send me doc.txt"))
    assert reply.files_to_send == [f]


def test_send_missing_file_reports_error(agent_env):
    make, _, _ = agent_env
    turns = [
        LLMTurn(
            stop_reason="tool_use",
            tool_calls=[{"id": "t1", "name": "send_file", "input": {"path": "/nope.txt"}}],
            raw_content=[],
        ),
        LLMTurn(text="Couldn't find it."),
    ]
    reply = asyncio.run(make(turns).run(1, "send"))
    assert reply.files_to_send == []


def test_memory_tool_persists(agent_env):
    make, db, _ = agent_env
    turns = [
        LLMTurn(
            stop_reason="tool_use",
            tool_calls=[{"id": "t1", "name": "save_memory", "input": {"content": "birthday is June 1"}}],
            raw_content=[],
        ),
        LLMTurn(text="Remembered."),
    ]
    asyncio.run(make(turns).run(1, "remember my birthday is June 1"))
    assert any("June 1" in m["content"] for m in db.list_memories())
    # and it shows up in the next system prompt
    agent2 = make([LLMTurn(text="ok")])
    asyncio.run(agent2.run(1, "hi"))
    assert "June 1" in agent2.provider.calls[0]["system"]


def test_destructive_command_blocked_without_confirmation(agent_env):
    make, _, _ = agent_env
    turns = [
        LLMTurn(
            stop_reason="tool_use",
            tool_calls=[{"id": "t1", "name": "run_local_command",
                         "input": {"action": "shutdown"}}],
            raw_content=[],
        ),
        LLMTurn(text="Please confirm you want to shut down."),
    ]
    agent = make(turns)
    asyncio.run(agent.run(1, "shut down my laptop"))
    tool_result = agent.provider.calls[1]["messages"][-1]["content"][0]["content"]
    assert "BLOCKED" in tool_result


def test_max_rounds_terminates(agent_env):
    make, _, _ = agent_env
    looping = LLMTurn(
        stop_reason="tool_use",
        tool_calls=[{"id": "t", "name": "system_status", "input": {}}],
        raw_content=[],
    )
    agent = make([looping] * 20)
    reply = asyncio.run(agent.run(1, "loop forever"))
    assert reply.text  # terminated with some text, no exception
    assert len(agent.provider.calls) <= 9
