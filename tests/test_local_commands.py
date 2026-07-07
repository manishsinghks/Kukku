from pathlib import Path
from unittest.mock import patch

from app.tools import local_commands
from app.tools.local_commands import CommandResult, execute


def test_unknown_action_rejected():
    res = execute("rm_rf_slash")
    assert not res.ok and "unknown action" in res.message


def test_destructive_requires_confirmation():
    for action in ("shutdown", "restart"):
        res = execute(action)
        assert not res.ok and res.needs_confirmation


def test_confirmed_destructive_runs_osascript():
    with patch.object(local_commands, "_run", return_value=CommandResult(True, "done")) as run:
        res = execute("shutdown", confirmed=True)
    assert res.ok
    assert run.call_args[0][0][0] == "osascript"


def test_open_folder_outside_home_rejected():
    res = execute("open_folder", target="/etc")
    assert not res.ok and "outside home" in res.message


def test_open_folder_traversal_rejected():
    res = execute("open_folder", target=str(Path.home() / ".." / ".." / "etc"))
    assert not res.ok


def test_open_folder_home_allowed():
    with patch.object(local_commands, "_run", return_value=CommandResult(True, "done")) as run:
        res = execute("open_folder", target="~")
    assert res.ok
    assert run.call_args[0][0] == ["open", str(Path.home().resolve())]


def test_open_folder_relative_name_resolves_to_home(tmp_path, monkeypatch):
    # a bare "Downloads" should mean ~/Downloads, not ./Downloads
    home = tmp_path
    (home / "Downloads").mkdir()
    monkeypatch.setattr(local_commands.Path, "home", classmethod(lambda cls: home))
    with patch.object(local_commands, "_run", return_value=CommandResult(True, "done")) as run:
        res = execute("open_folder", target="Downloads")
    assert res.ok
    assert run.call_args[0][0] == ["open", str((home / "Downloads").resolve())]


def test_open_vscode_missing_path():
    res = execute("open_vscode", target="/tmp/definitely-not-here-xyz")
    assert not res.ok


def test_open_chrome_adds_scheme():
    with patch.object(local_commands, "_run", return_value=CommandResult(True, "done")) as run:
        execute("open_chrome", target="example.com")
    assert run.call_args[0][0][-1] == "https://example.com"


def test_open_app_requires_name():
    assert not execute("open_app").ok


def test_open_file_outside_home_rejected():
    assert not execute("open_file", target="/etc/hosts").ok


def test_open_file_missing_rejected():
    assert not execute("open_file", target="~/definitely-not-a-real-file-xyz.txt").ok


def test_clipboard_roundtrip():
    r = execute("copy_to_clipboard", target="jarvis-unit-test")
    assert r.ok
    r = execute("read_clipboard")
    assert r.ok and r.message == "jarvis-unit-test"


def test_copy_to_clipboard_requires_text():
    assert not execute("copy_to_clipboard").ok
