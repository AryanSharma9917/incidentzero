# PR title

feat: prepare hosted demo deployment and polish the workspace

# PR description

Prepare IncidentZero for a hosted demo that visitors can use without configuring Kubernetes. Add an explicitly labeled infrastructure simulation while preserving real Nemotron reasoning and conditional Tavily research. Simulation passes remain separate from Kubernetes-verified fixes.

## Changes

- Polish the landing page with problem, workflow, architecture, technology, and safety content.
- Add simulated infrastructure evidence and configuration evaluation through the existing patch policy and bounded remediation loop; persist successful simulations as a distinct terminal status.
- Add runtime metadata, execution/storage notices, access-code controls, paused production writes, daily run-start limits, and production CORS/environment validation.
- Add structured metadata-only workflow logs with incident/run IDs, stage, event, duration, and status.
- Prepare standalone Next.js assets, non-root Dockerfiles, local Compose, an optional explicitly free Render blueprint, and a read-only deployed smoke-check script.
- Document deployment setup, credit/hosting boundaries, verification evidence, and outstanding acceptance work.

## Verification

- 83 backend tests and five frontend domain tests passed.
- 12 Chromium/WebKit browser checks passed, covering persisted execution, SSE-blocked failure, mobile layout, simulation labels/metrics, pause controls, and access-code writes.
- Frontend lint, typecheck, production build, standalone asset preparation, and local production route/static-asset smoke passed.
- Python dependency check, compileall, YAML inspection, and Git diff checks passed.
- Provider and Kubernetes boundaries were mocked; no live provider quota was consumed.

## Remaining acceptance and limitations

- No public deployment or URL yet; hosting access and confirmed free/credited capacity remain pending.
- Docker image builds/Compose smoke were not run because Docker is unavailable locally.
- Firefox fails before loading the app with a temporary-profile startup error; its six checks remain blocked.
- Live Nebius/Tavily and real UI-to-Kind acceptance remain pending.
- The inherited npm 11 optional-sharp clean-install issue remains; the verified setup uses `npm install`.
