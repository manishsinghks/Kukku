import time

from app.search.file_search import FileSearch


def _add_file(db, store, path, name, content, file_type="document", mtime=None):
    db.upsert_file({
        "path": path, "name": name, "ext": "." + name.split(".")[-1],
        "size": len(content), "mtime": mtime or time.time(), "file_type": file_type,
        "status": "indexed", "chunks": 1, "error": None, "indexed_at": time.time(),
    })
    store.index_file(path, name, file_type, [content])


def test_filename_search_finds_exact(db, fake_store):
    _add_file(db, fake_store, "/d/resume_2026.pdf", "resume_2026.pdf", "cv content")
    _add_file(db, fake_store, "/d/notes.md", "notes.md", "random notes")
    fs = FileSearch(db, fake_store)
    results = fs.search("resume", search_type="filename")
    assert results and results[0].name == "resume_2026.pdf"


def test_semantic_search_finds_by_content(db, fake_store):
    _add_file(db, fake_store, "/p/bot.py", "bot.py", "telegram notification sender project", "code")
    _add_file(db, fake_store, "/p/game.py", "game.py", "pygame snake game", "code")
    fs = FileSearch(db, fake_store)
    results = fs.search("telegram notifications", search_type="semantic")
    assert results and results[0].path == "/p/bot.py"


def test_combined_match_ranks_higher(db, fake_store):
    # file matching both name AND content should beat name-only match
    _add_file(db, fake_store, "/a/docker_notes.md", "docker_notes.md", "docker compose failed with exit 1")
    _add_file(db, fake_store, "/b/docker_logo.png", "docker_logo.png", "just a logo image", "image")
    fs = FileSearch(db, fake_store)
    results = fs.search("docker failed", search_type="all")
    assert results[0].path == "/a/docker_notes.md"


def test_file_type_filter(db, fake_store):
    _add_file(db, fake_store, "/s/error_shot.png", "error_shot.png", "docker daemon failed error", "image")
    _add_file(db, fake_store, "/s/error_notes.md", "error_notes.md", "docker daemon failed error")
    fs = FileSearch(db, fake_store)
    results = fs.search("docker failed", file_type="image")
    assert results and all(r.file_type == "image" for r in results)


def test_recency_boost_orders_equal_matches(db, fake_store):
    now = time.time()
    _add_file(db, fake_store, "/old/report.pdf", "report.pdf", "quarterly report", mtime=now - 400 * 86400)
    _add_file(db, fake_store, "/new/report.pdf", "report.pdf", "quarterly report", mtime=now)
    fs = FileSearch(db, fake_store)
    results = fs.search("report", search_type="filename")
    assert results[0].path == "/new/report.pdf"


def test_search_is_logged(db, fake_store):
    fs = FileSearch(db, fake_store)
    fs.search("anything")
    assert db.recent_searches()[0]["query"] == "anything"


def test_search_cache_skips_second_lookup(db, fake_store):
    _add_file(db, fake_store, "/c/cached.md", "cached.md", "cache me")
    fs = FileSearch(db, fake_store)
    first = fs.search("cached")
    second = fs.search("cached")
    assert second is first  # served from cache, same object
    # cache hit must not double-log the search
    assert len([s for s in db.recent_searches() if s["query"] == "cached"]) == 1


def test_search_cache_distinguishes_params(db, fake_store):
    _add_file(db, fake_store, "/c/x.md", "x.md", "content")
    fs = FileSearch(db, fake_store)
    a = fs.search("x", search_type="filename")
    b = fs.search("x", search_type="semantic")
    assert a is not b
