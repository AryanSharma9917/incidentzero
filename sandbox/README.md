# IncidentZero Kubernetes demo lab

This local Kind lab provides a healthy `payment-api` baseline and three deterministic incidents. It does not require cloud infrastructure.

## Prerequisites

- Docker
- Kind
- kubectl with Kustomize support

If `kubectl` is not on `PATH`, set `KUBECTL_BIN` to its absolute path when running a script.

## Create or update the lab

```bash
KUBECTL_BIN=/path/to/kubectl ./sandbox/scripts/create-cluster.sh
```

This creates the `incidentzero` Kind cluster when absent, builds the local demo image, loads it into Kind, and verifies the healthy rollout.

## Reproduce incidents

```bash
KUBECTL_BIN=/path/to/kubectl ./sandbox/scripts/apply-incident.sh oomkilled
KUBECTL_BIN=/path/to/kubectl ./sandbox/scripts/apply-incident.sh crashloop
KUBECTL_BIN=/path/to/kubectl ./sandbox/scripts/apply-incident.sh readiness
```

Run the reset between scenarios:

```bash
KUBECTL_BIN=/path/to/kubectl ./sandbox/scripts/reset.sh
```

Expected evidence:

| Scenario | Kubernetes evidence |
| --- | --- |
| `oomkilled` | `CrashLoopBackOff`, previous reason `OOMKilled`, exit code 137, 64 MiB limit |
| `crashloop` | `CrashLoopBackOff` and an invalid `DATABASE_HOST` error in logs |
| `readiness` | Container remains running but unready; probe event reports HTTP 404 for `/healthz` |

The workload runs as numeric UID 10001, drops Linux capabilities, disables privilege escalation, uses a read-only root filesystem, and is isolated in the `incidentzero-demo` namespace.

## Workflow verification

The backend graph remains planning-only by default. To explicitly enable controlled application, supply a verifier when building it:

```python
from app.services.sandbox import SandboxVerifier

graph = build_diagnosis_graph(
    collector, diagnosis_agent, research_agent, remediation_agent,
    sandbox_verifier=SandboxVerifier(kubectl_binary="kubectl"),
)
```

The verifier requires the `kind-incidentzero` context, a cluster with that name and an HTTPS loopback API endpoint, and the exact `incidentzero-demo/payment-api` target. It revalidates the patch against the live Deployment, applies it with explicit context and namespace, and bounds rollout to 90 seconds by default. It checks owned pods, readiness, zero restarts/terminations, recent logs, and `/health` via a fixed non-shell request inside the ownership-verified pod, with at most three transient execution attempts. This is a point-in-time health check.

Results contain named checks and a score. Every check must pass; a high partial score is still failure. Failed verification permits one new remediation candidate with refreshed evidence and previous validation results, for a maximum of two applications. Model-output repair attempts are separately bounded to two per candidate. `validation_history` and timeline checks retain both attempts. Successful local validation ends at `verified`; the product run manager then renders an evidence-based RCA and persists the terminal result.

These operations have deterministic mocked coverage. A historical Linux acceptance used real Kind operations with mocked reasoning. Full product UI-to-provider-to-Kind acceptance and five live golden-path runs remain pending; see `docs/demo.md`. Do not describe mocked reasoning or mocked Kubernetes responses as live verification.
