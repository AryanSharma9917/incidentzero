# PR title

feat: integrate persisted incident runs and live product workspace

# PR description

Connect the existing incident-resolution graph to a persisted product workflow. Users can create a demo incident, start a background run, follow its progress, and review evidence, remediation, sandbox validation, and an RCA.

## Changes

- Add SQLite incident/run storage, restart recovery, and atomic exclusion for the shared sandbox.
- Add typed REST APIs, reconnectable SSE with durable event replay, sanitized terminal errors, and Markdown RCA export.
- Add allow-listed demo preparation in the fixed local Kind context, preserving conditional Tavily research and the existing two-attempt remediation bound.
- Build Dashboard, Incidents, Agent Runs, and detail screens with stored-history metrics, timeline, evidence, diagnosis, sources, patch diff, and validation checks.
- Update setup documentation, environment configuration, tests, and state-of-play handoff.

## Verification

- 66 backend tests passed, with provider/Kubernetes boundaries mocked.
- Four frontend domain tests and two Chrome browser smoke tests passed, including persisted reload, mobile navigation, RCA download, and terminal failure with SSE disconnected.
- Frontend lint, typecheck, and production build passed.
- Python dependency check, compileall, and Git diff checks passed.

## Remaining acceptance and limitations

- Live UI → Nebius/Nemotron → Kind acceptance and conditional Tavily credential verification remain pending. No provider quota was consumed for this change.
- Keep the API local and use one worker; public hosting and its access model belong to the deployment milestone.
- Local npm 11.19.0 `npm ci` still fails on the existing optional sharp resolution. The verified setup uses `npm install`.
