# IncidentZero

> Autonomous AI incident-resolution engineer for diagnosing, fixing, and validating Kubernetes production incidents.

IncidentZero is being built for the Nebius x NVIDIA Global AI Hackathon 2026. It will collect incident evidence, reason with NVIDIA Nemotron through Nebius Token Factory, research with Tavily, propose a controlled remediation, and verify the result in a Kubernetes sandbox before requesting human approval.

## Current status

Phase 1 foundation provides:

- a FastAPI backend with a health endpoint;
- a Next.js, TypeScript, and Tailwind CSS frontend shell;
- local environment configuration; and
- basic backend and frontend quality checks.

The agent workflow, AI integrations, and Kubernetes sandbox are intentionally deferred until the foundation is verified.

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

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open <http://localhost:8000/health> to verify the API.

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

## Planned integrations

- NVIDIA Nemotron through Nebius Token Factory
- LangGraph orchestration
- Tavily research
- Kubernetes and Kind sandbox verification
- SQLite persistence and Server-Sent Events

## Safety model

Production-like environments will be read-only. Writes will be restricted to a controlled sandbox with explicit tool allow-lists, timeouts, and bounded remediation attempts.

## License

License information will be added before public release.
