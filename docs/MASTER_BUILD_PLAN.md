# IncidentZero — Master Build Plan

Internal feature-complete deadline: **October 25, 2026**.

This is the durable implementation plan. `INCIDENTZERO_STATE_OF_PLAY.md` records actual progress and evidence; this document defines what remains required.

## Product definition

Tagline: **Autonomous AI incident-resolution engineer for diagnosing, fixing, and validating Kubernetes production incidents.**

Short pitch: **From production incident to verified fix — autonomously.**

The product is an SRE/incident-management application, not a chatbot. Its visible agent workflow must observe, plan, use tools, reason over evidence, generate a real engineering change, execute and test that change in a controlled sandbox, evaluate the result, retry when appropriate, and produce a verified resolution for human approval.

## Priority order

1. Reliable OOMKilled golden path.
2. Agent infrastructure.
3. Sandbox verification.
4. Frontend visualization.
5. Public deployment.
6. Configuration CrashLoop and readiness incidents.
7. Documentation.
8. Submission assets.

Never sacrifice OOM reliability for optional breadth.

## Required stack

- AI reasoning: NVIDIA Nemotron through Nebius Token Factory.
- Conditional web research: Tavily.
- Backend: Python 3.12+, FastAPI, Pydantic, LangGraph; LangChain only where useful.
- Frontend: Next.js, TypeScript, Tailwind CSS, shadcn/ui, Lucide icons.
- Sandbox: Docker, Kubernetes, Kind, kubectl; plain manifests/Kustomize preferred over unnecessary Helm complexity.
- Persistence: SQLite.
- Live updates: Server-Sent Events unless a real requirement justifies WebSockets.

## Golden path

```text
Create OOMKilled demo incident
→ collect real Kubernetes pods, events, logs, previous logs, manifest, resources
→ Nemotron generates structured hypotheses
→ agent conditionally requests Tavily research
→ combine cluster, application, and external evidence
→ identify insufficient memory configuration
→ generate a concrete Kubernetes patch and diff
→ validate YAML and safety constraints
→ apply only to the sandbox
→ wait for rollout
→ inspect pod health, restarts, termination state, logs, and /health
→ PASS or feed evidence into one bounded retry
→ produce verified remediation and RCA
→ request human approval
```

## Agent state requirements

The typed workflow state should cover:

- incident and run IDs;
- normalized incident, service, environment, severity, and symptoms;
- cluster context, pod status, events, logs, previous logs, manifest, and resources;
- hypotheses;
- research-required decision, queries, normalized sources, and summary;
- root cause, confidence, evidence, and alternatives;
- remediation plan, patch, affected resource, risk, and expected outcome;
- validation results, score, pass/fail status, and iteration count;
- timeline events;
- final report, run status, and errors.

Prefer explicit Pydantic models for external and persistence boundaries and a typed LangGraph state for orchestration.

## Intended graph

```text
START
→ ingest_incident
→ collect_context
→ diagnose
→ needs_research?
   ├─ yes → research
   └─ no ─────────────┐
→ synthesize_diagnosis ←┘
→ remediate
→ validate
→ validation_passed?
   ├─ yes → generate_rca → END
   └─ no → retry_allowed?
            ├─ yes → remediate
            └─ no → failed_resolution → END
```

Maximum remediation attempts: two or three, configured once and tested. Infinite loops are forbidden.

## Milestones

### October 17 — foundation and provider access

Required:

- repository structure;
- FastAPI and health endpoint;
- Next.js foundation;
- environment configuration;
- Nebius/Nemotron client and connectivity check;
- Tavily client and connectivity check.

Current status: implementation complete; mocked provider contracts verified. Live provider connectivity still requires keys.

### October 18 — Kubernetes demo lab

Required:

- Kind cluster;
- healthy demo workload;
- reproducible OOMKilled, configuration CrashLoop, and readiness failures;
- setup/reset scripts;
- Kubernetes evidence collector.

Current status: complete and locally live-verified.

### October 19 — diagnosis

Required:

- typed LangGraph state;
- incident intake and normalization;
- Kubernetes context node;
- Nemotron diagnosis agent;
- structured hypotheses, confidence, supporting evidence, research decision, and focused questions;
- malformed model-output validation and careful repair/retry.

Exit criterion: OOMKilled is correctly diagnosed from evidence, not from a scenario-name shortcut.

### October 20 — research

Required:

- research node invoked only when useful;
- focused query generation;
- Tavily calls;
- source normalization, deduplication, explanation, and relevance;
- concise research synthesis returned to diagnosis;
- final diagnosis combining cluster, application, and external evidence.

Exit criterion: the live workflow visibly incorporates attributable technical evidence without exposing large scraped pages.

### October 21 — remediation

Required:

- structured remediation model;
- concrete patch or safely updated manifest;
- affected resource, reason, risk, expected outcome;
- YAML/schema validation and policy checks;
- logically correct candidate fixes for all three incidents.

Exit criterion: each scenario produces a reviewable, safe, scenario-appropriate patch.

### October 22 — verification

Required:

- validate configuration;
- apply only to sandbox;
- wait for rollout with timeout;
- inspect pod state, readiness, restart count, termination state, recent logs, and `/health`;
- produce named PASS/FAIL checks and score;
- feed failure evidence into remediation;
- bounded retry loop with visible iteration history.

Exit criterion: broken workload → diagnosis → patch → sandbox → healthy workload. This is the most important milestone.

### October 23 — product integration

Required backend:

- SQLite persistence for incidents, runs, status, events, and final results;
- `POST /api/incidents/demo/{scenario}`;
- `GET /api/incidents`;
- `GET /api/incidents/{incident_id}`;
- `POST /api/incidents/{incident_id}/run`;
- `GET /api/runs/{run_id}`;
- `GET /api/runs/{run_id}/events`;
- `GET /api/runs/{run_id}/stream` using SSE;
- proper bounded errors with no infinite spinner state.

Required frontend:

- navigation for Dashboard, Incidents, and Agent Runs;
- real metrics derived only from demo history;
- deterministic demo control for OOMKilled, CrashLoopBackOff, and readiness failure;
- incident summary;
- streamed agent timeline;
- diagnosis with confidence and evidence;
- Tavily source panel;
- GitHub-style patch diff;
- validation checks and PASS/FAIL status;
- final RCA and optional Markdown download.

Exit criterion: frontend reflects real persisted backend execution.

### October 24 — deployment and polish

Required:

- polished landing page with problem, workflow, architecture, technology, and safety;
- free or hackathon-credit hosting only;
- deployed frontend and backend;
- CORS and environment configuration;
- meaningful production logs with run ID, incident ID, node, event, duration, and status;
- no secret logging;
- public URL another developer can use without local Kubernetes configuration;
- cross-browser and failure-state checks.

If hosted Kubernetes is unreliable or expensive, infrastructure telemetry may be clearly labeled as controlled simulation, but agent reasoning and integrations shown as live must actually run.

### October 25 — freeze and submission

No major new features.

Required:

- five recorded successful OOM golden-path runs;
- bug fixes and regression checks;
- complete README with live demo/video/Devpost placeholders or links, problem, solution, features, demo, architecture, workflow, integrations, sandbox, safety, stack, structure, setup, environment, testing, screenshots, roadmap, team, and license;
- accurate `docs/architecture.md`, `docs/safety.md`, `docs/demo.md`, and `docs/development.md`;
- six to eight strong screenshots;
- architecture diagram;
- under-three-minute demo video;
- DEV.to article;
- completed Devpost submission.

Submission assets should include six to eight strong screenshots covering the landing page, dashboard, incident overview, agent timeline, diagnosis, Tavily sources, remediation diff, and sandbox verification. Prefer a 3:2 composition where practical.

The demo video must remain under three minutes and should follow this approximate sequence:

```text
0:00–0:15  problem
0:15–0:30  IncidentZero and architecture
0:30–2:15  live golden-path demonstration
2:15–2:40  safety and technical architecture
2:40–2:55  closing pitch
```

Explicitly mention NVIDIA Nemotron, Nebius Token Factory, Tavily, Kubernetes, and LangGraph.

Working DEV.to title: **IncidentZero: Building an Autonomous Kubernetes Incident Engineer with NVIDIA Nemotron and Nebius**. Cover the problem, motivation, architecture, agent workflow, Nemotron, Token Factory, Tavily, Kubernetes sandbox, verify-before-deploy principle, challenges, lessons, and next steps.

## Safety model

- Treat production and demo-production as read-only.
- Sandbox alone permits controlled writes.
- Use allow-listed tool operations, argument arrays, timeouts, bounded output, resource limits, and sanitized errors.
- Never pass LLM text directly to a shell.
- Validate target namespace/context before mutation.
- Never expose provider keys, kubeconfig contents, authorization headers, or raw secrets in logs or UI.
- Require human approval before production remediation.

## Error states to implement

- Nebius unavailable, timed out, unauthorized, or malformed output;
- Tavily unavailable, timed out, exhausted, or malformed output;
- Kubernetes unavailable, context invalid, namespace forbidden, pod missing, or collection timed out;
- invalid patch or manifest;
- sandbox apply failure;
- rollout, readiness, health, or log check timeout;
- database failure;
- network interruption;
- exhausted remediation attempts.

Every failure must become a clear terminal or retrying state—never an infinite spinner.

## Testing requirements

- state models and transitions;
- model structured-output parsing and repair;
- Kubernetes evidence parsing;
- research normalization/deduplication;
- patch validation and safety policy;
- validation score/pass processing;
- health and critical API endpoints;
- SSE behavior and terminal events;
- mocked external APIs;
- at least one real local OOM end-to-end workflow;
- final five-run golden-path stability check.

## Required timeline events

```text
incident.received
context.started
context.completed
diagnosis.started
diagnosis.completed
research.started
research.completed
remediation.generated
validation.started
validation.check
validation.failed
validation.completed
report.generated
run.completed
```

## RCA fields

- incident;
- service;
- severity;
- environment;
- timeline;
- root cause;
- impact;
- evidence;
- resolution;
- validation;
- preventive actions.

## UX requirements

- Modern, calm, technical, professional, and high-signal.
- No generic chat layout, fake terminal typing, excessive animation, rainbow gradients, or heavy glassmorphism.
- Semantic HTML, keyboard-accessible controls, reasonable contrast, and visible loading/error states.
- OOMKilled is the recommended primary demo.
- Never show fabricated customer or production metrics.

## Cost constraint

Target personal spend is ₹0. Use hackathon credits, free tiers, local Kind, open-source tooling, and free hosting. Stop and propose a free alternative before introducing anything requiring personal payment.
