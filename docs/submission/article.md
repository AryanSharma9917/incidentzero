---
title: "IncidentZero: Building an Autonomous Kubernetes Incident Engineer with NVIDIA Nemotron and Nebius"
published: false
description: "An evidence-driven Kubernetes workflow with bounded remediation, conditional research, and honest verification boundaries."
tags: ai, kubernetes, python, opensource
---

> Draft for DEV.to. Not published. Local screenshots/video use mocked external boundaries and are labeled accordingly. Replace pending demo/video links only after they exist; do not change live-verification claims without evidence.

# IncidentZero: Building an Autonomous Kubernetes Incident Engineer with NVIDIA Nemotron and Nebius

A restarting Kubernetes pod presents an investigation problem before it presents a patching problem. The useful clues live across pod state, previous termination, current and previous logs, events, and the Deployment specification. An engineer has to connect those observations, propose a change, and decide what would count as proof that it works.

IncidentZero puts those steps into a visible, persisted workflow. The aim is an incident-resolution engineer that produces a reviewable candidate and sandbox evidence for a human operator. Production changes are not implemented or executed.

## Start with one observable failure

Our primary controlled scenario is `payment-api` allocating 96 MiB while its container limit is 64 MiB. The local lab can produce OOMKilled termination, exit code 137, and restarting pods. It also contains configuration CrashLoop and readiness-probe faults, but OOMKilled remains the reliability priority.

The scenario label is not a diagnosis shortcut. The agent receives normalized symptoms and collected evidence. A correct conclusion must account for the termination reason, exit code, and resource configuration. A concrete patch still has to survive deterministic policy checks and environment validation.

## The reasoning boundary

NVIDIA Nemotron is integrated through Nebius Token Factory's OpenAI-compatible chat-completions endpoint. Separate typed steps produce hypotheses, synthesize a final diagnosis, and generate a remediation candidate. Each response is validated. Malformed structured output gets one repair attempt, then fails clearly.

This split makes model reasoning inspectable without treating arbitrary model text as an executable program. A candidate includes a reason, affected resource, risk, expected outcome, and an actual strategic-merge YAML patch. No model-generated command is passed to a shell.

Our API and graph tests mock provider responses. Live provider connectivity and the final live end-to-end run remain pending. We are documenting that gap rather than presenting deterministic test output as a successful inference call.

## Research is a decision, not a decoration

Tavily runs only when diagnosis requests research. The no-research branch makes no search calls. Research is limited to three focused questions and three compact results per query. Sources are deduplicated across queries and retain their titles, URLs, excerpts, and relevance explanations.

Final synthesis can cite only URLs that were actually supplied by research. Unsupported citations get one repair attempt. The point is attributable technical evidence, not a large scraped-page corpus or a search panel that always runs for visual effect.

## A patch needs a policy boundary

The deterministic policy permits one narrowly defined change domain: memory resources, the existing `DATABASE_HOST`, or readiness HTTP settings. It checks exact Deployment/container identity, safe YAML structure, and semantic constraints. Images, commands, replicas, secrets, security settings, and unrelated fields are rejected.

The graph permits two remediation attempts. If validation fails, refreshed evidence and prior named checks inform the next candidate. Exhaustion becomes a terminal failure with saved evidence. A high partial score is still failure when any named check fails.

## Verification and its limits

Local execution targets only the fixed Kind demo namespace and service. It checks the loopback Kind context, revalidates the live Deployment, applies the policy-approved candidate, waits for rollout, follows pod ownership, and inspects readiness, restarts, termination, recent logs, and HTTP health. Commands use fixed arrays and bounded deadlines.

An earlier Linux acceptance exercised those real Kubernetes operations with mocked reasoning and passed. That is useful evidence of the cluster boundary, but it is not evidence of live model reasoning or five consecutive golden-path runs. Health is also a point-in-time measurement, not a soak test.

For hosting without Kubernetes, an explicit simulation mode derives marked evidence from manifests and evaluates configuration. Its terminal status is `simulated`; it cannot increment the Kubernetes-verified fixes metric. Real provider calls are still required when the product presents reasoning as live.

## A product experience around the agent

FastAPI starts runs in background worker loops and persists state in SQLite. A transaction permits one active run in the shared sandbox. SSE replays durable event IDs, with periodic REST reads as a fallback. Restart recovery marks interrupted work failed when the database survives.

The Next.js workspace exposes incident details, timeline, evidence, diagnosis, conditional sources, diff, checks, and an RCA download. Metrics come only from stored demo history. A second API process cannot silently take over another process's database lease.

## What we learned

The useful engineering boundaries were more important than extra integrations. Kubernetes Service-proxy propagation caused an earlier health-check race; the verifier now uses a fixed in-pod request after ownership checks, with bounded retries. Python 3.12 executor-path stalls required async graph routing. These fixes are recorded in the repository handoff with their verification scope.

A demo also needs to communicate what really ran. Hosted simulation, mocked browser capture, and real local verification are separate categories. Our rehearsal screenshots have a visible mock label. They are review material, not invented customer results or production metrics.

## Current status and next steps

The implementation includes deterministic tests and Chromium/WebKit browser checks. Docker runtime verification, live provider-to-Kind acceptance, and five recorded successful OOM runs are complete. A free public hosted simulation is available at `https://incidentzero-web.onrender.com`; its infrastructure boundary is explicitly simulated, and one authenticated hosted workflow check remains pending.

Source: [IncidentZero on GitHub](https://github.com/AryanSharma9917/incidentzero). Public demo: [incidentzero-web.onrender.com](https://incidentzero-web.onrender.com). Final live video: [YouTube](https://youtu.be/RaPNBI7qMDQ). The project is licensed under MIT.

The next step is to complete those real boundaries, preserve the evidence, and publish a demo that makes the verification scope visible. The internal feature-complete target is October 25, 2026.
