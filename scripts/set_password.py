#!/usr/bin/env python3
"""Set the dashboard login credentials — run locally, password never leaves your Mac.

    ./.venv/bin/python scripts/set_password.py

Prompts for a username and password (hidden input), stores the username + an
Argon2 hash in data/auth.json (chmod 600). The plaintext password is never
written anywhere.
"""
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.auth.service import AuthStore  # noqa: E402
from app.config import get_settings  # noqa: E402


def main() -> None:
    settings = get_settings()
    store = AuthStore(settings.auth_path)

    print("— Kukku Dashboard: set login credentials —")
    if store.is_configured():
        print(f"(An account already exists: {store.username}. This will overwrite it.)")

    username = input("Username: ").strip()
    if not username:
        print("✗ Username cannot be empty.")
        sys.exit(1)

    pw1 = getpass.getpass("Password: ")
    if len(pw1) < 8:
        print("✗ Password must be at least 8 characters.")
        sys.exit(1)
    pw2 = getpass.getpass("Confirm password: ")
    if pw1 != pw2:
        print("✗ Passwords do not match.")
        sys.exit(1)

    store.set_credentials(username, pw1)
    print(f"✓ Credentials saved for '{username}' → {settings.auth_path} (chmod 600).")
    print("  You can now log in on the dashboard.")


if __name__ == "__main__":
    main()
