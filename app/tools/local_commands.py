"""Allowlisted local (macOS) commands.

Only actions in ACTIONS can run — the LLM cannot execute arbitrary shell.
Destructive actions (shutdown / restart) additionally require the `confirmed`
flag, which the agent only sets after the user explicitly confirms in chat.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.utils.logging import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class CommandResult:
    ok: bool
    message: str
    needs_confirmation: bool = False


DESTRUCTIVE = {"shutdown", "restart"}
ACTIONS = {
    "open_vscode": "Open VS Code, optionally at a folder/file",
    "open_chrome": "Open Google Chrome, optionally at a URL",
    "open_folder": "Reveal a folder in Finder",
    "open_file": "Open a file with its default application",
    "open_app": "Open a macOS application by name",
    "read_clipboard": "Read the current clipboard text",
    "copy_to_clipboard": "Copy the given text to the clipboard",
    "lock_screen": "Lock the screen",
    "sleep": "Put the Mac to sleep",
    "shutdown": "Shut down the Mac (requires confirmation)",
    "restart": "Restart the Mac (requires confirmation)",
}


def _run(cmd: list[str], timeout: int = 15) -> CommandResult:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return CommandResult(False, f"command not found: {cmd[0]}")
    except subprocess.TimeoutExpired:
        return CommandResult(False, f"timed out: {' '.join(cmd)}")
    if proc.returncode != 0:
        return CommandResult(False, proc.stderr.strip() or f"exit code {proc.returncode}")
    return CommandResult(True, "done")


def _safe_path(target: str) -> Path | None:
    """Resolve a user-supplied path and require it to live under $HOME.

    Bare relative names ("Downloads", "Desktop/notes.txt") resolve against the
    home directory, not the process CWD — models sometimes emit them that way.
    """
    raw = Path(target).expanduser()
    if not raw.is_absolute():
        raw = Path.home() / raw
    p = raw.resolve()
    home = Path.home().resolve()
    if p == home or home in p.parents:
        return p
    return None


def execute(action: str, target: str = "", confirmed: bool = False) -> CommandResult:
    action = action.strip().lower()
    if action not in ACTIONS:
        return CommandResult(False, f"unknown action '{action}'. Allowed: {', '.join(ACTIONS)}")
    if action in DESTRUCTIVE and not confirmed:
        return CommandResult(
            False,
            f"'{action}' needs explicit confirmation from the user first.",
            needs_confirmation=True,
        )
    log.info("local command: %s target=%r confirmed=%s", action, target, confirmed)

    if action == "open_vscode":
        if target:
            p = _safe_path(target)
            if p is None or not p.exists():
                return CommandResult(False, f"path not found or outside home: {target}")
            return _run(["open", "-a", "Visual Studio Code", str(p)])
        return _run(["open", "-a", "Visual Studio Code"])

    if action == "open_chrome":
        if target:
            if not target.startswith(("http://", "https://")):
                target = "https://" + target
            return _run(["open", "-a", "Google Chrome", target])
        return _run(["open", "-a", "Google Chrome"])

    if action == "open_folder":
        p = _safe_path(target or "~")
        if p is None or not p.is_dir():
            return CommandResult(False, f"folder not found or outside home: {target}")
        return _run(["open", str(p)])

    if action == "open_file":
        p = _safe_path(target)
        if p is None or not p.is_file():
            return CommandResult(False, f"file not found or outside home: {target}")
        return _run(["open", str(p)])

    if action == "open_app":
        if not target:
            return CommandResult(False, "app name required")
        # `open -a` only launches installed apps; no shell interpolation happens
        return _run(["open", "-a", target])

    if action == "read_clipboard":
        try:
            out = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=5)
        except (OSError, subprocess.TimeoutExpired) as e:
            return CommandResult(False, f"pbpaste failed: {e}")
        content = out.stdout.strip()
        return CommandResult(True, content[:3000] if content else "(clipboard is empty)")

    if action == "copy_to_clipboard":
        if not target:
            return CommandResult(False, "text required")
        try:
            subprocess.run(["pbcopy"], input=target, text=True, timeout=5, check=True)
        except (OSError, subprocess.SubprocessError) as e:
            return CommandResult(False, f"pbcopy failed: {e}")
        return CommandResult(True, "copied")

    if action == "lock_screen":
        # macOS lock via the SACLockScreenImmediate call isn't scriptable;
        # ctrl+cmd+q equivalent: use the login window's lock
        return _run([
            "osascript", "-e",
            'tell application "System Events" to keystroke "q" using {control down, command down}',
        ])

    if action == "sleep":
        return _run(["pmset", "sleepnow"])

    if action == "shutdown":
        return _run(["osascript", "-e", 'tell app "System Events" to shut down'])

    if action == "restart":
        return _run(["osascript", "-e", 'tell app "System Events" to restart'])

    return CommandResult(False, "unreachable")
