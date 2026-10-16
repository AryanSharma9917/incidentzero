#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
KUBECTL_BIN="${KUBECTL_BIN:-kubectl}"

"$KUBECTL_BIN" delete deployment payment-api --namespace incidentzero-demo \
  --ignore-not-found --wait=true
"$KUBECTL_BIN" delete pods --namespace incidentzero-demo \
  --selector app.kubernetes.io/name=payment-api --ignore-not-found --wait=true
"$KUBECTL_BIN" apply -k "$ROOT_DIR/sandbox/base"
"$KUBECTL_BIN" rollout status deployment/payment-api \
  --namespace incidentzero-demo --timeout=90s
"$KUBECTL_BIN" get pods --namespace incidentzero-demo
