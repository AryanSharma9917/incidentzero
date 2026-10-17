# Safety and operating limits

IncidentZero is a controlled demonstration of evidence-driven incident resolution. Production and demo-production Kubernetes contexts are read-only. There is no production apply endpoint, production approval engine, or enterprise authentication system.

## Kubernetes writes

The product's writable target is fixed to `kind-incidentzero`, `incidentzero-demo/payment-api`. The verifier checks the named context/cluster and an HTTPS loopback API endpoint. It revalidates the live Deployment identity and UID and checks the candidate against freshly collected configuration before applying. Pod inspection follows Deployment → ReplicaSet → Pod ownership.

Commands are fixed argument arrays, with `shell=False`, request deadlines, subprocess timeouts, and bounded rollout/health retries. Model output never selects an executable or becomes a shell command. Demo preparation takes only a three-value scenario enum and trusted repository manifest paths; it waits for previous pods to disappear and new fault evidence to appear.

The local lab shell scripts are developer tools. Their kubectl context must be explicitly selected/checked by the operator; they are not public API endpoints. The acceptance recorder uses the fixed-context verifier for reset rather than invoking an ambient-context shell reset.

## Remediation policy

Candidates are strict typed models. YAML must be a single safely parsed mapping without duplicate keys. Only the collected `apps/v1 Deployment`, namespace, known container, and required pod-template shape are accepted. One candidate may modify exactly one domain:

- Memory requests/limits: recognized Ki/Mi/Gi quantities; limit must increase, optional request cannot exceed it.
- The existing `DATABASE_HOST` value.
- A readiness HTTP path and optional port.

Images, commands, replicas, namespace changes, labels, selectors, secrets, volumes, service accounts, and security settings are forbidden. A policy pass is necessary but is not proof that a patch resolves the fault. All named environment checks must pass; a high partial score remains failure.

## Bounded execution and failure

The graph allows two remediation attempts; failure evidence feeds the second candidate. Structured model parsing allows one repair attempt per response. Clients have network timeouts. Kubernetes operations and health execution are bounded. Unexpected errors become sanitized terminal failures with saved partial evidence where storage works.

The run manager waits for bounded worker operations during orderly shutdown. Hosts may still kill a process before it finishes; SQLite recovery cannot recover history from a discarded ephemeral disk. The 600-second async graph deadline cannot preempt a synchronous command; individual subprocess deadlines provide the corresponding bound.

## Public demo controls

Public production configuration accepts only simulation mode, exact HTTPS CORS origins, and HTTPS provider endpoints without credentials in URLs. Writes default to paused. Enabled production mutations require a sufficiently long access code, compared in constant time, on both incident creation and run start. The UI stores the operator code only in tab-scoped session storage and never places it in SSE/report URLs. CORS alone is not authorization.

Daily accepted starts are counted transactionally, including failed runs. This count is a demo guard, not a billing cap: it resets with ephemeral storage and does not measure token consumption. Keep provider-side quotas and pause runs outside deliberate demonstrations. Never paste keys into the browser, repository, article, screenshot, or submission description. Judges' demo access instructions belong in the private testing field.

## Evidence and communication

Nemotron reasoning must be a real provider request when presented as live. Conditional Tavily sources retain their supplied URLs; synthesis rejects unsupported URLs. Cluster logs, provider text, and research excerpts are untrusted evidence, not instructions to execute. Claims from model output must still be reviewed by the operator.

Hosted simulation has an explicit `simulated` terminal state and cannot increment Kubernetes-verified metrics. Rehearsal screenshots/video have a visible mock banner and separate provenance manifest. Neither simulation nor mocks satisfy live golden-path acceptance. Do not publish a five-run success rate until those runs exist.

Structured logs contain timestamp, incident/run IDs, stage, event, elapsed duration, and status. They deliberately exclude workflow payloads, prompts, raw exceptions, authorization headers, and credentials. Controlled demo manifests contain no secrets; arbitrary production log collection is outside this release scope.

## Residual limits

Health verification is point-in-time. No sustained stability claim, multi-cluster support, authentication/RBAC guarantee, cloud permission automation, or real production impact measurement is implemented. Keep one API instance/database for the shared sandbox. Before production use, access control, resource policy bounds, sensitive-evidence handling, observability, and threat modeling need a separate engineering review.
