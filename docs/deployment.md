# October 24 deployment and polish

Status: application/packaging prepared locally. No public service or URL has been created. Hosting credentials, confirmed free capacity/credits, and deliberate authorization for provider quota remain necessary. Live October 23 UI-to-Kind acceptance is still pending.

## Hosting and hackathon credits

The user prefers existing hosting or hackathon credits. The supplied event is the [Nebius x NVIDIA Global AI Hackathon](https://nebiusglobalaihackathon.devpost.com/). Its [official FAQ](https://nebiusglobalaihackathon.devpost.com/details/faqs) says published promotional credits cover Token Factory rather than a separate AI Cloud compute grant, and that the rest of an application can be hosted elsewhere when the required NVIDIA model runs through Token Factory. This does not establish which credits or compute the user's account actually has. Confirm available credits before provisioning any paid service; personal spend must remain ₹0.

The repository supports two ordinary application services: Python/FastAPI and Node/Next.js. Use the Dockerfiles with existing credited compute, or the optional `render.yaml` free-tier fallback. Render's [free-tier documentation](https://render.com/docs/free) describes idle spin-down, cold starts, shared instance-hour allowances, and ephemeral local files. No persistent paid disk or paid plan is requested in the blueprint. Public deployment still requires an authenticated hosting account. `render.yaml` uses the current [Blueprint specification](https://render.com/docs/blueprint-spec); its YAML is locally parsed, not validated by a live Render deployment.

## Modes and truthful results

- `EXECUTION_MODE=kubernetes`: local Kind path, real evidence collection, controlled allow-listed writes, bounded two-attempt verification. Keep this mode local.
- `EXECUTION_MODE=simulation`: no kubectl or Docker calls. Controlled manifests produce explicitly simulated pods/events/logs. Real Nemotron calls generate diagnosis and remediation; Tavily is used only when requested by reasoning. The real patch policy validates generated changes, and configuration evaluation determines whether the modeled fault remains. It is not a real rollout, log check, or HTTP health check.

A successful simulation has terminal status `simulated`, displayed as **Simulation passed**. It never increments the dashboard's Kubernetes **Verified fixes** metric. UI banners, validation checks, persisted results, and RCA state that infrastructure is simulated. A failed or insufficient patch fails evaluation and can use the existing bounded retry; no diagnosis is hard-coded into the production simulation adapter. Mocked model responses exist only in tests.

## Public environment

| Variable | Deployment value |
| --- | --- |
| `APP_ENV` | `production` |
| `EXECUTION_MODE` | `simulation` |
| `CORS_ORIGINS` | Exact frontend HTTPS origin, with no trailing slash, path, wildcard, or query |
| `RUNS_ENABLED` | `false` until provider quota is deliberately authorized |
| `DEMO_RUN_TOKEN` | Random 24+ character code shared only with demo operators/judges |
| `DAILY_RUN_LIMIT` | 1–100 accepted starts per UTC day; default 20, failed runs count |
| `NEBIUS_API_KEY` | Server-side hosting secret; do not expose in frontend variables |
| `NEBIUS_MODEL` | A Nemotron model actually accessible through the account |
| `NEBIUS_TIMEOUT_SECONDS` | Bounded inference timeout in seconds; must be between 5 and 120 |
| `TAVILY_API_KEY` | Server-side secret required only for research-requesting runs |
| `DATABASE_PATH` | Writable local SQLite file; one instance and one worker |
| `STORAGE_EPHEMERAL` | `true` if the host discards local disk on restart/redeploy |
| `NEXT_PUBLIC_API_URL` | Backend public HTTPS origin, set **before the frontend build** |

Missing/invalid production CORS, non-HTTPS provider endpoints, public Kubernetes execution, and enabled production writes without an adequate access code fail startup. Runs default to paused if `RUNS_ENABLED` is omitted in production. Root `.env.example` is a **local-development** template; do not deploy it wholesale because it selects local Kind and enables local runs.

`GET /api/runtime` exposes execution mode, paused/access-code state, provider-configured boolean, storage lifetime, and daily start limit, never keys or the code. Public reads contain only controlled demo data. Both mutation endpoints require `X-Demo-Run-Token` when configured. The UI's code field saves it in session storage for the tab; SSE and export URLs never include it. CORS is not authentication. This is a small demo gate, not enterprise identity/RBAC.

The daily count is stored in SQLite. It resets if the host discards the database, so it is not an account-level spending guarantee. Use provider-side account quotas and keep runs paused when not needed. Neither viewing the site nor the read-only smoke script performs an inference call. If judging needs a code, include it in private testing instructions, not the public repository.

## Container preparation

From the repository root:

```bash
# Starts a local containerized simulation with runs paused; requires Docker.
docker compose up --build
```

The Compose ports bind to loopback. It uses a named volume for local history. No kubeconfig, Docker socket, provider credentials, or root `.env` is copied into either image. Provider secrets are runtime environment values. Backend/frontend processes run as non-root. The frontend build uses `npm install` because the inherited optional sharp override currently prevents `npm ci` on local npm 11.19.0.

Dockerfiles and Compose were prepared and parsed but cannot be built/run in the current checkout because Docker is unavailable. The equivalent Python app, Node production build, and standalone Node start are checked locally where available; do not describe that as a container smoke test.

For existing credited container hosting, build both images from the repository root using `deploy/backend.Dockerfile` and `deploy/frontend.Dockerfile`. Set the frontend build argument `NEXT_PUBLIC_API_URL` to the backend HTTPS origin. Backend listens on 8000; frontend listens on 3000. Supply TLS via the host's normal HTTPS routing. Keep one backend replica. Provide a writable volume if covered by existing credits; otherwise label storage ephemeral and expect history loss.

## Optional Render fallback

1. Authenticate/connect a Render account with repository access. Use the branch containing this change, or merge it after review. The deployment-preparation implementation was merged into `main` by PR #3 (`4594d42`). The freeze/submission branch adds documentation and rehearsal assets; use its reviewed/merged revision when ready.
2. Create the two services from `render.yaml`, verifying both explicitly remain on `free` and that the account's shared free instance-hour allowance is available. Never accept a paid upgrade to resolve a deployment failure.
3. Enter the frontend's exact public HTTPS origin as backend `CORS_ORIGINS`; enter the backend's public HTTPS origin as frontend `NEXT_PUBLIC_API_URL`. Confirm the generated secret code exists. Provide provider keys through hosting secrets.
4. Deploy with runs **paused**. Inspect startup logs and `/health`, `/api/runtime`, `/dashboard`, and all assets. Cold starts can exceed an initial UI request timeout; the runtime notice retries without an endless spinner.
5. Only after provider quota is authorized, set `RUNS_ENABLED=true`, set `NEBIUS_MODEL` if needed, give operators the demo code, and run the controlled demo. Confirm simulation labels on the UI and downloaded RCA.
6. Set runs paused again when finished. Record the actual returned deployment URLs and checks in the state of play.

Manual build/start equivalents:

```bash
# API (repo root; inject production settings and secrets through the host)
pip install -r backend/requirements.txt
uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port "$PORT" --workers 1 --no-access-log

# Frontend (frontend/; NEXT_PUBLIC_API_URL must already be set)
npm install --no-audit --no-fund
npm run build
HOSTNAME=0.0.0.0 npm start
```

`npm run build` prepares Next's standalone runtime and static assets. The backend health check is `/health`. Streaming proxies must preserve `text/event-stream`, avoid response buffering, and allow SSE idle heartbeats. The browser also polls durable events as a fallback. Deploy/restart can terminate an in-flight hosted run; restart recovery works when the same database survives. Ephemeral disks cannot retain recovery evidence across replacement.

## Logs and acceptance

Application events are JSON objects containing UTC timestamp, incident ID, run ID, node, event, duration in milliseconds, and status. Stage duration starts when that stage begins; the final duration covers the run. Logging accepts only these metadata fields, never prompts, evidence, sources, raw exceptions, authorization headers, or keys. Backend access logging is disabled by the hosted command.

Read-only deployed checks:

```bash
python3 deploy/check_public.py --frontend https://YOUR_FRONTEND --backend https://YOUR_BACKEND
```

Then verify CORS in a real browser, paused and wrong-code states, a deliberately authorized model run, conditional research where needed, SSE reconnection, per-run simulation labels, patch review, terminal status, Markdown download, mobile layout, and persisted reload. Record the hosting account/plan confirmation, exact URL, provider boundary, and storage lifetime. Check judges' ability to access the demo with supplied instructions. No public deployment or live integration claim is complete until those checks actually pass.

Cross-browser smoke tests use only the isolated mocked backend fixture. From `frontend/`, install test browsers with `npx playwright install chromium firefox webkit` and run `npm run test:browser`. For an existing Chrome installation set `PLAYWRIGHT_CHROMIUM_EXECUTABLE`. Keep production builds and browser tests sequential because the development test server and build use the same `.next` directory. Current local Firefox has a temporary-profile startup problem before any page loads; Chromium and WebKit checks can be run with `--project=chromium --project=webkit` while Firefox remains a documented environment limitation.
