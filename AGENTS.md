# IncidentZero repository instructions

These instructions apply to every file in this repository.

## Mandatory startup

Before planning or changing code:

1. Read `docs/INCIDENTZERO_STATE_OF_PLAY.md` completely.
2. Read `docs/MASTER_BUILD_PLAN.md` completely.
3. Read the relevant source, tests, and documentation for the current milestone.
4. Confirm `git status --short --branch` and preserve unrelated work.
5. Work on only the next incomplete milestone unless the user explicitly changes scope.

The internal feature-complete deadline is October 25, 2026. October 30 is not the engineering deadline.

## Product invariants

- Preserve the reliable OOMKilled golden path above optional functionality.
- Nebius Token Factory and NVIDIA Nemotron must perform real reasoning; never disguise hard-coded diagnoses as model output.
- Tavily is a conditional runtime research tool, not an unconditional call on every run.
- Production and demo-production Kubernetes contexts are read-only.
- Writes are allowed only in a controlled sandbox through allow-listed operations.
- Never execute arbitrary LLM-generated shell commands or use `shell=True` with generated input.
- Keep remediation iterations bounded to two or three.
- Keep the project usable without personal spending.
- Do not add excluded enterprise integrations or optional scope unless required work is complete and the user requests them.
- Never fabricate live results, sources, metrics, customers, success rates, or test outcomes.

## Engineering workflow

- Follow the phase order in `docs/MASTER_BUILD_PLAN.md`.
- Make the smallest coherent change that reaches a verifiable checkpoint.
- Use typed models at external and workflow boundaries.
- Add or update deterministic tests for each behavior.
- Run relevant tests, lint, type checks, builds, and real sandbox checks when available.
- Do not commit, push, deploy, publish, or spend provider quota unless requested or clearly authorized.
- Use Conventional Commits when recommending or creating commits.

## Mandatory state-of-play update

Every change to code, configuration, infrastructure, tests, or project documentation must include an update to `docs/INCIDENTZERO_STATE_OF_PLAY.md` in the same change set.

At minimum, update:

- `Last updated`
- `Current checkpoint`
- completed work and verification evidence
- current Git/worktree state when known
- known problems or environmental constraints
- the exact next recommended task
- the change log

Do not mark work complete unless it was actually verified. Clearly label mocked tests, local live tests, simulations, and unverified credential-dependent behavior.

## Handoff

End each milestone with:

- files created and changed
- commands and checks run
- pass/fail outcomes
- remaining problems
- next recommended step
- recommended Conventional Commit message

See `docs/CODEX_COLLABORATOR_GUIDE.md` for collaborator setup and a ready-to-use continuation prompt.
