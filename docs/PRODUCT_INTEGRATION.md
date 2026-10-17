# Local product integration

The product UI at `/dashboard` uses the persisted FastAPI workflow. `/incidents` lists demo incidents and `/runs` lists execution history. No customer or production metrics are seeded. The landing-page workflow card is explicitly a preview.

## Run locally

1. Create the Kind lab as described in `sandbox/README.md`.
2. Copy `.env.example` to `.env`. Set `NEBIUS_API_KEY` and the accessible `NEBIUS_MODEL`. Set `TAVILY_API_KEY` for runs that request research. Never commit credentials.
3. Start the backend from `backend/` with `.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000`. Use **one worker and one API instance** for this local sandbox. A database file lease rejects a second process using the same database; do not run different database files against the same sandbox concurrently.
4. Start the frontend from `frontend/` with `npm run dev`. Node 22.18+ or Node 24 is needed for `npm test` (native TypeScript stripping).
5. Open `http://localhost:3000/dashboard`, create the recommended OOMKilled incident, then choose **Start agent run** on its detail page.

Creating an incident only saves its metadata. Starting its run applies the selected fault to `kind-incidentzero` / `incidentzero-demo` / `payment-api` and uses configured provider quota. The API performs no provider requests automatically at startup. Missing Nebius credentials fail before any sandbox mutation. Tavily is conditional; missing Tavily credentials fail clearly if research is requested.

Keep Kubernetes execution local. The October 24 deployment preparation adds a distinct public simulation mode with an access code, pause control, daily run-start limit, and honest simulation labels. Follow [deployment instructions](deployment.md); do not expose the local Kubernetes configuration publicly.

The backend defaults to `backend/data/incidentzero.sqlite3` (ignored by Git). `DATABASE_PATH` optionally selects another persistent local file. `KUBECTL_BIN` selects the local kubectl binary. The frontend uses `NEXT_PUBLIC_API_URL`; set it before building the frontend. Backend CORS uses `CORS_ORIGINS`.

## Execution and safety

A SQLite transaction allows only one queued/running execution across all incidents. Conflicting starts return HTTP 409. All demo preparation and graph execution run in a worker thread with its own async loop, leaving the API event loop responsive. Every Kubernetes invocation uses fixed arguments, an explicit context, request deadlines, and `shell=False`.

Demo preparation reuses the verifier's HTTPS loopback Kind-context guard. The scenario path comes only from the three-value enum. Preparation waits for previous pods to disappear and for the newly created workload to show the selected fault. The model receives incident/evidence, never the scenario enum. The existing remediation policy and maximum of two attempts remain unchanged.

Run updates, named timeline events, results, and incident status persist to SQLite. Terminal status, error, and `run.completed` commit together. On restart, any queued/running history becomes a failed interrupted run, retaining its last saved evidence. Shutdown waits for bounded operations to finish; it does not release the sandbox lock while a write might still be running.

Errors sent to the UI are sanitized; raw provider exceptions and subprocess stderr are not persisted. If the database itself is unavailable, REST returns 503 and a connected stream emits `stream.error`. The browser displays errors and retries saved progress reads instead of relying solely on the stream. A database outage cannot durably save a failure until storage works again; restart recovery then handles interrupted runs.

RCA generation renders validated model conclusions and Kubernetes validation evidence. It adds no model request, invented production impact, or claimed sustained stability. The diff compares the proposed strategic-merge fields with their collected values; it is not a full Deployment replacement.

## HTTP surface

| Method | Path | Behavior |
| --- | --- | --- |
| POST | `/api/incidents/demo/{scenario}` | Save `oomkilled`, `crashloop`, or `readiness` incident; 201 |
| GET | `/api/incidents` | Newest incidents first |
| GET | `/api/incidents/{id}` | Incident and latest run status |
| POST | `/api/incidents/{id}/run` | Start persisted background execution; 202 or 409 |
| GET | `/api/runs` | Newest runs first |
| GET | `/api/runs/{id}` | Status, partial/final evidence and results |
| GET | `/api/runs/{id}/events?after=0` | Ordered durable events after a cursor |
| GET | `/api/runs/{id}/stream?after=0` | SSE replay followed by live events |
| GET | `/api/runs/{id}/report` | Markdown RCA attachment; 409 until available |

Unknown IDs return 404; unsupported scenarios return 422. SSE uses monotonic event IDs and supports `Last-Event-ID` on reconnect. Event names include `context.started`, `diagnosis.completed`, `remediation.generated`, `validation.check`, `run.error`, and `run.completed`. Consumers must close on `run.completed`; the server closes terminal streams after replaying all saved events. Heartbeat comments prevent silent idle streams. The UI merges SSE and periodic REST history by event ID so reconnects do not duplicate timeline entries.

## Verification boundaries

Deterministic integration tests use mocked provider and Kubernetes boundaries while running the real graph, persistence, API worker, and SSE replay. Demo-controller tests verify context refusal, fixed command arguments, stale-pod exclusion, all three fault predicates, and bounded waiting. Frontend tests verify history metrics, terminal states, and event deduplication. These tests do not establish live provider access or live Kubernetes behavior on this machine. A live UI → provider → Kind acceptance run remains required before calling the milestone live-accepted. Hosted simulation does not replace that acceptance.

## Browser smoke tests

From `frontend/`, run `npm run test:browser` after installing a Playwright Chromium browser (`npx playwright install chromium`), or set `PLAYWRIGHT_CHROMIUM_EXECUTABLE` to an existing compatible Chrome executable. The test starts isolated local servers on ports 3100/8100 and a fresh temporary SQLite database. The backend fixture exists only under `backend/tests/ui_fixture.py`; it supplies explicitly mocked results and never calls providers or Kubernetes. It is not selectable from the production app. Browser checks cover incident creation, background start, evidence/diagnosis/diff/validation, report download, persisted reload, mobile navigation, and terminal failure with the SSE connection blocked. Servers are stopped by Playwright on exit. The suite now includes simulation labeling, mutation pause, code entry, mobile landing layout, and Chromium/Firefox/WebKit projects; see `docs/deployment.md` for browser installation and the local Firefox startup limitation. Temporary databases remain under `/tmp/incidentzero-ui.*` and are safe to remove after tests.

Known local tooling issue: npm 11.19.0 rejects `npm ci` because the existing optional sharp peer/override lacks a resolved lock entry (`Missing: sharp@`). `npm install --no-audit --no-fund` and all subsequent frontend checks work. This pre-existing lock-resolution issue remains to be fixed separately. After a failed live demo, use `sandbox/scripts/reset.sh` to restore the healthy lab before continuing.
