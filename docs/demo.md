# Demo and acceptance runbook

## Current evidence boundary

The product code is implemented; final live acceptance and a public URL are pending. The historical Linux run used real Kind operations with mocked reasoning. The current screenshots and video are **local UI rehearsals with mocked Nemotron, Tavily, and Kubernetes**, not live results. Their visible banner and provenance manifest are intentional.

## Primary demonstration

Use the OOMKilled scenario for `payment-api`. The trusted manifest allocates 96 MiB under a 64 MiB limit. In local Kubernetes mode, expect previous termination `OOMKilled`, exit 137, and restarts. Do not teach the model a scenario-name diagnosis: the graph receives incident symptoms and collected evidence, not the scenario enum.

1. Prepare the healthy local Kind lab using [sandbox/README.md](../sandbox/README.md). Verify `kind-incidentzero` points to the loopback Kind API and select that context for developer shell scripts.
2. Configure root `.env` with `APP_ENV=local`, `EXECUTION_MODE=kubernetes`, `RUNS_ENABLED=true`, an accessible NVIDIA Nemotron model and Nebius key. Tavily credentials are needed only if reasoning requests research. Use one backend process.
3. Start backend/frontend using [development.md](development.md). Confirm `/health` and `/api/runtime`; keep keys and console headers out of the recording.
4. After provider quota is explicitly authorized, create the OOMKilled incident from `/dashboard`, open its detail, and start a run. This applies the controlled sandbox fault and makes real model requests.
5. Show incident symptoms, collected pod termination/resources/logs, timeline, diagnosis/confidence, conditional research, exact diff, named validation checks, terminal result, and RCA download. Do not force research solely for the video.
6. Reload the result to demonstrate persistence. Reset the lab healthy after acceptance. Never show a mocked browser fixture as a live run.

In hosted mode, call it a **simulation**: infrastructure evidence/configuration evaluation are simulated, real model reasoning is still required, and terminal success is `simulated`. That is useful product access without a visitor's cluster, but cannot substitute for local Kubernetes acceptance.

## Five consecutive OOM runs

The recorder is deliberately plan-only without flags:

```bash
# Repository root: no network, provider, or Kubernetes calls
PYTHONPATH=backend backend/.venv/bin/python -m scripts.record_golden_runs

# Only after credentials, cluster, running API, and quota authorization are ready
PYTHONPATH=backend backend/.venv/bin/python -m scripts.record_golden_runs \
  --execute --allow-provider-quota \
  --api-url http://127.0.0.1:8000 \
  --output artifacts/golden-path-results.json
```

The command checks the fixed Kind context, enabled runtime metadata, configured reasoning provider, no active run, and absence of the known browser fixture endpoint. It starts five sequential incidents and polls each to a bounded terminal state. Accepted results must be Kubernetes-mode `verified`, score 100, all nine named checks passing, one/two attempts, OOMKilled/137 evidence, a completion timestamp, and an RCA. It stops on a failed result and resets only after terminal API results.

Network interruption/polling timeout records an incomplete outcome and **does not reset into a possibly active worker**. Inspect its run ID and wait for/correct the terminal state before manual reset. Output intentionally omits raw provider errors, keys, kubeconfig, and full raw log payloads. The five API-reported passes are not independent proof of provider transport: retain server/provider evidence or an operator record of real configured calls. Do not run the command against fixtures or relabel fixture evidence.

`artifacts/` is ignored. Review/sanitize acceptance records before deliberately checking them into `docs/submission`. The committed acceptance template currently has zero accepted runs. Do not fill its rows with expected results.

## Reproducible rehearsal visuals

From `frontend/`, install Chromium or use an existing Chrome executable. A Playwright FFmpeg binary is used for local recording; no paid generation service is needed.

```bash
# The browser suite and production build must not run concurrently with capture.
PLAYWRIGHT_CHROMIUM_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
  npm run capture:submission
```

`backend/tests/submission_fixture.py` supplies mocked external boundaries to the real graph/persistence/API. Its source URL is an actual Kubernetes documentation page, but the search response and synthesis in this rehearsal are mocked. No live Tavily credit is consumed. Temporary isolated servers bind loopback and stop with Playwright. The existing database is not touched.

Capture produces eight 1440×960 (3:2) PNGs, an architecture PNG, an explicitly marked captioned silent WebM, a mocked RCA sample, and `docs/assets/capture-manifest.json`. `frontend/playwright.capture.config.ts` isolates the workflow from normal browser tests. The source script asserts the visible mock banner on every screenshot. The record is for review/rehearsal, not the final live submission video.

## Video storyboard (target 2:55; remain under 3:00)

| Time | Screen | Narration intent |
| --- | --- | --- |
| 0:00–0:15 | Landing/problem | Kubernetes evidence is scattered; show the operator problem without invented impact numbers. |
| 0:15–0:30 | Architecture | Name NVIDIA Nemotron, Nebius Token Factory, Tavily, Kubernetes, and LangGraph. |
| 0:30–0:50 | Incident creation | OOMKilled is the primary controlled failure; explain the read-only production boundary. |
| 0:50–1:20 | Evidence/timeline | Show real OOMKilled/137/resources/logs and the running graph. |
| 1:20–1:45 | Diagnosis/research | Inspect evidence-backed diagnosis; show attributable Tavily sources only if requested. |
| 1:45–2:15 | Diff/validation | Review the generated change and real local checks; include retry evidence if needed. |
| 2:15–2:40 | RCA/safety | Download RCA; distinguish a point-in-time sandbox pass from sustained stability. |
| 2:40–2:55 | Closing | State the exact verified boundary and current limitations; show real links only after available. |

The repository rehearsal is shorter and silent with on-screen captions. Record a final live take after acceptance, add consented narration if desired, inspect for keys/private data, verify duration, and upload to the required public video host only when authorized and connected. Do not claim that the current rehearsal is the final video.
