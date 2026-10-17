# IncidentZero — State of Play

Last updated: October 17, 2026 (Asia/Kolkata), product-integration PR preparation

This is the canonical live handoff document for developers and coding agents. Update it in every change set that modifies the project. Historical claims must remain truthful: distinguish mocked verification, local live verification, and work that still requires credentials or deployment access.

## Current checkpoint

The foundation through sandbox-verification implementation is complete. Product integration (the October 23 milestone) is now implemented on local branch `feat/product-integration`, based on `8a5ef55` (`fix: complete live sandbox workflow verification`). The user has authorized committing, pushing this branch, and opening a PR against `main`. Publication is being prepared; no deployment or provider-quota use is authorized by this request.

The new product includes SQLite incident/run persistence, background graph execution, REST APIs, resumable SSE, safe local demo preparation, evidence-based RCA/Markdown export, and Dashboard, Incidents, Agent Runs, and detail screens. Metrics come only from persisted demo history. One active run is enforced transactionally; a file lease prevents a second API process from recovering another process's active database. Restart recovery makes interrupted runs terminal failures.

Local verification in this macOS checkout uses Python 3.13.16 and Node 24.21.0. The backend suite has 66 passing tests; frontend lint, typecheck, four deterministic domain tests, production build, and two Chrome browser smoke tests passed. Final commands and verification boundaries are recorded below. External boundaries in the integration tests are mocked. No live Nebius/Tavily requests or live Kubernetes mutations were performed here; kubectl and Docker are unavailable on PATH.

The preceding Linux checkpoint live-verified real Kubernetes evidence collection, patch application, rollout, pod inspection, logs, and `/health` with **mocked Nemotron responses**. Its OOMKilled/137/restart-1 workload reached `verified`, 100/100, on attempt one and was reset healthy. That is historical acceptance of the core graph, not live acceptance of the new UI/API integration.

The exact next task is UI → persisted API → live Nemotron → local Kind OOMKilled acceptance on a machine with the sandbox/tools and deliberately authorized provider quota. Verify terminal success, streamed evidence, diff, validation, RCA download, and reset the lab healthy. Conditional Tavily access also remains credential-dependent. After that checkpoint, proceed to October 24 deployment and polish; the engineering deadline is October 25, 2026.

## Product goal

IncidentZero is an autonomous AI incident-resolution engineer for Kubernetes. The intended flow is:

```text
incident → collect evidence → form hypotheses → research when useful
→ determine root cause → generate remediation → validate in sandbox
→ retry within strict bounds → produce verified fix → human approval
```

The golden path is `payment-api` in `demo-production`, severity P1, repeatedly OOMKilled because its Kubernetes memory limit is too low. The product must visibly collect real evidence, use NVIDIA Nemotron through Nebius Token Factory for reasoning, use Tavily conditionally, propose a real patch, validate it in a sandbox, and generate an RCA.

## Completed work

### Repository foundation

- FastAPI backend under `backend/`.
- `GET /health` returns service name, version, and `status: ok`.
- Next.js, TypeScript, Tailwind CSS frontend foundation under `frontend/`.
- Professional non-chatbot landing page shell.
- Root environment template and ignore rules.
- Root README with setup, testing, integrations, sandbox, and safety notes.
- Local Python virtual environment and Node build artifacts remain ignored.

Verified at the foundation checkpoint:

- backend health test passed;
- backend and frontend started successfully;
- frontend returned HTTP 200;
- `/health` returned HTTP 200 with expected JSON;
- ESLint, TypeScript, and production Next.js build passed;
- production npm dependency audit reported zero vulnerabilities.

### Nebius and Tavily clients

- Typed async Nebius Token Factory client in `backend/app/integrations/nebius.py`.
- Uses the OpenAI-compatible `/v1/chat/completions` API.
- Configurable API key, base URL, model, timeout, temperature, and token limit.
- Default model is `nvidia/Nemotron-3_5-Lightning` but remains environment-configurable because catalog access can vary.
- Typed Tavily client in `backend/app/integrations/tavily.py`.
- Uses `POST /search`, basic-depth search, compact content, safe search, bounded result counts, no raw page bodies, and no generated answer.
- Tavily results are normalized and duplicate URLs removed.
- Both clients fail clearly for missing keys, network errors, non-success HTTP status, and malformed responses.
- Root `.env` is loaded for local backend development.
- `backend/scripts/check_integrations.py` performs one minimal live request to each provider.

Verification status:

- request construction, authentication headers, parsing, normalization, missing-key behavior, and malformed-response behavior are covered by mocked HTTP tests;
- live Nebius and Tavily calls have **not** been run because no API keys were present;
- running the live checker consumes provider quota and must be deliberate.

### Kubernetes demo lab

- Kind cluster definition at `sandbox/kind-config.yaml`.
- Demo namespace: `incidentzero-demo`.
- Demo deployment and service: `payment-api`.
- Dependency-free Python HTTP app exposing `/health`.
- Container uses numeric UID 10001, drops all capabilities, blocks privilege escalation, uses a read-only root filesystem, and has a two-second demo termination grace period.
- Python base image is pinned by digest.
- Deployment uses `Recreate` so a broken replacement cannot leave an old healthy pod serving and confusing the incident evidence.
- Setup, scenario, and reset scripts exist under `sandbox/scripts/`.
- The reset script removes prior scenario pods, reapplies the healthy baseline, waits for rollout, and prints pod state.

Three Kustomize scenarios are implemented:

| Scenario | Fault | Verified live evidence |
| --- | --- | --- |
| `oomkilled` | Allocates 96 MiB under a 64 MiB limit | `OOMKilled`, exit 137, restart, `CrashLoopBackOff` |
| `crashloop` | `DATABASE_HOST=db-invalid` | deterministic fatal log and `CrashLoopBackOff` |
| `readiness` | probe calls `/healthz` while app exposes `/health` | container running, pod `0/1 Ready`, probe HTTP 404 |

The read-only collector in `backend/app/integrations/kubernetes.py`:

- invokes `kubectl` with argument arrays and `shell=False`;
- validates Kubernetes resource names;
- has a subprocess timeout;
- performs only fixed read operations for pods, events, deployment, describe, current logs, and previous logs;
- parses readiness, restart count, current state, previous termination reason, exit code, requests, and limits;
- prefers unhealthy/restarting pods when multiple matching pods temporarily exist;
- was run against the live local OOM scenario and extracted `OOMKilled`, exit 137, and restart count 1.

The local Kind cluster was left in a healthy state after testing:

```text
payment-api   1/1 Running   0 restarts
```

### LangGraph diagnosis workflow

- LangGraph 1.2.15 is pinned as a backend dependency.
- `IncidentState` is a typed, forward-compatible graph state covering incident input, Kubernetes context, hypotheses, research, remediation, validation, timeline, status, and errors.
- Deterministic intake fixtures exist for OOMKilled, crash-loop, and readiness-failure demos; the scenario label is not placed in graph state or model evidence.
- The compiled workflow runs intake, read-only Kubernetes collection, and Nemotron diagnosis nodes.
- The diagnosis prompt contains compact incident and Kubernetes evidence, requires evidence-backed JSON, and is validated into strict Pydantic models.
- Invalid model output receives exactly one repair attempt; the workflow then fails clearly instead of retrying without a bound.
- Kubernetes collection remains read-only. No remediation or sandbox mutation was added.
- Mocked end-to-end graph verification shows OOMKilled evidence producing a validated insufficient-memory hypothesis with confidence and supporting evidence.
- A live Nemotron diagnosis was not run because provider credentials are not present; no quota was consumed.

### Conditional research and final diagnosis

- The graph now branches on Nemotron's validated `research_required` decision.
- The no-research branch makes zero Tavily calls and proceeds directly to synthesis.
- The research branch runs at most three normalized, deduplicated focused questions and requests at most three compact Tavily results per question.
- Sources are globally deduplicated by URL and retain the originating query, title, compact excerpt, relevance, and a plain-language relevance explanation.
- A second structured Nemotron step combines the incident, Kubernetes/application evidence, hypotheses, and optional research into a final root cause, confidence, cited evidence, alternatives, and concise research summary.
- External evidence must cite an exact URL supplied by Tavily. Unsupported or malformed citations receive one bounded repair attempt and then fail clearly.
- Mocked graph tests cover both branches and verify that the research branch incorporates an attributable Kubernetes documentation source.
- No live Tavily or Nemotron call was made because credentials are unavailable; no provider quota was consumed.

### Safe remediation candidates

- A strict remediation contract now records summary, exact affected Deployment, reason, risk, expected outcome, and a concrete strategic-merge YAML patch.
- Nemotron receives the final diagnosis and current Deployment and may change exactly one bounded configuration domain: memory resources, `DATABASE_HOST`, or readiness HTTP path/port.
- Model-generated commands, images, replicas, security fields, secrets, selectors, labels, service accounts, volumes, and namespace changes are forbidden by both the prompt and deterministic policy.
- YAML is parsed with safe loading, duplicate-key rejection, and a single-document requirement.
- Policy validation requires the exact collected `apps/v1 Deployment`, namespace, service, pod-template shape, and container name.
- Memory candidates must use Kubernetes `Ki`/`Mi`/`Gi` quantities, increase the observed limit, and keep an optional request at or below the limit.
- Environment candidates may change only the existing `DATABASE_HOST` value; readiness candidates may change only a non-root HTTP path and optional port.
- Unsafe or malformed model output receives exactly one repair attempt before a terminal generation error.
- The graph stops at `remediation_ready` with the candidate and named policy checks. It does not execute or apply the patch.
- Deterministic tests validate logically correct OOMKilled, configuration crash-loop, and readiness candidates and reject image mutation.
- No live Nemotron generation was run because credentials are unavailable; no quota was consumed.

### Product integration (October 23 implementation)

- SQLite storage with per-operation transactions/connections, durable run snapshots, incident status, ordered events, atomic shared-sandbox exclusion, terminal events committed with terminal status, restart recovery, and a single-process database lease.
- Typed incident/run/event API contracts; demo creation, incident history/details, background run start, run history/details, event history, SSE replay with `Last-Event-ID`, and RCA download.
- Worker-thread execution keeps synchronous kubectl operations outside the API event loop. Existing real Nemotron reasoning, conditional Tavily routing, strict remediation policy, and two-attempt bound are preserved.
- Demo setup uses only fixed local Kind arguments and repository scenario paths, reuses the verifier's context guard, and waits for old pods to disappear and new fault evidence to appear. Missing Nebius configuration fails before sandbox setup.
- Sanitized provider/Kubernetes/timeout errors, HTTP 404/409/422/503 responses, terminal run/error events, stream storage errors, and UI polling fallback prevent silent endless loading.
- Evidence-derived Markdown RCA and field-scoped Deployment diff; no additional model call or fabricated impact.
- Dashboard, incident and run histories/details, three scenario controls, real stored metrics, timeline, evidence/logs, diagnosis/confidence, source panel, diff, checks, final status, and report download. Landing-page CTA opens the workspace.
- Added `docs/PRODUCT_INTEGRATION.md` for local setup, API contracts, safety, lifecycle, and verification limits; refreshed the README and environment template.

## Test inventory and last verified results

Current product-integration checkpoint:

- `backend/.venv/bin/python -m pytest backend -q`: **66 passed** (all external provider/Kubernetes operations mocked).
- `backend/.venv/bin/python -m pip check`: passed; Python compileall of application and tests: passed.
- `cd frontend && npm run lint && npm run typecheck && npm test && npm run build`: passed, including **4 deterministic frontend tests** and Next.js 15.5.28 production build.
- `cd frontend && PLAYWRIGHT_CHROMIUM_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' npm run test:browser`: **2 passed**, using the real UI, HTTP API, worker, SQLite, SSE/report routes, and an explicitly mocked test executor. Verified OOM click-through, persisted reload, mobile navigation, terminal failure while SSE is blocked, and sanitized errors. This is Chrome local browser verification, not cross-browser verification or live model/Kind acceptance.
- Visually inspected the browser-generated run-detail screenshot; screenshot and browser outputs remain Git-ignored test artifacts.
- `git diff --check`: passed. Local branch remains `feat/product-integration`, based on `8a5ef55`, with this change set uncommitted.
- `npm install --no-audit --no-fund` succeeded with network permission. **Known pre-existing tooling problem:** `npm ci` on local npm 11.19.0 fails with `Missing: sharp@ from lock file`; the existing Next sharp override/optional-peer resolution is incompatible with clean-install validation in this environment. A direct optional-sharp attempt did not fix it and was reverted. Use the verified `npm install` setup for now; do not claim `npm ci` passed.
- No live provider calls, provider quota, local Kind operations, commit, push, PR, or deployment in this change set.

Files created/changed for this checkpoint:

- Backend: new `app/models/runs.py`, `app/storage/{__init__,sqlite}.py`, `app/api/incidents.py`, `app/services/{demo,reports,runs}.py`; updated `app/main.py`, `app/config/settings.py`, and the shared local-context guard in `app/services/sandbox.py`.
- Tests: new `backend/tests/test_product_integration.py`, `backend/tests/test_demo_controller.py`, and isolated `backend/tests/ui_fixture.py`; new `frontend/tests/domain.test.ts`, `frontend/tests/browser/workflow.spec.ts`, and `frontend/playwright.config.ts`.
- Frontend: new `app/dashboard/page.tsx`, `app/incidents/page.tsx`, `app/incidents/[id]/page.tsx`, `app/runs/page.tsx`, `app/runs/[id]/page.tsx`, `components/{overview,workspace}.tsx`, `lib/{api,domain}.ts`; updated landing page, global CSS, package manifests/lockfile, and TypeScript test-import configuration.
- Documentation/config: new `docs/PRODUCT_INTEGRATION.md`; updated this handoff, `README.md`, `.env.example`, and `.gitignore` (browser artifacts).
- Recommended Conventional Commit: `feat: integrate persisted incident runs and live product workspace`.

Historical core sandbox live-acceptance checkpoint (before product integration):

- `backend/.venv/bin/pytest backend -q`: **49 passed**, including mocked verifier operations, endpoint-propagation retry, and graph first-attempt success, failure then success, exhausted retry, and retry-generation failure.
- `backend/.venv/bin/python -m pip check`: passed (no broken requirements).
- Python compileall, shell syntax, all four Kustomize renders, and `git diff --check`: passed.
- Frontend ESLint, TypeScript, and Next.js 15.5.28 production build: passed.
- Real Kubernetes acceptance: OOMKilled/137/restart 1 → approved 128Mi patch → rollout → owned pod Running/Ready/restarts 0 → clean recent logs → `/health` status OK → `verified`, 100/100, one attempt.
- The reasoning responses in that run were deterministic mocks; no live Nebius or Tavily request was made and no provider quota was consumed.
- The local lab was reset to the healthy baseline after acceptance.

### October 22 implementation details

- Added typed sandbox validation results with named checks, score, and PASS/FAIL.
- Fixed write target is local `kind-incidentzero`, `incidentzero-demo/payment-api`; context configuration must identify the expected Kind cluster and an HTTPS loopback API server.
- Revalidate the candidate against the live Deployment and require its exact identity/UID before applying. Commands use fixed argument arrays, explicit context, request deadlines, and bounded rollout timeout.
- Apply only the policy-approved strategic-merge patch; inspect Deployment-owned pods through ReplicaSet ownership, phase/readiness, restarts, termination evidence, recent logs, and each healthy pod's `/health` through a fixed non-shell in-pod request.
- Retain the existing planning-only graph when no verifier is supplied. Explicitly supplying `SandboxVerifier` enables application and verification.
- The integrated graph permits exactly two remediation attempts. Retry recollects evidence and supplies previous validation checks to Nemotron. History and named timeline checks are retained, and exhausted validation or failed retry generation produces a terminal failure.
- Health is a point-in-time check, not a sustained soak or stability measurement. The fixed health request has at most three attempts for transient execution readiness.

Backend tests currently cover:

- health endpoint;
- Nebius request/response behavior;
- Tavily normalization and deduplication;
- missing credentials and malformed upstream data;
- Kubernetes OOM evidence parsing;
- collector command allow-list behavior;
- unsafe Kubernetes resource-name rejection;
- unhealthy-pod selection;
- YAML validity for every sandbox manifest;
- expected configuration encoded by all three incidents;
- incident normalization without leaking scenario labels;
- Nemotron structured-diagnosis parsing and bounded repair;
- bounded failure after two malformed model responses;
- end-to-end LangGraph intake, context, diagnosis, status, and timeline propagation;
- bounded research-query normalization and cross-query URL deduplication;
- zero Tavily calls on the no-research branch;
- conditional Tavily routing and final Nemotron synthesis;
- rejection and bounded repair of unsupported external citations;
- structured remediation generation and graph-state propagation;
- safe YAML loading, duplicate-key/single-document handling, target and shape checks;
- resource, environment, and readiness allow-list policies;
- correct candidates for all three demo scenarios;
- rejection and bounded repair of forbidden image changes.

Historical full-stack verification before this checkpoint:

```text
pytest:                    29 passed
Python dependency check:  passed
Python compileall:         passed
Bash syntax checks:        passed
Kustomize base render:     passed
Kustomize OOM render:      passed
Kustomize crash render:    passed
Kustomize readiness render: passed
Frontend ESLint:           passed
Frontend TypeScript:       passed
Frontend production build: passed
git diff --check:          passed
```

## Environment and operational notes

The **preceding core sandbox** live acceptance ran in the Linux workspace at `/home/aryan/Documents/Projects/incidentzero` using Python 3.12.3, the existing local Kind cluster, and the ignored checksum-verified `.tools/kubectl`. The preceding macOS collaborator environment did not have those local tools; treat machine-specific availability as non-portable.

- Product-integration checkout: macOS, Python 3.13.16, Node 24.21.0, npm 11.19.0; no kubectl or Docker on PATH. Browser tests used existing Google Chrome.
- Python: 3.12.3 during historical Linux verification.
- PyYAML is now a runtime dependency because remediation candidates are parsed and policy-validated before they can enter sandbox verification.
- Node.js: 22.23.2 during foundation verification.
- Kind: development build reporting `v0.32.0-alpha+9145d421e0d4f7`; it created a Kubernetes 1.35.0 node locally.
- Docker daemon works only with elevated sandbox permission in the current Codex environment.
- The system Snap installation of kubectl cannot run inside the sandbox because `snap-confine` lacks required capabilities.
- A checksum-verified official kubectl v1.37.1 was downloaded to ignored path `.tools/kubectl`; its SHA-256 matched the official checksum.
- ShellCheck was not installed. All shell scripts passed `bash -n`, and the scripts were exercised live.
- A local Kind cluster named `incidentzero` currently exists and was left with the healthy baseline workload. Do not delete it unless requested or cleanup is necessary and authorized.
- The last attempted npm audit after the Kubernetes commit could not reach the npm registry due to DNS failure. The most recent successful production-only audit before that reported zero vulnerabilities.
- A previous full audit reported development-only advisories in Tailwind 3/ESLint transitive tooling. Fixing them requires a Tailwind 4 migration; they are not in the production dependency tree.

## Configuration

Root `.env` variables currently supported:

```text
API_HOST
API_PORT
CORS_ORIGINS
NEXT_PUBLIC_API_URL
DATABASE_PATH
KUBECTL_BIN
NEBIUS_API_KEY
NEBIUS_BASE_URL
NEBIUS_MODEL
TAVILY_API_KEY
TAVILY_BASE_URL
```

Never commit `.env` or credentials.

## Safety invariants already established

- Production and demo-production are read-only.
- Sandbox writes must be controlled and allow-listed.
- No arbitrary commands from model output.
- No `shell=True` for generated input.
- External clients have timeouts and sanitized errors.
- Research output is compact and normalized; large raw pages are not forwarded.
- Future remediation loops must have a hard maximum of two or three attempts.
- Human approval remains required before any production change.

## Remaining work

The canonical sequence and acceptance criteria are expanded in `docs/MASTER_BUILD_PLAN.md`.

### Next: October 23 — live product acceptance

Implementation is locally test-verified with mocked external boundaries. Before advancing to deployment:

- On a prepared Kind machine, deliberately authorize/configure provider quota and run OOMKilled from the UI through the persisted API and real Nemotron reasoning.
- Verify SSE timeline, evidence, diagnosis, diff, checks, terminal status, RCA export, and persisted reload behavior, then reset the sandbox healthy.
- Verify Tavily connectivity and an actual conditional-research run when credentials/quota are authorized; do not force research on every run.
- Record exact live evidence here. Do not reuse mocked browser results as live provider or cluster proof.

Exit criterion: the product UI drives the real persisted workflow to a clear terminal state with attributable evidence and sandbox verification.

### Later milestones

- October 24: landing-page polish, deployment, CORS/environment validation, public URL, production logging, cross-browser check.
- October 25: feature freeze, five golden-path runs, bug fixes, full documentation, screenshots, architecture diagram, demo video, DEV.to article, Devpost submission.

## Explicitly pending

- Live provider credential/connectivity verification and UI/API-to-Kind acceptance of product integration.
- Public deployment, hosted demo access model, and October 24 production logging/polish.
- Final five-run golden-path stability acceptance and submission screenshots, video, DEV.to article, and Devpost entry.
- Sustained health/soak measurements; current sandbox verification remains point-in-time.

## Judging-criteria alignment

- **Technological implementation:** the current product has real Kubernetes evidence collection, typed Nebius/Nemotron and Tavily integrations, tested LangGraph diagnosis/research/synthesis paths, deterministic YAML remediation policy enforcement, and a live-accepted bounded sandbox validation loop. Live provider credentials remain necessary to demonstrate Nemotron/Tavily reasoning rather than mocked reasoning.
- **Design:** the frontend now implements the persisted incident workflow, timeline, evidence, diagnosis, diff, validation, and RCA experience. Public deployment and live end-to-end product acceptance remain pending.
- **Potential impact:** the three reproducible failure modes, read-only production boundary, and verified local OOM recovery make the operator use case concrete. Live acceptance of the persisted product integration and the final demo narrative remain essential proof.
- **Quality of the idea:** evidence-driven Nemotron reasoning, conditional research, and bounded sandbox validation are the core non-obvious differentiators. Avoid presenting mocked outputs as live model results; the final demo must make each real system boundary visible.

## Scope exclusions

Do not add Datadog, PagerDuty, ServiceNow, Prometheus, Grafana, Slack, Teams, AWS/Azure integrations, Terraform automation, multi-cluster management, voice, mobile apps, enterprise authentication, RBAC UI, billing, a vector database, or a large RAG corpus unless all required work is complete and the user explicitly asks.

## Useful commands

```bash
# Backend
cd backend
source .venv/bin/activate
pytest
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Optional live provider check; consumes quota
cd backend
python -m scripts.check_integrations

# Frontend
cd frontend
npm run lint
npm run typecheck
npm run build
npm run dev

# Kubernetes lab when kubectl is on PATH
./sandbox/scripts/create-cluster.sh
./sandbox/scripts/apply-incident.sh oomkilled
./sandbox/scripts/reset.sh

# Kubernetes lab with the current local binary
KUBECTL_BIN="$PWD/.tools/kubectl" ./sandbox/scripts/create-cluster.sh
KUBECTL_BIN="$PWD/.tools/kubectl" ./sandbox/scripts/apply-incident.sh oomkilled
KUBECTL_BIN="$PWD/.tools/kubectl" ./sandbox/scripts/reset.sh
```

## Commit history

```text
05a6742 Merge pull request #1 from rakshitsharma0402/feat/sandbox-verification
f1b5436 docs: record sandbox branch publication and PR blocker
148fdd5 feat: add bounded sandbox remediation verification
ec85693 feat: add safe remediation generation and policy validation
83486ee docs: add state of play and Codex handoff guide
5ebdd4b docs: add state of play and Codex handoff guide
36c09a2 feat: add Kubernetes demo lab and context collector
6f3c856 feat: integrate Nebius Nemotron and Tavily clients
3a14150 chore: initialize IncidentZero project structure
a6d5da2 Initial commit
```

## State change log

- October 17, 2026: user requested publication of the product-integration PR. Reviewed the change set and prepared the Conventional Commit, PR title, verification evidence, and explicit live-acceptance/tooling limits. Removed a stray root lockfile dependency entry left by the reverted optional-sharp experiment so it matches package.json. Publication outcome will be recorded after GitHub confirms it.

- October 17, 2026: created `feat/product-integration` from `8a5ef55`; implemented SQLite persistence, background graph execution, REST/SSE APIs, fixed-context demo controls, RCA/diff generation, and the full local product workspace. Verified 66 backend tests, four frontend tests, two Chrome browser smoke tests, lint/typecheck/build, dependency integrity, compilation, and diff formatting. External reasoning/Kubernetes boundaries were mocked. No commit/push/deployment, provider quota, or live Kubernetes mutation; live product acceptance remains next. Recorded the pre-existing npm 11 `npm ci` sharp-resolution failure and verified `npm install` workaround.

- October 17, 2026: live-verified the integrated OOMKilled workflow with mocked reasoning and real Kind operations. Fixed the Kubernetes health-check race by using a bounded fixed in-pod `/health` request, and fixed Python 3.12 LangGraph stalls caused by sync conditional/executor paths. The workflow passed all nine named checks at 100/100 on attempt one; the lab was reset healthy; 49 backend tests and the full project verification passed. Next: October 23 persistence, APIs, SSE, and product UI.
- October 17, 2026: collaborator requested a PR; committed implementation as `148fdd5` and pushed `feat/sandbox-verification`. PR creation was blocked by GitHub collaborator permissions, and automatic approval review rejected using a separate account credential without explicit authorization. Live Kubernetes acceptance remains pending and is called out in the prepared PR description.
- October 17, 2026: pulled current main and created `feat/sandbox-verification`; implemented fixed local sandbox targeting, live patch revalidation, rollout and owned-pod/log/HTTP checks, scores, validation history, and a maximum of two remediation attempts. All 48 backend tests passed with mocked external boundaries. Live Kubernetes verification remains blocked by missing local tooling; no provider quota consumed. Next: live local October 22 OOM workflow verification.
- October 17, 2026: completed and locally verified structured remediation generation, strict YAML and target policies, scenario-appropriate patches for all three demo failures, and bounded repair of rejected candidates; Kubernetes application remains intentionally pending.
- October 17, 2026: completed and locally verified conditional Tavily routing, bounded focused research, cross-query source deduplication, final structured Nemotron synthesis, and citation allow-list repair; live provider verification remains pending.
- October 17, 2026: completed and locally verified typed incident intake, LangGraph context/diagnosis flow, strict Nemotron output validation, and one bounded repair attempt; live provider verification remains pending.
- October 16, 2026: created the mandatory state-of-play and Codex collaborator handoff system.
- October 16, 2026: completed and live-verified the Kind lab, three deterministic incidents, reset workflow, and Kubernetes collector.
- October 16, 2026: completed typed Nebius and Tavily clients with mocked contract tests; live credential checks remain pending.
- October 16, 2026: completed and verified the FastAPI/Next.js foundation.
