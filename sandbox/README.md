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
