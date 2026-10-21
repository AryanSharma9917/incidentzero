# Devpost submission draft

Not submitted. The copy below is ready to review; unresolved fields must remain pending until real artifacts/access exist. Reference: [official hackathon rules](https://nebiusglobalaihackathon.devpost.com/rules), checked October 17, 2026. This is a project checklist, not an eligibility determination.

## Project name

IncidentZero

## Elevator pitch

An evidence-driven Kubernetes incident engineer that uses NVIDIA Nemotron on Nebius to diagnose failures, generate a constrained patch, and validate it in a controlled sandbox for human review.

## Suggested track

Best Apps and Agents. Confirm the team's final track selection before submitting. The current integration calls Nemotron through Token Factory; it does not use Token Factory Sandboxes, so do not imply that integration.

## Inspiration

Kubernetes incidents require reconstructing evidence before choosing a safe change. We wanted to make that investigation visible and repeatable: symptoms, observations, hypotheses, focused research, a concrete patch, and named validation checks.

## What it does

IncidentZero creates controlled OOMKilled, configuration CrashLoop, and readiness incidents. It collects evidence, uses structured Nemotron reasoning, invokes Tavily only when useful, generates a policy-constrained YAML patch, and performs bounded local sandbox validation. Its operator workspace exposes the timeline, sources, diff, checks, and Markdown RCA. Production changes are not executed.

## How we built it

Python/FastAPI, typed Pydantic boundaries, LangGraph orchestration, SQLite persistence, SSE, Next.js/TypeScript/Tailwind, Nebius Token Factory/NVIDIA Nemotron, conditional Tavily, and a Kind/kubectl sandbox. Hosted infrastructure simulation is labeled separately from Kubernetes-verified fixes.

## Challenges

Handling malformed model output without unbounded repair loops; enforcing a narrow remediation contract; preserving ownership and context checks at mutation boundaries; health-check propagation timing; avoiding blocking API handling; and making simulated, mocked, and live boundaries unmistakable.

## Accomplishments

Implemented the persisted product workflow, deterministic patch policy, bounded retry loop, and controlled sandbox checks. A historical local Linux run used real Kind operations with mocked reasoning. Current regression tests and cross-browser evidence are recorded in the state of play. Do not replace that sentence with an unverified live model or stability claim.

## What we learned

A useful autonomous workflow needs reliable failure states and reviewable evidence. A passing partial score cannot override a failed health check, and an attractive UI cannot turn a simulation into live verification.

## What's next

Complete one authenticated hosted simulation check, publish the DEV.to article, confirm team fields, and submit Devpost. Later work could evaluate sustained stability; enterprise integrations remain out of this release scope.

## Built with

Python; FastAPI; Pydantic; LangGraph; SQLite; Server-Sent Events; Next.js; TypeScript; Tailwind CSS; Kubernetes; Kind; Docker; Nebius Token Factory; NVIDIA Nemotron; Tavily.

## Links and media

| Field | Value |
| --- | --- |
| Source | https://github.com/AryanSharma9917/incidentzero — public visibility confirmed |
| Public demo/test build | https://incidentzero-web.onrender.com — free hosted simulation; access code required to start runs |
| Final public video (under three minutes) | https://youtu.be/RaPNBI7qMDQ — public, verified online at 2:31 |
| DEV.to article | PENDING — `article.md` is an unpublished draft |
| Eight screenshots | `../assets/screenshots/`; visibly marked mocked rehearsal |
| Architecture | `../assets/architecture.svg`, `../assets/architecture.png` |
| License | MIT, root `LICENSE` |
| Team names, roles, representative consent | PENDING — confirm with contributors |
| Existing-project/start-date declaration | PENDING — confirm with team; Git dates alone do not establish it |
| Provider/tool feedback | PENDING — add actual live usage feedback; do not invent experiences |

## Private judging instructions

Open `https://incidentzero-web.onrender.com`. The application uses controlled infrastructure simulation with real configured Nemotron reasoning and conditional Tavily; successful hosted runs are labeled `simulated`, not Kubernetes-verified. Enter the separately supplied demo access code before creating an incident. The free service may need about a minute to wake after inactivity, history is ephemeral, and starts are limited to five per UTC day. Share no provider keys and do not publish the demo access code in this repository.

## Final review

Use `readiness.json` for unresolved gates. Inspect every asset for accurate mock/simulation labels and secrets. The final live video is published and verified under three minutes. Publish the approved article, confirm the public demo URL/access and remaining team fields, then submit through the team's Devpost account. No Devpost submission or article publication has been performed by this change set.
