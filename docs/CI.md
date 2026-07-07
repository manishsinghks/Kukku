# Continuous Integration

Kukku runs automated checks on **every push to `main`** and **every pull request**
targeting `main`, via GitHub Actions. A change is only "green" when all three jobs
pass — this keeps `main` releasable at all times.

Workflow: [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) ·
Live status: **Actions** tab, or the CI badge in the [README](../README.md).

---

## What CI runs

The workflow has three independent jobs that run in parallel:

| Job | Steps | Fails the build when… |
|---|---|---|
| **Python** (`python`) | Install Tesseract → `pip install -r requirements-dev.txt` → **ruff** → **pytest + coverage** | lint errors or any test fails |
| **Web** (`web`) | `npm ci` → **`tsc --noEmit`** → **`next build`** | a TypeScript or build error |
| **Docker** (`docker`) | `docker build` from the [`Dockerfile`](../Dockerfile) (no push) | the image fails to build |

Any failing step stops that job immediately (fail-fast). A newer run on the same
branch/PR automatically cancels the older one (`concurrency`), and the workflow
only has read permission on the repo (`permissions: contents: read`).

Coverage is uploaded as a `coverage-xml` build artifact on each Python run.

---

## Run the same checks locally

Before pushing, run exactly what CI runs. Everything is green when these are:

### Python
```bash
./.venv/bin/pip install -r requirements-dev.txt      # one-time / when deps change
./.venv/bin/ruff check app tests                     # lint (must be clean)
./.venv/bin/pytest --cov=app --cov-report=term-missing   # tests + coverage
```

### Web
```bash
cd web
npm ci                 # clean install from the lockfile (what CI uses)
npx tsc --noEmit       # TypeScript check
npm run build          # Next.js production build
```

### Docker (optional — needs a running Docker daemon)
```bash
docker build -t kukku:ci .
```

> Tip: `pytest -q` (no coverage) is faster for the inner loop; add `--cov` when you
> want the coverage report.

---

## Debugging a failed run

1. **Open the run** — the red ✗ on your commit/PR, or the **Actions** tab → the
   failed run → the failed job → expand the red step.
2. **Reproduce locally** with the matching command above. CI uses:
   - **Python 3.12** on Ubuntu, deps from `requirements-dev.txt`.
   - **Node 20** on Ubuntu, `npm ci` from `web/package-lock.json`.
3. **Common causes**
   | Symptom in CI | Likely cause & fix |
   |---|---|
   | `ruff` step fails | Lint violation — run `ruff check app tests` and fix (or `ruff check --fix`). |
   | A `pytest` test fails | Reproduce with `pytest tests/<file>::<test> -q`. Don't weaken the test to make it pass. |
   | `tsc` errors | A type error in `web/` — run `npx tsc --noEmit` in `web/`. |
   | `next build` fails | A build/runtime error — run `npm run build` in `web/` to see it. |
   | `npm ci` fails | `package.json` and `web/package-lock.json` are out of sync — run `npm install` and commit the updated lockfile. |
   | Docker step fails | Reproduce with `docker build .`; usually a bad `Dockerfile` layer or a missing file in the build context. |
4. **Dependency changes** — if you add a Python or npm dependency, commit the
   updated `requirements*.txt` / `web/package-lock.json` so CI installs it too.
5. **Re-run** — push the fix (CI re-runs automatically), or use **Re-run jobs** in
   the Actions UI for a flake.

---

## For maintainers

- Make CI a **required status check** for `main` in
  *Settings → Branches → Branch protection* so PRs can't merge red.
- Keep the badge and this doc in sync if job names change.
