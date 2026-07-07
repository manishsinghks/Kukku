import time


def test_conversation_history_roundtrip(db):
    db.add_message(1, "user", "hello")
    db.add_message(1, "assistant", "hi there")
    db.add_message(2, "user", "other chat")
    msgs = db.recent_messages(1)
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert msgs[0]["content"] == "hello"
    db.clear_history(1)
    assert db.recent_messages(1) == []
    assert len(db.recent_messages(2)) == 1


def test_history_limit_returns_most_recent(db):
    for i in range(30):
        db.add_message(1, "user", f"msg {i}")
    msgs = db.recent_messages(1, limit=5)
    assert len(msgs) == 5
    assert msgs[-1]["content"] == "msg 29"
    assert msgs[0]["content"] == "msg 25"  # chronological order preserved


def test_memory_and_aliases(db):
    mid = db.add_memory("likes dark mode")
    assert any(m["id"] == mid for m in db.list_memories())
    db.delete_memory(mid)
    assert db.list_memories() == []

    db.set_alias("My Resume", "/tmp/resume.pdf")
    assert db.get_alias("my resume") == "/tmp/resume.pdf"  # case-insensitive
    db.set_alias("my resume", "/tmp/resume-v2.pdf")  # upsert
    assert db.get_alias("MY RESUME") == "/tmp/resume-v2.pdf"
    assert len(db.list_aliases()) == 1


def test_file_upsert_and_search(db):
    meta = {
        "path": "/x/report.pdf", "name": "report.pdf", "ext": ".pdf", "size": 100,
        "mtime": time.time(), "file_type": "document", "status": "indexed",
        "chunks": 3, "error": None, "indexed_at": time.time(),
    }
    db.upsert_file(meta)
    meta["chunks"] = 5
    db.upsert_file(meta)  # upsert, not duplicate
    rows = db.search_files_by_name("report")
    assert len(rows) == 1 and rows[0]["chunks"] == 5
    db.remove_file("/x/report.pdf")
    assert db.get_file("/x/report.pdf") is None


def test_reminders_crud(db):
    now = time.time()
    rid = db.add_reminder(42, "call mom", now + 100, "once")
    assert db.list_reminders(42)[0]["text"] == "call mom"
    assert db.due_reminders(now) == []            # not due yet
    assert len(db.due_reminders(now + 200)) == 1  # now due
    # scoped cancel: wrong chat can't cancel
    assert db.deactivate_reminder(rid, 999) is False
    assert db.deactivate_reminder(rid, 42) is True
    assert db.list_reminders(42) == []


def test_reminder_reschedule(db):
    rid = db.add_reminder(42, "standup", time.time() - 5, "daily", "09:00")
    db.reschedule_reminder(rid, time.time() + 3600)
    assert db.list_reminders(42)[0]["due_ts"] > time.time()


def test_db_backup_is_valid(db, tmp_path):
    db.add_memory("keep me")
    dest = tmp_path / "backup.db"
    db.backup(dest)
    import sqlite3
    con = sqlite3.connect(dest)
    n = con.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    con.close()
    assert n == 1


def test_request_and_search_logging(db):
    db.log_request(42, "text", "hi", "hello", 120)
    db.log_search("resume", "all", ["/a", "/b"])
    assert db.recent_requests()[0]["user_id"] == 42
    s = db.recent_searches()[0]
    assert s["results_count"] == 2 and s["top_result"] == "/a"
    summary = db.stats_summary()
    assert summary["requests"] == 1 and summary["searches"] == 1
