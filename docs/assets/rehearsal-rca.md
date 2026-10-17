> MOCKED UI REHEARSAL: all model, search, and Kubernetes evidence below is fixture output, not live acceptance.

# RCA: Payment API pods are repeatedly restarting

Incident: 1c5fee1e-0ddc-4cd9-a553-3089fcb2c439
Service: payment-api
Severity: P1
Environment: demo

## Execution mode
Local Kubernetes sandbox.

## Impact
Controlled demo incident. Production impact was not measured.

## Root cause
The payment-api container exceeded its 64Mi memory limit.

## Evidence
- The container was terminated as OOMKilled with exit code 137.
- Kubernetes enforces container memory limits with OOM termination. (https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)

## Timeline
- intake: Incident normalized
- context: Collected evidence from 1 pod(s)
- diagnosis: Generated 1 evidence-backed hypothesis(es)
- research: Collected 1 unique source(s)
- synthesis: Produced final evidence-grounded diagnosis
- remediation: Generated and policy-validated a reviewable patch candidate
- validation.started: Validation attempt 1
- validation.check: sandbox-target: Only incidentzero-demo/payment-api permits writes.
- validation.check: sandbox-context: Require the named Kind context and a loopback API server.
- validation.check: deployment-identity: Require the exact live Deployment identity and UID.
- validation.check: patch-policy: Revalidate candidate against the live Deployment.
- validation.check: sandbox-apply: Applied the policy-approved strategic-merge patch.
- validation.check: rollout: Deployment rollout completed within the deadline.
- validation.check: pod-health: Owned pod evidence: [{"pod": "payment-api-new", "phase": "Running", "containers": [{"name": "payment-api", "ready": true, "state": "running", "restarts": 0, "termination": null, "exit_code": null}]}]
- validation.check: recent-logs: Recent logs inspected for fatal application errors.
- validation.check: http-health: The replacement pod /health must return status ok.
- validation.completed: Attempt 1: score 100/100

## Resolution
Increase the payment-api container memory limit.
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-api
  namespace: incidentzero-demo
spec:
  template:
    spec:
      containers:
        - name: payment-api
          resources:
            limits:
              memory: 128Mi
```

## Validation
Verified in the controlled sandbox.
- Attempt 1: 100/100; PASS

## Preventive actions
Review workload configuration and add a regression check for the observed failure before production rollout.

Human approval is required before any production change. No production changes were applied.
