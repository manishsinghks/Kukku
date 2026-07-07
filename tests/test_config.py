from app.config import Settings


def test_allowed_ids_parsing():
    s = Settings(allowed_user_ids="123, 456,abc, ,789")
    assert s.allowed_ids == {123, 456, 789}
    assert Settings(allowed_user_ids="").allowed_ids == set()


def test_index_paths_skips_missing(tmp_path):
    existing = tmp_path / "Docs"
    existing.mkdir()
    s = Settings(index_dirs=f"{existing},/definitely/not/a/dir")
    assert s.index_paths == [existing]


def test_data_dir_relative_resolves(tmp_path, monkeypatch):
    s = Settings(data_dir="./data")
    assert s.data_dir.is_absolute()


def test_defaults_sane():
    s = Settings()
    assert s.dashboard_host == "127.0.0.1"  # local-only by default
    assert s.max_file_size_mb > 0
