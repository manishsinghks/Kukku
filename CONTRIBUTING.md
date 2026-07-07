# Contributing to Kukku

Thanks for your interest in improving Kukku! This project is a personal AI
assistant with a Telegram bot and a web dashboard sharing one Python backend.
Contributions of all sizes are welcome.

## Ground rules

- Be respectful and constructive.
- Keep changes focused — one logical change per pull request.
- Never commit secrets. `.env`, `data/`, and credentials are git-ignored; keep
  it that way. See [SECURITY.md](docs/SECURITY.md).

## Development setup

```bash
git clone <your-fork-url> Kukku
cd Kukku
./scripts/start.sh                       # creates .venv + installs deps on first run
cp .env.example .env                      # then fill in a bot token + one LLM key
./.venv/bin/pip install -r requirements-dev.txt
```

Web dashboard (optional):

```bash
cd web && npm install && npm run dev      # http://localhost:3000
```

## Before you open a PR

Run the full checks locally — they must be green:

```bash
./.venv/bin/pytest                        # all tests must pass
./.venv/bin/ruff check app tests          # lint must be clean
cd web && npm run build                   # dashboard must build (if you touched web/)
```

## Coding conventions

- **Python**: follow the existing style; `ruff` enforces it (`line-length = 100`).
  Prefer clear, small functions. New code should match the surrounding module.
- **Architecture**: dependencies flow downward — `bot → agent → tools → db`.
  Never import a higher layer from a lower one (e.g. `db` must not import `agent`).
  See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
- **New tools/features**: see [docs/EXTENDING.md](docs/EXTENDING.md) for the
  shared-backend pattern (a change to the agent benefits both Telegram and the
  dashboard automatically).
- **Tests**: add or update tests under `tests/` for any behavior change.

## Commit messages

Use clear, imperative subject lines (e.g. "Add PWA manifest to dashboard").
Reference an issue number when relevant.

## Reporting bugs / requesting features

Open a GitHub issue with:
- What you expected vs. what happened
- Steps to reproduce (and relevant `data/logs/` lines with secrets removed)
- Your OS and Python/Node versions

## Reporting security issues

**Do not** open a public issue for vulnerabilities. Follow the process in
[docs/SECURITY.md](docs/SECURITY.md#reporting-a-vulnerability).
