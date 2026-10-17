# Development and freeze workflow

Start with `AGENTS.md`, the full [state of play](INCIDENTZERO_STATE_OF_PLAY.md), and [master plan](MASTER_BUILD_PLAN.md). The internal feature-complete deadline is October 25, 2026. The user explicitly advanced work into October 25 preparation while earlier live acceptance/deployment remain pending.

## Local setup

Python 3.12+ and Node 22.18+ or 24 are required. Docker, Kind, and kubectl are needed only for real local Kubernetes work. Tests and mocked visual capture do not require provider keys or a cluster.

```bash
cp .env.example .env
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements-dev.txt
cd frontend
npm install --no-audit --no-fund
```

Never commit `.env`. The backend loads the root file; the frontend needs its public API origin exported before build/dev when using a nondefault origin. The public API origin is not a secret. See `.env.example` and [deployment.md](deployment.md) for every setting and production validation.

```bash
# Terminal 1, repository root
backend/.venv/bin/uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000

# Terminal 2, frontend/
npm run dev
```

Use [sandbox/README.md](../sandbox/README.md) to create the lab. Starting a real product run mutates only the fixed local demo and consumes configured provider quota; do not start one merely to inspect the UI.

## Checks

```bash
# Repository root
backend/.venv/bin/python -m pytest backend -q
backend/.venv/bin/python -m pip check
backend/.venv/bin/python -m compileall -q backend/app backend/tests backend/scripts scripts deploy
git diff --check

# frontend/ (run sequentially)
npm run lint
npm run typecheck
npm test
npm run build
```

The inherited npm 11 optional sharp resolution prevents `npm ci` locally; `npm install` is the verified setup. Build prepares the standalone runtime and static assets. Start it with `HOSTNAME=127.0.0.1 PORT=3000 npm start`.

For browser checks install Playwright browsers, then run `npm run test:browser`. The local Firefox profile-launch issue is documented, not a passing result. Chromium and WebKit can be selected explicitly. Do not run the dev-server browser suite concurrently with a production build: they share `.next` output.

## Rehearsal visual capture

`npm run capture:submission` starts isolated mocked servers through the capture configuration and produces eight PNG screenshots, an architecture PNG export, a short captioned WebM rehearsal, and provenance metadata under `docs/assets`. It never reads a live run database or calls providers/Kubernetes. The fixture module is test-only and cannot be selected by the production API. See [demo.md](demo.md) for browser setup and exact capture command.

Generated rehearsal files are intentional versioned draft assets, not ignored test screenshots. Do not remove the visible mock banner for submission. Re-record the final video from a deliberately authorized live run after acceptance; keep drafts distinct.

## Five-run acceptance

Use `backend/scripts/record_golden_runs.py` as described in [demo.md](demo.md). It is plan-only by default; execution requires two deliberate flags, provider configuration, a local Kind context, and a real running API. Unit tests mock these boundaries and do not count as accepted live runs. Saved records distinguish an API-reported result from independently observed provider calls.

## Freeze and handoff

Do not introduce major features in this milestone. Address observed regressions, run affected checks, update the state of play in every change set, and retain truthful verification scope. Keep unrelated work intact. Use a separate branch and Conventional Commits. Do not commit/push/deploy/publish without the user's request.

The submission packet has a manifest, an article draft, Devpost fields, a storyboard, and explicit unresolved gates. Run `python3 scripts/check_submission.py` for local package integrity. Its release-readiness mode must fail while required live/deployment/publication evidence is absent. Passing package integrity only establishes that local files and labels are consistent.

Contributors can use the [collaborator guide](CODEX_COLLABORATOR_GUIDE.md). Git history currently records Rakshit Sharma and Aryan Sharma; reconcile team identities and submission roles with both contributors before publishing. Do not infer authorship roles or team consent from Git alone.
