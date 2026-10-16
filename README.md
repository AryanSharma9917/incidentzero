# IncidentZero

> Autonomous AI incident-resolution engineer for diagnosing, fixing, and validating Kubernetes production incidents.

IncidentZero is being built for the Nebius x NVIDIA Global AI Hackathon 2026. It will collect incident evidence, reason with NVIDIA Nemotron through Nebius Token Factory, research with Tavily, propose a controlled remediation, and verify the result in a Kubernetes sandbox before requesting human approval.

## Current status

Phase 1 foundation provides:

- a FastAPI backend with a health endpoint;
- a Next.js, TypeScript, and Tailwind CSS frontend shell;
- local environment configuration; and
- basic backend and frontend quality checks.
- typed Nebius Token Factory and Tavily integration clients.
- a reproducible local Kind lab with three incident scenarios.

The LangGraph agent workflow and Kubernetes sandbox are intentionally deferred until their respective milestones.

## Project structure

```text
incidentzero/
├── backend/          FastAPI application and tests
├── frontend/         Next.js application
├── docs/             Architecture and operational documentation
├── sandbox/          Kubernetes demo scenarios (future phase)
└── scripts/          Development and demo utilities (future phase)
```

## Getting started

Copy the example environment file with `cp .env.example .env`.

For live integrations, set `NEBIUS_API_KEY`, `NEBIUS_MODEL`, and `TAVILY_API_KEY` in the root `.env`. The application loads this file for local development; deployed environments should inject the same variables through their secret manager.

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open <http://localhost:8000/health> to verify the API.

To make one minimal live request to Nebius and Tavily:

```bash
cd backend
python -m scripts.check_integrations
```

This command consumes provider quota. It is intentionally a developer command rather than a public HTTP endpoint.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:3000>.

## Tests and checks

```bash
cd backend && pytest
cd frontend && npm run lint && npm run typecheck && npm run build
```

## Kubernetes demo lab

The local sandbox includes healthy, OOMKilled, configuration CrashLoop, and readiness-probe states for `payment-api`. See [sandbox/README.md](sandbox/README.md) for setup, scenario, reset, and expected-evidence commands.

## Integrations

- NVIDIA Nemotron through Nebius Token Factory (client implemented)
- Tavily research (client implemented)
- LangGraph orchestration (planned)
- Kubernetes and Kind sandbox verification
- SQLite persistence and Server-Sent Events

## Safety model

Production-like environments will be read-only. Writes will be restricted to a controlled sandbox with explicit tool allow-lists, timeouts, and bounded remediation attempts.

## License

License information will be added before public release.
