# IncidentZero — Codex Collaborator Guide

This guide lets another developer and their Codex continue the project without reconstructing prior decisions.

## First-time setup

1. Clone or pull the repository and open Codex at the repository root.
2. Ensure Codex can see the root `AGENTS.md`; it contains mandatory project instructions.
3. Ask Codex to read these files completely before editing:
   - `AGENTS.md`
   - `docs/INCIDENTZERO_STATE_OF_PLAY.md`
   - `docs/MASTER_BUILD_PLAN.md`
4. Copy `.env.example` to `.env` and add personal/hackathon credentials locally. Never send keys through chat or commit `.env`.
5. Install backend and frontend dependencies using the README.
6. Verify the current checkpoint before beginning new work.

## Continuation prompt

Paste this into the collaborator's Codex from the repository root:

```text
You are continuing IncidentZero for the Nebius x NVIDIA Global AI Hackathon 2026.

First read AGENTS.md, docs/INCIDENTZERO_STATE_OF_PLAY.md, and docs/MASTER_BUILD_PLAN.md completely. Inspect git status and the existing implementation before changing anything. Treat the state-of-play document as the canonical handoff and update it in the same change set as every code/config/infrastructure/documentation change.

Continue only the exact next incomplete milestone recorded in the state of play. Preserve the OOMKilled golden path, production-read-only safety model, ₹0 personal-spend requirement, real Nebius/Nemotron reasoning, conditional Tavily research, controlled Kubernetes sandbox writes, bounded retries, and no-fabrication rule.

Implement the smallest coherent checkpoint, add deterministic tests, run the relevant checks, update the state of play with factual results and remaining work, then stop. Do not commit, push, deploy, spend provider quota, or mutate anything outside the requested local scope without authorization. End with files changed, commands/checks, problems, next recommended step, and a Conventional Commit suggestion.
```

## Mandatory handoff behavior

Before another developer stops working, they must ensure `docs/INCIDENTZERO_STATE_OF_PLAY.md` says:

- exactly what was implemented;
- what was verified and how;
- whether provider calls were mocked or live;
- whether Kubernetes checks were rendered only or run against a cluster;
- current branch, relevant commit, and uncommitted work;
- credentials or external access still required;
- known regressions, warnings, or environment limitations;
- the exact next task and its exit criterion.

The state document is not a marketing document. Do not write “complete,” “live,” “secure,” or “verified” without evidence.

## Working in parallel

When two developers work simultaneously:

- assign non-overlapping milestones or directories;
- announce which state-of-play sections each person owns;
- do not both edit shared workflow-state or database schemas independently;
- rebase or merge before marking a checkpoint complete;
- resolve the state-of-play document semantically rather than choosing one side wholesale;
- rerun affected tests after integration;
- record both contributors' verified outcomes in one consolidated state update.

Good parallel splits later in the project include frontend presentation versus backend persistence, documentation versus tested implementation, or screenshot/video preparation versus freeze testing. Avoid parallelizing the core LangGraph state schema and its node contracts before those interfaces stabilize.

## Repository-level Codex behavior

`AGENTS.md` is the automatic repository instruction file. It deliberately stays concise and points to the two canonical documents. If Codex appears to ignore project context, explicitly mention the three files in the prompt above.

Do not create separate personal copies of the project plan. Improvements belong in `MASTER_BUILD_PLAN.md`; real progress belongs in `INCIDENTZERO_STATE_OF_PLAY.md`.
