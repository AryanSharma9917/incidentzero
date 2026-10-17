# IncidentZero — State of Play

Last updated: October 17, 2026 (Asia/Kolkata)

This is the canonical live handoff document for developers and coding agents. Update it in every change set that modifies the project. Historical claims must remain truthful: distinguish mocked verification, local live verification, and work that still requires credentials or deployment access.

## Current checkpoint

The October 17 foundation, October 18 Kubernetes demo-lab, October 19 diagnosis, and October 20 conditional-research milestones are complete. The last committed checkpoint on `main` is synchronized with `origin/main` at:

```text
83486ee docs: add state of play and Codex handoff guide
```

The current uncommitted change set is the October 20 conditional-research milestone described below. It has passed local automated verification but has not been committed or pushed.

The next engineering milestone is October 21: structured remediation, a concrete safe patch, affected-resource/risk/outcome fields, and YAML and policy validation for all three incidents. Do not apply the patch to Kubernetes until the October 22 sandbox-verification milestone.

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

## Test inventory and last verified results

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
- rejection and bounded repair of unsupported external citations.

Last complete verification:

```text
pytest:                    22 passed
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

- Python: 3.12.3 during verification.
- Node.js: 22.23.2 during foundation verification.
- Kind: development build reporting `v0.32.0-alpha+9145d421e0d4f7`; it created a Kubernetes 1.35.0 node locally.
- Docker daemon works only with elevated sandbox permission in the current Codex environment.
- The system Snap installation of kubectl cannot run inside the sandbox because `snap-confine` lacks required capabilities.
- A checksum-verified official kubectl v1.37.1 was downloaded to ignored path `.tools/kubectl`; its SHA-256 matched the official checksum.
- ShellCheck was not installed. All shell scripts passed `bash -n`, and the scripts were exercised live.
- A local Kind cluster named `incidentzero` currently exists. Do not delete it unless requested or cleanup is necessary and authorized.
- The last attempted npm audit after the Kubernetes commit could not reach the npm registry due to DNS failure. The most recent successful production-only audit before that reported zero vulnerabilities.
- A previous full audit reported development-only advisories in Tailwind 3/ESLint transitive tooling. Fixing them requires a Tailwind 4 migration; they are not in the production dependency tree.

## Configuration

Root `.env` variables currently supported:

```text
API_HOST
API_PORT
CORS_ORIGINS
NEXT_PUBLIC_API_URL
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

### Next: October 21 — remediation

- Define a strict structured remediation model.
- Generate a concrete Kubernetes patch or safely updated manifest from the final diagnosis.
- Include the affected resource, reason, risk, and expected outcome.
- Validate YAML/schema shape and enforce safety policy before accepting a candidate.
- Produce logically correct candidates for OOMKilled, configuration crash-loop, and readiness failures.
- Keep model output separate from execution; do not apply candidates to Kubernetes in this milestone.

Exit criterion: every scenario produces a reviewable, safe, scenario-appropriate patch that passes deterministic configuration and policy validation.

### Later milestones

- October 22: sandbox application, rollout/health/restart/log checks, PASS/FAIL scoring, bounded retry loop—the most important engineering milestone.
- October 23: SQLite persistence, incident/run APIs, SSE timeline, dashboard, incident detail, diagnosis, research, diff, validation, and RCA UI.
- October 24: landing-page polish, deployment, CORS/environment validation, public URL, production logging, cross-browser check.
- October 25: feature freeze, five golden-path runs, bug fixes, full documentation, screenshots, architecture diagram, demo video, DEV.to article, Devpost submission.

## Explicitly not implemented yet

- Incident/run database persistence.
- Incident, run, or SSE APIs.
- Remediation generation or patch validation.
- Automated sandbox verification and retry loop.
- RCA generation or Markdown export.
- Dashboard, incident details, live timeline, diff viewer, or validation UI.
- Public deployment.
- Live Nebius or Tavily credential verification.
- Submission screenshots, video, DEV.to article, or Devpost entry.

## Judging-criteria alignment

- **Technological implementation:** the current product has real Kubernetes evidence collection, typed Nebius/Nemotron and Tavily integrations, and tested LangGraph diagnosis, conditional-research, and cited-synthesis paths. Live credential verification and the later remediation/verification loop remain necessary to demonstrate the integrations fully.
- **Design:** the frontend currently provides a polished foundation, not yet the complete incident workflow. The incident detail, timeline, evidence, diagnosis, diff, validation, and RCA experience remains scheduled for October 23–24.
- **Potential impact:** the three reproducible failure modes and read-only production/sandbox-write boundary make the operator use case concrete. Verified remediation and the final demo narrative remain essential proof.
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
83486ee docs: add state of play and Codex handoff guide
5ebdd4b docs: add state of play and Codex handoff guide
36c09a2 feat: add Kubernetes demo lab and context collector
6f3c856 feat: integrate Nebius Nemotron and Tavily clients
3a14150 chore: initialize IncidentZero project structure
a6d5da2 Initial commit
```

## State change log

- October 17, 2026: completed and locally verified conditional Tavily routing, bounded focused research, cross-query source deduplication, final structured Nemotron synthesis, and citation allow-list repair; live provider verification remains pending.
- October 17, 2026: completed and locally verified typed incident intake, LangGraph context/diagnosis flow, strict Nemotron output validation, and one bounded repair attempt; live provider verification remains pending.
- October 16, 2026: created the mandatory state-of-play and Codex collaborator handoff system.
- October 16, 2026: completed and live-verified the Kind lab, three deterministic incidents, reset workflow, and Kubernetes collector.
- October 16, 2026: completed typed Nebius and Tavily clients with mocked contract tests; live credential checks remain pending.
- October 16, 2026: completed and verified the FastAPI/Next.js foundation.
