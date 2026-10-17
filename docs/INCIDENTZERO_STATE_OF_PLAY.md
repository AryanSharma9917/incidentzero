# IncidentZero — State of Play

Last updated: October 17, 2026 (Asia/Kolkata), sandbox verification implementation checkpoint

This is the canonical live handoff document for developers and coding agents. Update it in every change set that modifies the project. Historical claims must remain truthful: distinguish mocked verification, local live verification, and work that still requires credentials or deployment access.

## Current checkpoint

The October 17 foundation through October 21 remediation implementations are complete. `git pull --ff-only origin main` confirmed that the clean local `main` was up to date at:

```text
ec85693 feat: add safe remediation generation and policy validation
```

The sandbox verification change set is on `feat/sandbox-verification`, branched from `ec85693`. It implements the October 22 controlled verifier and one bounded workflow retry. The collaborator explicitly authorized editing shared workflow-state contracts and subsequently requested a pull request, authorizing commit and branch push. This handoff is included in that PR change set. No deployment, provider call, or Kubernetes mutation was performed.

Implementation commit `148fdd5` was pushed successfully to `origin/feat/sandbox-verification`. GitHub PR creation returned HTTP 422 (`must be a collaborator`) using the default configured HTTPS credential. Automatic approval review rejected an owner-specific credential retry because separate-account use was not explicitly authorized. PR creation remains pending appropriate GitHub collaborator authentication; the branch is available for review. This documentation follow-up records the publication outcome.

October 22 remains the next incomplete milestone: the implementation is deterministically tested, but real local OOMKilled end-to-end verification is pending. The current macOS machine has no Docker, Kind, or kubectl on PATH and no `.tools/kubectl`. Provision the local lab and verify the integrated workflow before advancing to October 23. Writes remain restricted to the fixed `kind-incidentzero` context and `incidentzero-demo/payment-api` sandbox target.

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

## Test inventory and last verified results

Current sandbox implementation checkpoint:

- `cd backend && .venv/bin/python -m pytest`: **48 passed**, including mocked verifier operations and mocked end-to-end graph reasoning, first-attempt success, failure then success, exhausted retry, and retry-generation failure.
- `backend/.venv/bin/python -m pip check`: passed (no broken requirements).
- Python compileall and `git diff --check`: passed.
- Local Python 3.13 virtual environment created at ignored `backend/.venv`; pinned backend requirements installed after sandbox DNS failure using approved network access.
- No real Kubernetes or provider execution. Frontend checks were not rerun because this checkpoint changes only backend code/tests and documentation.

### October 22 implementation details

- Added typed sandbox validation results with named checks, score, and PASS/FAIL.
- Fixed write target is local `kind-incidentzero`, `incidentzero-demo/payment-api`; context configuration must identify the expected Kind cluster and an HTTPS loopback API server.
- Revalidate the candidate against the live Deployment and require its exact identity/UID before applying. Commands use fixed argument arrays, explicit context, request deadlines, and bounded rollout timeout.
- Apply only the policy-approved strategic-merge patch; inspect Deployment-owned pods through ReplicaSet ownership, phase/readiness, restarts, termination evidence, recent logs, and each healthy pod's `/health` through the Kubernetes API proxy.
- Retain the existing planning-only graph when no verifier is supplied. Explicitly supplying `SandboxVerifier` enables application and verification.
- The integrated graph permits exactly two remediation attempts. Retry recollects evidence and supplies previous validation checks to Nemotron. History and named timeline checks are retained, and exhausted validation or failed retry generation produces a terminal failure.
- Health is a point-in-time check, not a sustained soak or stability measurement. Live command compatibility and actual OOM recovery remain unverified here.

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

The following Linux/Kind environment notes describe the earlier collaborator machine, not the current macOS checkout at `/Users/rakshitsharma/Developer/Project/incidentzero`. Its existing Kind cluster and downloaded kubectl are not available on this machine. Current interpreter: Python 3.13.16. Docker, Kind, and kubectl are absent from PATH; no local cluster verification was possible in this session.

- Python: 3.12.3 during verification.
- PyYAML is now a runtime dependency because remediation candidates are parsed and policy-validated before they can enter sandbox verification.
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

### Next: October 22 — sandbox verification

The implementation below is now present and mocked-tested. **Exact next task:** provision or use an authorized local Docker/Kind lab, induce the OOMKilled scenario, invoke `build_diagnosis_graph(..., sandbox_verifier=SandboxVerifier(...))`, and verify real rollout/pod/log/HTTP checks and terminal status. Reset the lab afterward. Use explicitly labeled mocked reasoning if credentials/quota authorization remain unavailable; only run live Nebius/Tavily with separate quota authorization. Record actual evidence and address any live failures before calling October 22 complete.

- Validate the selected Kubernetes context and allow writes only to `incidentzero-demo`.
- Apply only the already policy-approved strategic-merge patch using argument arrays and fixed operations.
- Wait for Deployment rollout with a hard timeout.
- Inspect pod phase/readiness, restart count, termination state, recent logs, and `/health`.
- Produce named PASS/FAIL checks, a validation score, and a terminal result.
- Feed failed validation evidence into one bounded remediation retry; never permit an infinite loop.
- Record each iteration and validation check in the workflow timeline.
- Run at least one real local OOMKilled end-to-end workflow when provider credentials permit; otherwise distinguish mocked model reasoning from live Kubernetes verification exactly.

Exit criterion: broken workload → diagnosis → safe patch → sandbox-only application → verified healthy workload, with failure evidence supporting at most one retry.

### Later milestones

- October 23: SQLite persistence, incident/run APIs, SSE timeline, dashboard, incident detail, diagnosis, research, diff, validation, and RCA UI.
- October 24: landing-page polish, deployment, CORS/environment validation, public URL, production logging, cross-browser check.
- October 25: feature freeze, five golden-path runs, bug fixes, full documentation, screenshots, architecture diagram, demo video, DEV.to article, Devpost submission.

## Explicitly not implemented yet

- Incident/run database persistence.
- Incident, run, or SSE APIs.
- Live verification of the implemented sandbox verifier and retry loop.
- RCA generation or Markdown export.
- Dashboard, incident details, live timeline, diff viewer, or validation UI.
- Public deployment.
- Live Nebius or Tavily credential verification.
- Submission screenshots, video, DEV.to article, or Devpost entry.

## Judging-criteria alignment

- **Technological implementation:** the current product has real Kubernetes evidence collection, typed Nebius/Nemotron and Tavily integrations, tested LangGraph diagnosis/research/synthesis paths, deterministic YAML remediation policy enforcement, and a mocked-tested bounded sandbox validation loop. Live credential and integrated sandbox verification remain necessary to demonstrate the full autonomous cycle.
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

- October 17, 2026: collaborator requested a PR; committed implementation as `148fdd5` and pushed `feat/sandbox-verification`. PR creation was blocked by GitHub collaborator permissions, and automatic approval review rejected using a separate account credential without explicit authorization. Live Kubernetes acceptance remains pending and is called out in the prepared PR description.
- October 17, 2026: pulled current main and created `feat/sandbox-verification`; implemented fixed local sandbox targeting, live patch revalidation, rollout and owned-pod/log/HTTP checks, scores, validation history, and a maximum of two remediation attempts. All 48 backend tests passed with mocked external boundaries. Live Kubernetes verification remains blocked by missing local tooling; no provider quota consumed. Next: live local October 22 OOM workflow verification.
- October 17, 2026: completed and locally verified structured remediation generation, strict YAML and target policies, scenario-appropriate patches for all three demo failures, and bounded repair of rejected candidates; Kubernetes application remains intentionally pending.
- October 17, 2026: completed and locally verified conditional Tavily routing, bounded focused research, cross-query source deduplication, final structured Nemotron synthesis, and citation allow-list repair; live provider verification remains pending.
- October 17, 2026: completed and locally verified typed incident intake, LangGraph context/diagnosis flow, strict Nemotron output validation, and one bounded repair attempt; live provider verification remains pending.
- October 16, 2026: created the mandatory state-of-play and Codex collaborator handoff system.
- October 16, 2026: completed and live-verified the Kind lab, three deterministic incidents, reset workflow, and Kubernetes collector.
- October 16, 2026: completed typed Nebius and Tavily clients with mocked contract tests; live credential checks remain pending.
- October 16, 2026: completed and verified the FastAPI/Next.js foundation.
